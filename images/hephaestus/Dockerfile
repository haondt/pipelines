FROM python:3.12-slim-bookworm

RUN apt update && apt install -y git yq

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
