FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install only what's needed for SQLite and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libtiff-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libwebp-dev \
    tcl8.6-dev \
    tk8.6-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy the rest of the project
COPY . .

# Create database directory with proper permissions
RUN mkdir -p /app/db && chmod 777 /app/db

# Expose app port
EXPOSE 5000

# Start app with more workers now that WebSocket is disabled
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "--workers", "4", "--worker-class", "sync", "--max-requests", "1000", "--max-requests-jitter", "100", "wsgi:application"]