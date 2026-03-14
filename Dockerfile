# ---------- Builder Stage ----------
FROM public.ecr.aws/docker/library/python:3.12-slim \
    AS builder
# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# Install Python dependencies into a local directory
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Runtime Stage ----------
FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app
# Install only runtime libraries needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
# Copy installed packages from builder
COPY --from=builder /install /usr/local
# Copy application code
COPY . .

EXPOSE 3001
CMD ["python", "run.py"]
