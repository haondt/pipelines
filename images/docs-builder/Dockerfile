FROM python:3.15-slim-trixie

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y git

RUN apt-get clean
RUN pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /build

RUN git config --global --add safe.directory /build
