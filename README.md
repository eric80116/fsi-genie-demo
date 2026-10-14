# Databricks 銀行業智慧分析 Genie 實作指南

> **目標**：從原始資料到可對話的 AI 分析助理，完整流程約 30 分鐘。
> **使用資料**：星河商業銀行（虛構）結構化數據 + 法規/SOP 文件（Markdown）+ 季報與策略報告（PDF）
> **你會建立**：7 張 Delta 表、1 個 Metric View、1 個設定完成的 Genie Space（含 Instructions、Joins、SQL Examples、Benchmarks）

> **開始前**：本文中的 `your_catalog` 請替換為你 workspace 中的 catalog 名稱（需有 CREATE SCHEMA 權限）。
> **想跳過手動步驟？** Step 1–4.2 可用腳本一鍵完成，見 [`setup/README.md`](setup/README.md)。

---

## 流程總覽

```
Step 1  建立 Volume & 上傳檔案        (~5 min)  UI 操作
Step 2  用 AI 寫程式、建立 Delta 表   (~5 min)  Notebook + Genie Code
Step 3  建立 Genie Space              (~5 min)  UI 操作
Step 4  設定 Instructions & Join      (~5 min)  貼上即完成
Step 5  開始問答                     (~10 min) 試用範例問題
```

---

## Step 1 — 建立 Volume，上傳三類檔案

### 1-1 建立 Volume

1. 左側選單 → **Catalog**（目錄圖示）
2. 展開 `your_catalog` → `fsi_genie_demo`（若尚無此 schema，先在 `your_catalog` 點 **Create schema** 建立）
3. 右上角點 **Create** → **Volume**
4. 填入：
   - **Volume name**：`files`
   - **Volume type**：Managed volume
5. 點 **Create**

> 建立後路徑為 `/Volumes/your_catalog/fsi_genie_demo/files`

### 1-2 上傳檔案

在剛建立的 `files` Volume 頁面：

1. 切換到 `Files` 分頁，先建立子目錄再上傳
2. 點 **Create Directory** → 命名 → 再點 **Upload to this Volume**

| 子目錄 | 要上傳的檔案 |
|---|---|
| 建立 `csv` 資料夾 | 全部 5 個 `.csv`（customers、accounts、transactions、loans、branches）|
| 建立 `markdown` 資料夾 | 全部 12 個 `.md` 文件 |
| 建立 `pdf` 資料夾 | 6 個 `.pdf` 報告（`branch_npl_risk_analysis_2024q3.pdf` **不要上傳**，留到 Step 5 Type D 當附件使用）|

> 完成後確認三個資料夾各有對應檔案即可繼續。

---

## Step 2 — 用 Genie Code 建立 Delta 表

### 開啟 Notebook

1. 左側選單 → **New** → **Notebook**
2. 語言選 **Python**，Compute 選 **Serverless**
3. 畫面出現 **Genie Code** 對話框（若未顯示：點右上角神燈圖示）

---

### Cell 1 — 讀取 CSV → 5 張 Delta 表

在 Genie Code 輸入框貼上：

```
用 PySpark 從 /Volumes/your_catalog/fsi_genie_demo/files/csv/ 讀取以下 CSV，
各自存成獨立的 Delta table（saveAsTable，mode=overwrite）：

- customers.csv   → your_catalog.fsi_genie_demo.customers
- accounts.csv    → your_catalog.fsi_genie_demo.accounts
- transactions.csv → your_catalog.fsi_genie_demo.transactions
- loans.csv       → your_catalog.fsi_genie_demo.loans
- branches.csv    → your_catalog.fsi_genie_demo.branches

每個 CSV 的讀取選項：header=true, inferSchema=true
每讀完一張表，print 出 table name 和 row count
```

→ AI 產生 code 後 **▶ Run**，過程中會自動執行與偵錯

---

### Cell 2 — 讀取 Markdown → 1 張 Delta 表（每檔一 row）

新增 Cell，在 Genie Code 輸入框貼上：

```
用 Python（dbutils + PySpark）讀取 /Volumes/your_catalog/fsi_genie_demo/files/markdown/ 底下所有 .md 檔案。
每個檔案建立一筆 row，包含欄位：
- filename（原始檔名）
- title（從文件第一行 # 標題擷取）
- content（檔案全文）
- word_count（字數）

把所有 rows 轉成 Spark DataFrame，存成 Delta table：
your_catalog.fsi_genie_demo.policy_docs（mode=overwrite）
最後 print row count
```

→ AI 產生 code 後 **▶ Run**

---

### Cell 3 — 解析 PDF → 1 張 Delta 表（用 ai_parse_document）

新增 Cell，在 Genie Code 輸入框貼上：

```
用 SQL 讀取 /Volumes/your_catalog/fsi_genie_demo/files/pdf/ 底下所有 PDF 檔案，
使用 read_files() 搭配 binaryFile format 讀進來，
對每個 PDF 的 content 欄位呼叫 ai_parse_document()，
把解析結果展平，取出每頁文字合併成 full_text 欄位，
每個 PDF 一筆 row，包含 filename 和 full_text，
CREATE OR REPLACE TABLE your_catalog.fsi_genie_demo.reports
```

→ AI 產生 code 後 **▶ Run**

> ⏱ `ai_parse_document` 處理 6 個 PDF 約需 1–2 分鐘，正常現象。

---

### Cell 4 — 建立 Metric View（貸款組合核心業務指標）

新增 Cell，語言切換為 **SQL**，直接貼上以下 DDL 執行：

```sql
CREATE OR REPLACE VIEW your_catalog.fsi_genie_demo.loan_metrics
WITH METRICS LANGUAGE YAML AS $$
  version: 1.1
  comment: "星河銀行 貸款組合核心業務指標 — 可按任意維度切片分析 NPL、利率、逾期狀況"
  source: your_catalog.fsi_genie_demo.loans

  joins:
    - name: customers
      source: your_catalog.fsi_genie_demo.customers
      on: source.customer_id = customers.customer_id
      rely:
        at_most_one_match: true
    - name: branches
      source: your_catalog.fsi_genie_demo.branches
      on: source.branch_id = branches.branch_id
      rely:
        at_most_one_match: true

  fields:
    - name: loan_type
      expr: loan_type
      display_name: "貸款類型"
      synonyms: ["放款類型", "loan type"]
    - name: npl_classification
      expr: npl_classification
      display_name: "NPL分類"
      synonyms: ["不良貸款分類", "逾期分類", "資產品質"]
    - name: collateral_type
      expr: collateral_type
      display_name: "擔保品類型"
      synonyms: ["抵押品", "擔保"]
    - name: customer_segment
      expr: customers.customer_segment
      display_name: "客戶等級"
      synonyms: ["客戶分級", "財富等級"]
    - name: customer_risk_rating
      expr: customers.risk_rating
      display_name: "客戶風險評等"
      synonyms: ["風險等級", "信用評等"]
    - name: branch_region
      expr: branches.region
      display_name: "分行區域"
      synonyms: ["地區", "區域"]
    - name: branch_name
      expr: branches.branch_name
      display_name: "分行名稱"
    - name: loan_start_year
      expr: YEAR(loan_start_date)
      display_name: "貸款起始年份"

  measures:
    - name: total_loan_amount
      expr: SUM(loan_amount_twd)
      display_name: "放款總金額（TWD）"
      synonyms: ["總放款", "貸款總額"]
    - name: outstanding_balance
      expr: SUM(outstanding_balance_twd)
      display_name: "未償餘額（TWD）"
      synonyms: ["餘額", "未還金額"]
    - name: loan_count
      expr: COUNT(loan_id)
      display_name: "貸款件數"
      synonyms: ["件數", "筆數"]
    - name: npl_amount
      expr: SUM(outstanding_balance_twd) FILTER (WHERE npl_classification IN ('可望收回','收回困難','收回無望'))
      display_name: "NPL金額（TWD）"
      synonyms: ["不良貸款金額", "逾期貸款金額"]
    - name: npl_count
      expr: COUNT(loan_id) FILTER (WHERE npl_classification IN ('可望收回','收回困難','收回無望'))
      display_name: "NPL件數"
      synonyms: ["不良貸款件數", "逾期件數"]
    - name: avg_interest_rate
      expr: AVG(interest_rate_pct)
      display_name: "平均利率（%）"
      synonyms: ["利率", "平均放款利率"]
    - name: avg_overdue_days
      expr: AVG(days_overdue) FILTER (WHERE days_overdue > 0)
      display_name: "平均逾期天數"
      synonyms: ["逾期天數", "平均延遲天數"]
    - name: high_risk_balance
      expr: SUM(outstanding_balance_twd) FILTER (WHERE customers.risk_rating = 'High')
      display_name: "高風險客戶未償餘額（TWD）"
      synonyms: ["高風險放款", "高風險餘額"]
$$
```

→ 直接 **▶ Run** 即可（不需要 Genie Code，這是標準 SQL DDL）

> **為什麼要建 Metric View？**
> Metric View 把業務指標定義集中在一處——「NPL金額」、「高風險餘額」這些計算邏輯只需定義一次，Genie、Dashboard、BI 工具都能直接引用，確保全公司的數字口徑一致。

---

### ✅ Step 2 驗證

執行完 4 個 Cell 後，應在 `your_catalog.fsi_genie_demo` 下看到 7 張表 + 1 個 Metric View：

```
customers   accounts   transactions   loans   branches
policy_docs   reports
loan_metrics  ← Metric View（圖示與一般表不同）
```

在 Catalog Explorer 點 `loan_metrics` → 可看到所有 **Fields**（維度）與 **Measures**（指標）的定義。

### ✨ 加分動作 — AI 自動產生表格與欄位描述

1. 在 Catalog Explorer 進入任一表（如 `loans`）
2. 看到自動生成的 Description 建議 → 點 **Accept**
3. 點欄位表格右上角 **AI generate** → 自動生成欄位描述 → 點 **Save all**
4. 在每張表重複操作

> 清楚的欄位描述可大幅提升 Genie 回答的準確率——這是銀行業資料治理的最佳示範！

---

## Step 3 — 建立 Genie Space

1. 左側選單 → **Genie spaces**
2. 右上角 **New**
3. 加入以下資料表，點選 **Create**：

```
your_catalog.fsi_genie_demo.customers
your_catalog.fsi_genie_demo.accounts
your_catalog.fsi_genie_demo.transactions
your_catalog.fsi_genie_demo.loans
your_catalog.fsi_genie_demo.branches
your_catalog.fsi_genie_demo.policy_docs
your_catalog.fsi_genie_demo.reports
your_catalog.fsi_genie_demo.loan_metrics
```

4. 填入設定：

| 欄位 | 填入值 |
|---|---|
| **Name** | `星河銀行智慧分析助理` |
| **Description** | 點選 **Save** 採用自動生成的內容 |
| **SQL Warehouse** | 選擇 Serverless 或任一可用的 SQL Warehouse |

---

## Step 4 — 加入 Instructions 與 Join 關係

在 Genie Space → **Instructions** tab，貼入以下內容（全部複製貼上）：

```
## 資料範圍說明
本 Genie Space 涵蓋星河商業銀行的核心業務資料：
- 客戶：500位，分為 Private（私銀）、Wealth（財管）、Preferred（優先）、Retail（一般）四個等級
- 帳戶：850個，涵蓋存款、定存、投資、信用卡等帳戶類型
- 交易：6,000筆，時間範圍 2022–2024，涵蓋存款、提款、轉帳、投資等
- 貸款：800筆，涵蓋房貸、車貸、個貸、企業貸款等，含NPL五分類
- 分行：30家，含財富管理中心，遍布全台各區
- 法規/SOP文件：12份，含AML/KYC政策、信用審核SOP、NPL催收SOP等（policy_docs）
- 季報與策略報告：6份，含Q1-Q3季報、年報、NPL分析、數位轉型策略（reports）

## 關鍵業務指標定義
- NPL比率：npl_classification IN ('可望收回','收回困難','收回無望') 的放款金額 / 總放款金額
- 廣義逾期率：days_overdue > 0 的放款金額 / 總放款金額
- AUM（資產管理規模）：customers.total_aum_twd
- 客戶分級：Private（AUM≥3,000萬）、Wealth（AUM 500萬–2,999萬）、Preferred（100萬–499萬）、Retail（<100萬）
- KYC狀態：customers.kyc_status（Verified/Pending/Expired）
- 可疑交易：transactions.status = 'Suspicious'
- 數位管道：transactions.channel IN ('Mobile','Online')
- 傳統管道：transactions.channel IN ('Branch_Counter','Branch_Teller','ATM')

## 知識文件使用規則
- 凡涉及法規、合規、SOP、審核流程的問題，優先查詢 policy_docs 表的 content 欄位
- 凡涉及季報、風險分析、策略報告的問題，查詢 reports 表的 full_text 欄位
- 不可回答「資料庫中沒有此資訊」——一律先搜尋 policy_docs 和 reports

## 輸出格式規範
- 金額以新台幣（TWD）加千位分隔符顯示（如 NT$1,234,567）
- 比率保留2位小數（如 1.83%）
- 比較多個項目時，同時列出件數與金額
- 回答繁體中文問題時，以繁體中文回答
- 涉及敏感客戶資訊時，請提醒需依資料保護法規處理
```

### 加入 Join Relations

在 Genie Space → **Instructions** tab → **Joins** 區塊，依序加入：

| From table | From column | To table | To column | 類型 |
|---|---|---|---|---|
| `accounts` | `customer_id` | `customers` | `customer_id` | Many to one |
| `transactions` | `account_id` | `accounts` | `account_id` | Many to one |
| `transactions` | `customer_id` | `customers` | `customer_id` | Many to one |
| `loans` | `customer_id` | `customers` | `customer_id` | Many to one |
| `loans` | `branch_id` | `branches` | `branch_id` | Many to one |
| `accounts` | `branch_id` | `branches` | `branch_id` | Many to one |

> 加完 Join Relations 後，Genie 跨表問答的準確率會大幅提升。

---

## Step 4.1 — 加入 SQL Examples（Trusted Assets）

在 Genie Space → **Instructions** tab → **SQL Queries** 分頁，點 **Add** 逐一加入以下範例。

> **為什麼要加？** Genie 使用這些範例查詢時，回答會標示「已驗證（Verified）」，讓使用者能辨識哪些答案經過驗證。複雜的業務邏輯（如 NPL 計算、客戶分級定義）只需在這裡定義一次，之後任何相似問題都能套用。

---

### SQL Example 1

**Title（照這個文字填入）**：
```
各貸款類型的NPL比率和未償金額是多少？
```

**SQL**：
```sql
SELECT
  loan_type,
  COUNT(*)                                                              AS loan_count,
  SUM(outstanding_balance_twd)                                         AS outstanding_balance_twd,
  SUM(CASE WHEN npl_classification IN ('可望收回','收回困難','收回無望')
           THEN outstanding_balance_twd ELSE 0 END)                    AS npl_amount_twd,
  ROUND(
    SUM(CASE WHEN npl_classification IN ('可望收回','收回困難','收回無望')
             THEN outstanding_balance_twd ELSE 0 END)
    / NULLIF(SUM(outstanding_balance_twd), 0) * 100, 2
  )                                                                    AS npl_ratio_pct
FROM your_catalog.fsi_genie_demo.loans
GROUP BY loan_type
ORDER BY npl_ratio_pct DESC
```

---

### SQL Example 2

**Title**：
```
各分行的存款、放款和NPL比率排名
```

**SQL**：
```sql
SELECT
  b.branch_name,
  b.region,
  b.total_deposits_twd,
  b.total_loans_twd,
  b.npl_ratio_pct,
  b.deposit_growth_yoy_pct,
  RANK() OVER (ORDER BY CAST(b.npl_ratio_pct AS DOUBLE) DESC)           AS npl_risk_rank,
  RANK() OVER (ORDER BY CAST(b.deposit_growth_yoy_pct AS DOUBLE) DESC)  AS deposit_growth_rank
FROM your_catalog.fsi_genie_demo.branches b
ORDER BY CAST(b.npl_ratio_pct AS DOUBLE) DESC
```

---

### SQL Example 3

**Title**：
```
各客戶等級的人數、平均AUM和總AUM是多少？
```

**SQL**：
```sql
SELECT
  customer_segment,
  COUNT(*)                                  AS customer_count,
  ROUND(AVG(total_aum_twd))                 AS avg_aum_twd,
  SUM(total_aum_twd)                        AS sum_aum_twd,
  ROUND(AVG(total_aum_twd) / 10000, 1)      AS avg_aum_10k,
  ROUND(SUM(total_aum_twd) / 100000000.0, 2) AS sum_aum_100m
FROM your_catalog.fsi_genie_demo.customers
WHERE is_active = 'TRUE'
GROUP BY customer_segment
ORDER BY sum_aum_twd DESC
```

---

### SQL Example 4

**Title**：
```
2022到2024年行動與線上管道的交易筆數和佔比趨勢
```

**SQL**：
```sql
SELECT
  YEAR(transaction_date)                              AS txn_year,
  QUARTER(transaction_date)                           AS txn_quarter,
  COUNT(*)                                            AS total_txn_count,
  SUM(CASE WHEN channel IN ('Mobile','Online')
           THEN 1 ELSE 0 END)                         AS digital_txn_count,
  SUM(CASE WHEN channel IN ('Branch_Counter','Branch_Teller')
           THEN 1 ELSE 0 END)                         AS branch_txn_count,
  SUM(CASE WHEN channel = 'ATM'
           THEN 1 ELSE 0 END)                         AS atm_txn_count,
  ROUND(SUM(CASE WHEN channel IN ('Mobile','Online')
                 THEN 1 ELSE 0 END)
        / COUNT(*) * 100, 1)                          AS digital_pct
FROM your_catalog.fsi_genie_demo.transactions
GROUP BY YEAR(transaction_date), QUARTER(transaction_date)
ORDER BY txn_year, txn_quarter
```

---

### SQL Example 5

**Title**：
```
有可疑交易紀錄的客戶名單和風險狀況
```

**SQL**：
```sql
SELECT
  c.customer_id,
  c.full_name,
  c.customer_segment,
  c.risk_rating,
  c.kyc_status,
  c.total_aum_twd,
  COUNT(t.transaction_id)  AS suspicious_count,
  SUM(t.amount_twd)        AS suspicious_total_twd
FROM your_catalog.fsi_genie_demo.transactions t
JOIN your_catalog.fsi_genie_demo.customers c
  ON t.customer_id = c.customer_id
WHERE t.status = 'Suspicious'
GROUP BY
  c.customer_id, c.full_name, c.customer_segment,
  c.risk_rating, c.kyc_status, c.total_aum_twd
ORDER BY suspicious_count DESC
```

---

### SQL Example 6

**Title**：
```
NPL五分類的件數、金額分布和備抵提列狀況
```

**SQL**：
```sql
SELECT
  npl_classification,
  COUNT(*)                                                        AS loan_count,
  SUM(outstanding_balance_twd)                                    AS outstanding_balance_twd,
  ROUND(SUM(outstanding_balance_twd) / 100000000.0, 2)            AS outstanding_100m_twd,
  CASE npl_classification
    WHEN '正常'     THEN 1.0
    WHEN '應注意'   THEN 2.0
    WHEN '可望收回' THEN 10.0
    WHEN '收回困難' THEN 50.0
    WHEN '收回無望' THEN 100.0
  END                                                             AS provision_rate_pct,
  ROUND(SUM(outstanding_balance_twd) *
    CASE npl_classification
      WHEN '正常'     THEN 0.01
      WHEN '應注意'   THEN 0.02
      WHEN '可望收回' THEN 0.10
      WHEN '收回困難' THEN 0.50
      WHEN '收回無望' THEN 1.00
    END / 100000000.0, 2)                                         AS required_provision_100m_twd
FROM your_catalog.fsi_genie_demo.loans
GROUP BY npl_classification
ORDER BY CASE npl_classification
  WHEN '正常'     THEN 1
  WHEN '應注意'   THEN 2
  WHEN '可望收回' THEN 3
  WHEN '收回困難' THEN 4
  WHEN '收回無望' THEN 5
END
```

---

## Step 4.2 — 建立 Benchmark & 跑 Evaluation


### 如何加入 Benchmark

1. 在 Genie Space 頁面頂部點 **Benchmarks**
2. 點 **Add benchmark** 逐一加入以下題目
3. 全部加完後點 **Run benchmarks** → 切到 **Evaluation** tab 等結果

---

### Benchmark 1（Chat 模式）

**Question**：
```
各貸款類型的NPL比率和未償金額是多少？
```

**Mode**：Chat

**SQL Answer**：
```sql
SELECT
  loan_type,
  COUNT(*)                                                              AS loan_count,
  SUM(outstanding_balance_twd)                                         AS outstanding_balance_twd,
  SUM(CASE WHEN npl_classification IN ('可望收回','收回困難','收回無望')
           THEN outstanding_balance_twd ELSE 0 END)                    AS npl_amount_twd,
  ROUND(
    SUM(CASE WHEN npl_classification IN ('可望收回','收回困難','收回無望')
             THEN outstanding_balance_twd ELSE 0 END)
    / NULLIF(SUM(outstanding_balance_twd), 0) * 100, 2
  )                                                                    AS npl_ratio_pct
FROM your_catalog.fsi_genie_demo.loans
GROUP BY loan_type
ORDER BY npl_ratio_pct DESC
```

---

### Benchmark 2（Chat 模式）

**Question**：
```
NPL五種分類各有多少件？未償餘額各是多少？
```

**Mode**：Chat

**SQL Answer**：
```sql
SELECT
  npl_classification,
  COUNT(*)                     AS loan_count,
  SUM(outstanding_balance_twd) AS outstanding_balance_twd
FROM your_catalog.fsi_genie_demo.loans
GROUP BY npl_classification
ORDER BY CASE npl_classification
  WHEN '正常'     THEN 1
  WHEN '應注意'   THEN 2
  WHEN '可望收回' THEN 3
  WHEN '收回困難' THEN 4
  WHEN '收回無望' THEN 5
END
```

---

### Benchmark 3（Chat 模式）

**Question**：
```
各客戶等級的人數和總AUM是多少？
```

**Mode**：Chat

**SQL Answer**：
```sql
SELECT
  customer_segment,
  COUNT(*)           AS customer_count,
  SUM(total_aum_twd) AS sum_aum_twd
FROM your_catalog.fsi_genie_demo.customers
WHERE is_active = 'TRUE'
GROUP BY customer_segment
ORDER BY sum_aum_twd DESC
```

---

### Benchmark 4（Chat 模式）

**Question**：
```
2022、2023、2024年各年度行動銀行（Mobile）交易佔比是多少？
```

**Mode**：Chat

**SQL Answer**：
```sql
SELECT
  YEAR(transaction_date)                                               AS txn_year,
  COUNT(*)                                                             AS total_txn_count,
  SUM(CASE WHEN channel = 'Mobile' THEN 1 ELSE 0 END)                 AS mobile_count,
  ROUND(SUM(CASE WHEN channel = 'Mobile' THEN 1.0 ELSE 0 END)
        / COUNT(*) * 100, 1)                                           AS mobile_pct
FROM your_catalog.fsi_genie_demo.transactions
GROUP BY YEAR(transaction_date)
ORDER BY txn_year
```

---

### Benchmark 5（Chat 模式）

**Question**：
```
有可疑交易的客戶共幾位？哪位客戶的可疑交易件數最多？
```

**Mode**：Chat

**SQL Answer**：
```sql
SELECT
  c.customer_id,
  c.full_name,
  c.customer_segment,
  c.risk_rating,
  COUNT(t.transaction_id)  AS suspicious_count,
  SUM(t.amount_twd)        AS suspicious_total_twd
FROM your_catalog.fsi_genie_demo.transactions t
JOIN your_catalog.fsi_genie_demo.customers c
  ON t.customer_id = c.customer_id
WHERE t.status = 'Suspicious'
GROUP BY c.customer_id, c.full_name, c.customer_segment, c.risk_rating
ORDER BY suspicious_count DESC
```

---

### Benchmark 6（Agent 模式）

**Question**：
```
同時有高風險評等（risk_rating = High）又有可疑交易紀錄的客戶有哪些？他們的AUM和可疑交易金額各是多少？
```

**Mode**：Agent

**Evaluation Note**：
```
答案應包含：客戶姓名、客戶等級、AUM金額、可疑交易件數、可疑交易總金額。
必須同時滿足兩個條件：risk_rating = 'High' 且有 status = 'Suspicious' 的交易紀錄。
結果應按可疑交易件數或金額排序。
```

---

### Evaluation 結果解讀

| 評分 | 說明 | 建議處理 |
|------|------|---------|
| **Good** ✅ | SQL 產出與標準答案相符 | 不需處理 |
| **Manual review needed** 🔍 | 自動比對無法判定（如排序不同、格式差異）| 點開檢查結果，確認正確後標為 Good |
| **Bad** ❌ | 結果有誤 | 調整 Instructions 或補充 SQL Example 後重新執行 |

---

## Step 5 — 範例問題

### Genie 三種問答模式

| 模式 | 運作方式 | 適合情境 |
|---|---|---|
| **Chat — Do not inspect answer** | 直接產生 SQL 並執行 | 快速彙總、圖表呈現 |
| **Chat — Inspect answer** | 先產 SQL，再自動驗證邏輯正確性 | 需高準確度的業務指標 |
| **Agent** | 擬定 research plan，多步驟迭代，產出完整報告 | 複雜多維度分析 |

---

### 🏦 Type A — 結構化數據分析（有圖表）

> 建議模式：**Chat — Do not inspect answer**（快速產生結果與圖表）

**1. 整體不良貸款（NPL）全景概覽**
```
我們目前的NPL比率是多少？請按貸款類型分解，並顯示各類型的放款金額和逾期狀況
```
*使用資料*：`loans`（NPL 五分類、逾期天數）

**2. 各分行存放款績效排名**
```
比較各分行的存款規模、放款規模和NPL比率，找出績效最好和最需要關注的前五名分行
```
*使用資料*：`branches`

**3. 客戶財富分布與AUM分析**
```
我們的客戶按財富等級分布如何？Private、Wealth、Preferred、Retail各有多少人？
各等級的平均AUM和總AUM是多少？
```
*使用資料*：`customers`（customer_segment、total_aum_twd）

**4. 數位 vs 傳統管道交易趨勢**
```
2022到2024年，行動/線上管道的交易佔比如何變化？和ATM、臨櫃比較
```
*使用資料*：`transactions`（channel、transaction_date）

**5. 可疑交易分布分析**
```
可疑交易（Suspicious）的件數和金額分布如何？哪些帳戶類型和管道最多？
哪些客戶分段有最高比率的可疑交易？
```
*使用資料*：`transactions` × `accounts` × `customers`

---

### 📄 Type B — 文件知識問答（SOP / 法規 / 季報）

> 建議模式：**Chat — Inspect answer**（確保搜尋到正確文件再回答）

**6. 逾期貸款催收程序**
```
對於已進入「可望收回」分類（逾期31-90天）的客戶，我們的標準催收程序是什麼？
有哪些協商方案可以提供給客戶？
```
*使用資料*：`policy_docs`（npl_collection_sop.md）

**7. Private Banking KYC要求**
```
對私人銀行（Private Banking）客戶，我們的KYC盡職調查要求是什麼？
需要哪些文件和流程？
```
*使用資料*：`policy_docs`（aml_kyc_policy.md、wealth_management_policy.md）

**8. Q3 2024 風險報告重點發現**
```
根據2024年Q3風險管理報告，目前最需要關注的信用風險是哪些？
風險委員會有什麼建議行動？
```
*使用資料*：`reports`（q3_2024_risk_management_report.pdf）

---

### 🔀 Type C — 跨數據 + 文件混合分析

> 建議模式：**Agent**（多步驟推理，產出完整分析報告）

**9. 高風險客戶 × AML合規雙重分析**
```
找出同時符合以下條件的高風險客戶：
(1) risk_rating = 'High'，且
(2) 有可疑交易紀錄（status = 'Suspicious'）

列出這些客戶的名單、AUM、可疑交易件數和金額。
同時，根據我們的AML/KYC政策，對這些客戶應該啟動什麼等級的調查程序？
```
*使用資料*：`customers` × `transactions` + `policy_docs`（aml_kyc_policy.md）

**10. NPL集中度 × 催收策略連動分析**
```
哪5家分行的NPL比率最高？這些分行目前「收回困難」和「收回無望」的貸款金額共計多少？
根據NPL催收SOP，對收回困難的案件應採取哪些具體行動？
請預估若成功協商70%的可望收回案件可回正，這些分行的NPL比率能改善多少？
```
*使用資料*：`branches` × `loans` + `policy_docs`（npl_collection_sop.md），並包含情境試算

---

### 📎 Type D — 即時附件上傳問答（File Attachment Q&A）

> 建議模式：**Chat — Agent**（Genie 同時讀取上傳的 PDF 與底層資料表）

這類問題示範把一份**不在資料表中**的新報告直接上傳到對話中，與既有資料一起分析。

**操作步驟**：
1. 在 Genie Space 對話視窗點擊 **📎 附件圖示**（或直接將 PDF 拖入輸入框）
2. 選取 `branch_npl_risk_analysis_2024q3.pdf`（2024 Q3 分行 NPL 風險集中度專項分析報告）
3. 輸入以下問題

---

**11. 三源整合催收決策（PDF ＋ SOP ＋ Delta Table）**
```
根據上傳的報告，針對「收回困難」金額最高的分行，從貸款資料中找出這批案件的有擔保與無擔保比例，並依照我們的催收SOP說明應如何優先處置？
```
*使用資料*：上傳的 PDF（找出目標分行）+ `loans`（擔保品明細）+ `policy_docs`（npl_collection_sop.md）

---

---

## 📂 資料清單

### CSV 結構化資料（5張表）

| 檔案 | 筆數 | 說明 |
|---|---|---|
| `branches.csv` | 30 | 分行清單（含存放款規模、NPL比率、績效指標）|
| `customers.csv` | 500 | 客戶資料（含AUM、分級、KYC狀態、風險評等）|
| `accounts.csv` | 850 | 帳戶資料（含帳戶類型、餘額、利率）|
| `transactions.csv` | 6,000 | 交易紀錄（2022–2024，含管道、金額、可疑標記）|
| `loans.csv` | 800 | 貸款組合（含類型、NPL五分類、擔保品）|

### Markdown 文件（12份）

| 檔案 | 文件類型 |
|---|---|
| `aml_kyc_policy.md` | AML/KYC 法規遵循政策 |
| `npl_collection_sop.md` | 逾期貸款催收SOP（含五分類處理程序）|
| `credit_approval_sop.md` | 信用審核SOP（含授信核准權限表）|
| `customer_onboarding_sop.md` | 開戶與分級SOP（含數位開戶流程）|
| `investment_suitability_sop.md` | 投資商品適合度評估（KYC/RR分級）|
| `fraud_prevention_policy.md` | 詐欺防制政策（含即時偵測規則）|
| `mortgage_approval_sop.md` | 房屋貸款核貸SOP |
| `digital_banking_security.md` | 數位銀行資安規範（MFA/加密標準）|
| `operational_risk_framework.md` | 作業風險管理框架（Basel III）|
| `customer_complaint_sop.md` | 客訴處理SOP（含分級制度）|
| `branch_operations_sop.md` | 分行營運管理規範（KPI/分行轉型計畫）|
| `wealth_management_policy.md` | 財富管理業務政策（私銀服務/AUM計算）|

### PDF 報告（6份）

| 檔案 | 內容 |
|---|---|
| `q1_2024_financial_results.pdf` | 2024 Q1財務績效（NIM 1.92%、稅前盈餘42.7億）|
| `q2_2024_financial_results.pdf` | 2024 Q2財務績效（半年累計盈餘86.3億）|
| `q3_2024_risk_management_report.pdf` | 2024 Q3風險管理（建設業NPL警示、作業事件）|
| `2023_annual_report.pdf` | 2023年報（稅前盈餘152.4億、AUM2,980億）|
| `2024_npl_deep_dive_analysis.pdf` | NPL深度分析（建設業13% NPL比率、催收策略）|
| `digital_transformation_strategy_2024.pdf` | 數位轉型策略（AI成效、數位管道趨勢、2025計畫）|
