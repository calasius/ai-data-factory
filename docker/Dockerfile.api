FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential ca-certificates unzip && \
    rm -rf /var/lib/apt/lists/*

# opencode CLI — the generation engine. Pinned for reproducible deploys.
ENV OPENCODE_VERSION=1.14.31
RUN curl -fsSL https://opencode.ai/install | VERSION="${OPENCODE_VERSION}" bash
ENV PATH="/root/.opencode/bin:/root/.local/bin:$PATH"

# uv for the generators that the coding agent builds and runs
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Python deps
RUN pip install --no-cache-dir \
    fastapi 'uvicorn[standard]' sqlalchemy alembic asyncpg psycopg2-binary \
    redis pydantic pydantic-settings httpx aiofiles pyyaml \
    python-multipart python-dotenv \
    'openai>=1.54.0' 'pandas>=2.0.0' 'scipy>=1.11.0' && \
    pip install --no-cache-dir --pre 'opencode-ai>=0.1.0a36'

# git identity for tooling that shells out to git
RUN git config --global user.email "factory@ai-data-factory" && \
    git config --global user.name "Data Factory"

COPY api ./api
COPY tools ./tools
COPY .claude ./.claude

# App-owned opencode config (DeepSeek provider). Self-contained — no host mounts.
ENV OPENCODE_CONFIG=/app/api/opencode.json

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
