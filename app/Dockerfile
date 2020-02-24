FROM balenalib/rpi-python:3.7.6-latest

RUN mkdir /workspace
RUN mkdir /workspace/app
RUN mkdir /workspace/data
RUN mkdir /workspace/out

RUN apt-get update && apt-get upgrade -y

RUN apt-get install -y \
    build-essential \
    wget \
    curl \
    git \
    g++ \
    libatlas-base-dev \
    libcurl4-openssl-dev \
    libboost-python1.62.0 \
    libwebp-dev \
    ibgstreamer1.0-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms1-dev \
    libopenjp2-7-dev \
    libtiff5 \
    vim \
    htop

RUN pip install -U pip && \
    pip install pipenv

# install for PIL(pillow)
RUN apt-get install \
    libjpeg8-dev libpng-dev libfreetype6-dev

RUN apt-get install libxml2 libxml2-dev libxslt1-dev python3-lxml

RUN pip install async-timeout==3.0.1
RUN cd /workspace && git clone https://fengding2:1a4d3ad89c947e4d5db29fa9e8cdf33e7c27a40f@github.com/WeConnect/eventcollector-python.git
RUN cd /workspace/eventcollector-python && python3 setup.py install

WORKDIR /workspace/app
COPY . /workspace/app

RUN pipenv lock --requirements > requirements.txt
RUN pip install -r /workspace/app/requirements.txt

VOLUME ["/workspace/data", "/workspace/out"]
EXPOSE 8000

CMD ["python", "app_server.py"]