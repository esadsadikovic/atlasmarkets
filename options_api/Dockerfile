FROM python:3.12-slim
WORKDIR /app
RUN pip install --upgrade pip && pip install "x402[evm]>=2.16.0" fastapi uvicorn httpx jsonschema requests
COPY . .
ENV PYTHONUNBUFFERED=1
ENV PORT=10000
EXPOSE 10000
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}