CREATE OR REPLACE VIEW {{catalog}}.{{schema}}.loan_metrics
WITH METRICS LANGUAGE YAML AS $$
  version: 1.1
  comment: "星河銀行 貸款組合核心業務指標 — 可按任意維度切片分析 NPL、利率、逾期狀況"
  source: {{catalog}}.{{schema}}.loans

  joins:
    - name: customers
      source: {{catalog}}.{{schema}}.customers
      on: source.customer_id = customers.customer_id
      rely:
        at_most_one_match: true
    - name: branches
      source: {{catalog}}.{{schema}}.branches
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
