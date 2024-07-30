# ref:  https://fastapi.tiangolo.com/deployment/docker/#docker-image-with-poetry
FROM python:3.10

RUN apt-get -y update && apt-get install -y --no-install-recommends \
    g++ \
    make \
    cmake \
    wget \
    nginx \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python & \
    ln -s /usr/bin/pip3 /usr/bin/pip

ENV PATH="/opt/program:${PATH}"
ENV BASE_DIR="/opt/"
ENV PYTHONPATH="/opt/"

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./opt/ /opt/

RUN chmod 755 /opt/program/serve
RUN chmod 755 /opt/program/train




EXPOSE 8080