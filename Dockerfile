# Use a lightweight official Python image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy only requirements first (for better build caching)
COPY requirements.txt .

# Install dependencies (Telethon, Flask, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .

# Expose port for Render web service
EXPOSE 10000

# Default command to start the bot
CMD ["python", "-u", "raid.py"]
