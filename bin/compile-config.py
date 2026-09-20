#!/usr/bin/env python3
"""Compile .evolve/config.yaml -> .evolve/config.json, validating as it goes.

Humans edit the YAML (it takes comments; JSON does not). Every shell script
reads the compiled flat JSON with `jq`, so the hot path needs no YAML parser.

Uses PyYAML when available. Falls back to a parser for the restricted subset
this schema actually uses: up to three levels of nesting, scalars, string
lists and string->string maps. Nothing here needs anchors, flow style or multi-line
scalars, so the fallback is exact for valid input rather than best-effort.
"""
import json, os, re, sys

# key -> (yaml path, type, default, one-line meaning)
SCHEMA = [
    ("k_screen",                 "measurement.k.screen",              int,   2,   "rollouts per task when screening"),
    ("k_confirm",                "measurement.k.confirm",             int,   3,   "rollouts per task when confirming"),
    ("max_runs_per_cycle",       "measurement.max_runs_per_cycle",    int,   60,  "hard budget stop for one sweep"),
    ("rollout_timeout_s",        "measurement.rollout_timeout_s",     int,   600, "kill an agent that will not finish"),
    ("check_timeout_s",          "measurement.check_timeout_s",       int,   120, "kill a verifier that hangs"),
    ("max_invalid_rate",         "measurement.max_invalid_rate",      float, 0.1, "invalid share above which a sweep is unscorable"),
    ("parallel_rollouts",        "measurement.parallel.rollouts",     "auto|int", "auto", "rollouts a sweep runs at once, each in its own sandbox; auto = from ram_percent"),
    ("parallel_preflight",       "measurement.parallel.preflight",    "auto|int", "auto", "tasks preflight checks at once; auto = from ram_percent"),
    ("parallel_ram_percent",     "measurement.parallel.ram_percent",  int,   50,  "auto uses at most this share of the RAM available when it starts"),
    ("parallel_ram_per_rollout_mb", "measurement.parallel.ram_per_rollout_mb", int, 1024, "memory one rollout needs (agent + check), for auto"),
    ("parallel_ram_per_check_mb", "measurement.parallel.ram_per_check_mb", int, 512, "memory one preflight check needs, for auto"),
    ("parallel_max_rollouts",    "measurement.parallel.max_rollouts", int,   16,  "auto never runs more rollouts at once than this (API rate limits)"),
    ("parallel_cpus_per_rollout", "measurement.parallel.cpus_per_rollout", int, 1, "CPUs one rollout keeps busy (its agent and its tests); auto runs at most CPUs / this"),
    ("parallel_with_services",   "measurement.parallel.with_services", bool, False, "let tasks with a precondition.sh run in parallel too"),
    ("regression_tolerance",     "gates.regression_tolerance",        float, 0.34,"largest allowed drop on any single task"),
    ("min_net_runs",             "gates.min_net_runs",                int,   2,   "reject a win smaller than this many runs"),
    ("min_valid_tasks",          "collection.min_valid_tasks",        int,   3,   "refuse to evolve below this many valid tasks"),
    ("min_theme_occurrences",    "collection.min_theme_occurrences",  int,   3,   "how often a problem must recur to earn a skill"),
    ("lookback_days",            "collection.lookback_days",          int,   7,   "transcript window /evolve reads"),
    ("transcripts_dir",          "collection.transcripts_dir",        str,   "~/.claude/projects", "where sessions are mined"),
    ("stop_after_barren_cycles", "collection.stop_after_barren_cycles",int,  2,   "give up after N cycles with no KEEP"),
    ("always_on_budget_chars",   "collection.always_on_budget_chars", int,   3000, "always-on context above which check warns"),
    ("prune_usage_days",         "prune.usage_days",                  int,   30,  "session window of the usage report /prune chooses from"),
    ("prune_max_items",          "prune.max_items",                   int,   3,   "most items a routine /prune pass may test (a model change tests all)"),
    ("model",                    "baseline.model",                    str,   "",  "model pinned for rollouts; empty = CLI default"),
    ("baseline_max_age_days",    "baseline.max_age_days",             int,   30,  "when a cached baseline goes stale"),
    ("sandbox_root",             "environment.sandbox_root",          str,   "/tmp/cortex-evolve", "where rollout clones live"),
    ("permission_mode",          "environment.permission_mode",       str,   "acceptEdits", "how headless rollouts handle prompts"),
    ("harness_files",            "environment.harness_files",         list,  ["CLAUDE.md"], "files copied into both sandboxes"),
    ("cache_dirs",               "environment.cache_dirs",            list,  ["__pycache__", ".pytest_cache"], "build caches purged between states"),
    ("rollout_env",              "environment.rollout_env",           dict,  {"PYTHONDONTWRITEBYTECODE": "1"}, "env vars set for every rollout"),
    ("min_claude_version",       "environment.min_claude_version",    str,   "2.1.276", "oldest CLI whose skill/rule loading was verified"),
    # jev: the PROPOSAL-layer accelerator. `cortex init` never writes this block into
    # config.yaml — the defaults live here only, so a repo that never turns Jev on
    # never gains a `jev:` key, and a downgrade to an older Cortex stays silent
    # instead of warning `unknown key` once per key, every run, forever.
    # .env overrides every one of these at run time; `cortex config` prints the source.
    ("jev_enabled",              "jev.enabled",                       bool,  False, "master switch; false = Cortex behaves exactly as it does today"),
    ("jev_model",                "jev.model",                         str,   "jev-latest", "System One model or alias; pin a version to freeze J0's numbers"),
    ("jev_base_url",             "jev.base_url",                      str,   "https://api.typesafe.ai/v1/systemone", "the System One endpoint; Vercel AI Gateway serves the same shapes at https://ai-gateway.vercel.sh/typesafe/v1/systemone"),
    ("jev_timeout_s",            "jev.timeout_s",                     int,   10, "seconds one Jev call may take, retries included, before it falls back"),
    ("jev_confidence_floor",     "jev.confidence_floor",              float, 0.7, "below this confidence a Choice is escalated to Claude instead of acted on"),
    ("jev_retry_attempts",       "jev.retry.attempts",                int,   3, "429/529 attempts, honouring Retry-After; everything else falls back at once"),
    ("jev_retry_backoff_s",      "jev.retry.backoff_s",               float, 1.0, "first backoff, doubled per attempt, capped by timeout_s"),
    ("jev_max_requests_per_cycle", "jev.budget.max_requests_per_cycle", int, 2000, "a census over this many requests refuses to start"),
    ("jev_max_input_mtok_per_cycle", "jev.budget.max_input_mtok_per_cycle", float, 12.0, "a census over this many input MTok refuses to start"),
    ("jev_max_rps",              "jev.budget.max_rps",                int,   15, "requests per second, kept an order of magnitude under the published ceiling"),
    ("jev_relevance_floor",      "jev.scope.relevance_floor",         float, 0.35, "cortex scope warns below this relevance; it NEVER kills a candidate"),
    ("jev_harvest_threshold",    "jev.harvest.noul_threshold",        float, 0.6, "the session-end hook stays silent below this probability"),
]

def minimal_yaml(text):
    """Exact for this schema's subset; rejects anything it does not understand."""
    root, stack = {}, [(-1, None)]
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split(" #", 1)[0].rstrip() if " #" in raw else raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        body = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if parent is None:
            parent = root
            stack = [(-1, root)]
        if body.startswith("- "):
            item = body[2:].strip().strip('"\'')
            if not isinstance(parent, list):
                raise ValueError(f"line {lineno}: list item outside a list")
            parent.append(item)
            continue
        m = re.match(r'^([A-Za-z_][\w.-]*)\s*:\s*(.*)$', body)
        if not m:
            raise ValueError(f"line {lineno}: cannot parse {body!r}")
        key, val = m.group(1), m.group(2).strip()
        if not isinstance(parent, dict):
            raise ValueError(f"line {lineno}: mapping inside a list is not supported")
        if val == "":
            nxt = {}
            for future in text.splitlines()[lineno:]:
                if not future.strip() or future.lstrip().startswith("#"):
                    continue
                fi = len(future) - len(future.lstrip())
                if fi <= indent:
                    break
                nxt = [] if future.lstrip().startswith("- ") else {}
                break
            parent[key] = nxt
            stack.append((indent, nxt))
        else:
            v = val.strip('"\'')
            if re.fullmatch(r'-?\d+', v):        v = int(v)
            elif re.fullmatch(r'-?\d*\.\d+', v): v = float(v)
            elif v.lower() in ("true", "false"): v = v.lower() == "true"
            parent[key] = v
    return root

def load_yaml(path):
    text = open(path).read()
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        return minimal_yaml(text)

def dig(tree, dotted):
    node = tree
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node

def walk_keys(tree, known, prefix=""):
    """Yield leaf paths. A path that IS a known setting is a leaf even when its
    value is a map (rollout_env) — otherwise we would flag its contents."""
    for k, v in (tree or {}).items():
        path = f"{prefix}{k}"
        if path in known:
            yield path
        elif isinstance(v, dict):
            yield from walk_keys(v, known, path + ".")
        else:
            yield path

def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    ev = os.path.join(repo, ".evolve")
    src, dst = os.path.join(ev, "config.yaml"), os.path.join(ev, "config.json")
    if not os.path.exists(src):
        print(f"cortex config: no {src}", file=sys.stderr); return 1

    try:
        tree = load_yaml(src)
    except Exception as e:
        print(f"cortex config: {src}: {e}", file=sys.stderr); return 1

    out, errors, warnings = {}, [], []
    known = set()
    for key, path, typ, default, _doc in SCHEMA:
        known.add(path)
        val = dig(tree, path)
        if val is None:
            out[key] = default; continue
        try:
            if typ == "auto|int":
                if isinstance(val, str) and val.strip().lower() == "auto":
                    out[key] = "auto"
                elif isinstance(val, bool):
                    raise ValueError
                else:
                    out[key] = int(val)
            elif typ is bool:
                if isinstance(val, bool):
                    out[key] = val
                elif str(val).lower() in ("true", "false"):
                    out[key] = str(val).lower() == "true"
                else:
                    raise ValueError
            elif typ is int:   out[key] = int(val)
            elif typ is float: out[key] = float(val)
            elif typ is list:  out[key] = [str(x) for x in (val if isinstance(val, list) else [val])]
            elif typ is dict:  out[key] = {str(k): str(v) for k, v in (val or {}).items()}
            else:              out[key] = str(val)
        except (TypeError, ValueError):
            want = typ if isinstance(typ, str) else typ.__name__
            errors.append(f"{path}: expected {'auto or a number' if want == 'auto|int' else want}, got {val!r}")

    # a typo in a key name silently reverts that setting to its default —
    # the most confusing possible failure. Name it instead.
    if errors:      # a value of the wrong type: the checks below would crash on it
        for e in errors: print(f"cortex config: error: {e}", file=sys.stderr)
        return 1

    for path in walk_keys(tree, known):
        if path not in known:
            warnings.append(f"unknown key '{path}' (ignored — typo?)")

    out["transcripts_dir"] = os.path.expanduser(out["transcripts_dir"])

    # harness_files are copied into the sandbox AFTER the skills and rules, so an
    # entry under .claude/skills or .claude/rules would silently undo --replace;
    # an absolute or ../ path would copy from, or write to, outside the repo.
    for f in out["harness_files"]:
        parts = f.replace("\\", "/").split("/")
        if f.startswith("/") or f.startswith("~") or ".." in parts:
            errors.append(f"environment.harness_files: {f!r} must be a path inside the repository")
        elif os.path.normpath(f) == ".env" or os.path.basename(os.path.normpath(f)) == ".env":
            # harness_files is copied into BOTH rollout sandboxes, which is the one
            # place JEV_API_KEY must never appear. make_sandbox() clones the repo, so
            # an untracked .env cannot follow it — but this list copies arbitrary
            # repo paths, and would.
            errors.append(f"environment.harness_files: {f!r} is a .env — it would copy your API key "
                          "into both rollout sandboxes, where no secret may ever appear")
        elif (os.path.normpath(f) + "/").startswith((".claude/skills/", ".claude/rules/")):
            errors.append(f"environment.harness_files: {f!r} is under .claude/skills or .claude/rules, "
                          "which the sweep manages itself — listing it would undo --replace")
    # README has always said never to run unattended rollouts this way; enforce it.
    if out["permission_mode"] == "bypassPermissions":
        errors.append("environment.permission_mode: bypassPermissions is refused — rollouts are "
                      "unattended agents with real tool access (use acceptEdits)")
    if not re.fullmatch(r"\d+(\.\d+)+", out["min_claude_version"]):
        errors.append(f"environment.min_claude_version: {out['min_claude_version']!r} is not a version like 2.1.276")
    if not 1 <= out["prune_usage_days"] <= 3650:
        errors.append("prune.usage_days must be between 1 and 3650")
    if out["prune_max_items"] < 1:
        errors.append("prune.max_items must be >= 1 (a model change always tests every item anyway)")
    if out["always_on_budget_chars"] < 0:
        errors.append("collection.always_on_budget_chars must be >= 0")

    # jev: a typo in a key name silently reverts that setting to its default, so
    # every one of these needs its bound the way every other key has one.
    for key, path in (("jev_confidence_floor", "jev.confidence_floor"),
                      ("jev_relevance_floor", "jev.scope.relevance_floor"),
                      ("jev_harvest_threshold", "jev.harvest.noul_threshold")):
        if not 0 <= out[key] <= 1:
            errors.append(f"{path} must be between 0 and 1")
    if not 1 <= out["jev_timeout_s"] <= 120:
        errors.append("jev.timeout_s must be between 1 and 120 (no Jev call may sit on a blocking path)")
    if not 1 <= out["jev_retry_attempts"] <= 10:
        errors.append("jev.retry.attempts must be between 1 and 10")
    if not 0 <= out["jev_retry_backoff_s"] <= 60:
        errors.append("jev.retry.backoff_s must be between 0 and 60")
    if out["jev_max_requests_per_cycle"] < 1:
        errors.append("jev.budget.max_requests_per_cycle must be >= 1")
    if out["jev_max_input_mtok_per_cycle"] <= 0:
        errors.append("jev.budget.max_input_mtok_per_cycle must be > 0")
    if not 1 <= out["jev_max_rps"] <= 1200:
        errors.append("jev.budget.max_rps must be between 1 and 1200 (the published ceiling)")
    if not out["jev_base_url"].startswith(("http://", "https://")):
        errors.append(f"jev.base_url: {out['jev_base_url']!r} is not an http(s) URL")

    if out["k_confirm"] < 1 or out["k_screen"] < 1:
        errors.append("measurement.k.screen and .confirm must be >= 1")
    if not 0 <= out["max_invalid_rate"] <= 1:
        errors.append("measurement.max_invalid_rate must be between 0 and 1")
    if out["max_runs_per_cycle"] < 2:
        errors.append("measurement.max_runs_per_cycle must be >= 2")
    # parallel: a number is taken as given (capped only by the jobs there are);
    # auto is sized at run time from ram_percent of the RAM available then
    for key, path in (("parallel_rollouts", "rollouts"), ("parallel_preflight", "preflight")):
        if out[key] != "auto" and not 1 <= out[key] <= 64:
            errors.append(f"measurement.parallel.{path} must be auto or a number from 1 to 64")
    if not 1 <= out["parallel_ram_percent"] <= 90:
        errors.append("measurement.parallel.ram_percent must be between 1 and 90 "
                      "(the rest of the machine needs memory too)")
    for key, path in (("parallel_ram_per_rollout_mb", "ram_per_rollout_mb"),
                      ("parallel_ram_per_check_mb", "ram_per_check_mb")):
        if out[key] < 64:
            errors.append(f"measurement.parallel.{path} must be >= 64")
    if not 1 <= out["parallel_max_rollouts"] <= 64:
        errors.append("measurement.parallel.max_rollouts must be between 1 and 64")
    if not 1 <= out["parallel_cpus_per_rollout"] <= 64:
        errors.append("measurement.parallel.cpus_per_rollout must be between 1 and 64")
    # sandbox_root was restricted to /tmp, which is wrong on machines where the
    # docker daemon cannot see the user's /tmp (snap or rootless installs give
    # the daemon its own). A task that mounts the sandbox into a container would
    # silently mount an EMPTY directory there. So: allow any absolute path, and
    # rely on `cortex clean` only ever deleting its own named subdirectories.
    sr = os.path.abspath(os.path.expanduser(out["sandbox_root"]))
    out["sandbox_root"] = sr
    repo_abs = os.path.abspath(repo)
    if not sr.startswith("/"):
        errors.append("environment.sandbox_root must be an absolute path")
    elif sr.count("/") < 2 or sr in ("/", "/tmp", "/var", "/home", "/usr", "/etc", os.path.expanduser("~")):
        errors.append(f"environment.sandbox_root is too shallow to be safe: {sr!r}")
    elif sr == repo_abs or sr.startswith(repo_abs + "/") or repo_abs.startswith(sr + "/"):
        errors.append(f"environment.sandbox_root must not overlap the repository: {sr!r}")
    elif not sr.startswith(("/tmp/", "/var/tmp/")):
        warnings.append(f"sandbox_root {sr!r} is outside /tmp — fine (and required when the "
                        f"docker daemon cannot see /tmp), just make sure it is disposable")
    one_run = 1.0 / out["k_confirm"]
    if out["regression_tolerance"] < one_run:
        warnings.append(f"gates.regression_tolerance ({out['regression_tolerance']}) is below one run "
                        f"at k={out['k_confirm']} ({one_run:.2f}) — ANY drop will kill every candidate")
    if out["regression_tolerance"] > 2 * one_run:
        warnings.append(f"gates.regression_tolerance ({out['regression_tolerance']}) allows more than two "
                        f"runs of loss at k={out['k_confirm']} — regressions will slip through")
    if out["min_net_runs"] > out["k_confirm"]:
        warnings.append(f"gates.min_net_runs ({out['min_net_runs']}) exceeds k_confirm "
                        f"({out['k_confirm']}) — a single task can never clear it")

    for w in warnings: print(f"cortex config: warning: {w}", file=sys.stderr)
    if errors:
        for e in errors: print(f"cortex config: error: {e}", file=sys.stderr)
        return 1

    with open(dst, "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True); fh.write("\n")
    if "--quiet" not in sys.argv:
        print(f"compiled {src} -> {dst} ({len(out)} settings)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
