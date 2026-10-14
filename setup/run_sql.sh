#!/usr/bin/env bash
# Usage: ./run_sql.sh <file.sql>
# Replaces {{catalog}} / {{schema}} using config.env, then runs each ';'-terminated statement
# via the Statement Execution API (preserves YAML indentation for metric views).
set -euo pipefail
cd "$(dirname "$0")"
source ./config.env
FILE=$1

python3 -c '
import json, sys
src = open(sys.argv[1]).read().replace("{{catalog}}", sys.argv[2]).replace("{{schema}}", sys.argv[3])
parts = [src.strip().rstrip(";")] if "$$" in src else [p.strip() for p in src.split(";\n")]
for p in parts:
    if p: print(json.dumps(p))
' "$FILE" "$CATALOG" "$SCHEMA" | while IFS= read -r stmt; do
  databricks api post /api/2.0/sql/statements --profile "$DATABRICKS_PROFILE" \
    --json "{\"warehouse_id\":\"$WAREHOUSE_ID\",\"wait_timeout\":\"50s\",\"on_wait_timeout\":\"CONTINUE\",\"statement\":$stmt}" \
    | python3 -c '
import json, sys, subprocess, time
r = json.load(sys.stdin)
sid, state = r.get("statement_id"), r["status"]["state"]
while state in ("PENDING", "RUNNING"):
    time.sleep(5)
    r = json.loads(subprocess.check_output(["databricks", "api", "get", f"/api/2.0/sql/statements/{sid}", "--profile", sys.argv[1]]))
    state = r["status"]["state"]
err = r["status"].get("error", {}).get("message")
print(f"  {state}" + (f": {err}" if err else ""))
if state != "SUCCEEDED": sys.exit(1)
' "$DATABRICKS_PROFILE"
done
