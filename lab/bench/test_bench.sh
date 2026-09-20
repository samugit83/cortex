#!/usr/bin/env bash
# test_bench.sh — bench.py's own failure modes, on a clone of the lab repo with a
# fake `claude` (no API calls, nothing written to the real lab or to bench/).
#
#   ./lab/bench/test_bench.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_HOME="$(cd "$HERE/.." && pwd)"
SRC_REPO="${LAB_REPO:-$(cd "$LAB_HOME/../.." && pwd)/cortex-lab}"
T="${TMPDIR:-/tmp}/bench-test-$$"
PASS=0; FAIL=0
ok() { if [ "$1" = "$2" ]; then PASS=$((PASS+1)); echo "  PASS  $3"; else FAIL=$((FAIL+1)); echo "  FAIL  $3"; echo "        expected [$2] got [$1]"; fi; }
trap 'rm -rf "$T"' EXIT

[ -d "$SRC_REPO/.git" ] || { echo "test_bench: no lab repo at $SRC_REPO (set LAB_REPO)"; exit 2; }
mkdir -p "$T/out" "$T/stub"
git clone -q "$SRC_REPO" "$T/lab"
cp "$LAB_HOME/state/state.json" "$T/state.json"
cat > "$T/stub/claude" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--version" ]; then echo "2.1.278 (Claude Code)"; exit 0; fi
printf '{"type":"system","subtype":"init","cwd":"%s","skills":[],"claude_code_version":"2.1.278"}\n' "$PWD"
sleep 1
printf '{"type":"result","subtype":"success","total_cost_usd":0.01,"usage":{"input_tokens":10,"output_tokens":5}}\n'
EOF
chmod +x "$T/stub/claude"
export LAB_REPO="$T/lab" LAB_STATE="$T/state.json" BENCH_OUT="$T/out" BENCH_SANDBOX="$T/sandbox" PATH="$T/stub:$PATH"
B() { python3 "$HERE/bench.py" "$@"; }

echo "bench.py"
B prepare >/dev/null
first=$(python3 -c "import json; print(json.load(open('$T/out/tasks.json'))['tasks'][0]['id'])")
B run --k 1 --only "$first" --jobs 2 >/dev/null 2>&1
ok "$(wc -l < "$T/out/results.jsonl")" "2" "a run writes one row per rollout (both arms)"

# a commit made after the sandboxes were cloned, and a base that exists nowhere
git -C "$T/lab" commit -q --allow-empty -m "made after the sandboxes"
NEW=$(git -C "$T/lab" rev-parse HEAD)
read -r fresh broken < <(python3 - "$T/out/tasks.json" "$NEW" "$first" <<'P'
import json, sys
p, new, first = sys.argv[1:4]
m = json.load(open(p))
others = [t for t in m["tasks"] if t["id"] != first]
others[0]["base"] = new
others[1]["base"] = "0123456789abcdef0123456789abcdef01234567"
json.dump(m, open(p, "w"), indent=1)
print(others[0]["id"], others[1]["id"])
P
)
out=$(B run --k 1 --only "$fresh,$broken" --jobs 2 2>&1); rc=$?
ok "$rc" "1" "a rollout that could not run makes the run exit non-zero"
ok "$(echo "$out" | grep -c "^$broken .*DID NOT RUN")" "2" "each one is reported, with the reason (it used to vanish without a word)"
ok "$(echo "$out" | grep -c 'rollout(s) DID NOT RUN')" "1" "and listed again at the end"
ok "$(jq -r "select(.task == \"$fresh\") | .arm" "$T/out/results.jsonl" | sort | tr '\n' ' ')" "evolved none " \
   "a reused sandbox fetches commits made after it was cloned"

# the report compares arms only on tasks measured the same number of times
python3 - "$T/out/results.jsonl" "$first" <<'P'
import json, sys
p, first = sys.argv[1:3]
rows = [json.loads(l) for l in open(p)]
drop = next(i for i, r in enumerate(rows) if r["task"] == first and r["arm"] == "evolved")
open(p, "w").write("".join(json.dumps(r) + "\n" for i, r in enumerate(rows) if i != drop))
P
rep=$(B report)
ok "$(echo "$rep" | grep -c "Incomplete.*$first (none 1, evolved 0)")" "1" "a task whose arms have unequal counts is named"
ok "$(echo "$rep" | grep -c ' 2 valid rollouts ')" "1" "and left out of the comparison (only the paired task's 2 rollouts count)"
ok "$(echo "$rep" | grep -c "Not measured.*$broken")" "1" "a prepared task with no rollout at all is named"

echo ""
echo "passed $PASS   failed $FAIL"
[ "$FAIL" -eq 0 ]
