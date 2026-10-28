FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY gateway ./gateway
COPY web ./web
COPY server.py ./
COPY scripts ./scripts

# Non-root user; the data volume is the only writable path.
RUN useradd --create-home --uid 10001 gateway && mkdir -p /app/data && chown gateway /app/data
USER gateway

ENV GATEWAY_DATA_DIR=/app/data GATEWAY_PANEL_HOST=0.0.0.0
EXPOSE 8600
HEALTHCHECK --interval=15s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8600/api/health')"

CMD ["python", "-m", "uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8600"]
