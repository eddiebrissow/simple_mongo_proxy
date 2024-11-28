import asyncio
import logging
import hashlib
import pickle
import atexit
import os

MONGO_SERVER_HOST = os.environ["MONGO_SERVER_HOST"]

MONGO_SERVER_PORT = int(os.environ["MONGO_SERVER_PORT"])
CACHE_FOLDER = os.environ["CACHE_FOLDER"]) or "."


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

cache = {}


def save_cache():
    print("Saving Cache")
    with open(f'{CACHE_FOLDER}/cachebin', 'wb') as f:
        pickle.dump(cache, f)


def cache_key(query):
    """Generate a cache key based on the query data."""
    query_hash = hashlib.sha256(pickle.dumps(query)).hexdigest()
    return query_hash

def get_query_hash(data):
    index = None
    try:
        index = data.index(b'id')
        return cache_key(data[12:index])
    except:
        return cache_key(data[12:])


async def forward_authentication(reader, writer, mongo_reader, mongo_writer):
    """
    Forward the authentication commands from the client to MongoDB.
    """
    while True:
        data = await reader.read(1024)
        if not data:
            break  
        query_hash = get_query_hash(data)
        if cache.get(query_hash):
            logger.info(f"Reply cached response for query {query_hash}")
            writer.write(cache[query_hash])
        else:
            mongo_writer.write(data)
            await mongo_writer.drain()

            mongo_response = await mongo_reader.read(1024)
            # if b'saslStart' in mongo_response or b'saslContinue' in mongo_response:
            # TODO change to mongo's query
            if b'find' in data:
                cache[query_hash] = mongo_response
                logger.info(f"Cached response for query {query_hash}")
                exit_handler()
                
                
        
            writer.write(mongo_response)
        await writer.drain()


async def handle_client(reader, writer):
    """Handles the client connection and forwards requests to MongoDB server."""
    
    try:
        mongo_reader, mongo_writer = await asyncio.open_connection(MONGO_SERVER_HOST, MONGO_SERVER_PORT)
        logger.info("Connected to MongoDB server.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB server: {e}")
        writer.close()
        await writer.wait_closed()
        return
    
    await forward_authentication(reader, writer, mongo_reader, mongo_writer)
    
    while True:
        data = await reader.read(1024)
        if not data:
            logger.info("No data received from client, closing connection.")
            break


        mongo_writer.write(data)
        await mongo_writer.drain()

        mongo_response = await mongo_reader.read(1024)

        if not (b'saslStart' in mongo_response or b'saslContinue' in mongo_response):
            query_hash = cache_key(data)
            cache[query_hash] = mongo_response
            logger.info(f"Cached response for query {query_hash}")

        writer.write(mongo_response)
        await writer.drain()

    writer.close()
    await writer.wait_closed()
    mongo_writer.close()
    await mongo_writer.wait_closed()
    logger.info("Connections closed.")

async def start_proxy(host='localhost', port=5000):
    """Starts the TCP proxy server."""
    server = await asyncio.start_server(handle_client, host, port)
    addr = server.sockets[0].getsockname()
    logger.info(f"MongoDB proxy running on {addr}")
    
    async with server:
        await server.serve_forever()




def load_cache():
    global cache
    print("Loading Cache")
    try:
        with open('cachebin', 'rb') as f:
            cache = pickle.load(f)
            print(f"Loaded {len(cache)} cache entries")
    except:
        print("Failed to load cache")


if __name__ == '__main__':
    load_cache()
    atexit.register(save_cache)
    asyncio.run(start_proxy())

