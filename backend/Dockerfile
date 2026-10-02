FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv

WORKDIR /srv

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# O pacote é `backend.app`, então o contexto precisa preservar a hierarquia.
COPY app ./backend/app

EXPOSE 8010

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request, os, sys; \
url='http://127.0.0.1:'+os.getenv('PORT','8010')+'/health'; \
sys.exit(0 if urllib.request.urlopen(url, timeout=3).status==200 else 1)"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8010"]