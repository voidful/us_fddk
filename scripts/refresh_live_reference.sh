#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
cd "$project_dir"

lock_dir="$project_dir/artifacts/.refresh-live-reference.lock"
if ! mkdir "$lock_dir" 2>/dev/null; then
  lock_pid=""
  if [[ -f "$lock_dir/pid" ]]; then
    lock_pid="$(<"$lock_dir/pid")"
  fi
  if [[ "$lock_pid" =~ ^[0-9]+$ ]] && ! kill -0 "$lock_pid" 2>/dev/null; then
    rm "$lock_dir/pid"
    rmdir "$lock_dir"
    mkdir "$lock_dir"
    echo "Recovered stale LIVE refresh lock from process $lock_pid."
  else
    echo "Another LIVE refresh is running: $lock_dir" >&2
    exit 75
  fi
fi
echo "$$" > "$lock_dir/pid"
cleanup() {
  rm "$lock_dir/pid" 2>/dev/null || true
  rmdir "$lock_dir" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

readiness_path="$project_dir/artifacts/reference_readiness.json"
previous_data_through=""
if [[ -f "$readiness_path" ]]; then
  previous_data_through="$(python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("data_through") or "")' "$readiness_path")"
fi

python -m usfddk v25-live-update
python -m usfddk build "$@"
python -m usfddk reference-check
python -m usfddk v25-reference-check

(
  cd "$project_dir/site"
  npm run lint
  npm test
  npm audit --omit=dev --audit-level=high
  git diff --check
)

python -m usfddk refresh-status \
  --previous-data-through "$previous_data_through"
python -m usfddk v25-refresh-status
python -m usfddk paper status
if python -c 'import json,sys; paths=sys.argv[1:]; raise SystemExit(0 if all(json.load(open(path, encoding="utf-8"))["private_deploy_allowed"] for path in paths) else 1)' artifacts/live_refresh_status.json artifacts/v25_live_refresh_status.json; then
  echo "LIVE and v25 data advanced together; private deployment may proceed after owner-only access verification."
else
  echo "No jointly verified new session; no site version should be created."
fi
echo "Paper evidence integrity passed; inspect reference_readiness.json and v25_reference_readiness.json."
echo "A successful refresh does not authorize real-money reference trading."
