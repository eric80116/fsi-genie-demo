# 自動化部署

用 CLI / API 一鍵完成主 README 的 Step 1–4.2，可以重複執行。

## 前置需求

- 已安裝 [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html)（v0.230 以上），並完成登入：`databricks auth login --host <workspace-url> --profile <profile>`
- Python 3.9 以上（只用到標準函式庫）
- 一個你有 `CREATE SCHEMA` 權限的 Unity Catalog catalog
- 一個 SQL Warehouse（建議用 Serverless），用 `databricks warehouses list --profile <profile>` 查詢 ID
- Workspace 已啟用 `ai_parse_document`（用來解析 PDF）

## 步驟

```bash
cd setup

# 1. 編輯設定檔
vi config.env      # 填入 DATABRICKS_PROFILE、CATALOG、SCHEMA、WAREHOUSE_ID

# 2. 一鍵部署
./deploy.sh
```

完成後會印出 `space_id`，在 workspace 左側選單 **Genie** 就能找到「星河銀行智慧分析助理」。

之後如果修改了 Instructions 或 SQL Examples，用下面的指令更新同一個 Space，不會另外新建：

```bash
python3 build_genie_space.py --space-id <space_id>
```

## 檔案說明

| 檔案 | 說明 | 對應主 README |
|---|---|---|
| `config.env` | 環境設定（profile / catalog / schema / warehouse） | — |
| `deploy.sh` | 一鍵部署 | Step 1–4.2 |
| `00_schema.sql` | 建立 schema 與 volume | Step 1-1 |
| `01_*.sql` | 讀 CSV，建成 5 張 Delta 表 | Step 2 Cell 1 |
| `02_policy_docs.sql` | 讀 12 份 Markdown，建成 `policy_docs` | Step 2 Cell 2 |
| `03_reports.sql` | 用 `ai_parse_document` 解析 PDF，建成 `reports` | Step 2 Cell 3 |
| `04_comments.sql` | 中文表格與欄位註解 | 加分動作：AI generate |
| `05_loan_metrics.sql` | Metric View `loan_metrics` | Step 2 Cell 4 |
| `build_genie_space.py` | 建立 / 更新 Genie Space（Instructions、Joins、SQL Examples、Benchmarks、Sample Questions） | Step 3–4.2 |
| `run_sql.sh` | 代入 `{{catalog}}` / `{{schema}}` 後，透過 Statement Execution API 執行 SQL | — |

## 與主 README 手動流程的差異

- `reports` 只放 6 份 PDF。`branch_npl_risk_analysis_2024q3.pdf` 保留給 Type D 現場上傳附件的示範。
- `customers.is_active` 是 BOOLEAN，SQL 範例使用 `is_active = TRUE`。
- 用 `04_comments.sql` 取代在 UI 上點「AI generate」產生欄位描述。
- 除了 README 原有的內容，另外加入：
  - `customers → branches` 的 join
  - 文件查詢範例（policy_docs / reports）
  - Metric View 查詢範例
  - Instructions 裡的「主題 → 檔名」對照表，讓 Genie 能找到對應的文件
- Benchmarks 已寫入 Space，請在 UI 點 **Benchmarks → Run benchmarks** 執行。
