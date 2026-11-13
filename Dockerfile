# Stage 1: Build stage
# Pinned to python:3.12.6-slim for reproducible, auditable builds.
# To update: docker buildx imagetools inspect python:3.12-slim | grep Digest
FROM python:3.12.6-slim@sha256:ad48727987b259854d52241fac3bc633574364867b8e20aec305e6e7f4028b26 AS builder

WORKDIR /build

# TODO Missing OS Security Updates
# Install build tools if compilation is needed for wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and source files needed for build
COPY pyproject.toml README.md ./
COPY ctfvigil ./ctfvigil

# Build wheel and pre-fetch dependency wheels
RUN pip install --no-cache-dir --upgrade pip build && \
    python -m build --wheel --outdir /build/dist && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels /build/dist/*.whl

# Stage 2: Final runtime stage
FROM python:3.12.6-slim@sha256:ad48727987b259854d52241fac3bc633574364867b8e20aec305e6e7f4028b26 AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:${PATH}"

# Create non-root system user and group
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -s /bin/bash appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Copy pre-built wheels from builder stage with proper appuser ownership
COPY --from=builder --chown=appuser:appuser /build/wheels /tmp/wheels

# Install wheels as non-root user and remove temporary wheels folder
USER appuser
RUN pip install --no-cache-dir --user /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels

# Copy application files
COPY --chown=appuser:appuser bot.py ./
COPY --chown=appuser:appuser ctfvigil ./ctfvigil
COPY --chown=appuser:appuser tasks ./tasks

# Health: verify the Python runtime and installed packages are importable
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import ctfvigil; import discord; import celery" || exit 1

CMD ["python", "bot.py"]
