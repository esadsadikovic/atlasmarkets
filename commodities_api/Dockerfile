FROM python:3.12-slim

WORKDIR /app

RUN pip install --upgrade pip && pip install "x402[evm]>=2.16.0" httpx

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8004

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]