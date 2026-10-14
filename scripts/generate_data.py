"""
Banking demo data generator for FSI Genie Demo
Bank: 星河商業銀行 (Galaxy Commercial Bank)
"""
import csv
import random
import os
from datetime import date, timedelta

random.seed(42)

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "csv")
os.makedirs(BASE, exist_ok=True)

# ─── helpers ────────────────────────────────────────────────────────────────

def rand_date(start, end):
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def fmt(d):
    return d.strftime("%Y-%m-%d")

FIRST_NAMES = ["志明","淑芬","建志","雅婷","俊宏","怡君","文龍","佳蓉",
               "宗翰","雅雯","明哲","慧珍","世傑","欣怡","政賢","美玲",
               "嘉宏","秀蘭","冠廷","淑惠","駿傑","雅玲","天恩","靜宜",
               "承翰","曉萍","柏翰","詩婷","晉維","玉芳"]
LAST_NAMES  = ["陳","林","黃","張","李","王","吳","劉","蔡","楊",
               "許","鄭","謝","洪","郭","邱","曾","廖","賴","徐",
               "周","葉","蘇","莊","江","呂","何","羅","高","簡"]

# 依台灣實際人口比例加權，銀行客戶再向都會區偏移
CITY_WEIGHTS = {
    "新北市": 17.0, "台北市": 13.0, "台中市": 11.5, "高雄市": 10.5,
    "桃園市":  9.0, "台南市":  7.0, "彰化縣":  4.5, "新竹市":  2.5,
    "新竹縣":  2.5, "屏東縣":  3.0, "苗栗縣":  2.0, "雲林縣":  2.5,
    "南投縣":  2.0, "宜蘭縣":  2.0, "嘉義縣":  2.0, "嘉義市":  1.0,
    "基隆市":  1.5, "花蓮縣":  1.5, "台東縣":  0.5,
}
# Private/Wealth 高資產客戶更集中於北部都會
CITY_WEIGHTS_PREMIUM = {
    "台北市": 35.0, "新北市": 20.0, "台中市": 12.0, "高雄市":  8.0,
    "桃園市":  7.0, "台南市":  5.0, "新竹市":  4.0, "新竹縣":  2.0,
    "彰化縣":  2.0, "嘉義市":  1.0, "基隆市":  1.0, "花蓮縣":  0.5,
    "屏東縣":  0.5, "苗栗縣":  0.5, "雲林縣":  0.5, "南投縣":  0.3,
    "宜蘭縣":  0.3, "嘉義縣":  0.3, "台東縣":  0.1,
}

def pick_city(segment):
    if segment in ("Private", "Wealth"):
        return random.choices(list(CITY_WEIGHTS_PREMIUM.keys()),
                              weights=list(CITY_WEIGHTS_PREMIUM.values()), k=1)[0]
    return random.choices(list(CITY_WEIGHTS.keys()),
                          weights=list(CITY_WEIGHTS.values()), k=1)[0]

OCCUPATIONS = ["上班族","企業主","自由業","公務員","醫師","律師","工程師",
               "教師","退休人士","學生","金融業","製造業主管","貿易業"]

# ─── 1. branches.csv  (30 branches) ────────────────────────────────────────

branch_rows = []
branch_ids  = []

branch_templates = [
    ("台北信義分行","台北市","北區"),("台北大安分行","台北市","北區"),
    ("台北中山分行","台北市","北區"),("台北內湖分行","台北市","北區"),
    ("台北士林分行","台北市","北區"),("新北板橋分行","新北市","北區"),
    ("新北中和分行","新北市","北區"),("桃園中壢分行","桃園市","北區"),
    ("新竹竹北分行","新竹市","北區"),("基隆仁愛分行","基隆市","北區"),
    ("台中西屯分行","台中市","中區"),("台中北屯分行","台中市","中區"),
    ("台中南屯分行","台中市","中區"),("彰化中正分行","彰化縣","中區"),
    ("南投草屯分行","南投縣","中區"),("台南東區分行","台南市","南區"),
    ("台南北區分行","台南市","南區"),("高雄前鎮分行","高雄市","南區"),
    ("高雄左營分行","高雄市","南區"),("高雄三民分行","高雄市","南區"),
    ("高雄楠梓分行","高雄市","南區"),("嘉義中正分行","嘉義市","南區"),
    ("屏東市區分行","屏東縣","南區"),("花蓮中正分行","花蓮縣","東區"),
    ("台東成功分行","台東縣","東區"),("宜蘭羅東分行","宜蘭縣","東區"),
    ("信義財富管理中心","台北市","北區"),("敦南貴賓理財中心","台北市","北區"),
    ("台中財富管理中心","台中市","中區"),("高雄財富管理中心","高雄市","南區"),
]

manager_names = [f"{random.choice(LAST_NAMES)}{random.choice(FIRST_NAMES)}" for _ in range(30)]

for i, (bname, bcity, bregion) in enumerate(branch_templates):
    bid = f"BR{i+1:03d}"
    branch_ids.append(bid)
    open_yr = random.randint(1995, 2018)
    is_wealth = "財富" in bname or "貴賓" in bname
    deposits   = random.randint(2_000_000, 50_000_000) * 1000 if is_wealth else random.randint(500_000, 8_000_000) * 1000
    loans_     = int(deposits * random.uniform(0.55, 0.80))
    num_cust   = random.randint(500, 3000) if not is_wealth else random.randint(200, 800)
    monthly_tx = random.randint(3000, 30000)
    staff      = random.randint(8, 45)
    npl        = round(random.uniform(0.5, 4.5), 2)
    dep_growth = round(random.uniform(-3.0, 12.0), 2)
    branch_rows.append({
        "branch_id": bid, "branch_name": bname, "city": bcity, "region": bregion,
        "opening_year": open_yr, "branch_manager": manager_names[i],
        "total_deposits_twd": deposits, "total_loans_twd": loans_,
        "number_of_customers": num_cust, "monthly_transactions": monthly_tx,
        "staff_count": staff, "npl_ratio_pct": npl,
        "deposit_growth_yoy_pct": dep_growth,
        "is_wealth_center": str(is_wealth).upper()
    })

with open(f"{BASE}/branches.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(branch_rows[0].keys()))
    w.writeheader(); w.writerows(branch_rows)
print(f"branches.csv: {len(branch_rows)} rows")

# ─── 2. customers.csv (500 customers) ───────────────────────────────────────

customer_rows = []
customer_ids  = []
rm_ids = [f"RM{i:03d}" for i in range(1, 41)]   # 40 relationship managers

SEGMENTS = {
    "Private":   (30_000_000, 200_000_000),   # AUM > 3000萬
    "Wealth":    (5_000_000,  29_999_999),    # AUM 500萬~3000萬
    "Preferred": (1_000_000,   4_999_999),    # AUM 100萬~500萬
    "Retail":    (10_000,       999_999),     # AUM < 100萬
}
SEG_WEIGHTS = [25, 75, 150, 250]   # Private:Wealth:Preferred:Retail ≈ 5:15:30:50

seg_list = (["Private"]*25 + ["Wealth"]*75 + ["Preferred"]*150 + ["Retail"]*250)
random.shuffle(seg_list)

for i in range(500):
    cid = f"CUS{i+1:04d}"
    customer_ids.append(cid)
    seg = seg_list[i]
    aum_lo, aum_hi = SEGMENTS[seg]
    aum = random.randint(aum_lo, aum_hi)
    annual_income = int(aum * random.uniform(0.05, 0.4))
    fname = random.choice(LAST_NAMES) + random.choice(FIRST_NAMES)
    city  = pick_city(seg)
    branch_id = random.choice(branch_ids)
    rm = random.choice(rm_ids) if seg in ("Private","Wealth","Preferred") else ""
    kyc = random.choices(["Verified","Pending","Expired"], weights=[85,10,5])[0]
    risk = random.choices(["Low","Medium","High"], weights=[60,30,10])[0]
    onboard = rand_date(date(2005,1,1), date(2023,12,31))
    occ = random.choice(OCCUPATIONS)
    age = random.randint(22, 75)
    is_active = random.choices(["TRUE","FALSE"], weights=[92,8])[0]
    customer_rows.append({
        "customer_id": cid, "full_name": fname, "age": age,
        "gender": random.choice(["M","F"]),
        "occupation": occ, "annual_income_twd": annual_income,
        "customer_segment": seg,
        "relationship_manager_id": rm,
        "onboarding_date": fmt(onboard),
        "city": city, "branch_id": branch_id,
        "kyc_status": kyc, "risk_rating": risk,
        "total_aum_twd": aum, "is_active": is_active
    })

with open(f"{BASE}/customers.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(customer_rows[0].keys()))
    w.writeheader(); w.writerows(customer_rows)
print(f"customers.csv: {len(customer_rows)} rows")

# ─── 3. accounts.csv (~1,000 accounts, ~2 per customer) ─────────────────────

account_rows = []
account_ids  = []
ACCT_TYPES   = ["Savings","Checking","Time_Deposit","Investment","Credit_Card"]

acc_counter = 1
for cust in customer_rows:
    cid = cust["customer_id"]
    seg = cust["customer_segment"]
    num_accts = 1 if seg == "Retail" else (2 if seg == "Preferred" else 3)
    types_pool = ACCT_TYPES if seg in ("Wealth","Private") else ACCT_TYPES[:3]
    chosen_types = random.sample(types_pool, min(num_accts, len(types_pool)))
    for atype in chosen_types:
        aid = f"ACC{acc_counter:05d}"
        account_ids.append(aid)
        acc_counter += 1
        open_d = rand_date(date.fromisoformat(cust["onboarding_date"]), date(2024,12,31))
        if atype == "Savings":
            balance = random.randint(10_000, 5_000_000)
            rate = round(random.uniform(0.01, 1.00), 3)
        elif atype == "Checking":
            balance = random.randint(5_000, 2_000_000)
            rate = 0.0
        elif atype == "Time_Deposit":
            balance = random.randint(100_000, 20_000_000)
            rate = round(random.uniform(1.50, 4.50), 3)
        elif atype == "Investment":
            balance = random.randint(500_000, 30_000_000)
            rate = 0.0
        else:  # Credit_Card
            balance = random.randint(0, 200_000)   # outstanding balance
            rate = round(random.uniform(10.0, 19.7), 2)
        status = random.choices(["Active","Dormant","Closed"], weights=[90,7,3])[0]
        account_rows.append({
            "account_id": aid, "customer_id": cid,
            "account_type": atype,
            "opening_date": fmt(open_d),
            "balance_twd": balance,
            "interest_rate_pct": rate,
            "branch_id": cust["branch_id"],
            "status": status
        })

with open(f"{BASE}/accounts.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(account_rows[0].keys()))
    w.writeheader(); w.writerows(account_rows)
print(f"accounts.csv: {len(account_rows)} rows")

# ─── 4. transactions.csv (~6,000 transactions 2022-2024) ────────────────────

tx_rows = []
TX_TYPES    = ["Deposit","Withdrawal","Transfer","Payment","Investment","Loan_Repayment"]
TX_WEIGHTS  = [20, 20, 25, 20, 8, 7]
CHANNELS    = ["Mobile","Online","ATM","Branch_Counter","Branch_Teller"]
CHAN_WEIGHTS = [35, 25, 20, 12, 8]
MERCH_CATS  = ["餐飲","零售","交通","醫療","教育","娛樂","公用事業","保險","投資","其他"]

# map account_id -> customer_id
acct_to_cust = {a["account_id"]: a["customer_id"] for a in account_rows}
active_accts = [a["account_id"] for a in account_rows if a["status"] == "Active"]

for i in range(6000):
    tid  = f"TXN{i+1:06d}"
    aid  = random.choice(active_accts)
    cid  = acct_to_cust[aid]
    tdate = rand_date(date(2022,1,1), date(2024,12,31))
    ttype = random.choices(TX_TYPES, weights=TX_WEIGHTS)[0]
    chan  = random.choices(CHANNELS, weights=CHAN_WEIGHTS)[0]
    if ttype in ("Deposit","Investment"):
        amt = random.randint(10_000, 5_000_000)
    elif ttype == "Withdrawal":
        amt = random.randint(1_000, 500_000)
    elif ttype == "Transfer":
        amt = random.randint(5_000, 2_000_000)
    elif ttype == "Payment":
        amt = random.randint(500, 300_000)
    else:  # Loan_Repayment
        amt = random.randint(3_000, 100_000)
    mcat  = random.choice(MERCH_CATS) if ttype == "Payment" else ""
    # ~2% suspicious
    status = random.choices(["Completed","Pending","Failed","Suspicious"],
                            weights=[92, 3, 3, 2])[0]
    tx_rows.append({
        "transaction_id": tid, "account_id": aid, "customer_id": cid,
        "transaction_date": fmt(tdate),
        "transaction_type": ttype, "amount_twd": amt,
        "channel": chan, "merchant_category": mcat,
        "status": status
    })

with open(f"{BASE}/transactions.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(tx_rows[0].keys()))
    w.writeheader(); w.writerows(tx_rows)
print(f"transactions.csv: {len(tx_rows)} rows")

# ─── 5. loans.csv (~800 loans) ──────────────────────────────────────────────

loan_rows = []
LOAN_TYPES    = ["Mortgage","Car_Loan","Personal_Loan","Business_Loan","Credit_Card_Revolving"]
LOAN_WEIGHTS  = [35, 15, 25, 15, 10]
COLLATERALS   = ["不動產","汽車","無擔保","企業資產","有價證券"]
NPL_CLASSES   = ["正常","應注意","可望收回","收回困難","收回無望"]
NPL_WEIGHTS   = [78, 10, 6, 4, 2]

borrower_pool = [c["customer_id"] for c in customer_rows
                 if c["customer_segment"] in ("Retail","Preferred","Wealth","Private")]

for i in range(800):
    lid   = f"LN{i+1:05d}"
    cid   = random.choice(borrower_pool)
    ltype = random.choices(LOAN_TYPES, weights=LOAN_WEIGHTS)[0]
    if ltype == "Mortgage":
        principal = random.randint(2_000_000, 20_000_000)
        coll = "不動產"
        rate = round(random.uniform(1.5, 3.5), 3)
        term_yrs = random.randint(10, 30)
    elif ltype == "Car_Loan":
        principal = random.randint(300_000, 2_000_000)
        coll = "汽車"
        rate = round(random.uniform(2.5, 5.0), 3)
        term_yrs = random.randint(3, 7)
    elif ltype == "Personal_Loan":
        principal = random.randint(50_000, 1_000_000)
        coll = "無擔保"
        rate = round(random.uniform(4.0, 15.0), 3)
        term_yrs = random.randint(1, 7)
    elif ltype == "Business_Loan":
        principal = random.randint(500_000, 50_000_000)
        coll = random.choice(["不動產","企業資產","有價證券"])
        rate = round(random.uniform(2.0, 6.0), 3)
        term_yrs = random.randint(1, 10)
    else:  # CC revolving
        principal = random.randint(10_000, 300_000)
        coll = "無擔保"
        rate = round(random.uniform(12.0, 19.7), 3)
        term_yrs = 1
    start_d = rand_date(date(2015,1,1), date(2024,6,30))
    try:
        end_d = date(start_d.year + term_yrs, start_d.month, start_d.day)
    except ValueError:
        end_d = date(start_d.year + term_yrs, start_d.month, 28)
    payoff_ratio = random.uniform(0.0, 0.95)
    outstanding  = int(principal * (1 - payoff_ratio))
    monthly_pmt  = int(principal / (term_yrs * 12) * 1.05)
    npl_class = random.choices(NPL_CLASSES, weights=NPL_WEIGHTS)[0]
    days_od   = 0
    if npl_class == "應注意":      days_od = random.randint(1, 30)
    elif npl_class == "可望收回":  days_od = random.randint(31, 90)
    elif npl_class == "收回困難":  days_od = random.randint(91, 180)
    elif npl_class == "收回無望":  days_od = random.randint(181, 730)
    bid = random.choice(branch_ids)
    loan_rows.append({
        "loan_id": lid, "customer_id": cid, "branch_id": bid,
        "loan_type": ltype, "loan_amount_twd": principal,
        "outstanding_balance_twd": outstanding,
        "interest_rate_pct": rate,
        "loan_start_date": fmt(start_d),
        "loan_end_date": fmt(end_d),
        "monthly_payment_twd": monthly_pmt,
        "days_overdue": days_od,
        "npl_classification": npl_class,
        "collateral_type": coll
    })

with open(f"{BASE}/loans.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(loan_rows[0].keys()))
    w.writeheader(); w.writerows(loan_rows)
print(f"loans.csv: {len(loan_rows)} rows")

print("\n✅ All CSV files generated successfully.")
