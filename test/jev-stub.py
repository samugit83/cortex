#!/usr/bin/env python3
"""jev-stub.py — a stub System One server, so no test makes an API call.

run-tests.sh's central design rule is that rollouts are driven by a stub `claude`
whose behaviour each test controls. Jev's six network call sites must not break
that rule, so this is the same idea for the other API: a stdlib http.server that
returns canned TypeSafe responses, driven by environment variables.

  test/jev-stub.py [--port N] [--urlfile F] [--pidfile F]

Prints the base URL on stdout (`http://127.0.0.1:<port>/v1/systemone`), then
serves until killed. Point JEV_BASE_URL at it.

Behaviour, all from the environment, all read per request so a test can change
its mind between calls:

  JEV_STUB_STATUS       status to return (default 200)
  JEV_STUB_FAIL_TIMES   return JEV_STUB_STATUS this many times, then 200
  JEV_STUB_RETRY_AFTER  value of the Retry-After header on a 429/529
  JEV_STUB_MODEL        the model id to answer with (default jev-1.13.0)
  JEV_STUB_NOUL         probability every noul gets (default 0.9)
  JEV_STUB_ANSWERS      JSON: {question name -> probability | answer object}
  JEV_STUB_RULES        path to JSON: [{"match": <substring of the state>,
                                        "answers": {<name>: <p or object>}}]
                        the first rule whose `match` is in the state wins
  JEV_STUB_CHOICE       the choice every choice question returns
  JEV_STUB_CONFIDENCE   confidence for choice/score answers (default 0.9)
  JEV_STUB_SCORE        the score every score question returns (default 2)
  JEV_STUB_BODY         a raw body, returned verbatim (malformed-JSON tests)
  JEV_STUB_DROP         omit these question names from the answers (space separated)
  JEV_STUB_DELAY        seconds to sleep before answering
  JEV_STUB_HANG         never answer at all
  JEV_STUB_LOG          append one line per request here: the test counts them,
                        and an EMPTY file is how "no socket was opened" is asserted
  JEV_STUB_CONTROL      a JSON file whose keys override any of the above, re-read
                        per request — how a test changes a RUNNING stub's mind
  JEV_STUB_LOG_STATE    also record each request's `state` in JEV_STUB_LOG, so a
                        test can assert what did and did not leave the machine

It always requires `Authorization: Bearer <something>`, so the keyless path is
exercised against a server that would have refused anyway.
"""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {"calls": 0}
LOCK = threading.Lock()


CONTROL_CACHE = {"mtime": None, "values": {}}


def control():
    """JEV_STUB_CONTROL names a JSON file whose keys override the environment, read
    fresh per request. A test can therefore change the stub's mind between calls —
    the `claude` stub is rewritten between calls for the same reason, and a server
    cannot be."""
    path = os.environ.get("JEV_STUB_CONTROL")
    if not path:
        return {}
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {}
    if CONTROL_CACHE["mtime"] != mtime:
        try:
            with open(path, encoding="utf-8") as fh:
                CONTROL_CACHE["values"] = json.load(fh) or {}
        except (OSError, ValueError):
            CONTROL_CACHE["values"] = {}
        CONTROL_CACHE["mtime"] = mtime
    return CONTROL_CACHE["values"]


def env(name, default=""):
    v = control().get(name)
    if v is not None:
        return str(v)
    return os.environ.get(name, default)


def envf(name, default):
    try:
        return float(env(name, ""))
    except (TypeError, ValueError):
        return default


def envi(name, default):
    try:
        return int(env(name, ""))
    except (TypeError, ValueError):
        return default


def note(kind, detail=""):
    path = env("JEV_STUB_LOG")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": time.time(), "kind": kind, "detail": detail}) + "\n")
    except OSError:
        pass


def rule_answers(state, questions=None):
    """The first rule whose `match` is in the state (and whose optional
    `match_question` is in the questions) wins. Two keys, because the state says
    WHAT is being judged and the questions say what it is being judged AGAINST —
    and a test of `cortex scope` needs to vary both."""
    path = env("JEV_STUB_RULES")
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            rules = json.load(fh)
    except (OSError, ValueError):
        return None
    blob = json.dumps(state, default=str)
    qblob = json.dumps(questions or {}, default=str)
    for r in rules if isinstance(rules, list) else []:
        if not isinstance(r, dict):
            continue
        if str(r.get("match", "")) not in blob:
            continue
        if r.get("match_question") and str(r["match_question"]) not in qblob:
            continue
        return r.get("answers") or {}
    return None


def as_answer(qtype, raw):
    """A test may give a bare number (the natural thing) or a whole answer object."""
    if isinstance(raw, dict):
        return raw
    if qtype == "noul":
        return {"type": "noul", "noul": float(raw)}
    if qtype == "choice":
        return {"type": "choice", "choice": str(raw), "confidence": envf("JEV_STUB_CONFIDENCE", 0.9),
                "probabilities": {str(raw): 1.0}}
    return {"type": "score", "score": float(raw), "confidence": envf("JEV_STUB_CONFIDENCE", 0.9),
            "legend": {}, "probabilities": {}}


def answer_for(name, question, overrides):
    qtype = (question or {}).get("type", "noul")
    if name in overrides:
        return as_answer(qtype, overrides[name])
    if qtype == "noul":
        return {"type": "noul", "noul": envf("JEV_STUB_NOUL", 0.9)}
    if qtype == "choice":
        criteria = list((question or {}).get("criteria") or {})
        pick = env("JEV_STUB_CHOICE") or (criteria[0] if criteria else "unknown")
        probs = {c: 0.0 for c in criteria}
        if pick in probs:
            probs[pick] = 1.0
        return {"type": "choice", "choice": pick, "confidence": envf("JEV_STUB_CONFIDENCE", 0.9),
                "probabilities": probs or {pick: 1.0}}
    levels = list((question or {}).get("criteria") or [])
    return {"type": "score", "score": envf("JEV_STUB_SCORE", 2.0),
            "confidence": envf("JEV_STUB_CONFIDENCE", 0.9),
            "legend": {str(i): v for i, v in enumerate(levels)},
            "probabilities": {str(i): (1.0 if i == int(envf("JEV_STUB_SCORE", 2.0)) else 0.0)
                              for i in range(len(levels))}}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):                 # keep the test output readable
        pass

    def _send(self, status, body, headers=None):
        blob = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(blob)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(blob)

    def _authed(self):
        auth = self.headers.get("Authorization") or ""
        if not auth.startswith("Bearer ") or not auth[7:].strip():
            note("unauthenticated")
            self._send(401, {"detail": {"error_type": "authentication_error",
                                        "message": "Cannot authenticate with the server."}})
            return False
        return True

    def do_GET(self):
        note("GET", self.path)
        if not self._authed():
            return
        if self.path.rstrip("/").endswith("/models"):
            self._send(200, {"models": [{"name": env("JEV_STUB_MODEL", "jev-1.13.0"),
                                         "description": "stub", "release_date": "2026-09-15"}]})
            return
        self._send(404, {"detail": "not found"})

    def do_POST(self):
        with LOCK:
            STATE["calls"] += 1
            n = STATE["calls"]
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8", "replace"))
        except (ValueError, OSError):
            body = {}
        entry = {"n": n, "model": body.get("model"),
                 "questions": sorted(body.get("questions") or {})}
        if env("JEV_STUB_LOG_STATE"):
            # What actually left the machine. A test that asserts "this text was
            # never sent" cannot do it from the question names alone.
            entry["state"] = body.get("state")
        note("POST", json.dumps(entry, default=str))
        if not self._authed():
            return

        if env("JEV_STUB_HANG"):
            time.sleep(3600)
            return
        delay = envf("JEV_STUB_DELAY", 0.0)
        if delay > 0:
            time.sleep(delay)

        status = envi("JEV_STUB_STATUS", 200)
        fail_times = envi("JEV_STUB_FAIL_TIMES", 0)
        if status != 200 and fail_times and n > fail_times:
            status = 200
        if status != 200:
            headers = {}
            if env("JEV_STUB_RETRY_AFTER"):
                headers["Retry-After"] = env("JEV_STUB_RETRY_AFTER")
            self._send(status, {"detail": {"error_type": "stub", "message": f"stub says {status}"}},
                       headers)
            return

        if env("JEV_STUB_BODY"):
            self._send(200, env("JEV_STUB_BODY").encode("utf-8"))
            return

        questions = body.get("questions") or {}
        overrides = rule_answers(body.get("state"), questions)
        if overrides is None:
            try:
                overrides = json.loads(env("JEV_STUB_ANSWERS", "{}"))
            except ValueError:
                overrides = {}
        dropped = set(env("JEV_STUB_DROP").split())
        answers = {name: answer_for(name, q, overrides)
                   for name, q in questions.items() if name not in dropped}
        blob = json.dumps(body.get("state"), default=str)
        self._send(200, {"model": env("JEV_STUB_MODEL", "jev-1.13.0"),
                         "answers": answers,
                         "usage": {"input_tokens": max(1, len(blob) // 4),
                                   "output_tokens": 4 * max(1, len(answers))}})


def main(argv):
    port = 0
    urlfile = pidfile = None
    i = 0
    while i < len(argv):
        if argv[i] == "--port" and i + 1 < len(argv):
            port = int(argv[i + 1]); i += 2
        elif argv[i] == "--urlfile" and i + 1 < len(argv):
            urlfile = argv[i + 1]; i += 2
        elif argv[i] == "--pidfile" and i + 1 < len(argv):
            pidfile = argv[i + 1]; i += 2
        else:
            print(__doc__.strip(), file=sys.stderr)
            return 2
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    url = f"http://127.0.0.1:{srv.server_address[1]}/v1/systemone"
    if pidfile:
        with open(pidfile, "w") as fh:
            fh.write(str(os.getpid()))
    if urlfile:                                 # written last: its existence means "ready"
        tmp = urlfile + ".tmp"
        with open(tmp, "w") as fh:
            fh.write(url)
        os.replace(tmp, urlfile)
    print(url, flush=True)
    try:
        srv.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
