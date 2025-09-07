# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 시스템 의존성: 빌드 및 런타임에 필요한 패키지
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       ca-certificates \
       curl \
    && rm -rf /var/lib/apt/lists/*

## uv 설치 및 의존성 설치 (uv.lock 고정 버전 사용)
# uv 설치
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && echo "uv installed at: $(/root/.local/bin/uv --version)"

# uv 바이너리 경로 등록
ENV PATH="/root/.local/bin:${PATH}"

# 잠금파일과 메타만 먼저 복사해 캐시 최적화
COPY pyproject.toml uv.lock ./

# 시스템 파이썬 환경에 의존성 설치 (uv.lock 준수)
# - uv.lock을 기반으로 requirements를 export한 뒤, 시스템 환경에 설치
RUN uv export --frozen --no-dev --format requirements-txt > requirements.txt \
    && uv pip install --system --requirements requirements.txt

COPY ./src ./src

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "bot.main"]


