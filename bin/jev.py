#!/usr/bin/env python3
"""jev.py — client for Jev (TypeSafe System One), and Cortex's question library.

Jev is a JUDGE, and Cortex's founding constraint (THEORY §2) is that a verifier
is a command that exits 0 or non-zero — not an opinion, not an LLM judge. So
every call in this file sits in the PROPOSAL layer: which theme, which tier,
which scope, is there anything worth harvesting. None of it reaches
`cortex score`, the gates, `check.sh` or preflight, and none of it ever runs
inside a rollout sandbox, where it would become part of the harness under test.

Four properties this module must not lose:

  1. STDLIB ONLY. `cortex doctor` checks git/jq/claude/timeout/flock/python3 and
     nothing else, so a third-party import would fail at run time instead of at
     `doctor`. urllib.request is the whole HTTP client.
  2. IT NEVER RAISES ACROSS ITS BOUNDARY. Every entry point returns an Answers
     whose `.ok` is False on any failure. A caller that forgets to check still
     gets a deterministic fallback, never a traceback.
  3. IT NEVER BLOCKS. One `ask` — every retry and every backoff sleep included —
     returns within its timeout budget. No Jev call is on a blocking path.
  4. THE KEY NEVER LEAVES. It is read from the environment or a .env, sent in one
     Authorization header, and never logged, printed or written anywhere.

The wire contract (TypeSafe API 0.2.0, https://docs.typesafe.ai/api). Two
endpoints speak it and this module cannot tell them apart, which is the point:

  https://api.typesafe.ai/v1/systemone              TypeSafe direct (invite only)
  https://ai-gateway.vercel.sh/typesafe/v1/systemone  Vercel AI Gateway, same shapes

Only `base_url` and `model` differ between them, and both live in .env. There is
no adapter here and there must not be one: the day a third route appears, it is
two lines in a config file, not a branch in this file.

  POST <base_url>            Authorization: Bearer <key>
    {"state": <str|obj|list>, "model": "jev-latest", "questions": {<name>: Q}}
  Q is one of
    {"type":"noul",   "instructions": ..., "criteria": {"true":..., "false":...}}
    {"type":"choice", "instructions": ..., "criteria": {<name>: <when it applies>}}
    {"type":"score",  "instructions": ..., "criteria": [<level 0>, <level 1>, ...]}
  200 -> {"model": <id that answered>, "answers": {<name>: A}, "usage": {...}}
    A is {"type":"noul","noul":p}
       | {"type":"choice","choice":n,"confidence":c,"probabilities":{...}}
       | {"type":"score","score":s,"confidence":c,"legend":{...},"probabilities":{...}}
  401 invalid key · 422 malformed request · 429 rate limited · 529 overloaded

Subcommands (every one exits 0 even when Jev is off or unreachable, except where
a caller needs to tell "refused" from "answered no"):

  doctor [--json]           key present · endpoint answers · round-trip · model id
  status                    one line for `cortex status`
  config [--json]           every effective setting and where it came from
  ask --site S --state-file F --questions-file Q [--json]
                            one raw request; the shape the tests drive
  harvest [--repo R] [--transcript F] [--timeout N] [--json]
                            J2: did this session fix something, or get corrected?
                            exit 0 = nudge (printed) · 3 = stay silent ·
                            4 = Jev is off or unavailable, fall back to today
  tier --theme "<what recurs>" [--files "a.py b.py"] [--json]
                            J4(b): which layer the change belongs in, gated on
                            confidence_floor. exit 3 = escalate to Claude
  journal --candidate NAME [--repo R] [--days N]
                            D5: the cycle's `jev:` line, read back from the log
  models                    GET /v1/models for the authenticated account
"""
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

CORTEX_HOME = os.environ.get("CORTEX_HOME") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where a call came from. Written into every log line so a month later you can
# ask "what did the scope check actually say" without re-deriving it.
CALL_SITES = ("scope", "harvest", "themes", "tier", "trigger", "prune", "doctor", "ask")
RETRY_STATUS = (429, 529)
CHARS_PER_TOKEN = 4          # only ever used for the pre-flight budget estimate
MAX_WORKERS = 16             # a ceiling on threads, under max_rps' ceiling on requests


# ------------------------------------------------------------------ config --
def _bool(v):
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off", ""):
        return False
    raise ValueError(v)


# name, config.json key, .env name, cast, (lo, hi) or None
FIELDS = (
    ("enabled",                  "jev_enabled",                  "JEV_ENABLED",                  _bool, None),
    ("model",                    "jev_model",                    "JEV_MODEL",                    str,   None),
    ("base_url",                 "jev_base_url",                 "JEV_BASE_URL",                 str,   None),
    ("timeout_s",                "jev_timeout_s",                "JEV_TIMEOUT_S",                int,   (1, 120)),
    ("confidence_floor",         "jev_confidence_floor",         "JEV_CONFIDENCE_FLOOR",         float, (0.0, 1.0)),
    ("retry_attempts",           "jev_retry_attempts",           "JEV_RETRY_ATTEMPTS",           int,   (1, 10)),
    ("retry_backoff_s",          "jev_retry_backoff_s",          "JEV_RETRY_BACKOFF_S",          float, (0.0, 60.0)),
    ("max_requests_per_cycle",   "jev_max_requests_per_cycle",   "JEV_MAX_REQUESTS_PER_CYCLE",   int,   (1, 10 ** 7)),
    ("max_input_mtok_per_cycle", "jev_max_input_mtok_per_cycle", "JEV_MAX_INPUT_MTOK_PER_CYCLE", float, (0.000001, 10 ** 4)),
    ("max_rps",                  "jev_max_rps",                  "JEV_MAX_RPS",                  int,   (1, 1200)),
    ("relevance_floor",          "jev_relevance_floor",          "JEV_RELEVANCE_FLOOR",          float, (0.0, 1.0)),
    ("harvest_threshold",        "jev_harvest_threshold",        "JEV_HARVEST_THRESHOLD",        float, (0.0, 1.0)),
)

DEFAULTS = {
    "enabled": False,
    "model": "jev-latest",
    "base_url": "https://api.typesafe.ai/v1/systemone",
    "timeout_s": 10,
    "confidence_floor": 0.7,
    "retry_attempts": 3,
    "retry_backoff_s": 1.0,
    "max_requests_per_cycle": 2000,
    "max_input_mtok_per_cycle": 12.0,
    "max_rps": 15,
    "relevance_floor": 0.35,
    "harvest_threshold": 0.6,
}


def parse_env_file(path):
    """KEY=VALUE lines, never executed. A .env is a file the user pasted a secret
    into; sourcing it would run whatever else is in there."""
    out = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].lstrip()
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k):
                    continue
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                out[k] = v
    except OSError:
        pass
    return out


class Config:
    """Effective settings, and where each one came from.

    Precedence, stated once because two systems carry the same values:
    the environment beats $CORTEX_HOME/.env (or JEV_ENV_FILE), which beats
    <repo>/.env, which beats .evolve/config.yaml, which beats the built-in default.
    The reason is that a .env is per-machine and gitignored while config.yaml is
    committed, so a key or a one-run override must never require editing a tracked
    file. `cortex config` prints the effective value and its source for every key,
    because two systems carrying the same value is otherwise unanswerable.
    """

    def __init__(self):
        self.key = ""
        self.key_source = "(none)"
        self.repo = None
        self.source = {}
        for name, _c, _e, _t, _b in FIELDS:
            setattr(self, name, DEFAULTS[name])
            self.source[name] = "default"

    @property
    def on(self):
        return bool(self.enabled) and bool(self.key)

    @property
    def off_reason(self):
        if not self.enabled:
            return "jev disabled"
        if not self.key:
            return "no key"
        return ""

    def as_dict(self, with_source=False):
        d = {n: getattr(self, n) for n, *_ in FIELDS}
        d["key_present"] = bool(self.key)
        d["key_source"] = self.key_source
        d["on"] = self.on
        if with_source:
            d["source"] = dict(self.source, key=self.key_source)
        return d


def _config_json(repo):
    try:
        with open(os.path.join(repo, ".evolve", "config.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError, TypeError):
        return {}


def resolve(repo=None, env=None):
    """The effective configuration. Never raises: a malformed value keeps the
    value below it in the precedence order and records that in `source`."""
    cfg = Config()
    cfg.repo = repo
    env = os.environ if env is None else env

    # lowest first, so each later layer overwrites the one before it
    layers = []
    if repo:
        cj = _config_json(repo)
        layers.append(("config.yaml", {e: cj[c] for _n, c, e, _t, _b in FIELDS if c in cj}))
        layers.append((os.path.join(repo, ".env"), parse_env_file(os.path.join(repo, ".env"))))
    # The machine-level .env. JEV_ENV_FILE points it somewhere else — for a key
    # rendered by a password manager, and for the test suite, which must not read
    # the developer's own file or its results would depend on whose machine it ran on.
    home_env = env.get("JEV_ENV_FILE") or os.path.join(CORTEX_HOME, ".env")
    layers.append((home_env, parse_env_file(home_env)))
    layers.append(("environment", {k: v for k, v in env.items() if k.startswith("JEV_")}))

    for label, values in layers:
        for name, _c, evar, cast, bound in FIELDS:
            if evar not in values or values[evar] == "":
                continue
            try:
                v = cast(values[evar])
            except (TypeError, ValueError):
                continue
            if bound and not (bound[0] <= v <= bound[1]):
                continue
            if name == "base_url" and not str(v).startswith(("http://", "https://")):
                continue
            setattr(cfg, name, v)
            cfg.source[name] = label
        # PRESENT, not truthy: an explicitly empty JEV_API_KEY means "no key here",
        # and must shadow a key set lower down. Otherwise `JEV_API_KEY= cortex ...`
        # would silently fall through to $CORTEX_HOME/.env and use the real one.
        if "JEV_API_KEY" in values:
            cfg.key, cfg.key_source = values["JEV_API_KEY"], label
    return cfg


# ----------------------------------------------------------------- answers --
class Answers:
    """One request's result. `.ok` is False for every failure, and `.reason` is
    the one-line explanation a caller prints beside its deterministic half."""

    def __init__(self, ok=False, reason="", model="", answers=None, usage=None,
                 latency_ms=0, status=None):
        self.ok = ok
        self.reason = reason
        self.model = model
        self.answers = answers or {}
        self.usage = usage or {}
        self.latency_ms = latency_ms
        self.status = status

    def __bool__(self):
        return self.ok

    def answered(self, name):
        return isinstance(self.answers.get(name), dict)

    def noul(self, name, default=None):
        a = self.answers.get(name)
        if isinstance(a, dict) and a.get("type") == "noul":
            try:
                p = float(a["noul"])
            except (KeyError, TypeError, ValueError):
                return default
            return p if 0.0 <= p <= 1.0 else default
        return default

    def choice(self, name, allowed=None):
        """-> (choice, confidence, probabilities); (None, 0.0, {}) when absent.

        `allowed` is the criteria that were offered. A choice outside them is an
        answer to a question we did not ask, so it is treated as no answer: every
        caller then takes its keyless path rather than acting on a label it has no
        meaning for.
        """
        a = self.answers.get(name)
        if isinstance(a, dict) and a.get("type") == "choice" and isinstance(a.get("choice"), str):
            if allowed is not None and a["choice"] not in allowed:
                return None, 0.0, {}
            try:
                c = float(a.get("confidence", 0.0))
            except (TypeError, ValueError):
                c = 0.0
            probs = a.get("probabilities")
            return a["choice"], c, probs if isinstance(probs, dict) else {}
        return None, 0.0, {}

    def score(self, name):
        """-> (score, confidence, legend); (None, 0.0, {}) when absent."""
        a = self.answers.get(name)
        if isinstance(a, dict) and a.get("type") == "score":
            try:
                s = float(a["score"])
                c = float(a.get("confidence", 0.0))
            except (KeyError, TypeError, ValueError):
                return None, 0.0, {}
            legend = a.get("legend")
            return s, c, legend if isinstance(legend, dict) else {}
        return None, 0.0, {}

    def to_log(self):
        """What goes in .evolve/jev/*.jsonl. The state is NEVER included — that is
        the transcript, and it is not ours to keep."""
        out = {}
        for name, a in self.answers.items():
            if not isinstance(a, dict):
                continue
            if a.get("type") == "noul":
                out[name] = {"noul": a.get("noul")}
            elif a.get("type") == "choice":
                out[name] = {"choice": a.get("choice"), "confidence": a.get("confidence")}
            elif a.get("type") == "score":
                out[name] = {"score": a.get("score"), "confidence": a.get("confidence")}
        return out


# -------------------------------------------------------------------- http --
_warned = set()
_pruned = set()
# A census fans out to MAX_WORKERS threads, all appending to one log file and all
# able to trip the same drift warning. Two locks, so neither can interleave.
_log_lock = threading.Lock()
_warn_lock = threading.Lock()


def validated_model(home=None):
    """The model id jev/RESULTS.md says J0 was measured against, or ''."""
    try:
        with open(os.path.join(home or CORTEX_HOME, "jev", "RESULTS.md"), encoding="utf-8") as fh:
            for _ in range(20):
                line = fh.readline()
                if not line:
                    break
                m = re.search(r"validated-model:\s*(\S+)", line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return ""


def _check_drift(answering):
    """`jev-latest` is a moving alias with the same hazard as a Claude CLI version
    change, and no `blocked_because` to catch it. Warn once per run; never block —
    Jev is advisory everywhere, so a stale calibration degrades a hint, never a
    verdict."""
    want = validated_model()
    if not (want and answering and answering != want):
        return
    with _warn_lock:
        if "drift" in _warned:
            return
        _warned.add("drift")
    sys.stderr.write(f"jev: answering model is {answering}, J0 validated {want} "
                     "— re-run jev/validate.py\n")


class Limiter:
    """Requests per second, shared by every thread of one census. Kept an order of
    magnitude under the published ceiling while Jev is in early access."""

    def __init__(self, rps):
        self.gap = 1.0 / float(max(rps, 1))
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            at = max(now, self.next_at)
            self.next_at = at + self.gap
        delay = at - time.monotonic()
        if delay > 0:
            time.sleep(delay)


def _retry_after(headers, cap):
    try:
        v = headers.get("Retry-After") or headers.get("retry-after")
    except AttributeError:
        return None
    if not v:
        return None
    try:
        s = float(str(v).strip())
    except ValueError:
        return None
    return max(0.0, min(s, cap))


def _post(cfg, body, timeout):
    """-> (status, bytes, headers). Raises only urllib/socket errors."""
    req = urllib.request.Request(
        cfg.base_url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + cfg.key,
                 "Content-Type": "application/json",
                 "Accept": "application/json",
                 "User-Agent": "cortex-jev/1"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as ex:
        try:
            payload = ex.read()
        except Exception:                      # noqa: BLE001 - a body we cannot read is still a status
            payload = b""
        return ex.code, payload, ex.headers


def ask(cfg, state, questions, site="ask", repo=None, meta=None, timeout_s=None, limiter=None):
    """One request, one Answers. Never raises, never blocks past its budget.

    The whole call — every retry and every backoff sleep — returns within
    `timeout_s` (default: the configured one). That is what makes it safe to put
    on a session-end hook.
    """
    repo = repo if repo is not None else cfg.repo
    budget = float(timeout_s if timeout_s else cfg.timeout_s)
    budget = max(0.5, min(budget, float(cfg.timeout_s)))
    if not cfg.enabled:
        return Answers(reason="jev disabled")
    if not cfg.key:
        return Answers(reason="no key")
    if not isinstance(questions, dict) or not questions:
        return Answers(reason="no questions")

    body = {"state": state, "model": cfg.model, "questions": questions}
    deadline = time.monotonic() + budget
    attempts = max(1, int(cfg.retry_attempts))
    backoff = float(cfg.retry_backoff_s)
    started = time.monotonic()
    result = Answers(reason="no attempt made")

    for attempt in range(attempts):
        left = deadline - time.monotonic()
        if left <= 0.05:
            result = Answers(reason="timeout", status=result.status)
            break
        if limiter is not None:
            limiter.wait()
            left = deadline - time.monotonic()
            if left <= 0.05:
                result = Answers(reason="timeout")
                break
        try:
            status, payload, headers = _post(cfg, body, left)
        except Exception as ex:                # noqa: BLE001 - any transport failure is a fallback
            # urllib wraps a CONNECT timeout in URLError, so the exception type
            # alone is not the answer — ask what it wrapped. §3.5 asks the log to
            # tell `timeout` from `fallback`, and a connect timeout filed as a
            # plain fallback is exactly the case you most want to see there.
            name = type(ex).__name__
            inner = getattr(ex, "reason", None)
            timed_out = (isinstance(ex, TimeoutError) or isinstance(inner, TimeoutError)
                         or "timeout" in name.lower() or "timed out" in str(ex).lower())
            result = Answers(reason="timeout" if timed_out else f"unreachable ({name})")
            break

        if status == 200:
            try:
                doc = json.loads(payload.decode("utf-8", "replace"))
                answers = doc["answers"]
                model = str(doc.get("model") or "")
                if not isinstance(answers, dict) or not answers:
                    raise ValueError("no answers")
            except (ValueError, KeyError, TypeError, AttributeError):
                result = Answers(reason="malformed response", status=200)
                break
            usage = doc.get("usage") if isinstance(doc.get("usage"), dict) else {}
            _check_drift(model)
            result = Answers(ok=True, model=model, answers=answers, usage=usage,
                             latency_ms=int((time.monotonic() - started) * 1000), status=200)
            break

        if status in RETRY_STATUS and attempt < attempts - 1:
            wait = _retry_after(headers, max(0.0, deadline - time.monotonic()))
            if wait is None:
                wait = backoff * (2 ** attempt)
            left = max(0.0, deadline - time.monotonic())
            wait = min(wait, cfg.timeout_s, left)
            result = Answers(reason=f"http {status}", status=status)
            if left <= 0.05:
                break                          # out of budget: fall back, do not sleep
            if wait > 0:
                # `Retry-After: 0` is a documented answer and means retry NOW.
                # Treating a zero wait as "give up" would turn the server's
                # friendliest response into the client's harshest.
                time.sleep(wait)
            continue

        # 401 and 422 are our fault, not the network's: one warning, then fall back
        # on the first response. Retrying a bad key only makes the wait longer.
        result = Answers(reason=_explain(status, payload), status=status)
        break

    result.latency_ms = result.latency_ms or int((time.monotonic() - started) * 1000)
    _log(repo, cfg, site, questions, result, meta)
    if not result.ok:
        _warn_once(site, result.reason)
    return result


def _explain(status, payload):
    """A one-line reason, from whichever error shape the endpoint speaks.

    Three are in the wild and all three are this API's:
      TypeSafe native  {"detail": {"error_type": ..., "message": ...}}
      its 422          {"detail": [{"loc": [...], "msg": ...}]}
      AI Gateway       {"error": {"message": ..., "type": ...}}
    The message matters more than the label: a 403 is "you sent no key" on one and
    "your account needs a card on file" on the other, and a reader has to be able
    to tell those apart from one line.
    """
    msg = ""
    try:
        doc = json.loads(payload.decode("utf-8", "replace"))
        detail = doc.get("detail")
        if isinstance(detail, dict):
            msg = str(detail.get("message") or "")
        elif isinstance(detail, list) and detail:
            first = detail[0]
            if isinstance(first, dict):
                msg = f"{'.'.join(str(x) for x in first.get('loc', []))}: {first.get('msg', '')}".strip(": ")
        elif isinstance(doc.get("error"), dict):
            msg = str(doc["error"].get("message") or "")
        elif isinstance(doc.get("message"), str):
            msg = doc["message"]
    except (ValueError, AttributeError, TypeError):
        pass
    label = {401: "invalid key", 403: "refused", 422: "malformed request",
             429: "rate limited", 529: "overloaded"}.get(status, f"http {status}")
    return f"{label}" + (f" — {msg}" if msg else "")


def _warn_once(site, reason):
    """Once per run, not once per request: a census of 2000 failing calls must not
    print 2000 identical lines."""
    tag = f"{site}:{reason}"
    with _warn_lock:
        if tag in _warned:
            return
        _warned.add(tag)
    sys.stderr.write(f"jev: {site}: {reason} — falling back to the deterministic path\n")


# ------------------------------------------------------------------ census --
def estimate_tokens(jobs):
    """Input tokens a census would send. An estimate: the budget check must refuse
    BEFORE the first request, and only the server can count exactly."""
    n = 0
    for j in jobs:
        n += len(json.dumps(j.get("state", ""), default=str))
        n += len(json.dumps(j.get("questions", {}), default=str))
    return int(n / CHARS_PER_TOKEN)


class Census:
    """What a whole fan-out did. `refused` is the budget's answer and is not a
    failure of any single request."""

    def __init__(self):
        self.requests = 0
        self.answered = 0
        self.fell_back = 0
        self.model = ""
        self.input_tokens = 0
        self.output_tokens = 0
        self.refused = ""
        self.reasons = {}

    @property
    def ok(self):
        return not self.refused and self.answered > 0

    def as_dict(self):
        return {"requests": self.requests, "answered": self.answered,
                "fell_back": self.fell_back, "model": self.model,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "refused": self.refused or None,
                "reasons": self.reasons or None}


def budget_refusal(cfg, jobs):
    """'' when the census may start, else the sentence that says why it may not.
    A census that would exceed a ceiling refuses to start rather than silently
    becoming a sample again — which is the failure mode J3 exists to end."""
    n = len(jobs)
    if n > cfg.max_requests_per_cycle:
        return (f"{n} requests exceeds jev.budget.max_requests_per_cycle "
                f"({cfg.max_requests_per_cycle}) — raise it, or narrow what you are asking about")
    mtok = estimate_tokens(jobs) / 1e6
    if mtok > cfg.max_input_mtok_per_cycle:
        return (f"~{mtok:.2f} MTok exceeds jev.budget.max_input_mtok_per_cycle "
                f"({cfg.max_input_mtok_per_cycle}) — raise it, or narrow what you are asking about")
    return ""


def ask_many(cfg, jobs, site="ask", repo=None, timeout_s=None):
    """Fan out one request per job. -> ({job key: Answers}, Census).

    Each job is {"key": <yours>, "state": ..., "questions": {...}, "meta": {...}}.
    Jev ingests one state per request, so N states are N requests; they go out in
    parallel under `max_rps`, which is what makes a census affordable in seconds.
    """
    out, census = {}, Census()
    jobs = list(jobs)
    census.requests = len(jobs)
    if not jobs:
        return out, census
    if not cfg.on:
        census.refused = cfg.off_reason
        census.fell_back = len(jobs)
        for j in jobs:
            out[j.get("key")] = Answers(reason=cfg.off_reason)
        return out, census
    refusal = budget_refusal(cfg, jobs)
    if refusal:
        census.refused = refusal
        census.fell_back = len(jobs)
        for j in jobs:
            out[j.get("key")] = Answers(reason="budget")
        sys.stderr.write(f"jev: {site}: refused to start — {refusal}\n")
        return out, census

    limiter = Limiter(cfg.max_rps)
    workers = max(1, min(len(jobs), cfg.max_rps, MAX_WORKERS))

    def run(job):
        # A worker that raised would abort the whole census through pool.map, so a
        # malformed job degrades to one fallback answer like any other failure.
        key = job.get("key")
        try:
            return key, ask(cfg, job.get("state", ""), job.get("questions", {}), site=site,
                            repo=repo, meta=job.get("meta"), timeout_s=timeout_s,
                            limiter=limiter)
        except Exception as ex:                # noqa: BLE001 - never fail the caller
            return key, Answers(reason=f"client error ({type(ex).__name__})")

    if workers == 1:
        pairs = [run(j) for j in jobs]
    else:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pairs = list(pool.map(run, jobs))

    for key, a in pairs:
        out[key] = a
        if a.ok:
            census.answered += 1
            census.model = census.model or a.model
            census.input_tokens += int(a.usage.get("input_tokens") or 0)
            census.output_tokens += int(a.usage.get("output_tokens") or 0)
        else:
            census.fell_back += 1
            census.reasons[a.reason] = census.reasons.get(a.reason, 0) + 1
    return out, census


# ----------------------------------------------------------------- logging --
def log_dir(repo):
    return os.path.join(repo, ".evolve", "jev")


def _log(repo, cfg, site, questions, result, meta):
    """One line per request. It carries the answers, the probabilities, the model
    that answered and the outcome — and never the state that was sent.

    This log is also how an answer survives a turn boundary: /evolve is a resumable
    state machine whose cycle spans several turns and a background sweep, so an
    answer from A3 that D5 has to journal cannot live in the conversation.
    """
    if not repo or not os.path.isdir(os.path.join(repo, ".evolve")):
        return
    line = {"t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "site": site,
            "questions": sorted(questions) if isinstance(questions, dict) else [],
            "answers": result.to_log(),
            "model": result.model or cfg.model,
            "model_requested": cfg.model,
            "input_tokens": int(result.usage.get("input_tokens") or 0),
            "output_tokens": int(result.usage.get("output_tokens") or 0),
            "latency_ms": result.latency_ms,
            "outcome": "ok" if result.ok else (str(result.status) if result.status in RETRY_STATUS
                                               else ("timeout" if result.reason == "timeout" else "fallback")),
            "reason": "" if result.ok else result.reason}
    if isinstance(meta, dict):
        for k, v in meta.items():
            if k not in line:
                line[k] = v
    d = log_dir(repo)
    blob = json.dumps(line, sort_keys=True) + "\n"
    try:
        with _log_lock:
            os.makedirs(d, exist_ok=True)
            path = os.path.join(d, datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".jsonl")
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(blob)
    except OSError:
        return
    _prune_logs(repo, d)


def _prune_logs(repo, d):
    """Retention: files older than prune.usage_days go on the next write. Once per
    process — this runs inside a fan-out of hundreds of requests."""
    if repo in _pruned:
        return
    _pruned.add(repo)
    try:
        days = int(_config_json(repo).get("prune_usage_days", 30))
    except (TypeError, ValueError):
        days = 30
    cutoff = time.time() - max(1, days) * 86400
    try:
        for f in os.listdir(d):
            p = os.path.join(d, f)
            if f.endswith(".jsonl") and os.path.getmtime(p) < cutoff:
                os.remove(p)
    except OSError:
        pass


def log_summary(repo, cfg, site, meta, model=""):
    """One extra line recording what a whole fan-out CONCLUDED, so D5 can read the
    cycle's own answers back without re-deriving them from hundreds of per-request
    lines. Marked `summary: true` so a reader can tell the two apart."""
    _log(repo, cfg, site, {}, Answers(ok=True, model=model or cfg.model), dict(meta, summary=True))


def read_log(repo, candidate=None, site=None, days=3):
    """Lines this cycle wrote, newest last. D5 reads its own answers back by
    candidate name, the same way `cortex score` finds its results file."""
    d = log_dir(repo)
    rows = []
    if not os.path.isdir(d):
        return rows
    cutoff = time.time() - max(1, days) * 86400
    try:
        files = sorted(f for f in os.listdir(d) if f.endswith(".jsonl"))
    except OSError:
        return rows
    for f in files:
        p = os.path.join(d, f)
        try:
            if os.path.getmtime(p) < cutoff:
                continue
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(r, dict):
                        continue
                    if candidate and r.get("candidate") != candidate:
                        continue
                    if site and r.get("site") != site:
                        continue
                    rows.append(r)
        except OSError:
            continue
    return rows


# -------------------------------------------------------- question library --
# Every question Cortex asks lives here, because docs/JEV.md quotes this section
# and a question that drifts from its documentation is unauditable. Changing the
# wording of one of these invalidates the J0 accuracy recorded next to it.

def q_relevant(subject):
    """J0/J1. The discriminating quantity of the whole integration: is this task
    about the thing the candidate is about? Breadth (what fraction of the suite a
    glob reaches) is free and cannot answer it — 100% breadth appears in both the
    kept and the regression-buried group (plan §1.4)."""
    return {"type": "noul",
            "instructions": {"question": "Is this coding task about the subject below?",
                             "subject": subject},
            "criteria": {
                "true": "The task's own goal involves the subject: an agent doing this task "
                        "would have to read, write or reason about the subject to finish it.",
                "false": "The subject is incidental or absent: an agent could finish this task "
                         "correctly without ever thinking about the subject."}}


def q_would_fire(name, description):
    """J5. Only meaningful for a SKILL: a rule that is visible always fires (100%
    of 410 measured rollouts), so for a rule there is nothing to predict."""
    return {"type": "noul",
            "instructions": {"question": "Would an agent doing this task choose to invoke the "
                                         "skill below, given only its description?",
                             "skill": name,
                             "description": description},
            "criteria": {
                "true": "The description names the task the agent is doing, so the agent would "
                        "open the skill before acting.",
                "false": "The description names a side duty, or something the agent would not "
                         "connect to this task, so it would never be invoked."}}


Q_HARVEST = {
    # J2. The Stop hook's two questions, asked in one request. They replace
    # `git status --porcelain | wc -l`, which cannot tell a fix from a scratch file.
    "fixed": {"type": "noul",
              "instructions": "In this session, did something go from broken to working? "
                              "A failing test went green, a build started passing, a service "
                              "came up, an endpoint started answering.",
              "criteria": {"true": "Something that was demonstrably broken is now demonstrably working.",
                           "false": "Nothing was fixed: exploration, reading, planning, or work "
                                    "still in progress."}},
    "corrected": {"type": "noul",
                  "instructions": "In this session, did the user correct the assistant? "
                                  "For example: \"you forgot...\", \"CI still fails because...\", "
                                  "\"we never do it that way\", or a check they pasted that the "
                                  "assistant had to fix.",
                  "criteria": {"true": "The user told the assistant it was wrong, or supplied a "
                                       "constraint the assistant had missed.",
                               "false": "The user asked questions or gave new instructions, but "
                                        "corrected nothing."}},
}


def q_theme(areas):
    """J3. One Choice per lesson line, over the themes that already exist plus
    `new`. Counting the result in a shell script is what turns
    min_theme_occurrences from a model's recollection into arithmetic."""
    criteria = dict(areas)
    criteria["new"] = "This lesson is about something none of the areas above covers."
    return {"type": "choice",
            "instructions": "Which area is this lesson about?",
            "criteria": criteria}


Q_CORRECTION = {"type": "noul",
                "instructions": "Does this excerpt of a coding session contain the user "
                                "correcting the assistant?",
                "criteria": {"true": "The user tells the assistant it did something wrong, or "
                                     "supplies a constraint it had missed.",
                             "false": "No correction: questions, new instructions, or the "
                                      "assistant working uninterrupted."}}


TIERS = {
    "rule": "A short hard constraint for one area, where the fixes EDIT at least one existing "
            "file in that area. Injected in full when a matching file is read.",
    "gated-skill": "A procedure for an area where the fixes only CREATE new files. Offered when "
                   "a matching file is read or written; the model must then choose it.",
    "always-on-skill": "A moment with no area (\"before reporting done\", \"before committing\"). "
                       "Its description is in context every turn; the model must choose it.",
    "claude-md": "A fact an agent breaks during UNRELATED work. Loaded on every turn — ration it.",
    "permission": "A command the user always approves. Belongs in settings.json, not in a skill.",
    "hook": "Something that must ALWAYS run with no judgement. Belongs in a hook, not in a skill.",
}


def q_tier():
    """J4(b). A wrong pick is killed by the gates, so the verifier is intact — which
    is what makes this a safe site for a judge. Below confidence_floor the answer
    is escalated to Claude instead of acted on."""
    return {"type": "choice",
            "instructions": "Given this recurring problem and the files its fixes touch, which "
                            "layer should the change live in?",
            "criteria": dict(TIERS)}


REMOVABLE_LEVELS = [
    "Removing it would clearly cost something: it carries a constraint the tasks in its "
    "area depend on.",
    "Removing it would probably cost something.",
    "Unclear either way.",
    "Removing it would probably cost nothing: the model appears to do this unprompted.",
    "Removing it would clearly cost nothing: it restates a default, or nothing reaches it.",
]


def q_removable():
    """J6. A sort order only, merged with the existing `cortex usage` hints. The
    sweep still decides every removal — this never deletes anything."""
    return {"type": "score",
            "instructions": "How likely is removing this skill or rule to cost nothing?",
            "criteria": list(REMOVABLE_LEVELS)}


# --------------------------------------------------------------------- cli --
def _repo_arg(argv, default_cwd=True):
    if "--repo" in argv:
        i = argv.index("--repo")
        if i + 1 < len(argv):
            return argv[i + 1]
    if not default_cwd:
        return None
    import subprocess
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def _opt(argv, name, cast=str, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            try:
                return cast(argv[i + 1])
            except (TypeError, ValueError):
                return default
    return default


def cmd_config(argv):
    cfg = resolve(_repo_arg(argv))
    d = cfg.as_dict(with_source=True)
    if "--json" in argv:
        print(json.dumps(d, sort_keys=True))
        return 0
    src = d.pop("source")
    w = max(len(n) for n, *_ in FIELDS) + 4
    print(f"  {'key':<{w}} {'present' if cfg.key else 'absent':<38} {src['key']}")
    for name, *_ in FIELDS:
        print(f"  {'jev.' + name:<{w}} {str(getattr(cfg, name)):<38} {src[name]}")
    return 0


def cmd_status(argv):
    cfg = resolve(_repo_arg(argv))
    if cfg.on:
        print(f"jev      enabled ({cfg.model})")
    else:
        print(f"jev      disabled ({cfg.off_reason})")
    return 0


def cmd_doctor(argv):
    cfg = resolve(_repo_arg(argv))
    out = {"enabled": bool(cfg.enabled), "key_present": bool(cfg.key),
           "key_source": cfg.key_source, "base_url": cfg.base_url,
           "model_requested": cfg.model, "reachable": None, "model": None,
           "rtt_ms": None, "reason": cfg.off_reason,
           "validated_model": validated_model() or None}
    if cfg.on:
        a = ask(cfg, "ok", {"probe": {"type": "noul", "instructions": "Is this word 'ok'?"}},
                site="doctor", repo=None)
        out["reachable"] = bool(a.ok)
        out["model"] = a.model or None
        out["rtt_ms"] = a.latency_ms
        out["reason"] = "" if a.ok else a.reason
    if "--json" in argv:
        print(json.dumps(out, sort_keys=True))
        return 0 if (not cfg.on or out["reachable"]) else 1
    if not cfg.enabled:
        extra = " (a key is present — set JEV_ENABLED=1 in .env to use it)" if cfg.key else ""
        print(f"  {'jev':<10} off — jev.enabled is false{extra}")
        return 0
    if not cfg.key:
        print(f"  {'jev':<10} off — no JEV_API_KEY (see .env.example); Cortex runs fully without one")
        return 0
    if out["reachable"]:
        drift = ""
        if out["validated_model"] and out["model"] != out["validated_model"]:
            drift = f" — J0 validated {out['validated_model']}, re-run jev/validate.py"
        print(f"  {'jev':<10} {cfg.base_url} answered in {out['rtt_ms']} ms as {out['model']}"
              f" (key from {cfg.key_source}){drift}")
        return 0
    print(f"  {'jev':<10} {cfg.base_url} did not answer: {out['reason']} — every Jev step "
          f"falls back to its deterministic path")
    return 1


def cmd_models(argv):
    cfg = resolve(_repo_arg(argv))
    if not cfg.key:
        print("jev: no key", file=sys.stderr)
        return 1
    url = cfg.base_url.rsplit("/", 1)[0] + "/models"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + cfg.key,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_s) as r:
            print(r.read().decode("utf-8", "replace"))
        return 0
    except Exception as ex:                    # noqa: BLE001 - a CLI probe reports, never raises
        print(f"jev: {url}: {ex}", file=sys.stderr)
        return 1


def cmd_ask(argv):
    """The generic entry point the test suite drives against the stub."""
    repo = _repo_arg(argv, default_cwd=False)
    cfg = resolve(repo)
    site = _opt(argv, "--site", str, "ask")
    if site not in CALL_SITES:
        site = "ask"
    sf, qf = _opt(argv, "--state-file"), _opt(argv, "--questions-file")
    try:
        state = open(sf, encoding="utf-8", errors="replace").read() if sf else _opt(argv, "--state", str, "")
        questions = json.load(open(qf, encoding="utf-8")) if qf else json.loads(_opt(argv, "--questions", str, "{}"))
    except (OSError, ValueError) as ex:
        print(f"jev: cannot read the question: {ex}", file=sys.stderr)
        return 2
    a = ask(cfg, state, questions, site=site, repo=repo)
    print(json.dumps({"ok": a.ok, "reason": a.reason, "model": a.model,
                      "answers": a.answers, "usage": a.usage, "latency_ms": a.latency_ms},
                     sort_keys=True))
    return 0


USER_TURNS = 8               # how much of the conversation the hook sends
SYSTEM_BLOCK = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


def _user_text(row):
    """The user's own words in one transcript row. Only the user's: a correction is
    something the USER said, and sending the assistant's output back would multiply
    what leaves this machine for no gain in the answer."""
    if not isinstance(row, dict) or row.get("type") != "user" or row.get("isMeta"):
        return ""
    msg = row.get("message")
    if isinstance(msg, str):
        return msg
    if not isinstance(msg, dict):
        return ""
    c = msg.get("content")
    if isinstance(c, str):
        return c
    out = []
    for b in c if isinstance(c, list) else []:
        if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str):
            out.append(b["text"])
    return "\n".join(out)


def user_turns(transcript, n=USER_TURNS):
    """The last n user turns of a session transcript, oldest first."""
    if not transcript or not os.path.isfile(transcript):
        return []
    turns = []
    try:
        with open(transcript, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                text = SYSTEM_BLOCK.sub("", _user_text(row)).strip()
                if text:
                    turns.append(text[:4000])
    except OSError:
        return []
    return turns[-n:]


def session_state(repo, transcript=None):
    """Exactly what the Stop hook sends, and nothing else: the shape of the working
    tree, and the last few things the USER said. Deliberately small — this runs at
    the end of EVERY session, and docs/JEV.md has to be able to state it in a line.
    """
    import subprocess

    def run(*args):
        try:
            r = subprocess.run(args, cwd=repo, capture_output=True, text=True, timeout=5)
            return r.stdout.strip() if r.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    state = {"git_status": run("git", "status", "--porcelain")[:4000],
             "git_diffstat": run("git", "diff", "--stat", "HEAD")[:4000],
             "recent_commits": run("git", "log", "--oneline", "-5")}
    turns = user_turns(transcript) or ([os.environ["CORTEX_SESSION_TAIL"][:12000]]
                                       if os.environ.get("CORTEX_SESSION_TAIL") else [])
    if turns:
        state["what_the_user_said"] = turns
    return state


def cmd_harvest(argv):
    """J2. -> exit 0 and print the nudge when something is worth capturing, exit 3
    and print nothing when not. The hook treats every other exit as 'fall back'."""
    repo = _repo_arg(argv)
    if not repo:
        return 4
    cfg = resolve(repo)
    if not cfg.on:
        return 4
    timeout = _opt(argv, "--timeout", float, None)
    a = ask(cfg, session_state(repo, _opt(argv, "--transcript")), Q_HARVEST,
            site="harvest", repo=repo, timeout_s=timeout)
    if not a.ok:
        return 4
    fixed, corrected = a.noul("fixed"), a.noul("corrected")
    if fixed is None and corrected is None:
        return 4
    best = max(p for p in (fixed, corrected) if p is not None)
    if "--json" in argv:
        print(json.dumps({"fixed": fixed, "corrected": corrected,
                          "threshold": cfg.harvest_threshold, "nudge": best >= cfg.harvest_threshold},
                         sort_keys=True))
    if best < cfg.harvest_threshold:
        return 3
    which = []
    if fixed is not None and fixed >= cfg.harvest_threshold:
        which.append(f"something was fixed (p={fixed:.2f})")
    if corrected is not None and corrected >= cfg.harvest_threshold:
        which.append(f"you corrected me (p={corrected:.2f})")
    if "--json" not in argv:
        print("cortex: " + " and ".join(which) + " — consider /harvest")
    return 0


def cmd_journal(argv):
    """§3.6. The one optional indented `jev:` detail line a cycle entry gains.

    It must NEVER begin with '## ': `cmd_cycle` guards the journal by counting
    '## ' headings to refuse a cycle whose entry was not written, and a jev: line
    that looked like a heading would let a cycle through that recorded nothing.

    A cycle spans several turns and a background sweep, so the answers come from
    the log, not the conversation: scope lines are tagged with the candidate's
    name; theme and tier are chosen before that name exists, so the newest summary
    of each within `--days` is taken as this cycle's.

    exit 3 = nothing to say. D5 then writes a keyless entry, which is not an error.
    """
    repo = _repo_arg(argv)
    name = _opt(argv, "--candidate")
    days = _opt(argv, "--days", int, 3) or 3
    if not repo or not name:
        print("usage: jev.py journal --candidate <name> [--repo R] [--days N]", file=sys.stderr)
        return 2
    rows = read_log(repo, days=days)
    if not rows:
        return 3
    parts, model, fell_back, saw = [], "", False, False
    newest = {}
    for r in rows:
        if r.get("outcome") != "ok":
            fell_back = True
            continue
        site = r.get("site")
        if site == "scope" and r.get("summary") and r.get("candidate") == name:
            newest["scope"] = r
        elif site in ("themes", "tier") and r.get("summary"):
            newest[site] = r
    for site in ("themes", "tier", "scope"):
        r = newest.get(site)
        if not r:
            continue
        saw = True
        model = model or r.get("model") or ""
        if site == "themes" and r.get("theme"):
            p = r.get("theme_p")
            parts.append(f"theme={r['theme']}" + (f" p={p:.2f}" if isinstance(p, (int, float)) else ""))
        elif site == "tier" and r.get("tier"):
            c = r.get("tier_conf")
            parts.append(f"tier={r['tier']}" + (f" conf={c:.2f}" if isinstance(c, (int, float)) else ""))
        elif site == "scope" and r.get("relevance") is not None:
            parts.append(f"scope {int(round(r['relevance'] * 100))}% "
                         f"({r.get('relevant', '?')}/{r.get('injected', '?')} tasks)")
    if not parts:
        if fell_back or saw:
            print("jev: fallback")
            return 0
        return 3
    line = "jev: " + " \u00b7 ".join(parts)
    if model:
        line += f" \u00b7 model={model}"
    if fell_back:
        line += " \u00b7 some calls fell back"
    print(line)
    return 0


def cmd_tier(argv):
    """J4(b). A Choice over the six layers, gated on confidence_floor.

    A safe site for a judge: a wrong pick is killed by the gates, so the verifier
    is intact. Below the floor the answer is not acted on — it is escalated to
    Claude, which is the same path a low-confidence answer already takes.

    exit 0 = a usable pick · exit 3 = escalate (no answer, or below the floor).
    """
    repo = _repo_arg(argv)
    theme = _opt(argv, "--theme", str, "")
    files = _opt(argv, "--files", str, "")
    if not theme:
        print("usage: jev.py tier --theme \"<what recurs>\" [--files \"a/b.py c/d.py\"] "
              "[--repo R] [--json]", file=sys.stderr)
        return 2
    cfg = resolve(repo)
    if not cfg.on:
        if "--json" in argv:
            print(json.dumps({"ok": False, "reason": cfg.off_reason, "escalate": True}, sort_keys=True))
        return 3
    state = {"recurring_problem": theme[:4000]}
    if files:
        state["files_the_fixes_touch"] = files.split()[:200]
    a = ask(cfg, state, {"tier": q_tier()}, site="tier", repo=repo)
    choice, conf, probs = a.choice("tier", allowed=TIERS)
    ok = bool(choice) and conf >= cfg.confidence_floor
    if choice:
        log_summary(repo, cfg, "tier", {"tier": choice, "tier_conf": conf,
                                        "acted_on": ok, "theme": theme[:200]}, model=a.model)
    if "--json" in argv:
        print(json.dumps({"ok": ok, "tier": choice, "confidence": conf,
                          "floor": cfg.confidence_floor, "probabilities": probs,
                          "escalate": not ok, "reason": "" if a.ok else a.reason}, sort_keys=True))
    elif not a.ok:
        print(f"tier: unavailable ({a.reason}) — decide it from the A4 table, as before")
    elif not choice:
        print("tier: no answer — decide it from the A4 table, as before")
    elif ok:
        print(f"tier: {choice}  (confidence {conf:.2f} >= floor {cfg.confidence_floor})")
        print(f"  runners-up: " + ", ".join(f"{k} {v:.2f}" for k, v in
                                            sorted(probs.items(), key=lambda kv: -kv[1])[1:4]))
        print("  advisory: the gates still decide. If it says `rule`, run `cortex scope` on the")
        print("  draft paths in this same turn — that is the feedback the clock theme never got.")
    else:
        print(f"tier: {choice} at confidence {conf:.2f}, below floor {cfg.confidence_floor}")
        print("  ESCALATED: decide it yourself from the A4 table. A low-confidence pick is")
        print("  not a pick.")
    return 0 if ok else 3


COMMANDS = {"doctor": cmd_doctor, "status": cmd_status, "config": cmd_config,
            "ask": cmd_ask, "harvest": cmd_harvest, "journal": cmd_journal,
            "tier": cmd_tier, "models": cmd_models}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)
    try:
        sys.exit(COMMANDS[sys.argv[1]](sys.argv[2:]))
    except KeyboardInterrupt:
        sys.exit(130)
