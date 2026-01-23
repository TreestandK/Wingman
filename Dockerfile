FROM python:3.11-alpine

LABEL maintainer="Wingman Project"
LABEL description="Wingman Game Server Manager - Web GUI for automated game server deployments"

# Install system dependencies and build dependencies for Python packages
RUN apk add --no-cache \
    # Runtime dependencies
    curl \
    bind-tools \
    netcat-openbsd \
    jq \
    ca-certificates \
    tzdata \
    # Required for cryptography, bcrypt, python3-saml
    libffi \
    openssl \
    libxml2 \
    libxslt \
    xmlsec \
    && \
    # Build dependencies (needed for pip install, removed after)
    apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev \
    libxml2-dev \
    libxslt-dev \
    xmlsec-dev \
    cargo \
    rust

# Create application directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    # Remove build dependencies to reduce image size
    apk del .build-deps

# Copy application files
COPY app.py .
COPY deployment_manager.py .
COPY auth.py .
COPY models.py .
COPY security.py .
COPY oidc.py .
COPY rbac.py .
COPY errors.py .
COPY create_admin.py .
COPY migrate_to_sqlite.py .

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
