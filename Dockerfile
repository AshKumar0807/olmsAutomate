# Use official Python 3.13 slim image
FROM python:3.13-slim

# Install Chromium dependencies and build tools
RUN apt-get update && apt-get install -y \
    curl gnupg unzip wget ca-certificates \
    fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 \
    libnspr4 libnss3 libx11-xcb1 libxcomposite1 \
    libxdamage1 libxrandr2 xdg-utils libu2f-udev \
    libgbm1 libxshmfence1 libxss1 libxtst6 lsb-release \
    chromium chromium-driver \
    pkg-config default-libmysqlclient-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy your app files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000
EXPOSE 5000

# Start the app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
