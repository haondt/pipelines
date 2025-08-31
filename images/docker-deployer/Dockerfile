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

ARG KUBECTL_VERSION=v1.34.0
RUN curl -sSL -o /usr/local/bin/kubectl https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl \
  && chmod +x /usr/local/bin/kubectl

ARG KAPP_VERSION=v0.64.2
RUN curl -sSL https://github.com/carvel-dev/kapp/releases/download/${KAPP_VERSION}/kapp-linux-amd64 \
  -o /usr/local/bin/kapp \
  && chmod +x /usr/local/bin/kapp

RUN pip install --upgrade pip
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /build
RUN git config --global --add safe.directory /build

