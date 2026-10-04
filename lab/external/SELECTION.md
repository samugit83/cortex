# Choosing the second repository

This file states the rule and fixes the **search order**. It was
committed **before any candidate was inspected**, so that "the first repository
meeting every criterion" is a fact about the order rather than about the result.

## The rule

1. Python.
2. Permissively licensed: MIT, BSD or Apache-2.0.
3. Its own test suite runs in under about two minutes, with no network and no
   credentials.
4. At least 200 commits.
5. A convention a newcomer plausibly breaks, visible in its CONTRIBUTING, its
   linter configuration or its review comments.
6. **Not** a repository appearing in SWE-bench, SWE-gym, SWE-smith or Aider's
   benchmark, to limit contamination.

The first repository meeting every criterion is taken. Every rejection is recorded
below with the criterion it failed.

## The search order, fixed now

Chosen for being pure-Python libraries with fast suites and written-down
conventions, and for being absent from the common agent benchmarks. The order is
alphabetical by repository name, so it encodes no preference.

| # | repository | why it is a plausible candidate |
|---|---|---|
| 1 | `agronholm/anyio` | async library, strict typing conventions, fast suite |
| 2 | `hynek/structlog` | MIT, documented conventions, fast pure-Python suite |
| 3 | `jd/tenacity` | Apache-2.0, small, self-contained |
| 4 | `more-itertools/more-itertools` | MIT, pure Python, documented style rules, fast |
| 5 | `python-attrs/attrs` | MIT, strong written conventions, fast suite |
| 6 | `python-jsonschema/jsonschema` | MIT, self-contained, fast |
| 7 | `tox-dev/pyproject-api` | MIT, small, strict linting |

## Rejections and the choice

| # | repository | outcome | evidence |
|---|---|---|---|
| 1 | `agronholm/anyio` | **rejected, criterion 3** | 1,421 commits, MIT, but the suite does not pass without network: `165 failed, 3908 passed, 78 errors in 79.6s` on a clean checkout, the failures being TCP/TLS/IPv6 socket tests. A task suite that is already red cannot tell a good fix from a bad one. |
| 2 | `hynek/structlog` | **TAKEN** | see below |
| 3–7 | `jd/tenacity`, `more-itertools`, `attrs`, `jsonschema`, `pyproject-api` | not reached | the rule takes the first repository that meets every criterion |

## The repository: `hynek/structlog`

| Criterion | Evidence |
|---|---|
| 1 · Python | pure Python, `src/structlog/` |
| 2 · permissive | dual **Apache-2.0 / MIT** (`LICENSE-APACHE`, `LICENSE-MIT`) |
| 3 · fast, offline, no credentials | **`931 passed, 17 skipped in 1.00s`** — one second, no network, no services |
| 4 · history | **1,912 commits** |
| 5 · a convention a newcomer breaks | `[tool.ruff.lint] select = ["ALL"]` — every rule in ruff enabled, with a hand-curated ignore list. A newcomer's first patch trips it almost by construction, and the project's own `ignore` list documents which conventions it holds and which it waives |
| 6 · not benchmark-contaminated | absent from SWE-bench, SWE-gym, SWE-smith and Aider's benchmark |

The one-second suite matters more than it looks: it makes each rollout's check
almost free, so the cost of a rollout here is the agent's time alone, and a
flaky-check failure cannot be confused with a capability failure.
