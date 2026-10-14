"""
Rebalance NPL classification in loans.csv so it is consistent with branches.csv and the PDF reports.

- Each branch's NPL ratio computed from loans (by outstanding balance) matches branches.npl_ratio_pct
- Bank-wide: NPL ≈ 2.3–2.4% (Q3 risk report), broad overdue incl. 應注意 ≈ 4.9% (NPL deep-dive)
- Mortgages are the least likely to become NPL; personal / credit card / business loans the most
- Top-5 NPL branches follow the class mix in branch_npl_risk_analysis_2024q3.pdf

Only npl_classification, days_overdue and outstanding_balance_twd of the selected NPL loans change.
"""
import csv
import os
import random

random.seed(2024)

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "csv")
NPL_CLASSES = ["可望收回", "收回困難", "收回無望"]
WATCH_RATIO = 0.026  # 應注意 share of balance -> broad overdue ≈ NPL + 2.6% ≈ 4.9%

# Relative chance of a loan type being picked as NPL. Business loans carry most NPL balance,
# mortgages the least (NPL deep-dive: mortgage 0.31%, SME/corporate 3–4%)
NPL_TYPE_WEIGHT = {"Mortgage": 0.3, "Car_Loan": 0.5, "Personal_Loan": 1.0,
                   "Credit_Card_Revolving": 1.0, "Business_Loan": 3.0}
WATCH_TYPE_WEIGHT = {"Mortgage": 1.0, "Car_Loan": 1.0, "Personal_Loan": 1.5,
                     "Credit_Card_Revolving": 1.5, "Business_Loan": 1.5}

# NPL balance mix per class (default from Q3 report: 1.4 / 0.6 / 0.4)
DEFAULT_MIX = {"可望收回": 0.58, "收回困難": 0.25, "收回無望": 0.17}
BRANCH_MIX = {  # from branch_npl_risk_analysis_2024q3.pdf
    "高雄前鎮分行":     {"可望收回": 0.92, "收回困難": 0.05, "收回無望": 0.03},
    "信義財富管理中心": {"可望收回": 0.0,  "收回困難": 0.68, "收回無望": 0.32},
    "高雄楠梓分行":     {"可望收回": 1.0,  "收回困難": 0.0,  "收回無望": 0.0},
    "宜蘭羅東分行":     {"可望收回": 0.02, "收回困難": 0.94, "收回無望": 0.04},
    "台南北區分行":     {"可望收回": 0.16, "收回困難": 0.84, "收回無望": 0.0},
}
DAYS = {"正常": (0, 0), "應注意": (1, 30), "可望收回": (31, 90), "收回困難": (91, 180), "收回無望": (181, 730)}


def read(name):
    with open(os.path.join(BASE, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def weighted_order(loans, weight):
    """Random order where higher-weight loans tend to come first."""
    return sorted(loans, key=lambda l: random.random() ** (1.0 / weight(l)), reverse=True)


def pick_until(candidates, budget, limit):
    """Greedily pick up to `limit` loans whose balances fit within budget."""
    picked, total = [], 0
    for l in candidates:
        bal = int(l["outstanding_balance_twd"])
        if len(picked) < limit and 0 < bal and total + bal <= budget:
            picked.append(l)
            total += bal
    return picked, total


def assign_classes(npl_loans, mix):
    """Assign 可望收回/收回困難/收回無望 so each class's balance share approximates mix."""
    total = sum(int(l["outstanding_balance_twd"]) for l in npl_loans)
    remaining = {c: mix[c] * total for c in NPL_CLASSES}
    for l in sorted(npl_loans, key=lambda l: -int(l["outstanding_balance_twd"])):
        cls = max(NPL_CLASSES, key=lambda c: remaining[c])
        l["npl_classification"] = cls
        remaining[cls] -= int(l["outstanding_balance_twd"])


loans = read("loans.csv")
branches = {b["branch_id"]: b for b in read("branches.csv")}

for l in loans:
    l["npl_classification"] = "正常"

for bid, b in branches.items():
    bl = [l for l in loans if l["branch_id"] == bid]
    if not bl:
        continue
    target = float(b["npl_ratio_pct"]) / 100
    n_npl = 4 if b["branch_name"] in BRANCH_MIX else random.randint(1, 3)

    # Pick a few NPL loans, then scale their outstanding balances so the branch ratio hits the target:
    #   k*S / (T_others + k*S) = target
    # If scaling up would exceed a loan's principal, add one more loan and retry.
    candidates = [l for l in weighted_order(bl, lambda l: NPL_TYPE_WEIGHT[l["loan_type"]])
                  if int(l["outstanding_balance_twd"]) > 0]
    while True:
        picked = candidates[:n_npl]
        s_npl = sum(int(l["outstanding_balance_twd"]) for l in picked)
        t_others = sum(int(l["outstanding_balance_twd"]) for l in bl if l not in picked)
        k = target * t_others / (1 - target) / s_npl
        if k <= 1 or n_npl >= len(candidates) or all(
                int(l["outstanding_balance_twd"]) * k <= int(l["loan_amount_twd"]) for l in picked):
            break
        n_npl += 1
    for l in picked:
        l["outstanding_balance_twd"] = str(int(int(l["outstanding_balance_twd"]) * k))

    assign_classes(picked, BRANCH_MIX.get(b["branch_name"], DEFAULT_MIX))

    # 應注意 among the remaining performing loans
    branch_total = sum(int(l["outstanding_balance_twd"]) for l in bl)
    performing = [l for l in bl if l["npl_classification"] == "正常"]
    watch, _ = pick_until(weighted_order(performing, lambda l: WATCH_TYPE_WEIGHT[l["loan_type"]]),
                          WATCH_RATIO * branch_total, limit=4)
    for l in watch:
        l["npl_classification"] = "應注意"

for l in loans:
    lo, hi = DAYS[l["npl_classification"]]
    l["days_overdue"] = str(random.randint(lo, hi))

with open(os.path.join(BASE, "loans.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(loans[0].keys()))
    w.writeheader()
    w.writerows(loans)

# ── summary ──
tot = sum(int(l["outstanding_balance_twd"]) for l in loans)
npl = sum(int(l["outstanding_balance_twd"]) for l in loans if l["npl_classification"] in NPL_CLASSES)
od = sum(int(l["outstanding_balance_twd"]) for l in loans if l["npl_classification"] != "正常")
print(f"loans.csv rebalanced: NPL {npl / tot * 100:.2f}% | broad overdue {od / tot * 100:.2f}%")
