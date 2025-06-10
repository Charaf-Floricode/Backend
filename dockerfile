
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium fonts-liberation && \
    rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/lib/chromium/chromium  
ENV LOG_LEVEL=DEBUG

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt    

COPY . .

EXPOSE 10000
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","10000"]
