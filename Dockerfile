# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies for Oracle and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unzip \
    libaio1 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Oracle Instant Client
RUN mkdir -p /opt/oracle && \
    cd /opt/oracle && \
    wget https://download.oracle.com/otn_software/linux/instantclient/214000/instantclient-basic-linux.x64-21.4.0.0.0dbru.zip && \
    wget https://download.oracle.com/otn_software/linux/instantclient/214000/instantclient-sdk-linux.x64-21.4.0.0.0dbru.zip && \
    unzip instantclient-basic-linux.x64-21.4.0.0.0dbru.zip && \
    unzip instantclient-sdk-linux.x64-21.4.0.0.0dbru.zip && \
    rm -f instantclient-basic-linux.x64-21.4.0.0.0dbru.zip instantclient-sdk-linux.x64-21.4.0.0.0dbru.zip

# Set Oracle environment variables
ENV ORACLE_HOME=/opt/oracle/instantclient_21_4
ENV LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
ENV PATH=$ORACLE_HOME:$PATH

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs /app/documents

# Copy application code
COPY ./app /app/app
COPY ./database /app/database
COPY ./documents /app/documents

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]