FROM python:3.15-slim-trixie

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y git

RUN apt-get clean
RUN pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=oven/bun:1.4.4 /usr/local/bin/bun /usr/local/bin/bun
RUN ln -s /usr/local/bin/bun /usr/local/bin/node
ENV BUN_INSTALL=/usr/local
RUN bun install -g wrangler

WORKDIR /build

RUN git config --global --add safe.directory /build
