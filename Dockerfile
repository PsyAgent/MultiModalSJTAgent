FROM ubuntu:22.04

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

# 配置 apt 重试和超时
RUN echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::https::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries

RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-dev \
    python3-pip \
    gcc \
    g++ \
    git \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgl1-mesa-glx \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.12 /usr/bin/python

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_SYSTEM_PYTHON=1

COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-cache

COPY . .

RUN mkdir -p outputs

EXPOSE 4399

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "python", "app.py"]
