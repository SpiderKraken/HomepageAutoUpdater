# First stage: build dependencies
FROM python:3.9 as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t /app/deps
EXPOSE 80

# Second stage: lightweight final container
FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /app/deps /app/deps
COPY monitor_containers.py .

ENV PYTHONPATH=/app/deps
CMD ["python", "monitor_containers.py"]
