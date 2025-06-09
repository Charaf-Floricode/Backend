FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        fonts-liberation \
    && which chromedriver || true && ls -lR /usr | grep chromedriver || true \
    && rm -rf /var/lib/apt/lists/*


ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    CHROME_BIN=/usr/lib/chromium/chromium



# Symlink the Chrome binary to a name expected by Selenium (if needed)
RUN ln -s /usr/bin/chromium /usr/bin/google-chrome

# 4) Create & switch to the app directory
WORKDIR /app

# 5) Copy your dependency file and install Python libs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6) Copy the rest of your code
COPY . .

# 7) Expose the port your FastAPI app will listen on
EXPOSE 10000

# 8) Default CMD to run your app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
