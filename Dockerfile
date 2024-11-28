FROM alpine
RUN apk add --update --no-cache  python3
WORKDIR /opt
RUN git clone https://github.com/eddiebrissow/simple_mongo_proxy.git
WORKDIR /opt/simple_mongo_proxy
ENTRYPOINT ["python3 proxy.py"]