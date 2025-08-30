FROM python:3.12-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y \
    git \
    rsync \
    curl \
    make \
    wget \
    tar \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ARG YQ_VERSION=v4.34.2
ARG YQ_BINARY=yq_linux_amd64
RUN wget https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/${YQ_BINARY}.tar.gz -O - |\
  tar xz && mv ${YQ_BINARY} /usr/local/bin/yq

RUN pip install --upgrade pip
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /build
RUN git config --global --add safe.directory /build
