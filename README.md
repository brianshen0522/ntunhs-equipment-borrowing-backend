# NTUNHS 教務處器材借用管理系統

## 專案概述

本系統旨在數位化及簡化校內器材借用流程，實現「申請人 → 教務處 → 大樓管理員 → 教務處 → 申請人」的完整借用週期。系統提供線上申請、審核、分配及通知功能，並支援大樓與器材管理，實現無紙化、可追蹤的借用管理機制。

## 技術架構

- **後端框架**: Python FastAPI (非同步架構)
- **資料庫**: PostgreSQL with SQLAlchemy ORM
- **資料庫連接**: Asyncpg (非同步操作)
- **認證機制**: JWT (JSON Web Token)
- **容器化**: Docker, Docker Compose
- **API 文檔**: OpenAPI/Swagger
- **外部服務整合**: 
  - LINE Bot API (大樓管理員通知)
  - SMTP 郵件服務 (申請人通知)

## 系統角色與功能

### 1. 申請人 (Applicant)
- 借用申請提交與管理
- 申請進度追蹤
- 借用單接收與下載

### 2. 教務處人員 (Academic Staff)
- 審核申請
- 請求大樓管理員回應
- 器材分配管理
- 借用單生成及發送

### 3. 系統管理員 (System Admin)
- 用戶角色管理
- 系統參數設定
- LINE Bot 與 SMTP 設定
- 系統日誌查看

## 主要功能

1. **使用者管理**
   - 整合學校 SSO 身分認證
   - 多角色權限控制
   - 角色授權管理

2. **器材借用流程**
   - 線上申請表單
   - 多狀態追蹤: 待審核、待大樓回應、待分配、已完成、已駁回、已關閉
   - 申請狀態歷史記錄

3. **大樓管理員回應系統**
   - LINE Bot 自動通知
   - 無需登入的專屬填表連結
   - 即時可用數量回報

4. **器材分配管理**
   - 基於大樓回應的分配介面
   - 自動生成 PDF 借用單
   - 電子郵件通知申請人

5. **系統管理**
   - 大樓管理(新增、修改、刪除、啟用/停用)
   - 器材管理(新增、修改、刪除、啟用/停用)
   - 系統參數設定(過期時間、表單有效期、維護模式等)
   - LINE 與 SMTP 設定

## 系統架構

```
/ (專案根目錄)
├── app/                    # 應用程式主要代碼
│   ├── api/                # API 端點與路由
│   │   ├── allocations.py  # 器材分配 API
│   │   ├── auth.py         # 認證 API
│   │   ├── buildings.py    # 大樓管理 API
│   │   ├── deps.py         # 依賴注入
│   │   ├── equipment.py    # 器材管理 API
│   │   ├── requests.py     # 借用申請 API
│   │   ├── responses.py    # 大樓回應 API
│   │   ├── admin_users.py  # 使用者管理 API (管理員)
│   │   └── admin_settings.py # 系統設定 API (管理員)
│   ├── core/
│   │   └── auth.py         # 核心認證邏輯
│   ├── crud/               # 資料庫操作
│   │   ├── allocations.py  # 分配 CRUD
│   │   ├── base.py         # 基礎 CRUD 類別
│   │   ├── buildings.py    # 大樓 CRUD
│   │   ├── equipment.py    # 器材 CRUD
│   │   ├── requests.py     # 申請 CRUD
│   │   └── responses.py    # 回應 CRUD
│   ├── models/             # 資料庫模型
│   │   ├── allocations.py  # 分配模型
│   │   ├── buildings.py    # 大樓模型
│   │   ├── equipment.py    # 器材模型
│   │   ├── requests.py     # 申請模型
│   │   ├── responses.py    # 回應模型
│   │   ├── settings.py     # 設定模型
│   │   └── users.py        # 用戶模型
│   ├── schemas/            # Pydantic 模型 (API 格式)
│   ├── services/           # 外部服務集成
│   │   ├── email.py        # 郵件服務
│   │   ├── line_bot.py     # LINE Bot 服務
│   │   ├── logging.py      # 日誌服務
│   │   └── pdf.py          # PDF 生成服務
│   ├── config.py           # 應用程式設定
│   ├── database.py         # 資料庫連線
│   └── main.py             # 應用程式入口
├── storage/                # 檔案儲存目錄
│   └── requests/           # 生成的 PDF 借用單
├── .env.example            # 環境變數範例
├── Dockerfile              # Docker 配置
├── docker-compose.yml      # Docker Compose 配置
├── requirements.txt        # Python 依賴
└── wait-for-it.sh          # 啟動腳本 (等待資料庫)
```

## 安裝與啟動

### 使用 Docker Compose

1. 複製環境變數範例檔案並依需求修改：
   ```bash
   cp .env.example .env
   ```

2. 確保 `wait-for-it.sh` 腳本有執行權限：
   ```bash
   chmod +x wait-for-it.sh
   ```

3. 啟動服務：
   ```bash
   docker-compose up -d
   ```

4. 訪問系統：
   - API: http://localhost:8000/api
   - API 文檔: http://localhost:8000/api/docs

### 環境變數設定
主要環境變數說明 (詳見 `.env.example`)：

- **資料庫設定**：`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- **安全設定**：`SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- **LINE Bot 設定**：`LINE_BOT_CHANNEL_ACCESS_TOKEN`, `LINE_BOT_CHANNEL_SECRET`
- **SMTP 設定**：`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- **系統參數**：`REQUEST_EXPIRY_DAYS`, `RESPONSE_FORM_VALIDITY_HOURS`

## API 文檔

系統啟動後，可以通過以下地址訪問 API 文檔：
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 特別功能

1. **專屬回覆連結**：系統為每個借用申請生成專屬令牌，大樓管理員可通過 LINE 收到的連結直接回覆，無需登入系統。

2. **即時數量統計**：系統自動彙總各大樓回覆的可用數量，協助教務處人員高效分配器材。

3. **狀態追蹤**：完整的狀態歷史記錄，包含時間、操作者和備註，確保流程透明。

4. **自動通知**：重要節點自動透過 LINE Bot 或電子郵件發送通知，提升流程效率。

5. **系統日誌**：詳細的系統操作日誌，記錄所有重要操作，方便除錯和稽核。

## 系統安全

- JWT 令牌認證
- 角色基礎的訪問控制 (RBAC)
- 密碼/令牌加密存儲
- 操作日誌記錄
- IP 地址追蹤