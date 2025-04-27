# NTUNHS 教務處器材借用管理系統

## 專案概述

本系統旨在將現行「申請人 → 教務處 → 大樓管理員 → 教務處 → 申請人」的器材借用流程線上化，並提供大樓與器材管理功能，實現無紙化、可追蹤、易操作的借器材申請與分配機制。

## 技術架構

- **後端**：Python FastAPI
- **資料庫**：PostgreSQL
- **容器化**：Docker, Docker Compose
- **API 文檔**：OpenAPI (Swagger)
- **外部整合**：LINE Bot API, SMTP 郵件服務

## 功能特色

1. **使用者管理**
   - 集成學校 SSO 登入系統
   - 多角色支援：申請人、教務處人員、系統管理員

2. **申請流程管理**
   - 線上申請表單
   - 狀態追蹤
   - 自動通知

3. **大樓管理員回覆**
   - LINE Bot 整合
   - 專屬填表連結
   - 無需登入的簡化流程

4. **器材分配**
   - 視覺化分配介面
   - 自動生成 PDF 借用單
   - 電子郵件通知

5. **系統管理**
   - 大樓管理
   - 器材管理
   - 系統參數設定

## 系統要求

- Python 3.10+
- PostgreSQL 14+
- Docker 20.10+
- Docker Compose 2.0+

## 安裝與啟動

### 使用 Docker Compose

1. 複製環境變數範例檔案並依需求修改：
   ```bash
   cp .env.example .env
   ```

2. 啟動服務：
   ```bash
   docker-compose up -d
   ```

3. 執行資料庫遷移：
   ```bash
   docker-compose exec api alembic upgrade head
   ```

4. 訪問系統：
   - API: http://localhost:8000/api
   - API 文檔: http://localhost:8000/api/docs
   - PgAdmin: http://localhost:5050 (帳號: admin@example.com, 密碼: admin)

### 手動安裝

1. 安裝依賴：
   ```bash
   pip install -r requirements.txt
   ```

2. 設定環境變數：
   ```bash
   cp .env.example .env
   # 編輯 .env 文件以符合您的環境
   ```

3. 執行資料庫遷移：
   ```bash
   alembic upgrade head
   ```

4. 啟動服務：
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 專案結構

```
/ (專案根目錄)
├── app/                    # 應用程式代碼
│   ├── api/                # API 端點
│   ├── core/               # 核心功能 (認證、安全)
│   ├── crud/               # 資料庫操作
│   ├── models/             # 資料庫模型
│   ├── schemas/            # Pydantic 模型
│   ├── services/           # 外部服務 (LINE Bot, Email)
│   └── utils/              # 工具函數
├── alembic/                # 資料庫遷移
├── storage/                # 檔案儲存 (PDF)
├── tests/                  # 測試
├── .env.example            # 環境變數範例
├── Dockerfile              # Docker 配置
├── docker-compose.yml      # Docker Compose 配置
└── requirements.txt        # Python 依賴
```

## API 文檔

系統啟動後，可以通過以下地址訪問 API 文檔：
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 聯絡與支援

若有任何問題或建議，請聯絡專案維護人員。