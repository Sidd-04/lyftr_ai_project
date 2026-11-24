# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir --user -r requirements.txt; \
    elif [ -f backend/requirements.txt ]; then \
        pip install --no-cache-dir --user -r backend/requirements.txt; \
    fi

# Stage 2: Minimal runtime image
FROM python:3.12-slim

WORKDIR /workspace

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV LITELLM_LOCAL_MODEL_COST_MAP=True

# Copy files
COPY . .

# Setup application directory structure
RUN if [ -d "backend/app" ]; then \
        cp -r backend/app ./app; \
    fi

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
