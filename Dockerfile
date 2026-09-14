FROM python:3.12.4-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir \
    torch==2.12.1 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]