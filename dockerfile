# 1) Start from a slim Python base
FROM python:3.10-slim

# 2) Install system deps including Chromium & its driver
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      chromium chromium-driver \
 && rm -rf /var/lib/apt/lists/*

# 3) Tell Selenium where Chrome lives
ENV CHROME_BIN=/usr/bin/chromium

# 4) Create & switch to the app directory
WORKDIR /app

# 5) Copy your dependency file and install Python libs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6) Copy the rest of your code
COPY . .

# 7) Expose the port your FastAPI app will listen on
EXPOSE 8000

# 8) Default CMD to run your app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
