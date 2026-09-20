#!/usr/bin/env python3
"""jev-contract.py — L3. Producer and consumer against one shared schema.

127 assertions drive bin/jev.py against test/jev-stub.py. If the stub does not
speak what the real API speaks, all 127 are green against a fiction. This is the
only test that can catch that, and it needs no network: the spec is vendored at
test/jev-openapi.json (TypeSafe 0.2.0, the same document api.typesafe.ai serves
at /openapi.json).

Two directions, both required:

  CONSUMER  every request body bin/jev.py's question library can produce must
            satisfy SystemOneRequest — so a question Cortex asks is one the API
            would accept.
  PRODUCER  every response test/jev-stub.py returns must satisfy
            SystemOneResponse — so the stub cannot drift into answering in a
            shape the real API never sends.

A hand-rolled validator, because the repo is stdlib-only by rule (bin/jev.py's
whole point) and jsonschema is not a dependency. It covers what this spec uses:
required keys, types, oneOf-by-discriminator, enums, const, and additionalProperties
maps. Anything it cannot check it reports rather than passes silently.

    python3 test/jev-contract.py [-v]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "bin"))
import jev                                                       # noqa: E402

SPEC = json.load(open(os.path.join(HERE, "jev-openapi.json"), encoding="utf-8"))
SCHEMAS = SPEC["components"]["schemas"]

PASS, FAIL = 0, 0
VERBOSE = "-v" in sys.argv


def ok(cond, what, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        if VERBOSE:
            print(f"  PASS  {what}")
    else:
        FAIL += 1
        print(f"  FAIL  {what}\n        {detail}")


# ------------------------------------------------------------- validator --
def deref(node):
    while isinstance(node, dict) and "$ref" in node:
        node = SCHEMAS[node["$ref"].rsplit("/", 1)[-1]]
    return node


TYPES = {"string": str, "integer": int, "number": (int, float),
         "boolean": bool, "object": dict, "array": list}


def matches(value, schema, path, errors, depth=0):
    """True when `value` satisfies `schema`. Appends a reason to `errors` if not."""
    schema = deref(schema)
    if depth > 12 or not isinstance(schema, dict):
        return True

    if "oneOf" in schema or "anyOf" in schema:
        branches = schema.get("oneOf") or schema.get("anyOf")
        disc = schema.get("discriminator", {}).get("propertyName")
        if disc and isinstance(value, dict) and value.get(disc) is not None:
            mapping = schema["discriminator"].get("mapping", {})
            ref = mapping.get(str(value[disc]))
            if ref is None:
                errors.append(f"{path}: {disc}={value[disc]!r} is not in the discriminator mapping")
                return False
            return matches(value, {"$ref": ref}, path, errors, depth + 1)
        for b in branches:
            if matches(value, b, path, [], depth + 1):
                return True
        errors.append(f"{path}: matches none of the {len(branches)} alternatives")
        return False

    if "const" in schema:
        if value != schema["const"]:
            errors.append(f"{path}: expected const {schema['const']!r}, got {value!r}")
            return False
        return True

    t = schema.get("type")
    if t and t in TYPES:
        if t == "integer" and isinstance(value, bool):
            errors.append(f"{path}: expected integer, got a bool")
            return False
        if not isinstance(value, TYPES[t]):
            errors.append(f"{path}: expected {t}, got {type(value).__name__}")
            return False

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required key {req!r}")
                return False
        props = schema.get("properties") or {}
        for k, v in value.items():
            if k in props:
                if not matches(v, props[k], f"{path}.{k}", errors, depth + 1):
                    return False
            elif isinstance(schema.get("additionalProperties"), dict):
                if not matches(v, schema["additionalProperties"], f"{path}.{k}", errors, depth + 1):
                    return False
        if schema.get("minProperties") and len(value) < schema["minProperties"]:
            errors.append(f"{path}: needs at least {schema['minProperties']} entries")
            return False

    if isinstance(value, list):
        item = schema.get("items")
        if isinstance(item, dict) and item:
            for i, v in enumerate(value):
                if not matches(v, item, f"{path}[{i}]", errors, depth + 1):
                    return False
        if schema.get("minItems") and len(value) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} items")
            return False
    return True


def check(value, schema_name, what):
    errs = []
    ok(matches(value, {"$ref": f"#/components/schemas/{schema_name}"}, schema_name, errs),
       what, "; ".join(errs[:3]))


# ------------------------------------------------- CONSUMER: our requests --
def request_bodies():
    """One body per question the library can ask, built the way each call site
    builds it — so a question that drifts from the spec is caught here."""
    subject = {"name": "shop clock usage", "description": "read the time through shop.clock",
               "says": "# shop\n- NEVER read the wall clock directly."}
    task_state = {"task": "11", "title": "clock reads wall time",
                  "prompt": "make billing read the time through shop.clock",
                  "notes": "area: use-billing-helpers"}
    yield "scope (relevant only, a rule)", {
        "state": task_state, "model": "jev-latest",
        "questions": {"relevant": jev.q_relevant(subject)}}
    yield "scope (relevant + would_fire, a skill)", {
        "state": task_state, "model": "typesafe-ai/jev",
        "questions": {"relevant": jev.q_relevant(subject),
                      "would_fire": jev.q_would_fire("exporter-setup", "When adding an exporter…")}}
    yield "harvest (the Stop hook's two)", {
        "state": {"git_status": " M src/a.py", "git_diffstat": "1 file changed",
                  "recent_commits": "abc fix", "what_the_user_said": ["you forgot the changelog"]},
        "model": "jev-latest", "questions": dict(jev.Q_HARVEST)}
    crit = {"use-billing-helpers": "the live rule on shop/billing/**: Use the helpers",
            "exporters": "the area 'exporters', named by 3 task(s)"}
    yield "themes (a lesson line)", {
        "state": {"lesson": "read the wall clock directly", "task": "02"},
        "model": "jev-latest", "questions": {"area": jev.q_theme(crit)}}
    yield "themes (a transcript chunk)", {
        "state": {"session_excerpt": "you forgot to run the test"},
        "model": "jev-latest",
        "questions": {"correction": jev.Q_CORRECTION, "area": jev.q_theme(crit)}}
    yield "tier (Choice over the six layers)", {
        "state": {"recurring_problem": "reading the wall clock",
                  "files_the_fixes_touch": ["shop/billing/clock.py"]},
        "model": "jev-latest", "questions": {"tier": jev.q_tier()}}
    yield "prune (Score, 0-4)", {
        "state": {"name": "verify-before-done", "kind": "skill", "tier": "always"},
        "model": "jev-latest", "questions": {"removable": jev.q_removable()}}
    yield "doctor probe", {
        "state": "ok", "model": "jev-latest",
        "questions": {"probe": {"type": "noul", "instructions": "Is this word 'ok'?"}}}


# ------------------------------------------------- PRODUCER: stub answers --
def stub_answer(qtype, question):
    """Call the stub's own answer builder, so this tests the stub, not a copy."""
    sys.path.insert(0, HERE)
    import importlib.util
    spec = importlib.util.spec_from_file_location("jevstub", os.path.join(HERE, "jev-stub.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.answer_for("q", question, {})


def main():
    print("jev contract: bin/jev.py and test/jev-stub.py against "
          f"{SPEC['info']['title']} {SPEC['info']['version']}")
    print("")
    print("CONSUMER — every request the question library can build:")
    for what, body in request_bodies():
        check(body, "SystemOneRequest", what)

    print("")
    print("PRODUCER — every answer shape the stub can return:")
    for qtype, question in (
            ("noul", {"type": "noul", "instructions": "x"}),
            ("choice", {"type": "choice", "instructions": "x", "criteria": {"a": "A", "b": "B"}}),
            ("score", {"type": "score", "instructions": "x", "criteria": ["low", "mid", "high"]})):
        a = stub_answer(qtype, question)
        body = {"model": "jev-1.13.0", "answers": {"q": a},
                "usage": {"input_tokens": 12, "output_tokens": 4}}
        check(body, "SystemOneResponse", f"stub {qtype} answer")

    print("")
    print("CONSUMER — the client reads every answer shape the spec allows:")
    cases = [
        ({"q": {"type": "noul", "noul": 0.98}}, lambda r: r.noul("q") == 0.98, "noul -> probability"),
        ({"q": {"type": "choice", "choice": "a", "confidence": 0.9,
                "probabilities": {"a": 0.9, "b": 0.1}}},
         lambda r: r.choice("q")[0] == "a" and r.choice("q")[1] == 0.9, "choice -> (name, confidence)"),
        ({"q": {"type": "score", "score": 1.7, "confidence": 0.9,
                "legend": {"0": "low"}, "probabilities": {"0": 0.1}}},
         lambda r: r.score("q")[0] == 1.7, "score -> value"),
    ]
    for answers, read, what in cases:
        ok(read(jev.Answers(ok=True, answers=answers)), what)

    # A validator that accepts everything would make every row above meaningless.
    # These must all be REJECTED; if any is accepted, this file is not a test.
    print("")
    print("SELF-CHECK — the validator must reject each of these:")
    bad = [
        ("missing required 'state'", "SystemOneRequest",
         {"model": "m", "questions": {"q": {"type": "noul"}}}),
        ("missing required 'model'", "SystemOneRequest",
         {"state": "s", "questions": {"q": {"type": "noul"}}}),
        ("empty questions map", "SystemOneRequest",
         {"state": "s", "model": "m", "questions": {}}),
        ("unknown question type", "SystemOneRequest",
         {"state": "s", "model": "m", "questions": {"q": {"type": "vibes"}}}),
        ("choice question with no criteria", "SystemOneRequest",
         {"state": "s", "model": "m", "questions": {"q": {"type": "choice", "instructions": "x"}}}),
        ("score criteria not a list", "SystemOneRequest",
         {"state": "s", "model": "m",
          "questions": {"q": {"type": "score", "criteria": {"0": "low"}}}}),
        ("noul answer without a probability", "SystemOneResponse",
         {"model": "m", "answers": {"q": {"type": "noul"}},
          "usage": {"input_tokens": 1, "output_tokens": 1}}),
        ("choice answer without confidence", "SystemOneResponse",
         {"model": "m", "answers": {"q": {"type": "choice", "choice": "a",
                                          "probabilities": {"a": 1.0}}},
          "usage": {"input_tokens": 1, "output_tokens": 1}}),
        ("usage missing output_tokens", "SystemOneResponse",
         {"model": "m", "answers": {"q": {"type": "noul", "noul": 0.5}},
          "usage": {"input_tokens": 1}}),
        ("response with no answers at all", "SystemOneResponse",
         {"model": "m", "answers": {}, "usage": {"input_tokens": 1, "output_tokens": 1}}),
        ("input_tokens as a string", "SystemOneResponse",
         {"model": "m", "answers": {"q": {"type": "noul", "noul": 0.5}},
          "usage": {"input_tokens": "12", "output_tokens": 1}}),
    ]
    for what, schema, value in bad:
        errs = []
        accepted = matches(value, {"$ref": f"#/components/schemas/{schema}"}, schema, errs)
        ok(not accepted, f"rejects: {what}", "VALIDATOR ACCEPTED AN INVALID BODY")

    print("")
    print(f"passed {PASS}   failed {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
