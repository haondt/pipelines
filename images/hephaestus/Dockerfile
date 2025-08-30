FROM python:3.12-slim-bookworm

RUN apt update && apt install -y \
    git \
    wget \
    tar

ARG YQ_VERSION=v4.34.2
ARG YQ_BINARY=yq_linux_amd64
RUN wget https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/${YQ_BINARY}.tar.gz -O - |\
  tar xz && mv ${YQ_BINARY} /usr/local/bin/yq

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
