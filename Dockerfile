# Use official Python image
FROM python:3.11

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy everything to container
COPY . .

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for web service (needed by Railway)
EXPOSE 10000

# Start the Twitter bot
CMD ["python", "-u", "remote.py"]
