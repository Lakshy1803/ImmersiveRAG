FROM python:3.11.14-slim

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire backend source
COPY . /app/backend

WORKDIR /app/backend

# Replicate the exact install flow:
#   rm -rf .venv && python3 -m venv .venv && source .venv/bin/activate && pip install -e "backend[dev]"
# Inside Docker we don't need a venv (the container IS the isolation),
# so we just run the equivalent pip install directly.
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# Create data directories expected by the app
RUN mkdir -p /app/backend/data/uploads /app/backend/data/qdrant

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')"

# Start the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
