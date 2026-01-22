FROM python:alpine

LABEL maintainer="Wingman Project"
LABEL description="Wingman Game Server Manager - Web GUI for automated game server deployments"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    dnsutils \
    netcat-openbsd \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY deployment_manager.py .
COPY auth.py .
COPY rbac.py .
COPY errors.py .
COPY create_admin.py .
COPY test_auth.py .

# Create directories
RUN mkdir -p /app/data /app/logs /app/templates/saved /app/templates/html /app/static

# Copy HTML templates and static files
COPY templates/ /app/templates/
COPY static/ /app/static/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["python", "app.py"]
