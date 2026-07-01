FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir flask requests

CMD ["python", "load_balancer.py"]