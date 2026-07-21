FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget \
    && rm -rf /var/lib/apt/lists/*

# TA-Lib C library (optional — quant_engine has pure-numpy fallbacks)
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib && ./configure --prefix=/usr && make && make install \
    && cd .. && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz \
    || true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir $(grep -v 'TA-Lib' requirements.txt)

COPY app ./app
COPY .env.example .env

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--http", "httptools", "--ws", "websockets"]
