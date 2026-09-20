#!/usr/bin/env bash
# run-tests.sh — one test per known failure mode. No API calls: rollouts are
# driven by a stub `claude` whose behaviour each test controls.
#
#   ./test/run-tests.sh [-j auto|N] [pattern]
#
# -j runs N test functions at once (auto = the CPUs, at most 8), each in a temp
# folder of its own; the output is printed in the usual order. Default: 1.
# CORTEX_TEST_ROLLOUTS=N / CORTEX_TEST_PREFLIGHT=N run every sweep / preflight
# inside the tests N at a time (default 1, so each test sees one fixed order).
set -uo pipefail
CORTEX="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="${TMPDIR:-/tmp}/cortex-tests-$$"
PASS=0; FAIL=0; FAILED=()
# The machine's own load must not decide a test: a sweep marks timeouts on an
# oversubscribed machine invalid. Tests that need load set CORTEX_LOADAVG.
export CORTEX_LOADAVG="${CORTEX_LOADAVG:-0}"
export CORTEX_EXCLUSIVE_WAIT="${CORTEX_EXCLUSIVE_WAIT:-2}"
JOBS="${CORTEX_TEST_JOBS:-1}"
if [ "${1:-}" = "-j" ]; then JOBS="${2:-auto}"; shift 2 || shift; fi
if [ "$JOBS" = "auto" ]; then JOBS=$(nproc 2>/dev/null || echo 2); [ "$JOBS" -gt 8 ] && JOBS=8; fi
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || { echo "run-tests: -j needs auto or a number" >&2; exit 2; }

pass() { PASS=$((PASS+1)); printf '  \033[32mPASS\033[0m  %s\n' "$1"; }
fail() { FAIL=$((FAIL+1)); FAILED+=("$1"); printf '  \033[31mFAIL\033[0m  %s\n     %s\n' "$1" "${2:-}"; }
ok()   { if [ "$1" = "$2" ]; then pass "$3"; else fail "$3" "expected [$2] got [$1]"; fi; }

# ---------------------------------------------------------------- fixtures --
make_repo() {                 # $1 = dir, $2 = optional shell run before the first commit
  local R="$1"; rm -rf "$R"; mkdir -p "$R/src"; cd "$R"
  git init -q; git config user.email t@t; git config user.name t
  echo 'def add(a,b): return a - b' > src/calc.py
  [ -n "${2:-}" ] && eval "$2"
  git add -A; git commit -qm broken
  BROKEN=$(git rev-parse HEAD)
  echo 'def add(a,b): return a + b' > src/calc.py
  git add -A; git commit -qm fixed
  bash "$CORTEX/bin/cortex" init "$R" >/dev/null
  # the suite never sweeps in the user's sandbox_root: a real sweep may be running there
  setcfg 'sandbox_root: /tmp/cortex-evolve' "sandbox_root: $TMP/sandboxes"
  # auto would size by this machine's RAM: pinned, so every run is the same.
  # CORTEX_TEST_ROLLOUTS=4 ./test/run-tests.sh runs every sweep in the suite parallel.
  setcfg '    rollouts: auto' "    rollouts: ${CORTEX_TEST_ROLLOUTS:-1}"
  setcfg '    preflight: auto' "    preflight: ${CORTEX_TEST_PREFLIGHT:-1}"
  mk_task 01
  setcfg 'min_valid_tasks: 3' 'min_valid_tasks: 1'
  setcfg 'confirm: 3' 'confirm: 2'
  setcfg 'regression_tolerance: 0.34' 'regression_tolerance: 0.5'   # one run at k=2
}

mk_task() {                   # $1 = id
  local id="$1"
  mkdir -p ".evolve/tasks/$id"
  printf 'id: %s\ntitle: add subtracts\nbase_sha: %s\nservices: []\ntimeout_s: 60\nharvested: 2026-09-17\n' \
    "$id" "$BROKEN" > ".evolve/tasks/$id/task.yaml"
  git diff "$BROKEN" HEAD > ".evolve/tasks/$id/fix.patch"
  echo "fix add() in src/calc.py" > ".evolve/tasks/$id/prompt.txt"
  printf '#!/usr/bin/env bash\nset -euo pipefail\npython3 -c "from src.calc import add; assert add(2,3)==5"\n' \
    > ".evolve/tasks/$id/check.sh"
  chmod +x ".evolve/tasks/$id/check.sh"; echo n > ".evolve/tasks/$id/notes.md"
}

setcfg() {  # $1 = old line fragment, $2 = new ; edits config.yaml in place
  python3 - "$1" "$2" <<'P'
import sys
p=".evolve/config.yaml"; s=open(p).read()
open(p,"w").write(s.replace(sys.argv[1], sys.argv[2]))
P
}

addcfg() {  # insert $2 as a new line directly after the line containing $1
  python3 - "$1" "$2" <<'P'
import sys
p=".evolve/config.yaml"; out=[]
for line in open(p):
    out.append(line)
    if sys.argv[1] in line and not any(sys.argv[2] in o for o in out):
        out.append(sys.argv[2] + "\n")
open(p,"w").writelines(out)
P
}

mk_cand() { mkdir -p ".evolve/candidate/$1"; printf -- '---\nname: %s\ndescription: d\n---\nCheck.\n' "$1" > ".evolve/candidate/$1/SKILL.md"; }

stub() {                      # $1 = dir, $2 = body of the fake agent
  mkdir -p "$1"
  # Like the real CLI, the stub answers `--version` without doing any work
  # (sweep and doctor probe it; running the body there would act OUTSIDE the
  # sandbox), and every run starts its stream with a system/init event.
  # CORTEX_STUB_VERSION lets a test play an old CLI; CORTEX_STUB_NOINIT one
  # whose output is unreadable.
  { echo '#!/usr/bin/env bash'
    echo 'if [ "${1:-}" = "--version" ]; then echo "${CORTEX_STUB_VERSION:-2.1.276} (Claude Code)"; exit 0; fi'
    # init lists the always-on skills (no `paths:`), as the real CLI does
    echo '_sk=$(for d in .claude/skills/*/; do [ -f "$d/SKILL.md" ] && ! grep -q "^paths:" "$d/SKILL.md" && basename "$d"; done 2>/dev/null | jq -R . | jq -sc .)'
    echo '[ -n "${CORTEX_STUB_NOINIT:-}" ] || printf '"'"'{"type":"system","subtype":"init","cwd":"%s","skills":%s,"claude_code_version":"%s"}\n'"'"' "$PWD" "${_sk:-[]}" "${CORTEX_STUB_VERSION:-2.1.276}"'
    echo "$2"; } > "$1/claude"
  chmod +x "$1/claude"
  # `fire <skill>` inside a stub prints the stream-json line a real agent emits
  # when it invokes a skill, so tests can control what "fired".
  cat > "$1/fire" <<'F'
#!/usr/bin/env bash
printf '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"%s"}}]}}\n' "$1"
F
  # `reveal <skill>`: a path-gated skill entering the listing (commands_changed)
  cat > "$1/reveal" <<'F'
#!/usr/bin/env bash
printf '{"type":"system","subtype":"commands_changed","commands":[{"name":"%s","description":"d"}]}\n' "$1"
F
  # `readf <path> [abs|rel|real] [err]`: a Read tool call and its result
  cat > "$1/readf" <<'F'
#!/usr/bin/env bash
case "${2:-abs}" in abs) p="$PWD/$1" ;; rel) p="$1" ;; real) p="$(pwd -P)/$1" ;; *) p="$1" ;; esac
id="r$RANDOM$RANDOM"
printf '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"%s","name":"Read","input":{"file_path":"%s"}}]}}\n' "$id" "$p"
printf '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"%s","is_error":%s,"content":"x"}]}}\n' "$id" "$([ "${3:-}" = err ] && echo true || echo false)"
F
  chmod +x "$1/fire" "$1/reveal" "$1/readf"
}

mk_live() {                   # $1 = name, $2 = body marker ; a live skill
  mkdir -p ".claude/skills/$1"
  printf -- '---\nname: %s\ndescription: d\n---\n%s\n' "$1" "${2:-live}" > ".claude/skills/$1/SKILL.md"
}

synth() {                     # $1 = file, $2 = k, then "task base_passes cand_passes" triples
  local f="$1" k="$2"; shift 2
  printf '{"event":"start","phase":"confirm","mode":"add","k":%s,"candidate":"x","replaced":[]}\n' "$k" > "$f"
  while [ $# -gt 0 ]; do
    local t="$1" b="$2" c="$3" r; shift 3
    for r in $(seq 1 "$k"); do
      printf '{"v":"base","t":"%s","r":%s,"pass":%s,"valid":1,"skills":[]}\n' "$t" "$r" "$([ "$r" -le "$b" ] && echo 1 || echo 0)" >> "$f"
      printf '{"v":"cand","t":"%s","r":%s,"pass":%s,"valid":1,"skills":["x"]}\n' "$t" "$r" "$([ "$r" -le "$c" ] && echo 1 || echo 0)" >> "$f"
    done
  done
  echo '{"event":"done"}' >> "$f"
}

sweep() { PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" "$@" 2>>"$LOG"; }
score() { bash "$CORTEX/bin/score.sh" "$@"; }

echo "cortex test suite"; echo ""

# ============================================================ FINDING 1 =====
t_git_isolation() {
  local R="$TMP/f1"; make_repo "$R"; STUB="$TMP/stub1"; LOG="$R/log"
  git branch important-work
  git tag important-tag
  # an ordinary harvested prompt ("commit this", "clean up branches") reaches here
  stub "$STUB" 'git branch -D important-work 2>/dev/null
git tag -d important-tag 2>/dev/null
git checkout -q -b junk-branch 2>/dev/null
git commit -q --allow-empty -m "junk from a rollout" 2>/dev/null
git stash push -u -m "junk stash" 2>/dev/null
sed -i "s/a - b/a + b/" src/calc.py 2>/dev/null
exit 0'
  mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$(git branch --list important-work | wc -l)" "1" "F1 rollout cannot delete a real branch"
  ok "$(git tag -l important-tag | wc -l)"        "1" "F1 rollout cannot delete a real tag"
  ok "$(git branch --list junk-branch | wc -l)" "0" "F1 rollout cannot create a branch in the real repo"
  ok "$(git stash list | wc -l)" "0" "F1 rollout cannot push onto the real repo's stash"
}

# ============================================================ FINDING 2 =====
t_infra_not_capability() {
  local R="$TMP/f2"; make_repo "$R"; STUB="$TMP/stub2"; LOG="$R/log"
  stub "$STUB" 'exit 1'          # auth / rate-limit / 5xx shape
  mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r '.invalid')"  "4" "F2 non-timeout agent failures marked invalid"
  ok "$(echo "$j" | jq -r '.scorable')" "false" "F2 a sweep full of infra failures is NOT scorable"
  ok "$(echo "$j" | jq -r '.invalid_reasons | keys[0]')" "agent_rc_1" "F2 invalid reason is recorded"
  ok "$(echo "$j" | jq -r '.blocked_because | length > 0')" "true" "F2 blocked_because explains why"
}

t_timeout_is_a_real_failure() {
  local R="$TMP/f2b"; make_repo "$R"; STUB="$TMP/stub2b"; LOG="$R/log"
  stub "$STUB" 'exit 124'        # timeout must still count as capability failure
  mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r '.invalid')"  "0" "F2 timeout is VALID (a real failure, not infra)"
  ok "$(echo "$j" | jq -r '.scorable')" "true" "F2 a sweep of timeouts is still scorable"
  ok "$(echo "$j" | jq -r '.net')"      "0" "F2 timeouts score zero for both arms"
}

# ============================================================ FINDING 3 =====
t_locking() {
  local R="$TMP/f3"; make_repo "$R"; STUB="$TMP/stub3"; LOG="$R/log"
  stub "$STUB" 'sleep 3; exit 0'
  mk_cand vbd
  ( PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --phase confirm >/dev/null 2>&1 ) &
  local bg=$!
  sleep 1.5
  local out; out=$(PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --phase screen 2>&1); local rc=$?
  ok "$rc" "1" "F3 a second concurrent sweep is refused"
  case "$out" in *"lock held"*) pass "F3 refusal names the lock" ;; *) fail "F3 refusal names the lock" "$out" ;; esac
  # preflight has a lock of its own: a /harvest can check its task during a sweep
  local pout; pout=$(bash "$CORTEX/bin/preflight.sh" 2>&1); local prc=$?
  ok "$prc/$(echo "$pout" | grep -c 'valid=1')" "0/1" "F3 preflight still runs while a sweep holds the sweep lock"
  wait $bg 2>/dev/null
  ok "$(score | jq -r '"\(.invalid)/\(.rollouts)"')" "0/4" "F3 and the sweep beside it finished untouched"
}

# ============================================================ FINDING 4 =====
t_reset_is_verified() {
  local R="$TMP/f4"; make_repo "$R"; STUB="$TMP/stub4"; LOG="$R/log"
  # a check that passes even on the broken state == the task measures nothing
  printf '#!/usr/bin/env bash\ntrue\n' > .evolve/tasks/01/check.sh
  stub "$STUB" 'exit 0'
  mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r '.invalid')" "4" "F4 rollouts whose broken state already passes are invalid"
  ok "$(echo "$j" | jq -r '.invalid_reasons.broken_state_passes_check')" "4" "F4 the reason is named"
  ok "$(echo "$j" | jq -r '.scorable')" "false" "F4 such a sweep is not scorable"
}

t_no_fix_leaks_between_rollouts() {
  local R="$TMP/f4b"; make_repo "$R"; STUB="$TMP/stub4b"; LOG="$R/log"
  # agent fixes it once; if state leaked, later rollouts would pass without work
  stub "$STUB" 'if [ ! -f /tmp/cortex-f4b-done ]; then sed -i "s/a - b/a + b/" src/calc.py; touch /tmp/cortex-f4b-done; fi
exit 0'
  rm -f /tmp/cortex-f4b-done
  mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  local passes; passes=$(grep -c '"pass":1' "$(ls -1t .evolve/runs/*.jsonl | head -1)")
  ok "$passes" "1" "F4 a fix does not leak into the next rollout (exactly 1 pass)"
  rm -f /tmp/cortex-f4b-done
}

# ============================================================ FINDING 5 =====
t_budget_refused_up_front() {
  local R="$TMP/f5"; make_repo "$R"; STUB="$TMP/stub5"; LOG="$R/log"
  mk_task 02; mk_task 03
  setcfg 'max_runs_per_cycle: 60' 'max_runs_per_cycle: 3'
  rm -f "$R/ran"
  stub "$STUB" 'touch "$CORTEX_TEST_REPO/ran"; exit 0'
  mk_cand vbd
  local out rc; out=$(CORTEX_TEST_REPO="$R" PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --phase confirm 2>&1); rc=$?
  ok "$rc" "1" "F5 a sweep that cannot fit the budget is refused"
  case "$out" in *"needs 12 rollouts"*) pass "F5 the refusal says how many rollouts it needs" ;;
                 *) fail "F5 the refusal says how many rollouts it needs" "$out" ;; esac
  ok "$([ -f "$R/ran" ] && echo spent || echo none)" "none" "F5 not a single rollout is spent"
  ok "$(ls -1 .evolve/runs/*.jsonl 2>/dev/null | wc -l)" "0" "F5 no results file is written"
}

t_truncated_data_not_scorable() {
  local R="$TMP/f5b"; make_repo "$R"
  # the defensive path: a results file that stopped early (hand-built)
  printf '%s\n' '{"event":"start","phase":"confirm","mode":"add","k":2,"candidate":"vbd","replaced":[]}' \
    '{"v":"base","t":"01","r":1,"pass":0,"valid":1}' '{"v":"cand","t":"01","r":1,"pass":1,"valid":1}' \
    '{"v":"base","t":"01","r":2,"pass":0,"valid":1}' '{"v":"cand","t":"01","r":2,"pass":1,"valid":1}' \
    '{"v":"base","t":"03","r":1,"pass":0,"valid":1}' \
    '{"event":"truncated","runs":5}' > .evolve/runs/t.jsonl
  local j; j=$(score .evolve/runs/t.jsonl)
  ok "$(echo "$j" | jq -r '.finished')"  "false" "F5 score reports finished=false"
  ok "$(echo "$j" | jq -r '.scorable')"  "false" "F5 truncated data is not scorable"
  ok "$(echo "$j" | jq -r '.unmeasured | length > 0')" "true" "F5 unmeasured tasks are listed"
  # the old bug: an unmeasured task silently scored delta 0 and looked preserved
  ok "$(echo "$j" | jq -r '[.per_task[].task] | contains(["03"])')" "false" \
     "F5 an unmeasured task is EXCLUDED from per_task, not scored as delta 0"
}

# ============================================================ FINDING 6 =====
t_harness_snapshot() {
  local R="$TMP/f6"; make_repo "$R"; STUB="$TMP/stub6"; LOG="$R/log"
  mkdir -p .claude/skills/preexisting; echo "x" > .claude/skills/preexisting/SKILL.md
  mk_cand vbd
  # The stub only fixes the bug when it can SEE the candidate skill, and it
  # destroys the live skills folder on its very first invocation. If rollouts
  # read the live folder (the bug) later cand rollouts stop seeing vbd and the
  # measured cand score collapses. If they read a snapshot, every cand rollout
  # sees it and cand scores 1.0. This distinguishes the two; asserting only
  # that the sweep completed does not.
  stub "$STUB" 'rm -rf "$CORTEX_TEST_REPO/.claude/skills" 2>/dev/null
if [ -d .claude/skills/vbd ]; then sed -i "s/a - b/a + b/" src/calc.py; fi
exit 0'
  CORTEX_TEST_REPO="$R" sweep --candidate vbd --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r '.cand_total')" "1" "F6 every cand rollout saw the snapshot harness, not the live one"
  ok "$(echo "$j" | jq -r '.gain > 0')" "true" "F6 the candidate is still measurable after the live folder is destroyed"
  ok "$(echo "$j" | jq -r '.harness_base != .harness_cand')" "true" "F6 base and cand harnesses differ"
  ok "$(echo "$j" | jq -r '.harness_base | length')" "16" "F6 harness hash is recorded for audit"
}

# ============================================================ FINDING 7 =====
t_removal_needed_skill_rejected() {
  local R="$TMP/f7"; make_repo "$R"; STUB="$TMP/stub7"; LOG="$R/log"
  mk_live old-skill
  # the skill fires and is what fixes the bug; the stub also records whether the
  # LIVE folder still has it at every rollout (the old design moved it out)
  stub "$STUB" 'ls "$CORTEX_TEST_REPO/.claude/skills" >> "$CORTEX_TEST_REPO/live.txt"
if [ -d .claude/skills/old-skill ]; then fire old-skill; sed -i "s/a - b/a + b/" src/calc.py; fi
exit 0'
  CORTEX_TEST_REPO="$R" sweep --replace old-skill --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r .mode)" "replace" "F7 --replace is recorded as a replace sweep"
  ok "$(echo "$j" | jq -r .verdict)" "REJECT" "F7 removing a skill that does the work is REJECTED"
  ok "$(echo "$j" | jq -r '.replaced_fired_runs')" "2" "F7 base rollouts that invoked it are counted"
  ok "$(grep -c '^old-skill$' "$R/live.txt")" "4" "F7 the live skill never left .claude/skills during the sweep"
  ok "$(bash "$CORTEX/bin/cortex" status | grep -c 'PARKED')" "0" "F7 nothing is parked, so nothing can be left parked"
}

t_removal_dead_weight_accepted() {
  local R="$TMP/f7b"; make_repo "$R"; STUB="$TMP/stub7b"; LOG="$R/log"
  mk_live old-skill
  # it fires, but the agent solves the task either way: dead weight
  stub "$STUB" '[ -d .claude/skills/old-skill ] && fire old-skill
sed -i "s/a - b/a + b/" src/calc.py; exit 0'
  sweep --replace old-skill --phase confirm >/dev/null
  ok "$(score | jq -r .verdict)" "ACCEPT" "F7 removing a skill that fires but changes nothing is ACCEPTED"
}

t_removal_unmeasured_never_deletes() {
  local R="$TMP/f7c"; make_repo "$R"; STUB="$TMP/stub7c"; LOG="$R/log"
  mk_live old-skill
  # no task exercises the skill: it never fires, and the scores are identical
  stub "$STUB" 'sed -i "s/a - b/a + b/" src/calc.py; exit 0'
  sweep --replace old-skill --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r .verdict)" "UNMEASURED" "F7 a skill no task exercises is UNMEASURED, not deletable"
  ok "$(echo "$j" | jq -r '.verdict_because[0] | test("no task exercises")')" "true" "F7 and the reason says why"
}

t_replace_same_name() {
  local R="$TMP/f7d"; make_repo "$R"; STUB="$TMP/stub7d"; LOG="$R/log"
  mk_live vbd OLDBODY
  mk_cand vbd                               # a rewrite of the live skill
  stub "$STUB" 'grep -q OLDBODY .claude/skills/vbd/SKILL.md && echo "$1" >> "$CORTEX_TEST_REPO/old.txt"
[ -f .claude/skills/vbd/vbd/SKILL.md ] && echo nested >> "$CORTEX_TEST_REPO/old.txt"
exit 0'
  local out; out=$(PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd 2>&1)
  ok "$(echo "$out" | grep -c 'already called')" "1" "F7 a candidate named like a live skill needs --replace"
  CORTEX_TEST_REPO="$R" sweep --candidate vbd --replace vbd --phase confirm >/dev/null
  ok "$(grep -c nested "$R/old.txt" 2>/dev/null)" "0" "F7 the rewrite is never nested inside the old skill"
  ok "$(wc -l < "$R/old.txt")" "2" "F7 only the base arm sees the old body"
}

t_bury_and_promote() {
  local R="$TMP/f7e"; make_repo "$R"
  mkdir -p .evolve/graveyard/vbd; echo v1 > .evolve/graveyard/vbd/SKILL.md
  mk_cand vbd
  bash "$CORTEX/bin/cortex" bury vbd --from candidate --why "gate1 gain 0" >/dev/null
  ok "$(ls .evolve/graveyard | grep -c '^vbd-')" "1" "F7 burying next to a namesake gets its own dated entry"
  ok "$([ -d .evolve/graveyard/vbd/vbd ] && echo nested || echo flat)" "flat" "F7 it is never nested inside the old one"
  ok "$(cat .evolve/graveyard/vbd-*/BURIED.md | grep -c 'gate1 gain 0')" "1" "F7 the reason is kept with it"
  ok "$(cat .evolve/graveyard/vbd/SKILL.md)" "v1" "F7 the older entry is untouched"
  mk_live live-one; mk_cand live-one
  ok "$(bash "$CORTEX/bin/cortex" promote live-one 2>&1 | grep -c 'already called')" "1" "F7 promote refuses to overwrite a live skill"
  bash "$CORTEX/bin/cortex" bury live-one --from live >/dev/null
  bash "$CORTEX/bin/cortex" promote live-one --force >/dev/null
  ok "$(cat .claude/skills/live-one/SKILL.md | grep -c 'Check.')" "1" "F7 after burying the old one, promote succeeds"
  ok "$(bash "$CORTEX/bin/cortex" bury ../x --from live 2>&1 | grep -c 'invalid skill name')" "1" "F7 path-like names are refused"
}

t_candidate_fired_is_recorded() {
  local R="$TMP/f7f"; make_repo "$R"; STUB="$TMP/stub7f"; LOG="$R/log"
  mk_cand vbd
  stub "$STUB" '[ -d .claude/skills/vbd ] && fire vbd; exit 0'
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$(score | jq -r .candidate_fired_runs)" "2" "F7 cand rollouts that invoked the candidate are counted"
  ok "$(score | jq -r '.notes[]' | grep -c 'never fired')" "0" "F7 no warning when it fired"
  stub "$STUB" 'exit 0'
  sleep 1; sweep --candidate vbd --phase confirm >/dev/null
  ok "$(score | jq -r '.notes[0] | test("never fired")')" "true" "F7 a candidate that never fired is called out"
}

t_net_runs_rounding() {
  local R="$TMP/f7g"; make_repo "$R"
  setcfg 'regression_tolerance: 0.5' 'regression_tolerance: 0.34'
  bash "$CORTEX/bin/cortex" config >/dev/null 2>&1
  # exactly +2 runs, but summing thirds gives 1.9999999999999996
  synth .evolve/runs/r.jsonl 3  01 1 0  02 1 0  03 1 0  04 0 1  05 0 1  06 0 3
  ok "$(score .evolve/runs/r.jsonl | jq -r .net_runs)" "2" "F7 net_runs is exact, not 1.9999999999999996"
  ok "$(score .evolve/runs/r.jsonl | jq -r .verdict)" "KEEP" "F7 a win of exactly min_net_runs is kept"
}

t_status_shows_model() {
  local R="$TMP/f7h"; make_repo "$R"
  ok "$(bash "$CORTEX/bin/cortex" status | grep -c 'not pinned')" "1" "F7 status says when the model is not pinned"
  setcfg 'model: ""' 'model: claude-test-model'; bash "$CORTEX/bin/cortex" config >/dev/null 2>&1
  ok "$(bash "$CORTEX/bin/cortex" status | grep -c 'claude-test-model')" "1" "F7 status shows the pinned model"
}

t_empty_and_legacy_results() {
  local R="$TMP/f7i"; make_repo "$R"; STUB="$TMP/stub7i"; LOG="$R/log"; stub "$STUB" 'exit 0'
  mk_live old-skill
  ok "$(PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --replace old-skill --tasks 99 2>&1 | grep -c 'nothing to measure')" "1" \
     "F7 a sweep with no runnable task is refused"
  printf '%s\n' '{"event":"start","phase":"confirm","mode":"add","k":2,"candidate":"x","replaced":[]}' '{"event":"done"}' > .evolve/runs/e.jsonl
  ok "$(score .evolve/runs/e.jsonl | jq -r .verdict)" "RERUN" "F7 an empty results file is never a KILL"
  ok "$(score .evolve/runs/e.jsonl | jq -r '.blocked_because | index("no task was measured") != null')" "true" "F7 and says no task was measured"
  # written before sweeps recorded fired skills: firing is unknown, not zero
  printf '%s\n' '{"event":"start","phase":"confirm","mode":"replace","k":1,"candidate":"","replaced":["old-skill"]}' \
    '{"v":"base","t":"01","pass":1,"valid":1}' '{"v":"cand","t":"01","pass":1,"valid":1}' '{"event":"done"}' > .evolve/runs/o.jsonl
  ok "$(score .evolve/runs/o.jsonl | jq -r .verdict)" "UNMEASURED" "F7 an old replace file can never ACCEPT"
  ok "$(score .evolve/runs/o.jsonl | jq -r .replaced_fired_runs)" "null" "F7 firing is reported as unknown"
  ok "$(PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --replace 'a"b' 2>&1 | grep -c 'invalid skill name')" "1" "F7 sweep refuses a name that would break JSON"
  ok "$(bash "$CORTEX/bin/cortex" bury 'a b' --from live 2>&1 | grep -c 'invalid skill name')" "1" "F7 cortex refuses it too"
}

# ============================================================ FINDING 8 =====
t_interleaving() {
  local R="$TMP/f8"; make_repo "$R"; STUB="$TMP/stub8"; LOG="$R/log"
  stub "$STUB" 'exit 0'; mk_cand vbd
  sweep --candidate vbd --phase confirm --parallel 1 >/dev/null
  local seq; seq=$(jq -r 'select(.v != null) | .v' "$(ls -1t .evolve/runs/*.jsonl | head -1)" | tr '\n' ' ')
  ok "${seq% }" "base cand base cand" "F8 variants are interleaved, not run in two blocks"
}

# ============================================================ FINDING 9 =====
t_per_phase_files() {
  local R="$TMP/f9"; make_repo "$R"; STUB="$TMP/stub9"; LOG="$R/log"
  stub "$STUB" 'exit 0'; mk_cand vbd
  sweep --candidate vbd --phase screen >/dev/null
  sleep 1
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$(ls -1 .evolve/runs/*.jsonl | wc -l)" "2" "F9 screen and confirm each keep their own file"
  ok "$(score | jq -r '.phase')" "confirm" "F9 score defaults to the newest run"
  local first; first=$(ls -1t .evolve/runs/*.jsonl | tail -1)
  ok "$(score "$first" | jq -r '.phase')" "screen" "F9 an older run is still readable by path"
  bash "$CORTEX/bin/cortex" clean >/dev/null
  ok "$(ls -1 .evolve/runs/*.jsonl | wc -l)" "2" "F9 clean keeps evidence by default"
  bash "$CORTEX/bin/cortex" clean --runs >/dev/null
  ok "$(ls -1 .evolve/runs/*.jsonl 2>/dev/null | wc -l)" "0" "F9 clean --runs deletes it explicitly"
}

# ====================================================== regression guards ====
t_preflight_still_works() {
  local R="$TMP/r1"; make_repo "$R"; LOG="$R/log"
  printf '#!/usr/bin/env bash\ntrue\n' > .evolve/tasks/01/check.sh   # garbage task
  mk_task 02                                                        # good task
  bash "$CORTEX/bin/preflight.sh" >/dev/null 2>&1
  ok "$([ -d .evolve/tasks/_broken/01 ] && echo yes || echo no)" "yes" "R preflight quarantines a non-discriminating task"
  ok "$([ -d .evolve/tasks/02 ] && echo yes || echo no)" "yes" "R preflight keeps a good task"
}

t_happy_path() {
  local R="$TMP/r2"; make_repo "$R"; STUB="$TMP/stubr2"; LOG="$R/log"
  stub "$STUB" 'if [ -d .claude/skills/vbd ]; then fire vbd; sed -i "s/a - b/a + b/" src/calc.py; fi
exit 0'
  mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r '.scorable')" "true" "R happy path is scorable"
  ok "$(echo "$j" | jq -r '.gain > 0')" "true" "R a skill that helps shows a gain"
  ok "$(echo "$j" | jq -r '.regression')" "0" "R and no regression"
  ok "$(echo "$j" | jq -r '.protected_broken | length')" "0" "R protected set intact"
}

t_bad_input() {
  local R="$TMP/r3"; make_repo "$R"; STUB="$TMP/stubr3"; LOG="$R/log"; stub "$STUB" 'exit 0'
  ok "$(bash "$CORTEX/bin/sweep.sh" --candidate ghost 2>&1 | grep -c 'no such candidate')" "1" "R unknown candidate rejected"
  mk_cand vbd
  ok "$(PATH=/usr/bin:/bin bash "$CORTEX/bin/sweep.sh" --candidate vbd 2>&1 | grep -c 'not found on PATH')" "1" "R missing claude rejected"
  ok "$( (cd /tmp && bash "$CORTEX/bin/preflight.sh" 2>&1) | grep -c 'not inside a git repository')" "1" "R preflight outside a repo errors cleanly"
  local out; out=$( cd "$R" && jq '.sandbox_root="/etc"' .evolve/config.json > c && mv c .evolve/config.json
                    bash "$CORTEX/bin/cortex" clean 2>&1 )
  ok "$(echo "$out" | grep -c 'too shallow')" "1" "R clean refuses a shallow sandbox_root"
}

# ====================================================== new parameters =======
t_config_compiles() {
  local R="$TMP/c1"; make_repo "$R"
  ok "$([ -f .evolve/config.yaml ] && echo yes || echo no)" "yes" "C init writes config.yaml"
  ok "$(bash "$CORTEX/bin/cortex" config --check 2>&1)" "config.yaml is valid" "C default config validates"
  ok "$(jq -r '.cache_dirs|length>0' .evolve/config.json)" "true" "C lists compile into JSON"
  ok "$(jq -r '.rollout_env.PYTHONDONTWRITEBYTECODE' .evolve/config.json)" "1" "C maps compile into JSON"
  ok "$(jq -r '.transcripts_dir|startswith("/")' .evolve/config.json)" "true" "C ~ is expanded"
}

t_config_validation() {
  local R="$TMP/c2"; make_repo "$R"
  setcfg "sandbox_root: $TMP/sandboxes" 'sandbox_root: /usr'
  ok "$(bash "$CORTEX/bin/cortex" config --check >/dev/null 2>&1; echo $?)" "1" "C an unsafe sandbox_root is rejected"
  setcfg 'sandbox_root: /usr' "sandbox_root: $TMP/sandboxes"
  setcfg 'regression_tolerance: 0.5' 'regresion_tolerance: 0.5'
  ok "$(bash "$CORTEX/bin/cortex" config 2>&1 >/dev/null | grep -c "unknown key")" "1" "C a typo'd key is reported, not silently defaulted"
  setcfg 'regresion_tolerance' 'regression_tolerance'
  setcfg 'min_net_runs: 2' 'min_net_runs: 99'
  ok "$(bash "$CORTEX/bin/cortex" config 2>&1 >/dev/null | grep -c 'exceeds k_confirm')" "1" "C incoherent thresholds warn"
}

t_config_autorecompile() {
  local R="$TMP/c3"; make_repo "$R"; STUB="$TMP/stubc3"; LOG="$R/log"
  stub "$STUB" 'exit 0'; mk_cand vbd
  setcfg 'confirm: 2' 'confirm: 1'      # edit YAML only; never touch JSON
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$(jq -r .k_confirm .evolve/config.json)" "1" "C a sweep recompiles a newer config.yaml"
  ok "$(score | jq -r .k)" "1" "C the new value is actually used"
}

t_check_timeout() {
  local R="$TMP/c4"; make_repo "$R"; STUB="$TMP/stubc4"; LOG="$R/log"
  setcfg 'check_timeout_s: 120' 'check_timeout_s: 2'
  printf '#!/usr/bin/env bash\nsleep 60\n' > .evolve/tasks/01/check.sh   # a hanging verifier
  stub "$STUB" 'exit 0'; mk_cand vbd
  local t0; t0=$(date +%s)
  sweep --candidate vbd --phase confirm >/dev/null
  local elapsed=$(( $(date +%s) - t0 ))
  ok "$([ "$elapsed" -lt 40 ] && echo fast || echo HUNG)" "fast" "C a hanging check.sh cannot hang the sweep"
  ok "$(score | jq -r '.invalid_reasons.check_timeout // 0')" "4" "C it is recorded as check_timeout"
  ok "$(score | jq -r .verdict)" "RERUN" "C and the sweep is not scorable"
}

t_verdict_is_computed() {
  local R="$TMP/c5"; make_repo "$R"; STUB="$TMP/stubc5"; LOG="$R/log"
  stub "$STUB" 'if [ -d .claude/skills/vbd ]; then fire vbd; sed -i "s/a - b/a + b/" src/calc.py; fi
exit 0'
  mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$(score | jq -r .verdict)" "KEEP" "C score.sh emits the verdict itself"
  ok "$(score | jq -r '.thresholds.regression_tolerance')" "0.5" "C thresholds are echoed for audit"
  ok "$(score | jq -r '.gates_failed|length')" "0" "C no gate failed"
  # now make the gate impossible and prove the verdict flips
  setcfg 'min_net_runs: 2' 'min_net_runs: 3'
  bash "$CORTEX/bin/cortex" config >/dev/null 2>&1
  ok "$(score | jq -r .verdict)" "KILL" "C raising min_net_runs flips the verdict to KILL"
  ok "$(score | jq -r '.gates_failed[0]|startswith("gate4")')" "true" "C and names gate4 as the cause"
}

t_cycle_counter() {
  local R="$TMP/c6"; make_repo "$R"
  setcfg 'stop_after_barren_cycles: 2' 'stop_after_barren_cycles: 2'
  bash "$CORTEX/bin/cortex" config >/dev/null 2>&1
  ok "$(bash "$CORTEX/bin/cortex" cycle KILL >/dev/null 2>&1; echo $?)" "0" "C first barren cycle is allowed"
  ok "$(bash "$CORTEX/bin/cortex" cycle BARREN >/dev/null 2>&1; echo $?)" "2" "C the limit stops the loop"
  ok "$(bash "$CORTEX/bin/cortex" cycle KEEP >/dev/null 2>&1; echo $?)" "0" "C a KEEP resets the streak"
  ok "$(jq -r .barren_streak .evolve/state.json)" "0" "C the streak is persisted"
}

t_model_and_env() {
  local R="$TMP/c7"; make_repo "$R"; STUB="$TMP/stubc7"; LOG="$R/log"
  setcfg 'model: ""' 'model: claude-test-model'
  setcfg 'PYTHONDONTWRITEBYTECODE: "1"' 'CORTEX_MARKER: "hello"'
  stub "$STUB" 'echo "$* | env=$CORTEX_MARKER" >> "$CORTEX_TEST_OUT"; exit 0'
  mk_cand vbd
  CORTEX_TEST_OUT="$R/args.txt" sweep --candidate vbd --phase confirm >/dev/null
  ok "$(grep -c -- '--model claude-test-model' "$R/args.txt")" "4" "C the configured model is pinned on every rollout"
  ok "$(grep -c 'env=hello' "$R/args.txt")" "4" "C rollout_env reaches the agent"
  ok "$(score | jq -r '.model')" "claude-test-model" "C the model is recorded in the results for audit"
}

t_cache_dirs() {
  local R="$TMP/c8"; make_repo "$R"; STUB="$TMP/stubc8"; LOG="$R/log"
  addcfg '    - __pycache__' '    - .mycache'
  bash "$CORTEX/bin/cortex" config >/dev/null 2>&1
  ok "$(jq -r '.cache_dirs|index(".mycache")!=null' .evolve/config.json)" "true" "C extra cache dirs compile through"
  stub "$STUB" 'mkdir -p .mycache && echo stale > .mycache/x; sed -i "s/a - b/a + b/" src/calc.py; exit 0'
  mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$(score | jq -r .scorable)" "true" "C sweep still runs with custom cache dirs"
}

t_harness_files() {
  local R="$TMP/c9"; make_repo "$R"; STUB="$TMP/stubc9"; LOG="$R/log"
  echo "project memory" > CLAUDE.md
  printf 'AGENTS\n' > AGENTS.md
  addcfg '    - CLAUDE.md' '    - AGENTS.md'
  bash "$CORTEX/bin/cortex" config >/dev/null 2>&1
  stub "$STUB" 'ls CLAUDE.md AGENTS.md >> "$CORTEX_TEST_OUT" 2>&1; exit 0'
  mk_cand vbd
  CORTEX_TEST_OUT="$R/seen.txt" sweep --candidate vbd --phase confirm >/dev/null
  ok "$(grep -c '^AGENTS.md$' "$R/seen.txt")" "4" "C every harness_file is present in both sandboxes"
  ok "$(grep -c '^CLAUDE.md$' "$R/seen.txt")" "4" "C including CLAUDE.md"
}

t_sandbox_cleanup() {
  local R="$TMP/s1"; make_repo "$R"; STUB="$TMP/stubs1"; LOG="$R/log"
  local WT; WT=$(HX sandbox-dir)
  stub "$STUB" 'exit 0'; mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$(ls -d "$WT"/work* 2>/dev/null | wc -l)" "0" "S the sandbox is removed on a normal finish"

  # interrupted mid-sweep: the trap must still clean up
  stub "$STUB" 'sleep 5; exit 0'
  ( PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --phase confirm >/dev/null 2>&1 ) &
  local bg=$!; sleep 3
  kill -TERM $bg 2>/dev/null; wait $bg 2>/dev/null
  sleep 1
  ok "$(ls -d "$WT"/work* 2>/dev/null | wc -l)" "0" "S the sandbox is removed when the sweep is killed"
}

# ==================================================== precondition ==========
t_precondition_absent() {
  local R="$TMP/p0"; make_repo "$R"; STUB="$TMP/stubp0"; LOG="$R/log"
  stub "$STUB" 'sed -i "s/a - b/a + b/" src/calc.py; exit 0'; mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$(score | jq -r .invalid)" "0" "P no precondition.sh = nothing to check"
  ok "$(score | jq -r .scorable)" "true" "P and the sweep is scorable"
}

t_precondition_blocks_rollouts() {
  local R="$TMP/p1"; make_repo "$R"; STUB="$TMP/stubp1"; LOG="$R/log"
  printf '#!/usr/bin/env bash\nexit 1\n' > .evolve/tasks/01/precondition.sh   # stack down
  chmod +x .evolve/tasks/01/precondition.sh
  stub "$STUB" 'sed -i "s/a - b/a + b/" src/calc.py; exit 0'; mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r '.invalid_reasons.precondition_failed')" "4" "P a down stack marks rollouts INVALID"
  ok "$(echo "$j" | jq -r .scorable)" "false" "P and the sweep is not scorable"
  ok "$(echo "$j" | jq -r .verdict)" "RERUN" "P verdict is RERUN, never a fabricated KILL"
  # the crucial property: it must NOT look like the candidate simply failed
  ok "$(echo "$j" | jq -r '[.per_task[]] | length')" "0" "P nothing is scored from a down environment"
}

t_precondition_agent_never_runs() {
  local R="$TMP/p2"; make_repo "$R"; STUB="$TMP/stubp2"; LOG="$R/log"
  printf '#!/usr/bin/env bash\nexit 1\n' > .evolve/tasks/01/precondition.sh
  chmod +x .evolve/tasks/01/precondition.sh
  rm -f /tmp/cortex-p2.log
  stub "$STUB" 'echo ran >> /tmp/cortex-p2.log; exit 0'; mk_cand vbd
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$(cat /tmp/cortex-p2.log 2>/dev/null | wc -l)" "0" "P no tokens are spent when the environment is down"
  rm -f /tmp/cortex-p2.log
}

t_precondition_timeout() {
  local R="$TMP/p3"; make_repo "$R"; STUB="$TMP/stubp3"; LOG="$R/log"
  setcfg 'check_timeout_s: 120' 'check_timeout_s: 2'
  printf '#!/usr/bin/env bash\nsleep 60\n' > .evolve/tasks/01/precondition.sh
  chmod +x .evolve/tasks/01/precondition.sh
  stub "$STUB" 'exit 0'; mk_cand vbd
  local t0; t0=$(date +%s)
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$([ $(( $(date +%s) - t0 )) -lt 40 ] && echo fast || echo HUNG)" "fast" "P a hanging precondition cannot hang the sweep"
  ok "$(score | jq -r '.invalid_reasons.precondition_timeout')" "4" "P it is recorded as precondition_timeout"
}

t_preflight_does_not_quarantine_on_env() {
  local R="$TMP/p4"; make_repo "$R"
  printf '#!/usr/bin/env bash\nexit 1\n' > .evolve/tasks/01/precondition.sh
  chmod +x .evolve/tasks/01/precondition.sh
  local out rc
  out=$(bash "$CORTEX/bin/preflight.sh" 2>&1); rc=$?
  ok "$rc" "3" "P preflight exits 3 for an environment problem, not 2"
  ok "$(echo "$out" | grep -c 'environment not ready')" "1" "P and says so"
  # the destructive failure this prevents: losing the suite over a stopped service
  ok "$([ -d .evolve/tasks/01 ] && echo kept || echo LOST)" "kept" "P the task is NOT quarantined"
  ok "$([ -d .evolve/tasks/_broken/01 ] && echo yes || echo no)" "no" "P nothing moved to _broken"
}

t_precondition_passing() {
  local R="$TMP/p5"; make_repo "$R"; STUB="$TMP/stubp5"; LOG="$R/log"
  printf '#!/usr/bin/env bash\nexit 0\n' > .evolve/tasks/01/precondition.sh
  chmod +x .evolve/tasks/01/precondition.sh
  stub "$STUB" 'if [ -d .claude/skills/vbd ]; then fire vbd; sed -i "s/a - b/a + b/" src/calc.py; fi
exit 0'
  mk_cand vbd
  bash "$CORTEX/bin/preflight.sh" >/dev/null 2>&1
  ok "$?" "0" "P a healthy environment passes preflight"
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$(score | jq -r .verdict)" "KEEP" "P and the sweep decides normally"
}

t_tasks_are_snapshotted() {
  local R="$TMP/ts1"; make_repo "$R"; STUB="$TMP/stubts1"; LOG="$R/log"
  mk_cand vbd
  # The stub rewrites the LIVE check.sh to something that always passes on its
  # first run. If rollouts read the live task, later ones would pass for free.
  stub "$STUB" 'if [ ! -f /tmp/cortex-ts1 ]; then
  printf "#!/usr/bin/env bash\ntrue\n" > "$CORTEX_TEST_REPO/.evolve/tasks/01/check.sh"
  touch /tmp/cortex-ts1
fi
exit 0'
  rm -f /tmp/cortex-ts1
  CORTEX_TEST_REPO="$R" sweep --candidate vbd --phase confirm >/dev/null
  ok "$(score | jq -r '[.per_task[].cand] | add')" "0" "T rewriting a live check.sh mid-sweep does not leak in"
  ok "$(score | jq -r '.tasks_hash | length')" "16" "T the task set is hashed for audit"
  rm -f /tmp/cortex-ts1
}

t_sandbox_root_rules() {
  local R="$TMP/sr"; make_repo "$R"
  # a docker daemon that cannot see /tmp (snap, rootless) needs a path elsewhere
  setcfg "sandbox_root: $TMP/sandboxes" "sandbox_root: $HOME/.cortex-test-sandboxes"
  bash "$CORTEX/bin/cortex" config >/dev/null 2>&1
  ok "$(jq -r .sandbox_root .evolve/config.json)" "$HOME/.cortex-test-sandboxes" "SR a path outside /tmp is allowed"
  ok "$(bash "$CORTEX/bin/cortex" config 2>&1 >/dev/null | grep -c 'outside /tmp')" "1" "SR but it warns, so it is a choice not an accident"

  setcfg "sandbox_root: $HOME/.cortex-test-sandboxes" 'sandbox_root: /tmp'
  ok "$(bash "$CORTEX/bin/cortex" config --check >/dev/null 2>&1; echo $?)" "1" "SR a shallow path is refused"

  setcfg 'sandbox_root: /tmp' "sandbox_root: $R/inside"
  ok "$(bash "$CORTEX/bin/cortex" config --check 2>&1 >/dev/null | grep -c 'overlap the repository')" "1" \
     "SR a path inside the repo is refused"

  setcfg "sandbox_root: $R/inside" 'sandbox_root: ~/.cortex-tilde-test'
  bash "$CORTEX/bin/cortex" config >/dev/null 2>&1
  ok "$(jq -r .sandbox_root .evolve/config.json)" "$HOME/.cortex-tilde-test" "SR ~ is expanded"
}

t_single_sandbox_no_leak() {
  local R="$TMP/ss"; make_repo "$R"; STUB="$TMP/stubss"; LOG="$R/log"
  local WT; WT=$(HX sandbox-dir)
  mk_cand vbd
  # every rollout fixes the file. If state leaked between arms, a later rollout
  # would start already-fixed, and reset_to_broken would flag it invalid.
  stub "$STUB" 'sed -i "s/a - b/a + b/" src/calc.py; exit 0'
  sweep --candidate vbd --phase confirm >/dev/null
  ok "$(ls -d "$WT"/work* 2>/dev/null | wc -l)" "0" "SS the sandboxes are cleaned up"
  ok "$(score | jq -r '.invalid_reasons.broken_state_passes_check // 0')" "0" \
     "SS no rollout ever started from a leaked fix"
  ok "$(score | jq -r '[.per_task[].base, .per_task[].cand] | add')" "2" \
     "SS both arms measured independently at full marks"
}

# ============================================= tiers: rules and path-gating ==
mk_rule_cand() {              # $1 = name, $2 = glob (none = a path-less rule)
  mkdir -p ".evolve/candidate/$1"
  if [ -n "${2:-}" ]; then printf -- '---\npaths:\n  - "%s"\n---\n# %s\nNEVER do the wrong thing.\n' "$2" "$1"
  else printf -- '# %s\nNEVER do the wrong thing.\n' "$1"; fi > ".evolve/candidate/$1/RULE.md"
}
mk_live_rule() {              # $1 = name, $2 = glob
  mkdir -p .claude/rules
  printf -- '---\npaths:\n  - "%s"\n---\n# %s\nrule body\n' "$2" "$1" > ".claude/rules/$1.md"
}
mk_gated() {                  # $1 = name, $2 = glob ; a path-gated skill CANDIDATE
  mkdir -p ".evolve/candidate/$1"
  printf -- '---\nname: %s\ndescription: Use when editing calc.\npaths:\n  - "%s"\n---\nCheck.\n' "$1" "$2" \
    > ".evolve/candidate/$1/SKILL.md"
}
HX() { PYTHONDONTWRITEBYTECODE=1 python3 "$CORTEX/bin/harness.py" "$@"; }
CX() { bash "$CORTEX/bin/cortex" "$@"; }
dry() { PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" "$@" --dry-run 2>&1; }

t_rules_snapshot_overrides_base() {
  local R="$TMP/h1"
  make_repo "$R" 'mkdir -p .claude/rules; printf "old\n" > .claude/rules/old.md; echo "old memory" > CLAUDE.md'
  STUB="$TMP/stubh1"; LOG="$R/log"
  rm -f .claude/rules/old.md CLAUDE.md          # gone live, still tracked at base_sha
  mk_live_rule new 'src/**'
  stub "$STUB" '{ [ -f .claude/rules/old.md ] && echo old; [ -f .claude/rules/new.md ] && echo new
  [ -f CLAUDE.md ] && echo claude; } >> "$CORTEX_TEST_OUT"; exit 0'
  mk_cand vbd
  CORTEX_TEST_OUT="$R/seen.txt" sweep --candidate vbd --phase confirm >/dev/null
  ok "$(grep -c '^old$' "$R/seen.txt")" "0" "H a rule deleted live is absent in rollouts, not the base_sha copy"
  ok "$(grep -c '^new$' "$R/seen.txt")" "4" "H a live rule is installed in both arms"
  ok "$(grep -c '^claude$' "$R/seen.txt")" "0" "H a harness_file deleted live is absent too"
}

t_rule_fired_via_read() {
  local R="$TMP/h2"; make_repo "$R"; STUB="$TMP/stubh2"; LOG="$R/log"
  mk_rule_cand calc-rule 'src/**'
  stub "$STUB" 'readf src/calc.py
[ -f .claude/rules/calc-rule.md ] && sed -i "s/a - b/a + b/" src/calc.py; exit 0'
  sweep --candidate calc-rule --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r .candidate_kind)" "rule" "H a RULE.md candidate is swept as a rule"
  ok "$(echo "$j" | jq -r .candidate_fired_runs)" "2" "H a rule fires when a matching file is Read"
  ok "$(echo "$j" | jq -r .candidate_visible_runs)" "2" "H and it counts as visible"
  ok "$(echo "$j" | jq -r .verdict)" "KEEP" "H a rule that helps is kept"
  ok "$(jq -c 'select(.v=="base") | .skills | index("calc-rule")' "$(ls -1t .evolve/runs/*.jsonl | head -1)" | grep -vc null)" "0" \
     "H the base arm never had the candidate rule"
  CX promote calc-rule >/dev/null
  ok "$([ -f .claude/rules/calc-rule.md ] && [ ! -e .evolve/candidate/calc-rule ] && echo live || echo no)" "live" \
     "H promote installs a rule as .claude/rules/<name>.md"
}

t_rule_replace() {
  local R="$TMP/h3"; make_repo "$R"; STUB="$TMP/stubh3"; LOG="$R/log"
  mk_live_rule old-rule 'src/**'
  stub "$STUB" 'readf src/calc.py
[ -f .claude/rules/old-rule.md ] && sed -i "s/a - b/a + b/" src/calc.py; exit 0'
  sweep --replace old-rule --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r .verdict)" "REJECT" "H removing a rule that does the work is REJECTED"
  ok "$(echo "$j" | jq -r .replaced_fired_runs)" "2" "H the base arm's rule firings are counted"
  ok "$(jq -r 'select(.event=="start") | .replaced_kinds[0]' "$(ls -1t .evolve/runs/*.jsonl | head -1)")" "rule" \
     "H the start event records what kind was replaced"
}

t_observe_forms() {
  local R="$TMP/h4"; make_repo "$R"
  local H="$TMP/h4-harness" real="$TMP/h4-real" link="$TMP/h4-link" P="$TMP/h4-prompt" S="$TMP/h4.jsonl"
  mkdir -p "$H/skills/gz" "$H/rules" "$real"; ln -sfn "$real" "$link"
  printf -- '---\npaths:\n  - "src/**"\n---\nr\n' > "$H/rules/api.md"
  printf -- '---\nname: gz\ndescription: d\n---\nx\n' > "$H/skills/gz/SKILL.md"
  echo "do it" > "$P"
  local init; init=$(printf '{"type":"system","subtype":"init","cwd":"%s","skills":["other"],"claude_code_version":"2.1.276"}' "$link")
  rd() { printf '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"%s","name":"Read","input":{"file_path":"%s"}}]}}\n{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"%s","is_error":%s}]}}\n' "$1" "$2" "$1" "${3:-false}"; }
  { echo "$init"; rd a "$real/src/calc.py"; } > "$S"
  ok "$(HX observe "$S" "$H" "$link" "$P" | jq -c .rules)" '["api"]' "O a Read through the real path of a symlinked sandbox counts"
  { echo "$init"; rd a "src/calc.py"; } > "$S"
  ok "$(HX observe "$S" "$H" "$link" "$P" | jq -c .rules)" '["api"]' "O a relative Read path counts"
  { echo "$init"; rd a "/etc/hosts"; } > "$S"
  ok "$(HX observe "$S" "$H" "$link" "$P" | jq -c .rules)" '[]' "O a Read outside the sandbox does not"
  { echo "$init"; rd a "$link/src/calc.py" true; } > "$S"
  ok "$(HX observe "$S" "$H" "$link" "$P" | jq -c .rules)" '[]' "O a Read that errored does not"
  echo "look at @src/calc.py please" > "$P"; echo "$init" > "$S"
  ok "$(HX observe "$S" "$H" "$link" "$P" | jq -c .rules)" '["api"]' "O an @-mention in the prompt loads a rule without a Read"
  echo "do it" > "$P"
  { echo "$init"; printf '{"type":"system","subtype":"commands_changed","commands":[{"name":"harvest"},{"name":"plugin:x"},{"name":"gz"}]}\n'; } > "$S"
  ok "$(HX observe "$S" "$H" "$link" "$P" | jq -c .visible)" '["gz"]' "O visible keeps only this variant's skills and rules"
  echo "not json at all" > "$S"
  local o rc; o=$(HX observe "$S" "$H" "$link" "$P"); rc=$?
  ok "$rc/$(echo "$o" | jq -c .skills)" "2/null" "O an unreadable stream is unknown (null), never []"
}

t_visible_notes() {
  local R="$TMP/h5"; make_repo "$R"; STUB="$TMP/stubh5"; LOG="$R/log"
  mk_gated gz 'src/**'
  stub "$STUB" '[ -d .claude/skills/gz ] && reveal gz; exit 0'
  sweep --candidate gz --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r .candidate_visible_runs)/$(echo "$j" | jq -r .candidate_fired_runs)" "2/0" "V visible but never invoked is told apart"
  ok "$(echo "$j" | jq -r '.notes[0] | test("never invoked")')" "true" "V and the note says: fix the description"
  stub "$STUB" 'exit 0'
  sleep 1; sweep --candidate gz --phase confirm >/dev/null
  ok "$(score | jq -r '.notes[0] | test("never became visible")')" "true" "V never visible: the note says fix paths"
  stub "$STUB" 'if [ -d .claude/skills/gz ]; then fire gz; sed -i "s/a - b/a + b/" src/calc.py; fi; exit 0'
  sleep 1; sweep --candidate gz --phase confirm >/dev/null
  j=$(score)
  ok "$(echo "$j" | jq -r '.notes | length')/$(echo "$j" | jq -r .verdict)" "0/KEEP" "V a gated skill that fires and helps is kept"
  ok "$(echo "$j" | jq -r .candidate_visible_runs)" "2" "V firing implies visible"
  ok "$(echo "$j" | jq -r .candidate_tier)" "gated" "V the tier is recorded"
}

t_legacy_no_visible() {
  local R="$TMP/h6"; make_repo "$R"
  synth .evolve/runs/l.jsonl 2  01 0 2
  ok "$(score .evolve/runs/l.jsonl | jq -r .candidate_visible_runs)" "null" "V old results files report visibility as unknown"
  ok "$(score .evolve/runs/l.jsonl | jq -r .verdict)" "KEEP" "V and still decide as before"
}

t_keep_requires_fired() {
  local R="$TMP/h7"; make_repo "$R"; STUB="$TMP/stubh7"; LOG="$R/log"
  mk_cand vbd
  # the cand arm improves, but the candidate never loaded: not its doing
  stub "$STUB" 'if [ -d .claude/skills/vbd ]; then sed -i "s/a - b/a + b/" src/calc.py; fi; exit 0'
  sweep --candidate vbd --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r .verdict)" "KILL" "G5 a win from a candidate that never loaded is not kept"
  ok "$(echo "$j" | jq -r '[.gates_failed[] | startswith("gate5")] | any')" "true" "G5 and gate5 is named"
}

t_observe_failure_unknown() {
  local R="$TMP/h8"; make_repo "$R"; STUB="$TMP/stubh8"; LOG="$R/log"
  mk_cand vbd
  stub "$STUB" 'if [ -d .claude/skills/vbd ]; then fire vbd; sed -i "s/a - b/a + b/" src/calc.py; fi; exit 0'
  CORTEX_STUB_NOINIT=1 sweep --candidate vbd --phase confirm >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r .verdict)" "RERUN" "U unreadable output: add mode is RERUN, never KEEP or KILL"
  ok "$(echo "$j" | jq -r .candidate_fired_runs)/$(echo "$j" | jq -r .firing_unknown_runs)" "null/4" "U firing is null, not zero"
  mk_live old-skill
  stub "$STUB" 'sed -i "s/a - b/a + b/" src/calc.py; exit 0'
  sleep 1; CORTEX_STUB_NOINIT=1 sweep --replace old-skill --phase confirm >/dev/null
  ok "$(score | jq -r .verdict)" "RERUN" "U replace mode is RERUN: unknown firing can never ACCEPT a deletion"
}

t_cross_tier_guard() {
  local R="$TMP/h9"; make_repo "$R"; STUB="$TMP/stubh9"; LOG="$R/log"; stub "$STUB" 'exit 0'
  mk_live vbd; mk_rule_cand vbd 'src/**'
  ok "$(dry --candidate vbd | grep -c 'already called')" "1" "X a rule candidate named like a live skill needs --replace"
  dry --candidate vbd --replace vbd >/dev/null; ok "$?" "0" "X with --replace it is accepted (a tier change)"
  mk_live dup; mk_live_rule dup 'src/**'
  ok "$(dry --replace dup | grep -c 'both a live skill and a live rule')" "1" "X a name that is both tiers is refused"
  CX skills >/dev/null 2>&1; ok "$?" "1" "X and cortex skills reports it as an error"
}

t_sweep_dry_run() {
  local R="$TMP/h10"; make_repo "$R"; STUB="$TMP/stubh10"; LOG="$R/log"
  local WT; WT=$(HX sandbox-dir)
  stub "$STUB" 'sleep 3; exit 0'; mk_cand vbd
  local out; out=$(dry --candidate vbd); local rc=$?
  ok "$rc/$(echo "$out" | grep -c '^sweep: OK')" "0/1" "D a dry run that would succeed says OK"
  ok "$(ls -1 .evolve/runs/*.jsonl 2>/dev/null | wc -l)" "0" "D and spends nothing, writes no results file"
  ok "$(dry --candidate ghost | grep -c '^sweep: REFUSED:')" "1" "D every refusal carries the REFUSED marker"
  ( PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --phase confirm >/dev/null 2>&1 ) &
  local bg=$!; sleep 1.5
  ok "$(dry --candidate vbd | grep -c 'lock held')" "1" "D a dry run during a sweep is refused on the lock"
  PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --phase screen >/dev/null 2>&1
  ok "$(ls -d "$WT"/work-* 2>/dev/null | wc -l | grep -q '^[1-9]' && echo alive || echo DELETED)" "alive" \
     "D a refused sweep does not delete the running sweep's sandbox"
  wait $bg 2>/dev/null
  ok "$(score | jq -r .invalid)" "0" "D and the running sweep finished with no broken rollouts"
}

t_reach_uses_sweep_tasks() {
  local R="$TMP/h11"; make_repo "$R"; STUB="$TMP/stubh11"; LOG="$R/log"; stub "$STUB" 'exit 0'
  mkdir -p lib; echo x > lib/x.py; git add -A; git commit -qm lib
  BROKEN=$(git rev-parse HEAD); mk_task 02
  mk_rule_cand lib-rule 'lib/**'
  ok "$(dry --candidate lib-rule --tasks 01 | grep -c 'could never load')" "1" \
     "R a sweep none of whose tasks can load the candidate is refused"
  dry --candidate lib-rule --tasks "01 02" >/dev/null; ok "$?" "0" "R one reachable task is enough"
  mk_gated newfile 'src/fresh_*.py'
  ok "$(dry --candidate newfile --tasks 01 | grep -c 'could never load')" "1" "R a gated skill no task reads or writes is refused"
}

t_task_id_and_sha_validation() {
  local R="$TMP/h12"; make_repo "$R"; STUB="$TMP/stubh12"; LOG="$R/log"; stub "$STUB" 'exit 0'
  mk_cand vbd
  ok "$(dry --candidate vbd --tasks '../x' | grep -c 'invalid task id')" "1" "I a task id cannot be a path"
  mk_task 03; sed -i 's|^base_sha: .*|base_sha: --output=/tmp/x|' .evolve/tasks/03/task.yaml
  ok "$(dry --candidate vbd --tasks 03 | grep -c 'not a commit id')" "1" "I a base_sha cannot be a git option"
  ok "$(dry --candidate .x | grep -c 'invalid skill name')" "1" "I a hidden name is refused"
  ok "$(CX promote -x 2>&1 | grep -c 'invalid skill name')" "1" "I a name that reads as an option is refused"
}

t_config_guards() {
  local R="$TMP/h13"; make_repo "$R"
  setcfg 'permission_mode: acceptEdits' 'permission_mode: bypassPermissions'
  CX config --check >/dev/null 2>&1; ok "$?" "1" "K bypassPermissions is refused for unattended rollouts"
  setcfg 'permission_mode: bypassPermissions' 'permission_mode: acceptEdits'
  addcfg '    - CLAUDE.md' '    - .claude/rules/x.md'
  CX config --check >/dev/null 2>&1; ok "$?" "1" "K a harness_file under .claude/rules would undo --replace: refused"
  setcfg '    - .claude/rules/x.md' '    - ../outside.md'
  CX config --check >/dev/null 2>&1; ok "$?" "1" "K a harness_file outside the repo is refused"
  setcfg '    - ../outside.md' '    - AGENTS.md'
  ok "$(CX config --check 2>&1)" "config.yaml is valid" "K a normal harness_file still validates"
  ok "$(jq -r .min_claude_version .evolve/config.json)/$(jq -r .always_on_budget_chars .evolve/config.json)" "2.1.276/3000" \
     "K the new settings compile with their defaults"
}

t_cli_version_gate() {
  local R="$TMP/h14"; make_repo "$R"; STUB="$TMP/stubh14"; LOG="$R/log"; stub "$STUB" 'exit 0'
  mk_cand vbd
  ok "$(CORTEX_STUB_VERSION=2.0.1 dry --candidate vbd | grep -c 'older than min_claude_version')" "1" \
     "CLI a sweep on an older CLI is refused"
  local out rc; out=$(CORTEX_STUB_VERSION=2.0.1 PATH="$STUB:$PATH" bash "$CORTEX/bin/cortex" doctor 2>&1); rc=$?
  ok "$([ $rc -ne 0 ] && echo fail || echo ok)/$(echo "$out" | grep -c 'TOO OLD')" "fail/1" "CLI doctor fails on an old CLI"
  PATH="$STUB:$PATH" bash "$CORTEX/bin/cortex" doctor >/dev/null 2>&1; ok "$?" "0" "CLI doctor passes on a current one"
  printf '%s\n' '{"event":"start","phase":"confirm","mode":"add","k":1,"candidate":"x","replaced":[]}' \
    '{"v":"base","t":"01","r":1,"pass":0,"valid":1,"skills":[],"visible":[],"cli_version":"2.1.276"}' \
    '{"v":"cand","t":"01","r":1,"pass":1,"valid":1,"skills":["x"],"visible":["x"],"cli_version":"2.1.280"}' \
    '{"event":"done"}' > .evolve/runs/m.jsonl
  ok "$(score .evolve/runs/m.jsonl | jq -r .verdict)" "RERUN" "CLI a CLI change mid-sweep makes it RERUN"
}

t_rule_promote_bury() {
  local R="$TMP/h15"; make_repo "$R"
  mk_live r3; mk_rule_cand r3 'src/**'
  ok "$(CX promote r3 2>&1 | grep -c 'already called')" "1" "B promote refuses a rule over a live skill of the same name"
  mk_live_rule r1 'src/**'
  CX bury r1 --from live --why "prune ACCEPT" >/dev/null
  ok "$([ -f .evolve/graveyard/r1/RULE.md ] && [ ! -e .claude/rules/r1.md ] && echo buried || echo no)" "buried" \
     "B a live rule is buried as graveyard/<name>/RULE.md"
  ok "$(grep -c '^kind: rule' .evolve/graveyard/r1/BURIED.md)" "1" "B BURIED.md records the kind"
  mk_live_rule r1 'lib/**'
  CX bury r1 --from live >/dev/null
  ok "$(ls .evolve/graveyard | grep -c '^r1-')/$(grep -c 'src' .evolve/graveyard/r1/RULE.md)" "1/1" \
     "B a second burial gets a dated entry and never touches the first"
  mk_rule_cand r4 'src/**'; echo x > .evolve/candidate/r4/extra.txt
  ok "$(CX promote r4 2>&1 | grep -c 'single file')" "1" "B a rule candidate with extra files is not promoted"
}

t_check_errors() {
  local R="$TMP/h16"; make_repo "$R"
  cand() { rm -rf .evolve/candidate/c1; mkdir -p .evolve/candidate/c1; printf -- "$1" > ".evolve/candidate/c1/${2:-SKILL.md}"
           CX skills --candidate c1 >/dev/null 2>&1; echo $?; }
  ok "$(cand '---\nname: c1\ndescription: d\n---\nx\n')" "0" "E a valid candidate passes"
  ok "$(cand '---\nname: c1\ndescription: d\npaths:\n  - **/*.py\n---\nx\n')" "1" "E an unquoted glob (a YAML alias) is an error"
  ok "$(cand '---\nname: c1\ndescription: Use when: editing\n---\nx\n')" "1" "E an unquoted ': ' is an error"
  ok "$(cand '---\nname: other\ndescription: d\n---\nx\n')" "1" "E a name that differs from its directory is an error"
  ok "$(cand "---\nname: c1\ndescription: $(printf 'x%.0s' $(seq 1 1600))\n---\nx\n")" "1" "E a description over 1536 chars is an error"
  mkdir -p .evolve/candidate/c1; printf -- '---\nname: c1\ndescription: d\n---\nx\n' > .evolve/candidate/c1/RULE.md
  CX skills --candidate c1 >/dev/null 2>&1; ok "$?" "1" "E both SKILL.md and RULE.md is an error"
  rm -rf .evolve/candidate/evolve; mkdir -p .evolve/candidate/evolve
  printf -- '---\nname: evolve\ndescription: d\n---\nx\n' > .evolve/candidate/evolve/SKILL.md
  CX skills --candidate evolve >/dev/null 2>&1; ok "$?" "1" "E a name that collides with a command is an error"
  rm -rf .evolve/candidate/Bad_Name; mkdir -p .evolve/candidate/Bad_Name
  printf -- '---\ndescription: d\n---\nx\n' > .evolve/candidate/Bad_Name/SKILL.md
  CX skills --candidate Bad_Name >/dev/null 2>&1; ok "$?" "1" "E a candidate must be lowercase-hyphenated"
  printf -- '# no paths\nalways\n' > .claude/rules/everywhere.md
  mkdir -p sub/.claude/skills/n; printf -- '---\nname: n\ndescription: d\n---\nx\n' > sub/.claude/skills/n/SKILL.md; git add sub
  mk_live cites; printf -- '---\nname: cites\ndescription: d\n---\nSee `src/missing.py`.\n' > .claude/skills/cites/SKILL.md
  local out; out=$(CX skills 2>&1); local rc=$?
  ok "$rc" "0" "E warnings never fail the check"
  ok "$(echo "$out" | grep -c 'belongs in CLAUDE.md')" "1" "E a path-less rule is flagged as always loaded"
  ok "$(echo "$out" | grep -c 'nested .claude/skills')" "1" "E a nested .claude/skills is flagged as unmeasured"
  ok "$(echo "$out" | grep -c 'cites src/missing.py')" "1" "E a cited path that no longer exists is flagged (drift)"
}

t_check_folded_description() {
  local R="$TMP/h17"; make_repo "$R"
  mkdir -p .claude/skills/folded
  printf -- '---\nname: folded\ndescription: >\n  Use when editing calc.\n  Second line.\n---\nbody\n' > .claude/skills/folded/SKILL.md
  local out; out=$(CX skills 2>&1); local rc=$?
  ok "$rc/$(echo "$out" | grep -c 'always *folded .*Use when editing calc.')" "0/1" "E a folded description is parsed and shown"
}

t_live_items_never_block() {
  local R="$TMP/h18"; make_repo "$R"
  mkdir -p .claude/skills/My_Skill
  printf -- '---\ndescription: d\npaths:\n  - **/*.py\n---\nx\n' > .claude/skills/My_Skill/SKILL.md
  mk_live_rule nowhere 'nothere/**'
  local out; out=$(CX skills 2>&1); local rc=$?
  ok "$rc" "0" "L hand-written live items only warn, they never block"
  ok "$(echo "$out" | grep -c 'DEAD glob')" "1" "L a glob that matches nothing is reported DEAD"
  ok "$(echo "$out" | grep -c 'My_Skill.*quote it')" "1" "L a live YAML problem is reported"
  ok "$(CX status | grep -c 'DEAD')" "1" "L status shouts about DEAD paths"
}

t_dead_glob_repair() {
  local R="$TMP/h19"; make_repo "$R"
  mkdir -p services/api; echo a > services/api/a.py; git add -A; git commit -qm api
  mk_live_rule api 'services/api/**'
  git mv services/api services/backend; git commit -qm rename
  ok "$(CX skills 2>&1 | grep -c "repair: 'services/api/\*\*' -> 'services/backend/\*\*'")" "1" \
     "L a directory rename is traced in git and the repaired glob is proposed"
  sed -i 's|services/api/\*\*|services/backend/**|' .claude/rules/api.md
  ok "$(CX skills 2>&1 | grep -c 'DEAD')" "0" "L after the repair the rule is live again"
}

t_glob_unit() {
  local R="$TMP/h20"; make_repo "$R"
  local bad; bad=$(PYTHONDONTWRITEBYTECODE=1 python3 - "$CORTEX/bin" <<'P'
import sys; sys.path.insert(0, sys.argv[1]); import harness as h
# every case marked (CLI) was observed on the real Claude Code 2.1.276
cases = [("src/**/*.py","src/calc.py",1),("src/**/*.py","src/a/b.py",1),
 ("lib3/*","lib3/x/c.py",1),                 # (CLI) a dir match covers what is below it
 ("src2","src2/sub/a.py",1),                 # (CLI) bare dir name, any depth
 ("conf2/","conf2/deep/b.py",1),             # (CLI) trailing slash
 ("src5/*.py","src5/sub/b.py",0),            # (CLI) a FILE pattern does not reach down
 ("e6/f6","d6/e6/f6/c.py",0),                # (CLI) a / anchors at the root
 ("{zzA,zzB}/*.py","zzB/f.py",1),            # (CLI) braces expand
 ("*.txt","x.txt",1),("src/*","src/a",1),
 ("*.txt","deep/nest/note.txt",1),("*.txt","note.txt",1),("src/*","src/.hidden",1),
 ("conf/**","conf/.cfg/x.txt",1),("src/?.py","src/a.py",1),("src/?.py","src/ab.py",0),
 ("{src,lib}/**/*.{ts,tsx}","lib/x/y.tsx",1),("{a,{b,c}}/x","c/x",1),("./src/*","src/a",1),
 ("docs/","docs/a/b.md",1),("src/[ab].py","src/b.py",1),("src/[!ab].py","src/b.py",0),("src/**","lib/a",0)]
print(sum(1 for p, f, e in cases if h.Globs([p]).match(f) != bool(e)))
P
)
  ok "$bad" "0" "GL glob semantics match Claude Code (slash-less at any depth, dotfiles, braces)"
  ok "$(PYTHONDONTWRITEBYTECODE=1 python3 -c "import sys; sys.path.insert(0,'$CORTEX/bin'); import harness as h; print(h.Globs(['{a,b}{c,d}{e,f}{g,h}{i,j}{k,l}{m,n}{o,p}{q,r}']).error is not None)")" \
     "True" "GL a brace bomb is refused, not expanded"
}

t_touching() {
  local R="$TMP/h21"; make_repo "$R"
  mk_live_rule oldarea 'old/**'; mk_live_rule newrule 'new/**'
  mkdir -p .claude/skills/newarea
  printf -- '---\nname: newarea\ndescription: d\npaths:\n  - "new/**"\n---\nx\n' > .claude/skills/newarea/SKILL.md
  printf 'diff --git a/old/a.py b/new/a.py\nrename from old/a.py\nrename to new/a.py\n--- /dev/null\n+++ b/new/b.py\n' > p1
  ok "$(HX touching p1)" "area: newarea, oldarea" "T a rule matches files that existed before the fix, a skill either side"
  printf -- '--- /dev/null\n+++ b/new/c.py\n' > p2
  ok "$(HX touching p2)" "area: newarea" "T a file the fix only creates never reaches a rule"
}

t_hash_paths() {
  local R="$TMP/h22"; make_repo "$R"
  mkdir -p .claude/skills/x; printf 'same\n' > .claude/skills/x/SKILL.md
  local h1 h2; h1=$(HX hash)
  rm -rf .claude/skills/x; printf 'same\n' > .claude/rules/x.md; h2=$(HX hash)
  ok "$([ "$h1" != "$h2" ] && echo differ || echo same)" "differ" "HS moving the same text from a skill to a rule changes the hash"
  mkdir -p ".claude/skills/sp ace"; printf 'a\n' > ".claude/skills/sp ace/SKILL.md"
  ok "$(HX hash | wc -c)" "17" "HS names with spaces are hashed safely"
  ok "$(CX status | grep -c "^harness  $(HX hash)")" "1" "HS status prints the harness hash"
  synth .evolve/runs/b.jsonl 1  01 0 1
  CX baseline --model m >/dev/null
  ok "$(jq -r .hash_v .evolve/baseline.json)/$([ "$(jq -r .skills_hash .evolve/baseline.json)" = "$(HX hash)" ] && echo match)" "2/match" \
     "HS the baseline records the same hash, versioned"
}

t_init_claude_md() {
  local R="$TMP/h23"; rm -rf "$R"; mkdir -p "$R"; cd "$R"; git init -q
  CX init . >/dev/null
  ok "$([ -f CLAUDE.md ] && [ -d .claude/rules ] && echo yes)" "yes" "IN init creates a minimal CLAUDE.md and .claude/rules"
  CX init . >/dev/null
  ok "$(grep -cx '.evolve/runs/' .gitignore)/$(grep -cx '.evolve/candidate/' .gitignore)" "1/1" "IN re-init never duplicates .gitignore lines"
  R="$TMP/h23b"; rm -rf "$R"; mkdir -p "$R"; cd "$R"; git init -q; echo mine > CLAUDE.md
  printf '# cortex runtime\n.evolve/runs/\n' > .gitignore
  CX init . >/dev/null
  ok "$(cat CLAUDE.md)" "mine" "IN an existing CLAUDE.md is never touched"
  ok "$(grep -cx '.evolve/candidate/' .gitignore)" "1" "IN a repo from an older Cortex gets the missing .gitignore line"
  R="$TMP/h23c"; rm -rf "$R"; mkdir -p "$R/.claude"; cd "$R"; git init -q; echo m > .claude/CLAUDE.md
  CX init . >/dev/null
  ok "$([ -e CLAUDE.md ] && echo created || echo none)" "none" "IN no second CLAUDE.md beside .claude/CLAUDE.md"
  R="$TMP/h23d"; rm -rf "$R"; mkdir -p "$R"; cd "$R"; git init -q; ln -s missing CLAUDE.md
  CX init . >/dev/null
  ok "$([ -L CLAUDE.md ] && echo link || echo replaced)" "link" "IN a dangling CLAUDE.md symlink is left alone"
}

t_init_backs_up_commands() {
  local R="$TMP/h24"; make_repo "$R"
  echo "# my local edit" >> .claude/commands/evolve.md
  CX init "$R" >/dev/null
  ok "$(ls .claude/commands/evolve.md.bak-* 2>/dev/null | wc -l)" "1" "IN re-init keeps an edited command as .bak"
  ok "$(grep -c 'my local edit' .claude/commands/evolve.md.bak-*)" "1" "IN with the edit inside"
  ok "$(cmp -s "$CORTEX/commands/evolve.md" .claude/commands/evolve.md && echo same)" "same" "IN and installs the new one"
  sleep 1; CX init "$R" >/dev/null
  ok "$(ls .claude/commands/*.bak-* 2>/dev/null | wc -l)" "1" "IN an unedited command is not backed up again"
  # an OLDER Cortex's unedited copy: it matches what init recorded installing
  echo "# an older shipped version" > .claude/commands/prune.md
  python3 - <<'PY'
import hashlib; p=".claude/commands/.cortex-installed"; lines=open(p).read().split("\n")
h=hashlib.sha256(open(".claude/commands/prune.md","rb").read()).hexdigest()
open(p,"w").write("\n".join(("prune "+h) if l.startswith("prune ") else l for l in lines))
PY
  sleep 1; local out; out=$(CX init "$R")
  ok "$(ls .claude/commands/prune.md.bak-* 2>/dev/null | wc -l)/$(echo "$out" | grep -c 'updated /prune')" "0/1" \
     "IN an older unedited copy is updated quietly, not reported as your edit"
}

t_symlink_out_of_repo_refused() {
  local R="$TMP/h25"; make_repo "$R"; STUB="$TMP/stubh25"; LOG="$R/log"; stub "$STUB" 'exit 0'
  echo secret > "$TMP/outside.txt"
  mk_live evil; ln -s "$TMP/outside.txt" .claude/skills/evil/leak.txt
  local out; out=$(CX skills 2>&1); local rc=$?
  ok "$rc/$(echo "$out" | grep -c 'points outside the repository')" "1/1" "SY a symlink out of the repo is an error"
  mk_cand vbd
  ok "$(dry --candidate vbd | grep -c '^sweep: REFUSED:')" "1" "SY and no sweep copies it into a sandbox"
}

# ================================================ deep-review regressions ====
t_frontmatter_differential() {
  local R="$TMP/r10"; make_repo "$R"
  python3 -c "import yaml" 2>/dev/null || { pass "FM (skipped: PyYAML not installed)"; return; }
  local out; out=$(PYTHONDONTWRITEBYTECODE=1 python3 - "$CORTEX/bin" <<'P'
import sys, yaml; sys.path.insert(0, sys.argv[1]); import harness as h
bodies = ['name: x\ndescription: d\npaths:\n  - "src/**"', 'name: x\ndescription: d\npaths:\n  - **/*.py',
 'name: x\ndescription: d\npaths: "src/**, lib/*"', 'name: x\ndescription: d\npaths: [src/**, "lib/*"]',
 'name: x\ndescription: Use when: editing', 'name: x\ndescription: "Use when: editing"',
 "name: x\ndescription: 'it''s fine'", 'name: x\ndescription: >\n  Use when\n  editing.\n\n  Second.',
 'name: x\ndescription: |\n  l1\n  l2', 'name: x   # c\ndescription: d # c2\npaths:   # c3\n  - "a/**"  # c4',
 'name: x\ndescription: a#b', 'name: x\ndescription: "unterminated', 'name: x\ndescription: &anchor d',
 'name: x\ndescription: !tag d', 'name: x\ndescription: @at', 'name: x\ndescription: ?q',
 'name: x\ndescription: plain\n  continued line', 'name: x\ndescription: ends with colon:',
 'name: x\ndescription: url https://example.com/a', 'name: x\ndescription: d\npaths: "{a,b}/*.py"',
 'name: x\ndescription: d\n\n# comment\npaths:\n  - "a/**"', 'name: x\ndescription: %p']
def mine(b):
    try: return h.parse_frontmatter("---\n" + b + "\n---\nbody\n")[0]
    except h.FrontmatterError: return None
def oracle(b):
    try: return yaml.safe_load(b)
    except yaml.YAMLError: return None
def norm(d):
    if d is None: return "REJECT"
    ds = d.get("description")
    return (d.get("name"), ds.rstrip("\n") if isinstance(ds, str) else ds, h.split_paths(d.get("paths")))
print(sum(1 for b in bodies if norm(mine(b)) != norm(oracle(b))))
P
)
  ok "$out" "0" "FM the frontmatter parser accepts and rejects exactly what YAML does"
  ok "$(PYTHONDONTWRITEBYTECODE=1 python3 -c "import sys; sys.path.insert(0,'$CORTEX/bin'); import harness as h
try: h.parse_frontmatter('---\nname: x\nname: y\n---\n'); print('accepted')
except h.FrontmatterError: print('rejected')")" "rejected" "FM a duplicate key is rejected (strict loaders refuse it)"
}

t_candidate_hygiene() {
  local R="$TMP/r11"; make_repo "$R"
  mkdir -p .evolve/candidate/manual
  printf -- '---\nname: manual\ndescription: d\ndisable-model-invocation: true\n---\nx\n' > .evolve/candidate/manual/SKILL.md
  ok "$(CX skills --candidate manual 2>&1 | grep -c 'no rollout can ever load it')" "1" \
     "CH a candidate the model can never invoke is refused before a sweep"
  mkdir -p .evolve/candidate/broken; printf 'x\n' > .evolve/candidate/broken/notes.txt
  CX bury broken --from candidate --why "malformed" >/dev/null 2>&1
  ok "$([ -d .evolve/graveyard/broken ] && [ ! -e .evolve/candidate/broken ] && echo buried || echo stuck)" "buried" \
     "CH a malformed candidate can still be buried (cleaned up)"
  ok "$(grep -c '^kind: malformed' .evolve/graveyard/broken/BURIED.md)" "1" "CH and its kind says so"
  ok "$(CX skills --candidate 2>&1; echo "rc=$?")" "$(printf 'harness: check: --candidate needs a value\nrc=2')" \
     "CH a missing option value is a clean error, not a traceback"
  ok "$(HX cli-version --min abc >/dev/null 2>&1; echo $?)" "2" "CH an unreadable version bound fails closed"
}

t_sweep_args_injection() {
  local R="$TMP/r12"; make_repo "$R"; STUB="$TMP/stubr12"; LOG="$R/log"; stub "$STUB" 'exit 0'; mk_cand vbd
  rm -f "$TMP/pwned"
  # REPO is set inside sweep.sh, so under `set -u` bash WOULD expand the subscript
  dry --candidate vbd --k "REPO[\$(touch $TMP/pwned)]" >/dev/null
  ok "$([ -e "$TMP/pwned" ] && echo EXECUTED || echo safe)" "safe" "SA --k cannot inject a command through bash arithmetic"
  ok "$(dry --candidate vbd --phase ../../escape | grep -c 'must be screen, confirm or recheck')" "1" "SA --phase cannot name a path"
  ok "$(PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate 2>&1 | grep -c 'needs a value')" "1" \
     "SA a missing option value is refused cleanly"
}

t_symlink_variants() {
  local R="$TMP/r13"; make_repo "$R"; STUB="$TMP/stubr13"; LOG="$R/log"
  # the layout from research/skills_management: .claude/rules -> ../rules (inside the repo)
  rm -rf .claude/rules; mkdir -p rules; mk_rule_cand dummy 'src/**'; rm -rf .evolve/candidate/dummy
  printf -- '---\npaths:\n  - "src/**"\n---\nLIVE-RULE-TEXT\n' > rules/api.md
  ln -s ../rules .claude/rules
  ok "$(CX skills >/dev/null 2>&1; echo $?)" "0" "SV a .claude/rules symlink inside the repo is fine"
  stub "$STUB" '{ [ -f .claude/rules/api.md ] && [ ! -L .claude/rules/api.md ] && grep -q LIVE-RULE-TEXT .claude/rules/api.md && echo live; } >> "$CORTEX_TEST_OUT"; exit 0'
  mk_cand vbd
  CORTEX_TEST_OUT="$R/seen.txt" sweep --candidate vbd --phase confirm >/dev/null
  ok "$(grep -c '^live$' "$R/seen.txt" 2>/dev/null)" "4" "SV the sandbox gets the live rule text, dereferenced"
  # a link INSIDE the tree, to a file that is not committed: copied as a link it
  # would dangle in the sandbox (which is checked out at base_sha)
  mkdir -p shared .claude/skills/linked; printf -- '---\nname: linked\ndescription: d\n---\nSHARED-TEXT\n' > shared/SKILL.md
  ln -s ../../../shared/SKILL.md .claude/skills/linked/SKILL.md
  stub "$STUB" '{ [ -f .claude/skills/linked/SKILL.md ] && [ ! -L .claude/skills/linked/SKILL.md ] && grep -q SHARED-TEXT .claude/skills/linked/SKILL.md && echo inner; } >> "$CORTEX_TEST_OUT"; exit 0'
  sleep 1; CORTEX_TEST_OUT="$R/seen2.txt" sweep --candidate vbd --phase confirm >/dev/null
  ok "$(grep -c '^inner$' "$R/seen2.txt" 2>/dev/null)" "4" "SV a symlinked file inside the tree reaches the sandbox as its live content"
  rm -rf .claude/skills/linked shared
  rm .claude/rules; mkdir -p "$TMP/outside-rules"; ln -s "$TMP/outside-rules" .claude/rules
  ok "$(CX skills 2>&1 | grep -c 'symlink .claude/rules points outside')" "1" "SV .claude/rules itself linked outside the repo is an error"
  rm .claude/rules; mkdir .claude/rules
  ln -s "$R/nowhere" .claude/skills/dangling
  ok "$(CX skills 2>&1 | grep -c 'is dangling')" "1" "SV a dangling symlink is an error"
  rm .claude/skills/dangling
  mkdir -p "$TMP/outside-skill"; printf -- '---\nname: out\ndescription: d\n---\nx\n' > "$TMP/outside-skill/SKILL.md"
  ln -s "$TMP/outside-skill" .claude/skills/out
  ok "$(CX skills 2>&1 | grep -c 'points outside the repository')" "1" "SV a skill DIRECTORY symlinked outside the repo is an error"
}

t_tier_change_skill_to_rule() {
  local R="$TMP/r14"; make_repo "$R"; STUB="$TMP/stubr14"; LOG="$R/log"
  mk_live a; mk_rule_cand a 'src/**'
  stub "$STUB" 'echo "$([ -d .claude/skills/a ] && echo skill || echo -)/$([ -f .claude/rules/a.md ] && echo rule || echo -)" >> "$CORTEX_TEST_OUT"; exit 0'
  CORTEX_TEST_OUT="$R/arms.txt" sweep --candidate a --replace a --phase confirm >/dev/null
  ok "$(LC_ALL=C sort "$R/arms.txt" | tr '\n' ' ')" "-/rule -/rule skill/- skill/- " \
     "TC narrowing a skill into a rule: base has only the skill, cand only the rule"
}

t_status_and_budget() {
  local R="$TMP/r15"; make_repo "$R"
  local out rc; out=$(CX status 2>&1); rc=$?
  ok "$rc/$(echo "$out" | grep -c '^last cycle:')" "0/1" "ST status runs to the end in a new repo (no .evolve/ablation)"
  rm -rf .claude/skills; out=$(CX status 2>&1); rc=$?
  ok "$rc/$(echo "$out" | grep -c '^last cycle:')" "0/1" "ST and without .claude/skills"
  mkdir -p .claude/skills
  mk_live s1; mkdir -p .claude/skills/g1
  printf -- '---\nname: g1\ndescription: d\npaths:\n  - "src/**"\n---\nx\n' > .claude/skills/g1/SKILL.md
  mk_live_rule r1 'src/**'
  ok "$(CX status | grep -c '^tiers    1 always-on, 1 path-gated, 1 rules')" "1" "ST status counts every tier"
  local before after; before=$(HX summary | jq .always_on_chars)
  printf '%0500d\n' 0 > CLAUDE.local.md; after=$(HX summary | jq .always_on_chars)
  ok "$(( after - before ))" "501" "ST CLAUDE.local.md is counted as always-on context"
}

# ======================================================== /prune: usage + plan ==
# a transcript line in the shape Claude Code writes them
tx_skill() { printf '{"type":"assistant","timestamp":"%s","cwd":"%s","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"%s"}}]}}\n' "$1" "$2" "$3"; }
tx_file()  { printf '{"type":"assistant","timestamp":"%s","cwd":"%s","message":{"content":[{"type":"tool_use","name":"%s","input":{"file_path":"%s"}}]}}\n' "$1" "$2" "$3" "$4"; }
tx_dir()   { python3 -c "import re,os,sys; print(re.sub(r'[^A-Za-z0-9]','-',os.path.realpath(sys.argv[1])))" "$1"; }
hist_rows() {                 # past sweep rows: base-arm firing + measured cost
  printf '%s\n' '{"event":"start","k":1}' \
    '{"v":"base","t":"01","valid":1,"agent_rc":0,"secs":100,"wall_secs":110,"tokens":140000,"cost_usd":0.2,"skills":["a"],"visible":["a","b"]}' \
    '{"v":"cand","t":"01","valid":1,"agent_rc":0,"secs":90,"wall_secs":90,"tokens":160000,"cost_usd":0.4,"skills":[],"visible":[]}' \
    > .evolve/runs/20200101T000000-confirm.jsonl
}

t_usage_report() {
  local R="$TMP/u1"; make_repo "$R"; local TX="$TMP/u1-tx"; rm -rf "$TX"
  setcfg 'transcripts_dir: ~/.claude/projects' "transcripts_dir: $TX"; CX config >/dev/null 2>&1
  mk_live a; mk_live_rule srcrule 'src/**'
  local P now old real; P="$TX/$(tx_dir "$R")"; mkdir -p "$P" "$TX/$(tx_dir "$R")-sibling"
  now=$(date -u +%Y-%m-%dT%H:%M:%S.000Z); old=$(date -u -d '-90 days' +%Y-%m-%dT%H:%M:%S.000Z); real=$(cd "$R" && pwd -P)
  { tx_skill "$now" "$real" a; tx_file "$now" "$real" Edit "$real/src/calc.py"; } > "$P/s1.jsonl"
  { tx_skill "$now" "$real" a; tx_file "$now" "$real" Read "$real/src/calc.py"; } > "$P/s2.jsonl"
  tx_skill "$old" "$real" a > "$P/s3-old.jsonl"
  # a folder whose name shares the prefix but whose sessions ran elsewhere
  tx_skill "$now" "/somewhere/else" a > "$TX/$(tx_dir "$R")-sibling/s4.jsonl"
  local j; j=$(CX usage --json)
  ok "$(echo "$j" | jq -r '.items[] | select(.name=="a") | "\(.sessions)/\(.uses)"')" "2/2" \
     "UR a skill's real uses are counted, per session"
  ok "$(echo "$j" | jq -r '.sessions_scanned')" "2" "UR events older than the window, and sessions outside the repo, are ignored"
  ok "$(echo "$j" | jq -r '.items[] | select(.name=="srcrule") | .uses')" "1" "UR a rule counts as used when a matching file was Read"
  ok "$(echo "$j" | jq -r '.items[] | select(.name=="a") | .top_folder')" "src/" "UR the folder its use concentrates in is reported"
  ok "$(echo "$j" | jq -r '.items[] | select(.name=="srcrule") | .reachable_tasks | join(",")')" "01" "UR which tasks can measure it"
  ok "$(CX usage --days 200 --json | jq -r '.items[] | select(.name=="a") | .uses')" "3" "UR --days widens the window"
  ok "$(CX usage 2>&1 | grep -c 'never a reason to delete')" "1" "UR the report says it is advisory"
}

t_prune_plan_flow() {
  local R="$TMP/u2"; make_repo "$R"; STUB="$TMP/stubu2"; LOG="$R/log"
  setcfg 'model: ""' 'model: m1'; CX config >/dev/null 2>&1
  mk_live a; mk_live b; mk_live c
  mkdir -p .claude/skills/g; printf -- '---\nname: g\ndescription: d\npaths:\n  - "src/**"\n---\nx\n' > .claude/skills/g/SKILL.md
  hist_rows
  ok "$(CX prune plan --items "a b c g" >/dev/null 2>&1; echo $?)" "2" "PP a routine pass cannot exceed prune.max_items"
  CX prune plan --items "a b g" --why "a=overlaps c" >/dev/null
  local p=.evolve/prune-plan.json
  ok "$(jq -r '.status + "/" + .mode' $p)" "proposed/routine" "PP a plan starts PROPOSED"
  ok "$(jq -r '.items[] | select(.name=="a") | .tasks | join(",")' $p)" "01" "PP an always-on item is measured where it loaded before"
  ok "$(jq -r '.items[] | select(.name=="b") | .state' $p)" "skipped" "PP an item live but never loaded is skipped (it could only be UNMEASURED)"
  ok "$(jq -r '.items[] | select(.name=="g") | .tasks | join(",")' $p)" "01" "PP a gated item is measured where its paths exist"
  ok "$(jq -r '.estimate.rollouts' $p)" "8" "PP the estimate counts tasks x k x 2 for every item that runs"
  ok "$(jq -r '.estimate.basis | startswith("measured")' $p)/$(jq -r '.estimate.cost_usd' $p)" "true/2.4" \
     "PP the estimate is measured from this repo's own rollouts (tokens, time, cost)"
  ok "$(CX prune status | grep -c 'nothing runs until you approve')" "1" "PP the plan tells the user nothing runs before approval"
  ok "$(CX prune next >/dev/null 2>&1; echo $?)" "1" "PP next refuses before the user approves"
  ok "$(CX prune plan --items a >/dev/null 2>&1; echo $?)" "1" "PP a second plan cannot start while one is open"
  CX prune approve >/dev/null
  ok "$(CX prune next --json | jq -r '.name + " " + .command')" 'a cortex sweep --replace a --tasks "01" --phase confirm' \
     "PP next hands out the targeted command"
  stub "$STUB" '[ -d .claude/skills/a ] && fire a; sed -i "s/a - b/a + b/" src/calc.py; exit 0'
  sleep 1; sweep --replace a --tasks 01 --phase confirm >/dev/null
  ok "$(CX prune next --json | jq -r '.sweep.finished')" "true" "PP next finds the item's finished sweep by itself"
  ok "$(CX prune record a --verdict RERUN >/dev/null 2>&1; echo $?)" "2" "PP a RERUN is not recorded as a decision"
  CX prune record a --verdict ACCEPT --results "$(CX prune next --json | jq -r .sweep.file)" >/dev/null
  ok "$(CX prune next --json | jq -r '.name')" "g" "PP then the next item"
  CX prune record g --verdict REJECT >/dev/null
  ok "$(CX prune next >/dev/null 2>&1; echo $?)" "3" "PP next says when nothing is left"
  CX prune finish >/dev/null
  ok "$(jq -r '.last_prune_model' .evolve/state.json)/$(jq -r .status $p)" "m1/done" "PP finish closes the plan and remembers the model"
  CX prune plan --items a >/dev/null; CX prune cancel >/dev/null
  ok "$(jq -r .status $p)" "cancelled" "PP a plan can be cancelled"
}

t_prune_model_upgrade() {
  local R="$TMP/u3"; make_repo "$R"
  setcfg 'model: ""' 'model: m2'; CX config >/dev/null 2>&1
  mk_live small
  mkdir -p .claude/skills/big; printf -- '---\nname: big\ndescription: %s\n---\nx\n' "$(printf 'w%.0s' $(seq 1 300))" > .claude/skills/big/SKILL.md
  for i in 1 2 3 4; do mk_live "extra$i"; done
  printf '{"last_prune_model":"m1"}' > .evolve/state.json
  ok "$(CX prune plan --items small >/dev/null 2>&1; echo $?)" "2" "MU after a model change the user cannot narrow the pass"
  CX prune plan >/dev/null
  ok "$(jq -r .mode .evolve/prune-plan.json)" "model-upgrade" "MU a changed pinned model is detected"
  ok "$(jq -r '.items | length' .evolve/prune-plan.json)" "6" "MU every item is in the plan, beyond prune.max_items"
  ok "$(jq -r '.items[0].name' .evolve/prune-plan.json)" "big" "MU the biggest always-on context is tested first"
  CX prune cancel >/dev/null
  setcfg 'model: m2' 'model: ""'; CX config >/dev/null 2>&1
  ok "$(CX prune plan 2>&1 | grep -c 'choose what to test')" "1" "MU with no pinned model a pass is routine (a change cannot be detected)"
}

t_prune_estimate_defaults() {
  local R="$TMP/u4"; make_repo "$R"
  ok "$(CX prune estimate --tasks 01 | grep -c '4 rollouts')" "1" "PE estimate counts tasks x k x 2"
  ok "$(CX prune estimate --tasks 01 | grep -c 'defaults')" "1" "PE with no history it says the numbers are defaults"
}

t_sweep_records_cost() {
  local R="$TMP/u5"; make_repo "$R"; STUB="$TMP/stubu5"; LOG="$R/log"; mk_cand vbd
  stub "$STUB" 'if [ -d .claude/skills/vbd ]; then fire vbd; sed -i "s/a - b/a + b/" src/calc.py; fi
printf "{\"type\":\"result\",\"usage\":{\"input_tokens\":10,\"output_tokens\":20,\"cache_creation_input_tokens\":30,\"cache_read_input_tokens\":40},\"total_cost_usd\":0.05}\n"
exit 0'
  sweep --candidate vbd --phase confirm >/dev/null
  local f; f=$(ls -1t .evolve/runs/*.jsonl | head -1)
  ok "$(jq -r 'select(.v=="cand") | .tokens' "$f" | head -1)" "100" "SC every rollout records its real tokens"
  ok "$(jq -r 'select(.v=="cand") | .wall_secs | type' "$f" | head -1)" "number" "SC and its wall-clock time"
  ok "$(score | jq -r '.tokens_total')/$(score | jq -r '.cost_usd_total')" "400/0.2" "SC score totals what the sweep cost"
}

t_config_prune_keys() {
  local R="$TMP/u6"; make_repo "$R"
  ok "$(jq -r '"\(.prune_usage_days)/\(.prune_max_items)"' .evolve/config.json)" "30/3" \
     "CP the new prune settings compile with their defaults"
  setcfg 'max_items: 3' 'max_items: 0'
  ok "$(CX config --check >/dev/null 2>&1; echo $?)" "1" "CP max_items 0 is refused"
  setcfg 'max_items: 0' 'max_items: many'
  ok "$(CX config --check 2>&1 | grep -c 'expected int')" "1" "CP a wrongly typed value is an error, not a crash"
}

# ================================ exposure, recheck, sandbox leaks, fixpatch ==
synthv() {  # $1 file, $2 phase, $3 k, then "task base_passes cand_passes exposed(0|1)" quads
  local f="$1" ph="$2" k="$3"; shift 3
  printf '{"event":"start","phase":"%s","mode":"add","k":%s,"candidate":"x","candidate_kind":"skill","candidate_tier":"gated","replaced":[],"harness_base":"hb","harness_cand":"hc"}\n' "$ph" "$k" > "$f"
  while [ $# -gt 0 ]; do
    local t="$1" b="$2" c="$3" e="$4" r l; shift 4
    [ "$e" = 1 ] && l='["x"]' || l='[]'
    for r in $(seq 1 "$k"); do
      printf '{"v":"base","t":"%s","r":%s,"pass":%s,"valid":1,"skills":[],"rules":[],"visible":[]}\n' "$t" "$r" "$([ "$r" -le "$b" ] && echo 1 || echo 0)" >> "$f"
      printf '{"v":"cand","t":"%s","r":%s,"pass":%s,"valid":1,"skills":%s,"rules":[],"visible":%s}\n' "$t" "$r" "$([ "$r" -le "$c" ] && echo 1 || echo 0)" "$l" "$l" >> "$f"
    done
  done
  echo '{"event":"done"}' >> "$f"
}

# ============================================================ PARALLEL =====
t_parallel_config() {
  local R="$TMP/p1"; rm -rf "$R"; mkdir -p "$R"; cd "$R"; git init -q; git commit -q --allow-empty -m i
  CX init . >/dev/null
  ok "$(jq -c '[.parallel_rollouts, .parallel_preflight, .parallel_ram_percent, .parallel_ram_per_rollout_mb, .parallel_ram_per_check_mb, .parallel_max_rollouts, .parallel_with_services]' .evolve/config.json)" \
     '["auto","auto",50,1024,512,16,false]' "P the defaults: auto, 50% of the available RAM, services one at a time"
  cp .evolve/config.yaml "$TMP/p1.yaml"
  local bad
  for bad in 'rollouts: 0' 'rollouts: fast' 'preflight: 65' 'ram_percent: 95' 'with_services: maybe' 'max_rollouts: 100'; do
    cp "$TMP/p1.yaml" .evolve/config.yaml
    sed -i "s|^    ${bad%%:*}: [^#]*|    $bad |" .evolve/config.yaml
    ok "$(CX config >/dev/null 2>&1; echo $?)" "1" "P '$bad' is refused"
  done
  cp "$TMP/p1.yaml" .evolve/config.yaml; sed -i 's|^    rollouts: auto|    rollouts: 6|' .evolve/config.yaml
  CX config >/dev/null 2>&1
  ok "$(jq -r .parallel_rollouts .evolve/config.json)" "6" "P a number is kept as given"
}

t_parallel_auto_sizing() {
  local R="$TMP/p2"; make_repo "$R"
  setcfg "    rollouts: ${CORTEX_TEST_ROLLOUTS:-1}" '    rollouts: auto'
  setcfg "    preflight: ${CORTEX_TEST_PREFLIGHT:-1}" '    preflight: auto'
  CX config >/dev/null 2>&1
  par() { CORTEX_MEM_AVAILABLE_MB="$1" CORTEX_CPUS="$2" HX parallel --kind "$3" --jobs "$4" ${5:+--override "$5"} --json; }
  ok "$(par 8192 12 rollouts 54 | jq -c '[.workers, .limited_by]')" '[4,"ram"]' "P auto: 50% of 8 GB at 1 GB a rollout is 4"
  ok "$(par 65536 2 rollouts 54 | jq -c '[.workers, .limited_by]')" '[2,"cpus"]' "P never more rollouts than CPUs"
  ok "$(par 999999 64 rollouts 54 | jq -c '[.workers, .limited_by]')" '[16,"max"]' "P never more than max_rollouts (API rate limits)"
  ok "$(par 65536 12 rollouts 3 | jq -c '[.workers, .limited_by]')" '[3,"jobs"]' "P never more workers than jobs"
  ok "$(par 100 12 rollouts 54 | jq -r .workers)" "1" "P too little RAM still runs, one at a time"
  ok "$(par unknown 12 rollouts 54 | jq -c '[.workers, .limited_by]')" '[1,"unknown RAM"]' "P unknown RAM: one at a time"
  ok "$(par 8192 12 preflight 54 | jq -r .workers)" "8" "P preflight: 512 MB a check, so 8 from 4 GB"
  setcfg 'ram_percent: 50' 'ram_percent: 25'; CX config >/dev/null 2>&1
  ok "$(par 8192 12 rollouts 54 | jq -r .workers)" "2" "P ram_percent is the share auto may use"
  ok "$(par 8192 12 rollouts 54 6 | jq -c '[.workers, .setting]')" '[6,"6"]' "P a number overrides auto"
  ok "$(par 8192 12 rollouts 2 6 | jq -r .workers)" "2" "P a number is still capped by the jobs"
  ok "$(HX parallel --kind rollouts --override 0 >/dev/null 2>&1; echo $?)" "1" "P an override out of range is refused"
}

t_parallel_sweep_same_results() {
  local R="$TMP/p3"; make_repo "$R"; STUB="$TMP/stubp3"; LOG="$R/log"
  local WT; WT=$(HX sandbox-dir)
  mk_task 02; mk_task 03; mk_task 04; mk_cand vbd
  stub "$STUB" 'if [ -d .claude/skills/vbd ]; then fire vbd; sed -i "s/a - b/a + b/" src/calc.py; fi; exit 0'
  sweep --candidate vbd --phase confirm --parallel 1 >/dev/null
  local serial; serial=$(score | jq -c '[.verdict, .per_task, .candidate_fired_runs, .invalid]')
  sleep 1                                                # a new results file name
  sweep --candidate vbd --phase confirm --parallel 4 >/dev/null
  local f; f=$(ls -1t .evolve/runs/*.jsonl | head -1)
  ok "$(score | jq -c '[.verdict, .per_task, .candidate_fired_runs, .invalid]')" "$serial" \
     "P 4 at a time: the same verdict and per-task results as one at a time"
  ok "$(jq -s -c '[.[] | select(.v) | "\(.v)\(.t)\(.r)"] | [length, (unique | length)]' "$f")" "[16,16]" \
     "P every rollout ran exactly once"
  ok "$(jq -r 'select(.event == "start") | .workers' "$f")/$(score | jq -r .workers)" "4/4" "P the results file records the workers"
  ok "$(jq -s '[.[] | select(.v) | .w] | unique | length' "$f")" "4" "P all four workers took jobs"
  ok "$(ls -d "$WT"/work* 2>/dev/null | wc -l)/$(ls .evolve/runs/ | grep -c '\.lock$')" "0/0" \
     "P no sandbox and no append lock left behind"
}

t_parallel_really_concurrent() {
  local R="$TMP/p4"; make_repo "$R"; STUB="$TMP/stubp4"; LOG="$R/log"
  mk_task 02; mk_task 03; mk_cand vbd
  mkdir -p "$R.active"
  stub "$STUB" 'touch "$CORTEX_TEST_OUT/$$"; sleep 1; ls "$CORTEX_TEST_OUT" | wc -l >> "$CORTEX_TEST_OUT.n"; rm -f "$CORTEX_TEST_OUT/$$"; exit 0'
  CORTEX_TEST_OUT="$R.active" sweep --candidate vbd --phase confirm --parallel 4 >/dev/null
  local most; most=$(sort -n "$R.active.n" | tail -1)
  ok "$([ "$most" -ge 2 ] && [ "$most" -le 4 ] && echo yes || echo "no ($most)")" "yes" \
     "P rollouts really overlap, never more than the 4 workers"
  ok "$(score | jq -r '(.elapsed_secs | type == "number") and (.elapsed_secs < .wall_secs_total)')" "true" \
     "P elapsed time is less than the sum over rollouts"
}

t_parallel_services_one_at_a_time() {
  local R="$TMP/p5"; make_repo "$R"; STUB="$TMP/stubp5"; LOG="$R/log"
  mk_task 02; mk_cand vbd
  local t; for t in 01 02; do printf '#!/usr/bin/env bash\nexit 0\n' > ".evolve/tasks/$t/precondition.sh"; done
  mkdir -p "$R.active"
  stub "$STUB" 'touch "$CORTEX_TEST_OUT/$$"; sleep 1; ls "$CORTEX_TEST_OUT" | wc -l >> "$CORTEX_TEST_OUT.n"; rm -f "$CORTEX_TEST_OUT/$$"; exit 0'
  CORTEX_TEST_OUT="$R.active" sweep --candidate vbd --phase confirm --parallel 4 >/dev/null
  ok "$(sort -n "$R.active.n" | tail -1)" "1" "P tasks that need services run one at a time, even with 4 workers"
  rm -f "$R.active.n"; setcfg 'with_services: false' 'with_services: true'
  CORTEX_TEST_OUT="$R.active" sweep --candidate vbd --phase confirm --parallel 4 >/dev/null
  ok "$([ "$(sort -n "$R.active.n" | tail -1)" -ge 2 ] && echo parallel || echo serial)" "parallel" \
     "P with_services: true lets them overlap"
}

t_parallel_kill_stops_every_worker() {
  local R="$TMP/p6"; make_repo "$R"; STUB="$TMP/stubp6"; LOG="$R/log"
  local WT; WT=$(HX sandbox-dir)
  mk_task 02; mk_cand vbd
  : > "$R.pids"
  stub "$STUB" 'echo $$ >> "$CORTEX_TEST_OUT"; sleep 30; exit 0'
  ( CORTEX_TEST_OUT="$R.pids" PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --phase confirm --parallel 3 >/dev/null 2>&1 ) &
  local bg=$! i
  for i in $(seq 1 50); do [ "$(wc -l < "$R.pids")" -ge 3 ] && break; sleep 0.2; done
  ok "$(wc -l < "$R.pids")" "3" "P three agents running at once"
  kill -TERM $bg 2>/dev/null; wait $bg 2>/dev/null; sleep 1
  local alive=0 p; for p in $(cat "$R.pids"); do kill -0 "$p" 2>/dev/null && alive=$((alive+1)); done
  ok "$alive" "0" "P killing the sweep stops every worker's agent: no orphans"
  ok "$(ls -d "$WT"/work* 2>/dev/null | wc -l)" "0" "P and removes every worker's sandbox"
}

t_parallel_dry_run_and_estimate() {
  local R="$TMP/p7"; make_repo "$R"; STUB="$TMP/stubp7"; LOG="$R/log"
  stub "$STUB" 'exit 0'; mk_task 02; mk_cand vbd
  ok "$(sweep --candidate vbd --phase confirm --dry-run --parallel 3 2>&1 >/dev/null; grep -c '3 at a time' "$LOG")" "1" \
     "P --dry-run says how many run at once"
  ok "$(PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --parallel 0 2>&1 | grep -c 'REFUSED')" "1" "P --parallel 0 is refused"
  ok "$(PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --parallel lots 2>&1 | grep -c 'REFUSED')" "1" "P --parallel lots is refused"
  setcfg "    rollouts: ${CORTEX_TEST_ROLLOUTS:-1}" '    rollouts: 1'
  ok "$(HX prune estimate 2>/dev/null | grep -c 'one at a time')" "1" "P the estimate says one at a time with 1 worker"
  setcfg '    rollouts: 1' "    rollouts: ${CORTEX_TEST_ROLLOUTS:-1}"
  setcfg "    rollouts: ${CORTEX_TEST_ROLLOUTS:-1}" '    rollouts: 4'
  ok "$(HX prune estimate 2>/dev/null | grep -c '4 at a time')" "1" "P and divides the time by the workers"
  ok "$(PATH="$STUB:$PATH" CX doctor 2>&1 | grep -c '^  rollouts .* at a time')" "1" "P doctor shows what parallel resolves to"
}

t_preflight_parallel() {
  local R="$TMP/p8"; make_repo "$R"
  mk_task 02; mk_task 03; mk_task 04; mk_task 05; mk_task 06
  printf '#!/usr/bin/env bash\ntrue\n' > .evolve/tasks/03/check.sh                     # passes before the fix
  echo 'garbage' > .evolve/tasks/04/fix.patch                                          # fix does not apply
  sed -i '/^base_sha:/d' .evolve/tasks/06/task.yaml                                    # no base_sha
  cp -r .evolve/tasks "$TMP/p8.tasks"
  local one four
  one=$(bash "$CORTEX/bin/preflight.sh" --parallel 1 2>&1); local q1; q1=$(ls .evolve/tasks/_broken | tr '\n' ' ')
  rm -rf .evolve/tasks; cp -r "$TMP/p8.tasks" .evolve/tasks
  four=$(bash "$CORTEX/bin/preflight.sh" --parallel 4 2>&1); local q4; q4=$(ls .evolve/tasks/_broken | tr '\n' ' ')
  ok "$four" "$one" "PF 4 at a time prints exactly what 1 at a time prints"
  ok "$q4" "$q1" "PF and quarantines the same tasks"
  ok "$q4" "03 04 06 " "PF (the three bad ones)"
  ok "$(echo "$four" | grep -E '^0[1-6] ' | awk '{print $1}' | tr '\n' ' ')" "01 02 03 04 05 06 " "PF rows in task order"
  ok "$(git worktree list | wc -l)" "1" "PF no worktree left behind (only the repository itself)"
}

t_preflight_beside_a_sweep() {
  local R="$TMP/p9"; make_repo "$R"; STUB="$TMP/stubp9"; LOG="$R/log"
  ( exec 9>.evolve/runs/.lock; flock 9; sleep 3 ) & local holder=$!
  sleep 0.5
  local out; out=$(bash "$CORTEX/bin/preflight.sh" 2>&1)
  ok "$(echo "$out" | grep -c 'valid=1')" "1" "PF preflight runs while a sweep holds its lock (a /harvest during /evolve)"
  wait $holder 2>/dev/null
  ( exec 9>.evolve/runs/.preflight.lock; flock 9; sleep 3 ) & holder=$!
  sleep 0.5
  ok "$(bash "$CORTEX/bin/preflight.sh" 2>&1 | grep -c 'another preflight')" "1" "PF two preflights never run at once"
  wait $holder 2>/dev/null
  # a sweep copies the tasks only when no preflight is moving them: it waits
  stub "$STUB" 'exit 0'; mk_cand vbd
  ( exec 8>>.evolve/runs/.tasks.lock; flock 8; sleep 3; date +%s > "$R.released" ) & holder=$!
  sleep 0.5
  sweep --candidate vbd --phase confirm >/dev/null
  wait $holder 2>/dev/null
  local started; started=$(jq -r 'select(.event == "start") | .epoch' "$(ls -1t .evolve/runs/*.jsonl | head -1)")
  ok "$([ "$started" -ge "$(cat "$R.released")" ] && echo waited || echo "did not wait")/$(score | jq -r .rollouts)" "waited/4" \
     "PF a sweep waits for a running preflight before copying the tasks, then runs in full"
}

# ====================================================== PARALLEL, SAFELY =====
busy_check() {  # $1 = task id, $2 = dir: a check that fails whenever another copy runs at the same moment
  mkdir -p "$2"
  cat > ".evolve/tasks/$1/check.sh" <<EOF
#!/usr/bin/env bash
set -e
touch "$2/\$\$"; sleep 0.5; n=\$(ls "$2" | wc -l); rm -f "$2/\$\$"
[ "\$n" -eq 1 ]
python3 -c "from src.calc import add; assert add(2,3)==5"
EOF
}

t_exclusive_tasks_run_alone() {
  local R="$TMP/x1"; make_repo "$R"; STUB="$TMP/stubx1"; LOG="$R/log"
  mk_task 02; mk_cand vbd
  local t; for t in 01 02; do echo "exclusive: true" >> ".evolve/tasks/$t/task.yaml"; done
  mkdir -p "$R.active"
  stub "$STUB" 'touch "$CORTEX_TEST_OUT/$$"; sleep 1; ls "$CORTEX_TEST_OUT" | wc -l >> "$CORTEX_TEST_OUT.n"; rm -f "$CORTEX_TEST_OUT/$$"; exit 0'
  CORTEX_TEST_OUT="$R.active" sweep --candidate vbd --phase confirm --parallel 4 >/dev/null
  ok "$(sort -n "$R.active.n" | tail -1)" "1" "X a task marked exclusive: true runs one rollout at a time, even with 4 workers"
  ok "$(score | jq -r '"\(.invalid)/\(.rollouts)"')" "0/8" "X and every rollout still runs"
}

t_preflight_retries_alone() {
  local R="$TMP/x2"; make_repo "$R"; STUB="$TMP/stubx2"; LOG="$R/log"
  mk_task 02
  local t; for t in 01 02; do busy_check "$t" "$R.busy"; done
  local out; out=$(bash "$CORTEX/bin/preflight.sh" --parallel 2 2>&1)
  ok "$(ls .evolve/tasks/_broken 2>/dev/null | wc -l)" "0" "PX checks that fail beside each other quarantine nothing: each is checked again alone"
  ok "$(grep -l '^exclusive: true' .evolve/tasks/0*/task.yaml | wc -l)" "2" "PX and each is marked exclusive: true"
  ok "$(echo "$out" | grep -c 'ok (exclusive: ')" "2" "PX with the reason in the table"
  # a sweep then runs them one at a time: a correct fix passes in both arms
  mk_cand vbd; stub "$STUB" 'sed -i "s/a - b/a + b/" src/calc.py; exit 0'
  sweep --candidate vbd --phase confirm --parallel 4 >/dev/null
  ok "$(score | jq -c '[.invalid, [.per_task[] | "\(.task) \(.base)>\(.cand)"]]')" '[0,["01 1>1","02 1>1"]]' \
     "PX and the parallel sweep measures them right: no collision reads as a failure"
}

t_preflight_probe() {
  local R="$TMP/x3"; make_repo "$R"
  mk_task 02; mk_task 03
  busy_check 02 "$R.b2"
  printf '#!/usr/bin/env bash\nset -e\necho run >> "%s"\npython3 -c "from src.calc import add; assert add(2,3)==5"\n' "$R.calls" > .evolve/tasks/01/check.sh
  local out; out=$(bash "$CORTEX/bin/preflight.sh" --parallel 1 2>&1)
  ok "$(grep -c '^exclusive: true' .evolve/tasks/02/task.yaml)" "1" "PP a check that fails beside a copy of itself is marked exclusive (even with one preflight worker, even with rollouts: 1)"
  ok "$(echo "$out" | grep '^02' | grep -c 'two copies run at once')" "1" "PP and the table says why"
  ok "$(cat .evolve/tasks/01/task.yaml .evolve/tasks/03/task.yaml | grep -c '^exclusive')" "0" "PP checks that pass side by side are left alone"
  ok "$(wc -l < "$R.calls")" "4" "PP (broken, fixed, then the fixed state twice at once)"
  bash "$CORTEX/bin/preflight.sh" --parallel 1 >/dev/null 2>&1
  ok "$(wc -l < "$R.calls")" "6" "PP a safe verdict is kept: the next preflight does not probe again"
  echo "# v2" >> .evolve/tasks/01/check.sh
  bash "$CORTEX/bin/preflight.sh" --parallel 1 >/dev/null 2>&1
  ok "$(wc -l < "$R.calls")" "10" "PP until the task changes"
  echo 'exclusive: false' >> .evolve/tasks/03/task.yaml; busy_check 03 "$R.b3"
  bash "$CORTEX/bin/preflight.sh" --parallel 1 >/dev/null 2>&1
  ok "$(grep -c '^exclusive: true' .evolve/tasks/03/task.yaml)" "0" "PP a value someone wrote in task.yaml is never overridden"
}

t_worker_tmpdir() {
  local R="$TMP/x4"; make_repo "$R"; STUB="$TMP/stubx4"; LOG="$R/log"
  local WT; WT=$(HX sandbox-dir)
  mk_task 02; mk_cand vbd
  stub "$STUB" 'echo "$TMPDIR" >> "$CORTEX_TEST_OUT"; sleep 0.3; exit 0'
  CORTEX_TEST_OUT="$R.tmpdirs" sweep --candidate vbd --phase confirm --parallel 2 >/dev/null
  ok "$(sort -u "$R.tmpdirs" | wc -l)" "2" "T each worker gives its rollouts a TMPDIR of its own"
  ok "$(grep -vc "^$WT/tmp-[0-9]*\$" "$R.tmpdirs")" "0" "T inside this repository's sandbox folder"
  ok "$(ls -d "$WT"/tmp-* 2>/dev/null | wc -l)" "0" "T and gone after the sweep"
}

t_cpus_per_rollout_and_quota() {
  local R="$TMP/x5"; make_repo "$R"
  setcfg "    rollouts: ${CORTEX_TEST_ROLLOUTS:-1}" '    rollouts: auto'
  setcfg 'cpus_per_rollout: 1' 'cpus_per_rollout: 4'; CX config >/dev/null 2>&1
  ok "$(CORTEX_MEM_AVAILABLE_MB=65536 CORTEX_CPUS=12 HX parallel --kind rollouts --jobs 54 --json | jq -c '[.workers, .limited_by]')" '[3,"cpus"]' \
     "C cpus_per_rollout 4 on 12 CPUs: 3 rollouts at once"
  local CG="$TMP/x5.cg"; mkdir -p "$CG"
  echo "200000 100000" > "$CG/cpu.max"; echo 4294967296 > "$CG/memory.max"; echo 1073741824 > "$CG/memory.current"
  ok "$(CORTEX_CGROUP_DIR="$CG" HX parallel --kind rollouts --jobs 54 --json | jq -c '[.cpus, .ram_available_mb, .ram_source]')" '[2,3072,"cgroup limit"]' \
     "C a cgroup CPU quota and memory limit are what auto sizes by (not the whole host)"
  echo "max 100000" > "$CG/cpu.max"; echo max > "$CG/memory.max"
  ok "$(CORTEX_CGROUP_DIR="$CG" HX parallel --kind rollouts --jobs 54 --json | jq -r .ram_source)" "MemAvailable" "C no limit: the host's own numbers"
  setcfg 'cpus_per_rollout: 4' 'cpus_per_rollout: 0'
  ok "$(CX config >/dev/null 2>&1; echo $?)" "1" "C cpus_per_rollout 0 is refused"
}

t_timeout_under_load() {
  local R="$TMP/x6"; make_repo "$R"; STUB="$TMP/stubx6"; LOG="$R/log"
  mk_task 02; mk_cand vbd
  stub "$STUB" 'exit 124'
  CORTEX_CPUS=4 CORTEX_LOADAVG=50 sweep --candidate vbd --phase confirm --parallel 2 >/dev/null
  local j; j=$(score)
  ok "$(echo "$j" | jq -r '.invalid_reasons.timeout_under_load // 0')" "8" "L an agent that timed out while the CPUs were oversubscribed is INVALID, not a failure"
  ok "$(echo "$j" | jq -r '.verdict')" "RERUN" "L a sweep run oversubscribed is not scored"
  ok "$(echo "$j" | jq -r '[.blocked_because[] | test("oversubscribed")] | any')" "true" "L and says so, with what to change"
  CORTEX_CPUS=4 CORTEX_LOADAVG=1 sweep --candidate vbd --phase confirm --parallel 2 >/dev/null
  ok "$(score | jq -r '"\(.invalid)/\(.oversubscribed_runs)"')" "0/0" "L with CPUs to spare, a timeout is still a real failure"
  ok "$(jq -s '[.[] | select(.v) | .load == 1] | all' "$(ls -1t .evolve/runs/*.jsonl | head -1)")" "true" "L every row records the load it ran under"
  # a few more runnable tasks than CPUs is normal for agents (they wait on the
  # API, not the CPU): it costs time, not correctness, and must not block a score
  stub "$STUB" 'exit 0'
  CORTEX_CPUS=4 CORTEX_LOADAVG=6 sweep --candidate vbd --phase confirm --parallel 2 >/dev/null
  ok "$(score | jq -r '"\(.scorable)/\(.oversubscribed_runs)"')" "true/8" "L mildly oversubscribed is scored, not refused"
  ok "$(score | jq -r '[.notes[] | test("more runnable work than CPUs")] | any')" "true" "L with a note saying what it cost"
}

t_queue_broken_is_incomplete() {
  local R="$TMP/x7"; make_repo "$R"; STUB="$TMP/stubx7"; LOG="$R/log"
  local WT; WT=$(HX sandbox-dir)
  mk_task 02; mk_task 03; mk_cand vbd
  stub "$STUB" 'sleep 1; exit 0'
  ( PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --phase confirm --parallel 2 >/dev/null 2>&1 ) &
  local bg=$! i n
  for i in $(seq 1 60); do n=$(cat "$WT/queue/next" 2>/dev/null); [ "${n:-0}" -ge 3 ] 2>/dev/null && break; sleep 0.2; done
  : > "$WT/queue/next"                                  # what a full disk used to leave behind
  wait $bg
  local j; j=$(score)
  ok "$(tail -1 "$(ls -1t .evolve/runs/*.jsonl | head -1)" | jq -r .event)" "incomplete" "Q a sweep whose job queue broke ends incomplete, never done"
  ok "$(echo "$j" | jq -r '"\(.scorable)/\(.verdict)"')" "false/RERUN" "Q and is not scored"
  ok "$(echo "$j" | jq -r '.planned_missing | length > 0')" "true" "Q the planned tasks it never ran are named"
  ok "$(HX evolve-phase --json | jq -r .phase)" "D" "Q /evolve reads it as ended (the RERUN verdict says: sweep again)"
  # the queue itself: all handed out and broken are never the same answer
  local Qd="$TMP/x7.q"
  ok "$(bash -c ". '$CORTEX/bin/parallel.sh'; printf 'a\n' | queue_init '$Qd'; queue_claim '$Qd' >/dev/null; queue_claim '$Qd' 2>/dev/null; echo \$?")" "1" "Q a drained queue answers 1"
  ok "$(bash -c ". '$CORTEX/bin/parallel.sh'; rm -rf '$Qd'; queue_claim '$Qd' 2>/dev/null; echo \$?")" "2" "Q a missing queue answers 2"
}

t_same_area_as_live_warns() {
  local R="$TMP/x12"; make_repo "$R"
  mk_live_gated() { mkdir -p ".claude/skills/$1"; printf -- '---\nname: %s\ndescription: d\npaths:\n  - "src/**"\n---\nLive.\n' "$1" > ".claude/skills/$1/SKILL.md"; }
  mk_live_gated area-skill
  mkdir -p .evolve/candidate/area-rule
  printf -- '---\npaths:\n  - "src/**"\n---\n# same area\n' > .evolve/candidate/area-rule/RULE.md
  local out; out=$(CX skills --candidate area-rule 2>&1); local rc=$?
  ok "$rc" "0" "SA a candidate over a live item's files is not an error: it may be a different rule"
  ok "$(echo "$out" | grep -c "covers exactly the same files")" "1" "SA but it is warned about, naming the live item"
  ok "$(echo "$out" | grep -c 'REPLACEMENT (--replace area-skill)')" "1" "SA and says what to do if it is the same idea in another tier"
  printf -- '---\npaths:\n  - "docs/**"\n---\n# elsewhere\n' > .evolve/candidate/area-rule/RULE.md
  ok "$(CX skills --candidate area-rule 2>&1 | grep -c 'covers exactly the same files')" "0" "SA a candidate for another area is not warned about"
}

t_screen_never_decides_a_removal() {
  local R="$TMP/x13"; make_repo "$R"
  local f=.evolve/runs/20260101T000000-screen.jsonl
  # a replace sweep at screen phase: cheap, few tasks — it filters, it never deletes.
  # (the removed item must be VISIBLE in the base arm, or nothing is gated)
  rmsweep() {   # $1 = file, then "task base_passes cand_passes" triples at k=2
    local file="$1"; shift
    printf '{"event":"start","phase":"screen","mode":"replace","k":2,"candidate":"","replaced":["vbd"],"harness_base":"hb","harness_cand":"hc"}\n' > "$file"
    while [ $# -gt 0 ]; do
      local t="$1" b="$2" c="$3" r; shift 3
      for r in 1 2; do
        printf '{"v":"base","t":"%s","r":%s,"pass":%s,"valid":1,"skills":["vbd"],"rules":[],"visible":["vbd"]}\n' \
          "$t" "$r" "$([ "$r" -le "$b" ] && echo 1 || echo 0)" >> "$file"
        printf '{"v":"cand","t":"%s","r":%s,"pass":%s,"valid":1,"skills":[],"rules":[],"visible":[]}\n' \
          "$t" "$r" "$([ "$r" -le "$c" ] && echo 1 || echo 0)" >> "$file"
      done
    done
    echo '{"event":"done"}' >> "$file"
  }
  rmsweep "$f"  01 2 2  02 2 1
  ok "$(score "$f" | jq -r .verdict)" "KILL" "SR a screen that shows a loss says so: the live item stays"
  rmsweep "$f"  01 2 2  02 2 2
  ok "$(score "$f" | jq -r .verdict)" "CONFIRM" "SR and one that shows no loss asks for the confirm — never ACCEPT on a screen"
}

t_recheck_pairs_when_the_path_has_a_space() {
  # A repository under "Progetti didattici" made every recheck answer "no confirm
  # precedes this one": the list of confirms was split on the space, so none was
  # ever read, and a cleared regression still killed the candidate.
  local R="$TMP/a space/e2s"; make_repo "$R"
  setcfg 'regression_tolerance: 0.5' 'regression_tolerance: 0.34'; CX config >/dev/null 2>&1
  local C=.evolve/runs/20260101T000000-confirm.jsonl
  synthv "$C" confirm 3  01 0 3 1  02 3 2 1
  ok "$(score "$C" | jq -r .verdict)" "RECHECK" "RS a lost run on a 3/3 task asks for a recheck (path with a space)"
  synthv .evolve/runs/20260101T010000-recheck.jsonl recheck 3  02 3 3 1
  local j; j=$(score)
  ok "$(basename "$(echo "$j" | jq -r '.confirm_file // "NOT PAIRED"')")" "20260101T000000-confirm.jsonl" \
     "RS the recheck still finds its confirm"
  ok "$(echo "$j" | jq -r .verdict)" "KEEP" "RS so a regression that did not replicate is not a KILL"
}

t_uninformative_sweep_is_not_a_kill() {
  local R="$TMP/x11"; make_repo "$R"
  local f=.evolve/runs/20260101T000000-screen.jsonl
  # 01 nobody passes (a check no rollout can satisfy), 02 already passes in base:
  # neither can show a gain, so this sweep says nothing about the candidate
  synthv "$f" screen 2  01 0 0 1  02 2 2 1
  local j; j=$(score "$f")
  ok "$(echo "$j" | jq -r '"\(.verdict)/\(.uninformative)"')" "RERUN/true" "U a sweep where no task could show a gain is RERUN, never KILL"
  ok "$(echo "$j" | jq -r '[.verdict_because[] | test("never passed in either arm")] | any')" "true" "U and says which tasks made it unmeasurable"
  # one task with room to move makes it a real measurement again
  synthv "$f" screen 2  01 0 0 1  02 1 1 1
  ok "$(score "$f" | jq -r '"\(.verdict)/\(.uninformative)"')" "KILL/false" "U one task that can move is enough to decide"
}

t_score_planned_missing() {
  local R="$TMP/x8"; make_repo "$R"
  local f=.evolve/runs/20260101T000000-confirm.jsonl
  synthv "$f" confirm 3  01 0 3 1  02 3 3 1
  cp "$f" "$f.orig"
  jq -c 'if .event == "start" then . + {planned: ["01","02","03"]} else . end' "$f.orig" > "$f"
  ok "$(score "$f" | jq -r '"\(.scorable)/\(.planned_missing | join(","))"')" "false/03" \
     "Q a planned task with no row blocks the score instead of vanishing from it"
  jq -c 'if .event == "start" then . + {jobs: 18} else . end' "$f.orig" > "$f"
  ok "$(score "$f" | jq -r '"\(.scorable)/\([.blocked_because[] | test("only 12 of 18")] | any)"')" "false/true" \
     "Q and so does a file with fewer rows than the sweep had jobs"
  rm -f "$f.orig"
}

t_preflight_interrupted_reports() {
  local R="$TMP/x9"; make_repo "$R"
  mk_task 02; mk_task 03
  printf '#!/usr/bin/env bash\ntrue\n' > .evolve/tasks/01/check.sh             # quarantined at once
  local t; for t in 02 03; do printf '#!/usr/bin/env bash\nset -e\nsleep 4\npython3 -c "from src.calc import add; assert add(2,3)==5"\n' > ".evolve/tasks/$t/check.sh"; done
  bash "$CORTEX/bin/preflight.sh" --parallel 2 > "$R.out" 2>&1 &
  local pf=$! i
  for i in $(seq 1 50); do [ -d .evolve/tasks/_broken/01 ] && break; sleep 0.2; done
  kill -TERM $pf; wait $pf 2>/dev/null
  ok "$(grep -c '^01 .*QUARANTINE' "$R.out")/$(grep -c 'INTERRUPTED' "$R.out")" "1/1" "PI stopped part-way, preflight still prints what it decided"
  ok "$(grep -c 'passes BEFORE the fix' .evolve/tasks/_broken/01/QUARANTINED.txt)" "1" "PI and the quarantined task keeps its reason"
  ok "$(grep -c '^01 .*QUARANTINE' .evolve/runs/preflight.log)" "1" "PI and so does the log"
  ok "$(git worktree list | wc -l)" "1" "PI no worktree left behind"
  # repaired and moved back: the old reason goes with the next preflight
  for t in 02 03; do printf '#!/usr/bin/env bash\nset -e\npython3 -c "from src.calc import add; assert add(2,3)==5"\n' > ".evolve/tasks/$t/check.sh"; done
  cp .evolve/tasks/02/check.sh .evolve/tasks/_broken/01/check.sh
  mv .evolve/tasks/_broken/01 .evolve/tasks/01
  bash "$CORTEX/bin/preflight.sh" >/dev/null 2>&1
  ok "$([ -f .evolve/tasks/01/QUARANTINED.txt ] && echo stale || echo gone)" "gone" "PI a repaired task loses its old reason"
}

t_preflight_busy_skip() {
  local R="$TMP/x10"; make_repo "$R"
  echo "exclusive: true" >> .evolve/tasks/01/task.yaml
  ( exec 7>>.evolve/runs/.services.lock; flock 7; sleep 4 ) & local holder=$!
  sleep 0.5
  local out rc; out=$(CORTEX_EXCLUSIVE_WAIT=1 bash "$CORTEX/bin/preflight.sh" 2>&1); rc=$?
  ok "$rc/$(echo "$out" | grep -c 'SKIP (busy')" "3/1" "PB a task that must run alone is skipped, not waited on, while a sweep holds what it needs"
  ok "$([ -d .evolve/tasks/01 ] && echo kept || echo moved)" "kept" "PB and is not quarantined"
  wait $holder 2>/dev/null
}

t_never_passed_named() {
  local R="$TMP/e15"; make_repo "$R"
  # 01: the candidate wins. 02: no rollout of either arm ever passes — too hard,
  # or a check that pins the harvested fix's own names or wording (rule 6)
  local f=.evolve/runs/20260101T000000-confirm.jsonl
  synthv "$f" confirm 3  01 0 3 1  02 0 0 1
  local j; j=$(score "$f")
  ok "$(echo "$j" | jq -c .never_passed)" '["02"]' "NP a task no rollout of either arm passed is named"
  ok "$(echo "$j" | jq -r '.notes[]' | grep -c 'never passed in any rollout of either arm')" "1" "NP with a note that says what to read"
  synthv "$f" confirm 3  01 0 3 1  02 1 0 1
  ok "$(score "$f" | jq -c .never_passed)" '[]' "NP one pass in either arm is enough"
  # a task the change never reached is not evidence about the check: there,
  # "nobody passed" only says the live harness fails it — the point of a task
  synthv "$f" confirm 3  01 0 3 1  02 0 0 0
  ok "$(score "$f" | jq -c '[.never_passed, .unexposed]')" '[[],["02"]]' \
     "NP a task the change never reached is never blamed for it"
}

t_exposure_filter() {
  local R="$TMP/e1"; make_repo "$R"
  setcfg 'regression_tolerance: 0.5' 'regression_tolerance: 0.34'; CX config >/dev/null 2>&1
  # 01: the candidate loads and wins every run. 02: it never loads there, and a
  # base-perfect task loses one run by chance: noise, not the candidate's doing
  local f=.evolve/runs/20260101T000000-confirm.jsonl
  synthv "$f" confirm 3  01 0 3 1  02 3 2 0
  local j; j=$(score "$f")
  ok "$(echo "$j" | jq -r .verdict)" "KEEP" "E a drop where the candidate never reached the agent does not count"
  ok "$(echo "$j" | jq -c .unexposed)" '["02"]' "E that task is reported as unexposed"
  ok "$(echo "$j" | jq -r '.per_task[] | select(.task=="02") | .exposed')" "false" "E it stays in per_task, flagged"
  ok "$(echo "$j" | jq -r '[.notes[] | test("never had the change")] | any')" "true" "E and a note says why it was left out"
  f=.evolve/runs/20260101T000100-confirm.jsonl
  synthv "$f" confirm 3  01 0 3 1  02 3 2 1
  ok "$(score "$f" | jq -r .verdict)" "RECHECK" "E the same drop WITH the candidate in context is not ignored"
  f=.evolve/runs/20260101T000200-confirm.jsonl
  synth "$f" 3  01 0 3  02 3 2
  ok "$(score "$f" | jq -r '.unexposed | length')" "0" "E results without visibility still gate every task"
}

t_recheck_flow() {
  local R="$TMP/e2"; make_repo "$R"
  setcfg 'regression_tolerance: 0.5' 'regression_tolerance: 0.34'; CX config >/dev/null 2>&1
  local C=.evolve/runs/20260101T000000-confirm.jsonl j
  synthv "$C" confirm 3  01 0 3 1  02 3 2 1  03 3 3 1
  j=$(score "$C")
  ok "$(echo "$j" | jq -r .verdict)" "RECHECK" "RC one lost run on a 3/3 task asks for a recheck, not a KILL"
  ok "$(echo "$j" | jq -c .recheck_tasks)" '["02"]' "RC and names the task to re-measure"
  synthv .evolve/runs/20260101T010000-recheck.jsonl recheck 3  02 3 3 1
  j=$(score)
  ok "$(echo "$j" | jq -r .verdict)" "KEEP" "RC a regression that does not replicate was noise: KEEP"
  ok "$(basename "$(echo "$j" | jq -r .confirm_file)")" "20260101T000000-confirm.jsonl" "RC the recheck is paired with its confirm"
  ok "$(echo "$j" | jq -r '.per_task | length')" "3" "RC the verdict still reports the confirm's full per_task"
  synthv .evolve/runs/20260101T020000-recheck.jsonl recheck 3  02 3 1 1
  j=$(score)
  ok "$(echo "$j" | jq -r .verdict)" "KILL" "RC a regression that replicates kills"
  ok "$(echo "$j" | jq -r '.gates_failed[0] | test("replicated on recheck: task 02")')" "true" "RC naming both measurements"
  synthv .evolve/runs/20260101T030000-recheck.jsonl recheck 3  03 3 3 1
  ok "$(score | jq -r .verdict)" "RERUN" "RC a recheck that skipped the flagged task decides nothing"
  synthv .evolve/runs/20260101T040000-recheck.jsonl recheck 3  02 3 3 1
  sed -i 's/"harness_cand":"hc"/"harness_cand":"zz"/' .evolve/runs/20260101T040000-recheck.jsonl
  ok "$(score | jq -r .verdict)" "RERUN" "RC a recheck of another harness is never paired"
  synthv .evolve/runs/20260101T050000-confirm.jsonl confirm 3  01 0 1 1  02 3 2 1
  ok "$(score .evolve/runs/20260101T050000-confirm.jsonl | jq -r .verdict)" "KILL" "RC no recheck when the win itself is too small"
  synthv .evolve/runs/20260101T060000-screen.jsonl screen 3  01 0 3 1  02 3 2 1
  ok "$(score .evolve/runs/20260101T060000-screen.jsonl | jq -r .verdict)" "CONFIRM" "RC a passing screen says CONFIRM: never RECHECK, never KEEP"
  local STUB="$TMP/stube2" LOG="$R/log"; stub "$STUB" 'exit 0'; mk_cand vbd
  ok "$(dry --candidate vbd --phase recheck --tasks 01 | grep -c 'sweep: OK')" "1" "RC sweep accepts --phase recheck"
}

t_sandbox_hides_evolve() {
  local R="$TMP/e3"
  make_repo "$R" 'mkdir -p .evolve/tasks/00; echo "the answer" > .evolve/tasks/00/fix.patch; echo "a lesson" > .evolve/lessons.md'
  STUB="$TMP/stube3"; LOG="$R/log"
  stub "$STUB" '{ [ -e .evolve ] && echo leak || echo hidden; git status --porcelain | grep -c "\.evolve"; } >> "$CORTEX_TEST_OUT"
mkdir -p .evolve; echo planted > .evolve/lessons.md; exit 0'
  mk_cand vbd
  CORTEX_TEST_OUT="$R/seen.txt" sweep --candidate vbd --phase confirm >/dev/null
  ok "$(git ls-tree -r --name-only "$BROKEN" | grep -c '^\.evolve/')" "2" "L (the broken commit really does track .evolve/)"
  ok "$(grep -c '^hidden$' "$R/seen.txt")/$(grep -c '^leak$' "$R/seen.txt")" "4/0" \
     "L a committed .evolve/ never reaches a rollout, even after one wrote there"
  ok "$(grep -c '^0$' "$R/seen.txt")" "4" "L and git status in the sandbox does not show it"
}

t_preflight_check_needs_fix_tests() {
  local R="$TMP/e4"; make_repo "$R" 'mkdir -p tests'
  local newtest='diff --git a/tests/test_calc.py b/tests/test_calc.py\nnew file mode 100644\n--- /dev/null\n+++ b/tests/test_calc.py\n@@ -0,0 +1,2 @@\n+from src.calc import add\n+assert add(2, 3) == 5\n'
  local id
  for id in 02 03; do
    mkdir -p ".evolve/tasks/$id"; cp .evolve/tasks/01/{task.yaml,prompt.txt,notes.md} ".evolve/tasks/$id/"
    { cat .evolve/tasks/01/fix.patch; printf "$newtest"; } > ".evolve/tasks/$id/fix.patch"
  done
  # 02 runs the test the FIX added: no rollout agent writes that exact file
  printf '#!/usr/bin/env bash\nset -e\nPYTHONPATH=. python3 tests/test_calc.py\n' > .evolve/tasks/02/check.sh
  # 03 runs its own copy of that test, kept in the task folder
  printf 'from src.calc import add\nassert add(2, 3) == 5\n' > .evolve/tasks/03/check_calc.py
  printf '#!/usr/bin/env bash\nset -e\nPYTHONPATH=. python3 "$(dirname "$0")/check_calc.py"\n' > .evolve/tasks/03/check.sh
  # 04: the house rule wants a golden file under tests/, and the check requires it.
  # Test DATA is part of the job, not the fix's own test: it must not be stripped.
  local golden='diff --git a/tests/golden/sum.txt b/tests/golden/sum.txt\nnew file mode 100644\n--- /dev/null\n+++ b/tests/golden/sum.txt\n@@ -0,0 +1 @@\n+5\n'
  local helper='diff --git a/tests/helpers.py b/tests/helpers.py\nnew file mode 100644\n--- /dev/null\n+++ b/tests/helpers.py\n@@ -0,0 +1 @@\n+FIVE = 5\n'
  for id in 04 05; do
    mkdir -p ".evolve/tasks/$id"; cp .evolve/tasks/01/{task.yaml,prompt.txt,notes.md} ".evolve/tasks/$id/"
  done
  { cat .evolve/tasks/01/fix.patch; printf "$golden"; } > .evolve/tasks/04/fix.patch
  cat > .evolve/tasks/04/check.sh <<'EOF'
#!/usr/bin/env bash
set -e
test -f tests/golden/sum.txt
PYTHONPATH=. python3 -c 'from src.calc import add; assert add(2, 3) == int(open("tests/golden/sum.txt").read())'
EOF
  # 05: test CODE in a test folder, without a test name, is still the fix's own test
  { cat .evolve/tasks/01/fix.patch; printf "$helper"; } > .evolve/tasks/05/fix.patch
  cat > .evolve/tasks/05/check.sh <<'EOF'
#!/usr/bin/env bash
set -e
PYTHONPATH=. python3 -c 'from tests.helpers import FIVE; from src.calc import add; assert add(2, 3) == FIVE'
EOF
  local out; out=$(bash "$CORTEX/bin/preflight.sh" 2>&1)
  ok "$([ -d .evolve/tasks/_broken/02 ] && echo quarantined || echo kept)" "quarantined" \
     "PF a check that needs the fix's own new test is quarantined"
  ok "$(echo "$out" | grep '^02' | grep -c "own test code")" "1" "PF with the reason printed"
  ok "$([ -d .evolve/tasks/03 ] && echo kept || echo quarantined)" "kept" "PF a check that carries its own copy is kept"
  ok "$([ -d .evolve/tasks/01 ] && echo kept || echo quarantined)" "kept" "PF a fix with no test edits is unaffected"
  ok "$([ -d .evolve/tasks/04 ] && echo kept || echo quarantined)" "kept" \
     "PF a golden file the fix adds under tests/ is kept: test data is part of the job"
  ok "$([ -d .evolve/tasks/_broken/05 ] && echo quarantined || echo kept)" "quarantined" \
     "PF test code inside tests/ without a test name is still the fix's own test"
}

t_fixpatch() {
  local R="$TMP/e5"; make_repo "$R"
  echo 'def add(a,b): return b + a' > src/calc.py; echo 'X = 1' > src/new_mod.py
  echo "a lesson" >> .evolve/lessons.md; git add src/calc.py
  local staged; staged=$(git diff --cached --name-only)
  local p; p=$(CX harness fixpatch 2>/dev/null)
  ok "$(echo "$p" | grep -c '^+++ b/src/new_mod.py')" "1" "FP a file the fix CREATES is in the patch (git diff drops it)"
  ok "$(echo "$p" | grep -c '^+++ b/src/calc.py')" "1" "FP modified files are in it"
  ok "$(echo "$p" | grep -c '^+++ b/\.evolve/\|^--- a/\.evolve/')" "0" "FP .evolve/ is never part of a fix"
  ok "$(git diff --cached --name-only)" "$staged" "FP the user's index is left exactly as it was"
  ok "$(CX harness fixpatch --base "$BROKEN" 2>/dev/null | grep -c '^-def add(a,b): return a - b')" "1" \
     "FP --base spans committed and uncommitted work"
  git add -A -- . ':!.evolve' && git commit -qm more
  ok "$(CX harness fixpatch >/dev/null 2>&1; echo $?)" "1" "FP nothing changed is an error, not an empty patch"
  ok "$(CX harness fixpatch --base 'HEAD;x' >/dev/null 2>&1; echo $?)" "2" "FP a base that is not a commit id is refused"
}

t_task_new() {
  local R="$TMP/e6"; make_repo "$R"
  echo 'Y = 2' > src/extra.py                       # a file the fix creates, never committed
  local out; out=$(CX task new --base "$BROKEN" --title "add fixed" 2>&1)
  ok "$(echo "$out" | grep -c 'created .evolve/tasks/02/')" "1" "TN the next free id is used (01 exists)"
  ok "$(grep -c '^+++ b/src/extra.py' .evolve/tasks/02/fix.patch)" "1" "TN a file the fix created is in fix.patch"
  ok "$(grep -c '^-def add(a,b): return a - b' .evolve/tasks/02/fix.patch)" "1" "TN committed work since the base is in it too"
  ok "$(awk '/^base_sha:/{print $2}' .evolve/tasks/02/task.yaml)" "$BROKEN" "TN task.yaml carries the full base_sha"
  ok "$(grep -c '^title: add fixed' .evolve/tasks/02/task.yaml)" "1" "TN and the title"
  mkdir -p .evolve/tasks/_broken/07
  ok "$(CX task new --base "$BROKEN" 2>&1 | grep -c 'created .evolve/tasks/08/')" "1" "TN a quarantined id is never reused"
  local SIDE; git checkout -q -b side "$BROKEN"; echo z > z.txt; git add z.txt; git commit -qm side
  SIDE=$(git rev-parse HEAD); git checkout -q -
  ok "$(CX task new --base "$SIDE" >/dev/null 2>&1; echo $?)" "1" "TN a base outside HEAD's history is refused"
  ok "$(CX task new >/dev/null 2>&1; echo $?)" "2" "TN a usage error exits 2"
  # a late harvest: the session's work was committed, then someone else's came after it
  rm -f src/extra.py; git add -A -- . ':!.evolve'; git commit -qm "session: fix add"
  local SESSION; SESSION=$(git rev-parse HEAD)
  echo 'W = 3' > src/later.py; git add src/later.py; git commit -qm "later: another session"
  echo 'V = 4' > src/wip.py                         # uncommitted work of the next session
  out=$(CX task new --base "$BROKEN" --head "$SESSION" --title late 2>&1)
  local T; T=$(echo "$out" | sed -n 's|^created .evolve/tasks/\([0-9]*\)/.*|\1|p')
  ok "$(grep -c '^-def add(a,b): return a - b' ".evolve/tasks/$T/fix.patch" 2>/dev/null)" "1" \
     "TN --head: the session's committed work is in fix.patch"
  ok "$(grep -c '^+++ b/src/later.py\|^+++ b/src/wip.py' ".evolve/tasks/$T/fix.patch" 2>/dev/null)" "0" \
     "TN --head: later commits and uncommitted work are not"
  ok "$(CX task new --base "$SESSION" --head "$BROKEN" >/dev/null 2>&1; echo $?)" "1" "TN --head before --base is refused"
  ok "$(CX task new --base "$BROKEN" --head "$SIDE" >/dev/null 2>&1; echo $?)" "1" "TN --head outside HEAD's history is refused"
}

t_preflight_runs_like_a_sweep() {
  local R="$TMP/e7"; make_repo "$R"
  # a check that cd's relative to its own location: from inside the repo it would
  # land in the user's FIXED working copy and "pass"; a sweep runs a copy elsewhere
  mkdir -p .evolve/tasks/02; cp .evolve/tasks/01/{task.yaml,prompt.txt,notes.md,fix.patch} .evolve/tasks/02/
  printf '#!/usr/bin/env bash\nset -e\ncd "$(dirname "$0")/../../.."\npython3 -c "from src.calc import add; assert add(2,3)==5"\n' \
    > .evolve/tasks/02/check.sh
  rm -rf .evolve/tasks/_broken                     # an agent deleted it: preflight must cope
  local out; out=$(bash "$CORTEX/bin/preflight.sh" 2>&1)
  ok "$([ -d .evolve/tasks/_broken/02 ] && echo quarantined || echo kept)" "quarantined" \
     "PR a check that cd's out of the checkout is quarantined, as a sweep would fail it"
  ok "$([ "$(echo "$out" | grep -c 'check said:')" -ge 1 ] && echo yes || echo no)" "yes" "PR the check's own output is printed as the reason"
  ok "$([ -d .evolve/tasks/01 ] && echo kept || echo quarantined)" "kept" "PR a normal check still passes from the copy"
}

t_screen_never_keeps() {
  local R="$TMP/e8"; make_repo "$R"
  setcfg 'regression_tolerance: 0.5' 'regression_tolerance: 0.34'; CX config >/dev/null 2>&1
  mk_cand x
  ok "$(CX promote x 2>&1 | grep -c 'no sweep has measured it')" "1" "PG a candidate no sweep measured is not promoted"
  synthv .evolve/runs/20260101T000000-screen.jsonl screen 2  01 0 2 1
  local j; j=$(score .evolve/runs/20260101T000000-screen.jsonl)
  ok "$(echo "$j" | jq -r .verdict)" "CONFIRM" "PG a screen that wins says CONFIRM, not KEEP"
  ok "$(echo "$j" | jq -r '.verdict_because[0] | test("never keeps")')" "true" "PG and says why"
  ok "$(CX promote x 2>&1 | grep -c 'says: add screen CONFIRM')" "1" "PG promote refuses a candidate only a screen has seen"
  ok "$([ -d .evolve/candidate/x ] && echo still || echo moved)" "still" "PG and moves nothing"
  ok "$(CX baseline --model m 2>&1 | grep -c 'a baseline comes from a confirm')" "1" "PG no baseline from a screen"
  synthv .evolve/runs/20260101T000100-screen.jsonl screen 2  01 1 1 1
  ok "$(score .evolve/runs/20260101T000100-screen.jsonl | jq -r .verdict)" "KILL" "PG a screen that wins nothing says KILL"
  synthv .evolve/runs/20260101T000200-screen.jsonl screen 2  01 0 2 0
  ok "$(score .evolve/runs/20260101T000200-screen.jsonl | jq -r .verdict)" "KILL" "PG a screen whose candidate never loaded says KILL"
  synthv .evolve/runs/20260101T010000-confirm.jsonl confirm 3  01 0 3 1  02 0 3 1
  ok "$(CX promote x 2>&1 | tail -1)" "promoted x (skill)" "PG a confirm that says KEEP promotes"
  mk_cand y
  ok "$(CX promote y --force 2>&1 | tail -1)" "promoted y (skill)" "PG --force skips the check"
}

t_dead_sweep_detected() {
  local R="$TMP/e9"; make_repo "$R"
  # a results file cut off mid-sweep, and nothing holding the lock: it died
  printf '%s\n' '{"event":"start","phase":"screen","mode":"add","k":2,"candidate":"x","replaced":[]}' \
    '{"v":"base","t":"01","r":1,"pass":0,"valid":1,"skills":[],"visible":[]}' > .evolve/runs/20260101T000000-screen.jsonl
  local j; j=$(score)
  ok "$(echo "$j" | jq -r '.running')/$(echo "$j" | jq -r '.finished')" "false/false" "DS an unfinished sweep with a free lock is not running"
  ok "$(echo "$j" | jq -r '[.blocked_because[] | test("stopped without finishing")] | any')" "true" "DS and cortex score says it died"
  # the same file while a sweep holds the lock: running, nothing added
  ( exec 9>.evolve/runs/.lock; flock 9; sleep 3 ) & local holder=$!
  sleep 1
  j=$(score)
  ok "$(echo "$j" | jq -r '.running')" "true" "DS a held lock reads as running"
  ok "$(echo "$j" | jq -r '[.blocked_because[] | test("stopped without finishing")] | any')" "false" "DS and is not called dead"
  wait $holder 2>/dev/null
}

t_sweep_detach() {
  local R="$TMP/e10"; make_repo "$R"; STUB="$TMP/stube10"; LOG="$R/log"
  stub "$STUB" 'sleep 1; if [ -d .claude/skills/vbd ]; then fire vbd; sed -i "s/a - b/a + b/" src/calc.py; fi; exit 0'
  mk_cand vbd
  local t0 out i; t0=$(date +%s)
  out=$(PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --phase confirm --detach 2>&1)
  ok "$(echo "$out" | grep -c 'started in the background')" "1" "D --detach returns at once"
  ok "$([ $(( $(date +%s) - t0 )) -lt 3 ] && echo fast || echo slow)" "fast" "D without waiting for the rollouts"
  for i in $(seq 1 60); do score 2>/dev/null | jq -e '.finished' >/dev/null 2>&1 && break; sleep 1; done
  ok "$(score | jq -r '.finished')/$(score | jq -r '.rollouts')" "true/4" "D the detached sweep runs to the end"
  ok "$(grep -c 'sweep done' .evolve/runs/sweep.log)" "1" "D and logs to .evolve/runs/sweep.log"
  ok "$(PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate ghost --detach 2>&1 | grep -c 'REFUSED')" "1" \
     "D a refusal is reported at once, not in the background"
}

t_evolve_phase() {
  local R="$TMP/e11"; make_repo "$R"
  ph() { CX phase --json | jq -r .phase; }
  ok "$(ph)" "A" "PH no candidate: phase A"
  synthv .evolve/runs/20260101T000000-confirm.jsonl confirm 3  01 0 3 1      # a finished sweep of "x"
  ok "$(ph)" "A" "PH a finished sweep of a candidate that is gone belongs to a closed cycle: still A"
  mk_cand x
  ok "$(ph)" "D" "PH the candidate's sweep has ended: D"
  ok "$(CX phase --json | jq -r .sweep.phase)" "confirm" "PH and says which sweep"
  rm -f .evolve/runs/*.jsonl
  ok "$(ph)" "B" "PH a candidate never swept: B"
  printf '%s\n' '{"event":"start","phase":"screen","mode":"add","k":2,"candidate":"x","tasks":"01","replaced":[]}' \
    > .evolve/runs/20260101T000100-screen.jsonl
  ok "$(ph)" "relaunch" "PH an unfinished sweep with nothing running: relaunch"
  ( exec 9>.evolve/runs/.lock; flock 9; sleep 3 ) & local holder=$!
  sleep 1
  ok "$(ph)" "C" "PH an unfinished sweep holding the lock: C"
  wait $holder 2>/dev/null
  printf '%s\n' '{"event":"start","phase":"confirm","mode":"replace","k":2,"candidate":"x","replaced":["old"]}' '{"event":"done"}' \
    > .evolve/runs/20260101T000200-confirm.jsonl
  ok "$(ph)" "prune" "PH a candidate a /prune swap is measuring belongs to /prune"
  rm -f .evolve/runs/*.jsonl; mk_cand y
  ok "$(ph)" "error" "PH two candidates: error"
  ok "$(CX cycle KEEP x 2>&1 | grep -c 'journal entry first')" "1" "PH a KEEP is not recorded before its journal entry"
  printf '\n## 2026-01-01  x\n\nDECISION: KEEP\n' >> .evolve/journal.md
  ok "$(CX cycle KEEP x >/dev/null 2>&1; echo $?)/$(CX cycle KEEP x 2>&1 | grep -c 'already recorded')" "0/1" \
     "PH a cycle is recorded once: the same KEEP twice is refused"
  ok "$(jq -r .cycles .evolve/state.json)" "1" "PH and the counter did not move"
  ok "$(CX cycle KILL x 2>&1 | grep -c 'journal entry first')" "1" "PH a second cycle of x needs a second entry"
  ok "$(CX cycle BARREN >/dev/null 2>&1; echo $?)/$(grep -c 'nothing to learn' .evolve/journal.md)" "0/1" \
     "PH BARREN needs no name and writes its own journal line"
}

t_two_repos_sweep_at_once() {
  local R1="$TMP/c1a" R2="$TMP/c2a"; STUB="$TMP/stubc12"; LOG="$TMP/c12.log"
  make_repo "$R2"; mk_cand vbd
  make_repo "$R1"; mk_cand vbd                      # both use the default sandbox_root
  stub "$STUB" 'sleep 2; if [ -d .claude/skills/vbd ]; then fire vbd; sed -i "s/a - b/a + b/" src/calc.py; fi; exit 0'
  ( cd "$R1" && PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --phase confirm >/dev/null 2>&1 ) &
  local p1=$!
  ( cd "$R2" && PATH="$STUB:$PATH" bash "$CORTEX/bin/sweep.sh" --candidate vbd --phase confirm >/dev/null 2>&1 ) &
  local p2=$!
  wait $p1 $p2
  ok "$(cd "$R1" && score | jq -r '"\(.invalid)/\(.scorable)"')/$(cd "$R2" && score | jq -r '"\(.invalid)/\(.scorable)"')" "0/true/0/true" \
     "SR two repositories sweeping at once never touch each other's sandbox"
  ok "$([ "$(cd "$R1" && HX sandbox-dir)" != "$(cd "$R2" && HX sandbox-dir)" ] && echo own || echo shared)" "own" \
     "SR each repository has its own folder under sandbox_root"
}

t_one_name_one_idea() {
  local R="$TMP/e12"; make_repo "$R"; STUB="$TMP/stube12"; LOG="$R/log"; stub "$STUB" 'exit 0'
  mk_cand vbd; CX bury vbd --from candidate --why "screen: never invoked" >/dev/null
  mk_cand vbd                                        # the same name, revised
  ok "$(dry --candidate vbd | grep -c 'already in the graveyard')" "1" "N a revised idea may not reuse a buried name"
  mk_cand vbd-v2
  ok "$(dry --candidate vbd-v2 | grep -c '^sweep: OK')" "1" "N under a new name it runs"
  printf '\n## 2026-01-01  x\n\nKILL\n' >> .evolve/journal.md
  CX cycle KILL x >/dev/null 2>&1
  ok "$(CX cycle KEEP x 2>&1 | grep -c 'add one below the others')" "1" "N the refusal says a NEW entry is needed, not an edited one"
}

t_transcripts_scoped() {
  local R="$TMP/e13"; make_repo "$R"
  local T="$TMP/transcripts"; mkdir -p "$T/$(printf '%s' "$R" | sed 's/[^A-Za-z0-9]/-/g')" "$T/-some-other-project"
  echo '{}' > "$T/$(printf '%s' "$R" | sed 's/[^A-Za-z0-9]/-/g')/mine.jsonl"
  echo '{}' > "$T/-some-other-project/theirs.jsonl"
  setcfg 'transcripts_dir: ~/.claude/projects' "transcripts_dir: $T"
  local out; out=$(HX transcripts)
  ok "$(echo "$out" | grep -c 'mine.jsonl')/$(echo "$out" | grep -c 'theirs.jsonl')" "1/0" \
     "T transcripts lists this project's sessions and never another project's"
}

# ---------------------------------------------------------------- driver ----
mkdir -p "$TMP"
ALL_TESTS=(t_git_isolation t_infra_not_capability t_timeout_is_a_real_failure \
         t_locking t_reset_is_verified t_no_fix_leaks_between_rollouts \
         t_budget_refused_up_front t_truncated_data_not_scorable t_harness_snapshot \
         t_removal_needed_skill_rejected t_removal_dead_weight_accepted \
         t_removal_unmeasured_never_deletes t_replace_same_name t_bury_and_promote \
         t_candidate_fired_is_recorded t_net_runs_rounding t_status_shows_model \
         t_empty_and_legacy_results t_interleaving \
         t_per_phase_files t_sandbox_cleanup t_tasks_are_snapshotted \
         t_single_sandbox_no_leak \
         t_precondition_absent t_precondition_blocks_rollouts \
         t_precondition_agent_never_runs t_precondition_timeout \
         t_preflight_does_not_quarantine_on_env t_precondition_passing \
         t_config_compiles t_config_validation t_sandbox_root_rules \
         t_config_autorecompile t_check_timeout t_verdict_is_computed \
         t_cycle_counter t_model_and_env t_cache_dirs t_harness_files \
         t_preflight_still_works t_happy_path t_bad_input \
         t_rules_snapshot_overrides_base t_rule_fired_via_read t_rule_replace t_observe_forms \
         t_visible_notes t_legacy_no_visible t_keep_requires_fired t_observe_failure_unknown \
         t_cross_tier_guard t_sweep_dry_run t_reach_uses_sweep_tasks t_task_id_and_sha_validation \
         t_config_guards t_cli_version_gate t_rule_promote_bury t_check_errors \
         t_check_folded_description t_live_items_never_block t_dead_glob_repair t_glob_unit \
         t_touching t_hash_paths t_init_claude_md t_init_backs_up_commands \
         t_symlink_out_of_repo_refused \
         t_frontmatter_differential t_candidate_hygiene t_sweep_args_injection t_symlink_variants \
         t_tier_change_skill_to_rule t_status_and_budget \
         t_usage_report t_prune_plan_flow t_prune_model_upgrade t_prune_estimate_defaults \
         t_sweep_records_cost t_config_prune_keys \
         t_exposure_filter t_recheck_flow t_sandbox_hides_evolve \
         t_parallel_config t_parallel_auto_sizing t_parallel_sweep_same_results t_parallel_really_concurrent \
         t_parallel_services_one_at_a_time t_parallel_kill_stops_every_worker t_parallel_dry_run_and_estimate \
         t_preflight_parallel t_preflight_beside_a_sweep \
         t_exclusive_tasks_run_alone t_preflight_retries_alone t_preflight_probe t_worker_tmpdir \
         t_cpus_per_rollout_and_quota t_timeout_under_load t_queue_broken_is_incomplete \
         t_score_planned_missing t_same_area_as_live_warns t_screen_never_decides_a_removal t_recheck_pairs_when_the_path_has_a_space t_uninformative_sweep_is_not_a_kill t_preflight_interrupted_reports t_preflight_busy_skip \
         t_never_passed_named t_preflight_check_needs_fix_tests t_fixpatch t_task_new t_preflight_runs_like_a_sweep \
         t_screen_never_keeps t_dead_sweep_detected t_sweep_detach t_evolve_phase \
         t_two_repos_sweep_at_once t_one_name_one_idea t_transcripts_scoped)
SELECTED=()
for t in "${ALL_TESTS[@]}"; do
  [ $# -gt 0 ] && case "$t" in *"$1"*) ;; *) continue ;; esac
  SELECTED+=("$t")
done

if [ "$JOBS" -le 1 ]; then
  for t in "${SELECTED[@]}"; do
    echo "$t"
    "$t"
  done
else
  # each test in a subshell with its own TMP; counters come back through files
  OUTS="$TMP/.outs"; mkdir -p "$OUTS"
  run_one() {
    local t="$1"
    ( TMP="$TMP/$t"; mkdir -p "$TMP"; PASS=0; FAIL=0; FAILED=()
      echo "$t"; "$t"
      printf '%s %s\n' "$PASS" "$FAIL" > "$OUTS/$t.count"
      [ "${#FAILED[@]}" -gt 0 ] && printf '%s\n' "${FAILED[@]}" > "$OUTS/$t.failed"
      true ) > "$OUTS/$t.out" 2>&1 < /dev/null
  }
  for t in "${SELECTED[@]}"; do
    while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n 2>/dev/null || true; done
    run_one "$t" &
  done
  wait
  for t in "${SELECTED[@]}"; do
    cat "$OUTS/$t.out"
    if [ -f "$OUTS/$t.count" ]; then
      read -r p f < "$OUTS/$t.count"; PASS=$((PASS + p)); FAIL=$((FAIL + f))
    else
      FAIL=$((FAIL + 1)); FAILED+=("$t: did not finish")
    fi
    [ -f "$OUTS/$t.failed" ] && mapfile -t -O "${#FAILED[@]}" FAILED < "$OUTS/$t.failed"
  done
fi

echo ""
echo "──────────────────────────────────────────"
printf 'passed %s   failed %s\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then printf '%s\n' "${FAILED[@]}" | sed 's/^/  - /'; fi
cd /; rm -rf "$TMP"
[ "$FAIL" -eq 0 ]
