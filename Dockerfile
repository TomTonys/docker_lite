FROM python:3.11-slim

LABEL maintainer="Docker Lite"
LABEL description="轻量级本地 Docker 管理工具"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8090
CMD ["python", "app.py"]