FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium fonts-liberation wget unzip ca-certificates && \

    CHROME_MAJOR=$(chromium --version | awk '{print $2}' | cut -d'.' -f1) && \
    wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_MAJOR}.0.0/linux64/chromedriver-linux64.zip" \
        -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/lib/chromium/chromium \
    CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","${PORT:-10000}"]
