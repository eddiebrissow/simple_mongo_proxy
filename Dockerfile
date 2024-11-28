FROM alpine
RUN apk add --update --no-cache python3 git bash
RUN ln -sf /usr/bin/python3 /usr/bin/python
RUN /usr/bin/python -m ensurepip
WORKDIR /opt
RUN git clone https://github.com/eddiebrissow/simple_mongo_proxy.git
WORKDIR /opt/simple_mongo_proxy
ENTRYPOINT ["python3 proxy.py"]