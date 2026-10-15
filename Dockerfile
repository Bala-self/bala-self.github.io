FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && python -m playwright install --with-deps chromium && chmod -R a+rX /opt/playwright && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 10001 --create-home pocket
COPY --chown=pocket:pocket app.py seo.py ./
COPY --chown=pocket:pocket content ./content
COPY --chown=pocket:pocket static ./static
USER pocket
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--no-proxy-headers"]
