FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY llama_app.py .
RUN pip3 install --no-cache-dir -r requirements.txt
CMD ["python", "llama_app.py"]
