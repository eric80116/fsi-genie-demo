"""Create or update the 星河銀行 Genie Space (instructions, joins, SQL examples, benchmarks).

Usage:
  python3 build_genie_space.py                       # create a new space
  python3 build_genie_space.py --space-id <ID>       # update an existing space
  python3 build_genie_space.py --dry-run             # print serialized_space only
"""
import argparse
import hashlib
import json
import os
import subprocess


def load_config(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.env")):
    cfg = {}
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


CONFIG = load_config()
PROFILE = CONFIG["DATABRICKS_PROFILE"]
WAREHOUSE_ID = CONFIG["WAREHOUSE_ID"]
SCHEMA = f"{CONFIG['CATALOG']}.{CONFIG['SCHEMA']}"
TITLE = "星河銀行智慧分析助理"
DESCRIPTION = (
    "星河商業銀行（虛構）智慧分析助理。涵蓋客戶、帳戶、交易、放款、分行等結構化資料，"
    "以及內部法規/SOP文件（policy_docs）與季報/策略報告（reports），"
    "可回答 NPL、AUM、數位轉型、AML可疑交易等經營問題，並引用內部政策給出行動建議。"
)
NPL = "('可望收回','收回困難','收回無望')"


def hid(*parts):
    """Deterministic 32-hex id so re-runs produce a stable payload."""
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def t(name):
    return f"{SCHEMA}.{name}"


TABLES = ["customers", "accounts", "transactions", "loans", "branches", "policy_docs", "reports"]

# Categorical columns users name directly -> entity matching + format assistance
ENTITY_COLUMNS = {
    "customers": ["customer_segment", "risk_rating", "kyc_status", "occupation", "city"],
    "accounts": ["account_type", "status"],
    "transactions": ["transaction_type", "channel", "status", "merchant_category"],
    "loans": ["loan_type", "npl_classification", "collateral_type"],
    "branches": ["branch_name", "region", "city"],
    "policy_docs": ["filename", "title"],
    "reports": ["filename"],
}

TEXT_INSTRUCTIONS = f"""## 資料範圍說明
本 Genie Space 涵蓋星河商業銀行的核心業務資料：
- 客戶 customers：500位，分為 Private（私銀）、Wealth（財管）、Preferred（優先）、Retail（一般）四個等級
- 帳戶 accounts：850個，涵蓋 Savings、Checking、Time_Deposit、Investment、Credit_Card
- 交易 transactions：6,000筆，時間範圍 2022–2024，涵蓋 Deposit、Withdrawal、Transfer、Payment、Investment、Loan_Repayment
- 貸款 loans：800筆，涵蓋 Mortgage、Car_Loan、Personal_Loan、Business_Loan、Credit_Card_Revolving，含NPL五分類
- 分行 branches：30家，含財富管理中心，遍布北區/中區/南區/東區
- 法規/SOP文件 policy_docs：12份（每份一筆，全文在 content 欄位）
- 季報與策略報告 reports：6份（每份一筆，全文在 full_text 欄位）
- 貸款指標 loan_metrics：Metric View，查詢時必須用 MEASURE(<measure_name>) 並 GROUP BY 維度

## 關鍵業務指標定義
- NPL（不良貸款）：npl_classification IN {NPL}
- NPL比率：NPL 的 outstanding_balance_twd 合計 / 全部 outstanding_balance_twd 合計 × 100
- 廣義逾期率：days_overdue > 0 的未償餘額 / 總未償餘額
- 備抵提列率：正常 1%、應注意 2%、可望收回 10%、收回困難 50%、收回無望 100%
- AUM（資產管理規模）：customers.total_aum_twd
- 客戶分級：Private（AUM≥3,000萬）、Wealth（500萬–2,999萬）、Preferred（100萬–499萬）、Retail（<100萬）
- 有效客戶：customers.is_active = TRUE
- KYC狀態：customers.kyc_status（Verified/Pending/Expired）
- 高風險客戶：customers.risk_rating = 'High'
- 可疑交易：transactions.status = 'Suspicious'
- 數位管道：transactions.channel IN ('Mobile','Online')
- 傳統管道：transactions.channel IN ('Branch_Counter','Branch_Teller','ATM')（臨櫃 = Branch_Counter、Branch_Teller）
- 分行層級的 NPL 比率若問「公告/官方」數字用 branches.npl_ratio_pct；若問「實際放款組合」則用 loans 依 branch_id 計算
- loans 為800筆抽樣放款明細：比率（NPL比率、逾期率、類別結構）可用 loans 計算，與報告一致；但金額總和不等於全行放款規模。
  問到全行放款總額、NPL總金額（億元）等絕對規模時，以 reports 的報告數字為準；分行放款規模以 branches.total_loans_twd 為準

## 知識文件使用規則
- 凡涉及法規、合規、SOP、審核流程的問題，查詢 policy_docs 的 content 欄位，並在回答中引用文件標題
- 凡涉及季報、財報、風險分析、策略報告的問題，查詢 reports 的 full_text 欄位
- 文件對照（filename）：
  - AML/KYC、洗錢防制、盡職調查、可疑交易申報 → aml_kyc_policy.md
  - NPL催收、逾期處理、協商方案 → npl_collection_sop.md
  - 授信審核、核准權限 → credit_approval_sop.md
  - 開戶、客戶分級 → customer_onboarding_sop.md
  - 投資適合度、KYC風險屬性 → investment_suitability_sop.md
  - 詐欺防制 → fraud_prevention_policy.md
  - 房貸核貸 → mortgage_approval_sop.md
  - 數位銀行資安、MFA → digital_banking_security.md
  - 作業風險、Basel → operational_risk_framework.md
  - 客訴 → customer_complaint_sop.md
  - 分行營運、KPI → branch_operations_sop.md
  - 財富管理、私人銀行服務 → wealth_management_policy.md
  - Q1/Q2 財報 → q1_2024_financial_results.pdf、q2_2024_financial_results.pdf
  - Q3 風險管理報告、風險委員會建議 → q3_2024_risk_management_report.pdf
  - 2023 年報 → 2023_annual_report.pdf
  - NPL 深度分析、建設業 → 2024_npl_deep_dive_analysis.pdf
  - 數位轉型策略 → digital_transformation_strategy_2024.pdf
- 不要回答「資料庫中沒有此資訊」——一律先依上表從 policy_docs 或 reports 取出全文再回答

## 輸出格式規範
- 金額以新台幣（TWD）加千位分隔符顯示（如 NT$1,234,567），大額可另以「億元」表示
- 比率保留2位小數（如 1.83%）
- 比較多個項目時，加上件數/金額讓結果更有說服力
- 使用者以繁體中文提問時，以繁體中文回答
- 涉及客戶姓名等敏感個資時，提醒需依個人資料保護法規處理
"""

JOINS = [
    ("accounts", "customer_id", "customers", "customer_id"),
    ("transactions", "account_id", "accounts", "account_id"),
    ("transactions", "customer_id", "customers", "customer_id"),
    ("loans", "customer_id", "customers", "customer_id"),
    ("loans", "branch_id", "branches", "branch_id"),
    ("accounts", "branch_id", "branches", "branch_id"),
    ("customers", "branch_id", "branches", "branch_id"),
]

SQL_NPL_BY_TYPE = f"""SELECT
  loan_type,
  COUNT(*) AS loan_count,
  SUM(outstanding_balance_twd) AS outstanding_balance_twd,
  SUM(CASE WHEN npl_classification IN {NPL} THEN outstanding_balance_twd ELSE 0 END) AS npl_amount_twd,
  ROUND(SUM(CASE WHEN npl_classification IN {NPL} THEN outstanding_balance_twd ELSE 0 END)
        / NULLIF(SUM(outstanding_balance_twd), 0) * 100, 2) AS npl_ratio_pct
FROM {t('loans')}
GROUP BY loan_type
ORDER BY npl_ratio_pct DESC"""

SQL_BRANCH_RANK = f"""SELECT
  b.branch_name,
  b.region,
  b.total_deposits_twd,
  b.total_loans_twd,
  b.npl_ratio_pct,
  b.deposit_growth_yoy_pct,
  RANK() OVER (ORDER BY b.npl_ratio_pct DESC) AS npl_risk_rank,
  RANK() OVER (ORDER BY b.deposit_growth_yoy_pct DESC) AS deposit_growth_rank
FROM {t('branches')} b
ORDER BY b.npl_ratio_pct DESC"""

SQL_SEGMENT_AUM = f"""SELECT
  customer_segment,
  COUNT(*) AS customer_count,
  ROUND(AVG(total_aum_twd)) AS avg_aum_twd,
  SUM(total_aum_twd) AS sum_aum_twd,
  ROUND(AVG(total_aum_twd) / 10000, 1) AS avg_aum_10k,
  ROUND(SUM(total_aum_twd) / 100000000.0, 2) AS sum_aum_100m
FROM {t('customers')}
WHERE is_active = TRUE
GROUP BY customer_segment
ORDER BY sum_aum_twd DESC"""

SQL_CHANNEL_TREND = f"""SELECT
  YEAR(transaction_date) AS txn_year,
  QUARTER(transaction_date) AS txn_quarter,
  COUNT(*) AS total_txn_count,
  SUM(CASE WHEN channel IN ('Mobile','Online') THEN 1 ELSE 0 END) AS digital_txn_count,
  SUM(CASE WHEN channel IN ('Branch_Counter','Branch_Teller') THEN 1 ELSE 0 END) AS branch_txn_count,
  SUM(CASE WHEN channel = 'ATM' THEN 1 ELSE 0 END) AS atm_txn_count,
  ROUND(SUM(CASE WHEN channel IN ('Mobile','Online') THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS digital_pct
FROM {t('transactions')}
GROUP BY YEAR(transaction_date), QUARTER(transaction_date)
ORDER BY txn_year, txn_quarter"""

SQL_SUSPICIOUS_CUSTOMERS = f"""SELECT
  c.customer_id,
  c.full_name,
  c.customer_segment,
  c.risk_rating,
  c.kyc_status,
  c.total_aum_twd,
  COUNT(t.transaction_id) AS suspicious_count,
  SUM(t.amount_twd) AS suspicious_total_twd
FROM {t('transactions')} t
JOIN {t('customers')} c ON t.customer_id = c.customer_id
WHERE t.status = 'Suspicious'
GROUP BY c.customer_id, c.full_name, c.customer_segment, c.risk_rating, c.kyc_status, c.total_aum_twd
ORDER BY suspicious_count DESC, suspicious_total_twd DESC"""

NPL_ORDER = """CASE npl_classification
  WHEN '正常' THEN 1 WHEN '應注意' THEN 2 WHEN '可望收回' THEN 3
  WHEN '收回困難' THEN 4 WHEN '收回無望' THEN 5 END"""

SQL_NPL_PROVISION = f"""SELECT
  npl_classification,
  COUNT(*) AS loan_count,
  SUM(outstanding_balance_twd) AS outstanding_balance_twd,
  ROUND(SUM(outstanding_balance_twd) / 100000000.0, 2) AS outstanding_100m_twd,
  CASE npl_classification
    WHEN '正常' THEN 1.0 WHEN '應注意' THEN 2.0 WHEN '可望收回' THEN 10.0
    WHEN '收回困難' THEN 50.0 WHEN '收回無望' THEN 100.0
  END AS provision_rate_pct,
  ROUND(SUM(outstanding_balance_twd) * CASE npl_classification
    WHEN '正常' THEN 0.01 WHEN '應注意' THEN 0.02 WHEN '可望收回' THEN 0.10
    WHEN '收回困難' THEN 0.50 WHEN '收回無望' THEN 1.00
  END / 100000000.0, 2) AS required_provision_100m_twd
FROM {t('loans')}
GROUP BY npl_classification
ORDER BY {NPL_ORDER}"""

SQL_POLICY_LOOKUP = f"""SELECT title, content
FROM {t('policy_docs')}
WHERE filename = 'npl_collection_sop.md'"""

SQL_REPORT_LOOKUP = f"""SELECT filename, full_text
FROM {t('reports')}
WHERE filename = 'q3_2024_risk_management_report.pdf'"""

SQL_METRIC_VIEW = f"""SELECT
  branch_region,
  MEASURE(loan_count) AS loan_count,
  MEASURE(outstanding_balance) AS outstanding_balance_twd,
  MEASURE(npl_amount) AS npl_amount_twd,
  ROUND(MEASURE(npl_amount) / MEASURE(outstanding_balance) * 100, 2) AS npl_ratio_pct
FROM {t('loan_metrics')}
GROUP BY branch_region
ORDER BY npl_ratio_pct DESC"""

EXAMPLES = [
    ("各貸款類型的NPL比率和未償金額是多少？", SQL_NPL_BY_TYPE),
    ("各分行的存款、放款和NPL比率排名", SQL_BRANCH_RANK),
    ("各客戶等級的人數、平均AUM和總AUM是多少？", SQL_SEGMENT_AUM),
    ("2022到2024年行動與線上管道的交易筆數和佔比趨勢", SQL_CHANNEL_TREND),
    ("有可疑交易紀錄的客戶名單和風險狀況", SQL_SUSPICIOUS_CUSTOMERS),
    ("NPL五分類的件數、金額分布和備抵提列狀況", SQL_NPL_PROVISION),
    ("我們的逾期貸款催收SOP是什麼？", SQL_POLICY_LOOKUP),
    ("Q3風險管理報告的重點是什麼？", SQL_REPORT_LOOKUP),
    ("各區域的NPL比率（用貸款指標 Metric View）", SQL_METRIC_VIEW),
]

SAMPLE_QUESTIONS = [
    "我們目前的NPL比率是多少？請按貸款類型分解，並顯示各類型的放款金額和逾期狀況",
    "比較各分行的存款規模、放款規模和NPL比率，找出績效最好和最需要關注的前五名分行",
    "2022到2024年，行動/線上管道的交易佔比如何變化？和ATM、臨櫃比較",
    "對於已進入「可望收回」分類的客戶，我們的標準催收程序是什麼？有哪些協商方案？",
    "根據2024年Q3風險管理報告，目前最需要關注的信用風險是哪些？",
    "找出 risk_rating = 'High' 且有可疑交易紀錄的客戶，並說明依AML/KYC政策應啟動什麼調查程序",
]

BENCHMARKS = [
    ("各貸款類型的NPL比率和未償金額是多少？", SQL_NPL_BY_TYPE, None),
    ("NPL五種分類各有多少件？未償餘額各是多少？", f"""SELECT
  npl_classification,
  COUNT(*) AS loan_count,
  SUM(outstanding_balance_twd) AS outstanding_balance_twd
FROM {t('loans')}
GROUP BY npl_classification
ORDER BY {NPL_ORDER}""", None),
    ("各客戶等級的人數和總AUM是多少？", f"""SELECT
  customer_segment,
  COUNT(*) AS customer_count,
  SUM(total_aum_twd) AS sum_aum_twd
FROM {t('customers')}
WHERE is_active = TRUE
GROUP BY customer_segment
ORDER BY sum_aum_twd DESC""", None),
    ("2022、2023、2024年各年度行動銀行（Mobile）交易佔比是多少？", f"""SELECT
  YEAR(transaction_date) AS txn_year,
  COUNT(*) AS total_txn_count,
  SUM(CASE WHEN channel = 'Mobile' THEN 1 ELSE 0 END) AS mobile_count,
  ROUND(SUM(CASE WHEN channel = 'Mobile' THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) AS mobile_pct
FROM {t('transactions')}
GROUP BY YEAR(transaction_date)
ORDER BY txn_year""", None),
    ("有可疑交易的客戶共幾位？哪位客戶的可疑交易件數最多？", f"""SELECT
  c.customer_id,
  c.full_name,
  c.customer_segment,
  c.risk_rating,
  COUNT(t.transaction_id) AS suspicious_count,
  SUM(t.amount_twd) AS suspicious_total_twd
FROM {t('transactions')} t
JOIN {t('customers')} c ON t.customer_id = c.customer_id
WHERE t.status = 'Suspicious'
GROUP BY c.customer_id, c.full_name, c.customer_segment, c.risk_rating
ORDER BY suspicious_count DESC""", None),
    ("同時有高風險評等（risk_rating = High）又有可疑交易紀錄的客戶有哪些？他們的AUM和可疑交易金額各是多少？", None,
     "答案應包含：客戶姓名、客戶等級、AUM金額、可疑交易件數、可疑交易總金額。"
     "必須同時滿足兩個條件：risk_rating = 'High' 且有 status = 'Suspicious' 的交易紀錄。"
     "結果應按可疑交易件數或金額排序。"),
]


def build():
    tables = []
    for name in sorted(TABLES, key=t):
        entry = {"identifier": t(name)}
        cols = ENTITY_COLUMNS.get(name, [])
        if cols:
            entry["column_configs"] = [
                {"column_name": c, "enable_format_assistance": True, "enable_entity_matching": True}
                for c in sorted(cols)
            ]
        tables.append(entry)

    join_specs = [
        {
            "id": hid("join", lt, lc, rt, rc),
            "left": {"identifier": t(lt), "alias": lt},
            "right": {"identifier": t(rt), "alias": rt},
            "sql": [f"`{lt}`.`{lc}` = `{rt}`.`{rc}`", "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"],
        }
        for lt, lc, rt, rc in JOINS
    ]

    benchmarks = []
    for q, sql, note in BENCHMARKS:
        b = {"id": hid("bench", q), "question": [q], "answer": [{"format": "SQL", "content": [sql] if sql else []}]}
        if note:
            b["evaluation_note"] = [note]
        benchmarks.append(b)

    return {
        "version": 2,
        "config": {
            "sample_questions": sorted(
                [{"id": hid("sample", q), "question": [q]} for q in SAMPLE_QUESTIONS], key=lambda x: x["id"]
            )
        },
        "data_sources": {"tables": tables, "metric_views": [{"identifier": t("loan_metrics")}]},
        "instructions": {
            "text_instructions": [{"id": hid("text"), "content": [TEXT_INSTRUCTIONS]}],
            "example_question_sqls": sorted(
                [{"id": hid("example", q), "question": [q], "sql": [s]} for q, s in EXAMPLES],
                key=lambda x: x["id"],
            ),
            "join_specs": sorted(join_specs, key=lambda x: x["id"]),
        },
        "benchmarks": {"questions": sorted(benchmarks, key=lambda x: x["id"])},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--space-id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    space = json.dumps(build(), ensure_ascii=False)
    if args.dry_run:
        print(space)
        return
    body = {"serialized_space": space, "title": TITLE, "description": DESCRIPTION, "warehouse_id": WAREHOUSE_ID}
    if args.space_id:
        cmd = ["databricks", "api", "patch", f"/api/2.0/genie/spaces/{args.space_id}"]
    else:
        cmd = ["databricks", "api", "post", "/api/2.0/genie/spaces"]
    out = subprocess.run(cmd + ["--profile", PROFILE, "--json", json.dumps(body, ensure_ascii=False)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(out.stderr or out.stdout)
    resp = json.loads(out.stdout)
    print(json.dumps({k: resp.get(k) for k in ("space_id", "title")}, ensure_ascii=False))
    print("Genie Space 已就緒：在 workspace 左側選單 Genie 中開啟。之後更新請使用 --space-id", resp.get("space_id"))


if __name__ == "__main__":
    main()
