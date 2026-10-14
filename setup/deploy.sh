#!/usr/bin/env bash
# 一鍵部署：schema/volume → 上傳檔案 → Delta 表 / Metric View → Genie Space
# Usage: ./deploy.sh [--space-id <ID>]   （帶 --space-id 時更新既有 Genie Space）
set -euo pipefail
cd "$(dirname "$0")"
source ./config.env

if [[ "$CATALOG" == "your_catalog" || "$WAREHOUSE_ID" == "your_warehouse_id" ]]; then
  echo "請先編輯 setup/config.env，填入 CATALOG 與 WAREHOUSE_ID" >&2
  exit 1
fi

echo "[1/4] 建立 schema 與 volume：$CATALOG.$SCHEMA"
./run_sql.sh 00_schema.sql

echo "[2/4] 上傳 csv / markdown / pdf 至 /Volumes/$CATALOG/$SCHEMA/files"
for d in csv markdown pdf; do
  databricks fs cp -r "../data/$d" "dbfs:/Volumes/$CATALOG/$SCHEMA/files/$d" --overwrite --profile "$DATABRICKS_PROFILE" >/dev/null
  echo "  $d uploaded"
done

echo "[3/4] 建立 Delta 表、欄位註解與 Metric View（ai_parse_document 約需 1–2 分鐘）"
for f in 01_*.sql 02_policy_docs.sql 03_reports.sql 04_comments.sql 05_loan_metrics.sql; do
  echo " $f"
  ./run_sql.sh "$f"
done

echo "[4/4] 建立 Genie Space"
python3 build_genie_space.py "$@"
