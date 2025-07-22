FROM python:3.11-slim
WORKDIR /app
COPY ./src/requirements.txt /app/
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
COPY ./src /app 