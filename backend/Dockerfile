FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN mkdir -p /app/data && chmod -R 777 /app/data
RUN mkdir -p /downloads && chmod -R 777 /downloads

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/backend

VOLUME ["/downloads"]

EXPOSE 8000
