FROM python:3.12-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y \
    git \
    rsync \
    curl \
    ca-certificates \
    gpg \
    nodejs \
    npm

RUN npm install -g cdk8s-cli

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /build
RUN git config --global --add safe.directory /build

