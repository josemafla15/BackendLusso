FROM mcr.microsoft.com/playwright/python:v1.62.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --break-system-packages -r requirements.txt

COPY . .

CMD ["celery", "-A", "config", "worker", "-l", "info", "--concurrency=1", "--max-tasks-per-child=1"]