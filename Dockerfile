FROM python:3.10-slim

WORKDIR /app

# 設置環境變數
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 安裝系統依賴
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev libpq-dev netcat-openbsd\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案文件
COPY . .

# 建立 storage 目錄
RUN mkdir -p storage/requests

# 暴露端口
EXPOSE 8000

# 啟動命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]