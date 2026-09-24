# Linux container, so Windows Smart App Control doesn't block scipy's DLLs.
FROM python:3.12-slim

WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY spamfilter spamfilter
COPY app app
COPY frontend frontend
COPY train.py .
COPY models models

EXPOSE 8000
# Render (and similar hosts) pass the port in $PORT; fall back to 8000 locally.
CMD ["sh", "-c", "fastapi run app/main.py --host 0.0.0.0 --port ${PORT:-8000}"]
