# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Blokada przed trzymaniem spacji w pip i outputach systemowych  
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Narzędzia PDFPlumber
RUN apt-get update && apt-get install -y \
    libpoppler-cpp-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY v2/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pobranie roota środowiska wykonawczego PWr
COPY v2/ .

# Logi preinincjalizacyjne
RUN mkdir -p logs data

# Konfiguracja portu i start serwera
EXPOSE 5000
# Używamy formy powłokowej, aby wspierać zmienną środowiskową $PORT (Render/Heroku)
CMD gunicorn -b 0.0.0.0:${PORT:-5000} app:app
