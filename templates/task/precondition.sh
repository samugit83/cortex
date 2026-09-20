#!/usr/bin/env bash
# OPTIONAL. Delete this file if the task needs no running services.
#
# Asserts the ENVIRONMENT is ready — not that the code is correct.
#   exit 0  = ready, run the rollout
#   exit !0 = not ready, mark the rollout INVALID (not failed)
#
# Why this exists: without it, a stack that dies mid-sweep makes every
# remaining rollout fail, and the sweep reads that as "the candidate is
# terrible". An invalid rollout is excluded from the scores instead, and
# enough of them make the whole sweep unscorable rather than wrong.
#
# Rules:
#   - Check readiness, never correctness. That is check.sh's job.
#   - Must finish well inside measurement.check_timeout_s (default 120s).
#   - Runs once per rollout, so keep it fast. Assert, do not build.
#   - Runs from the sandbox root, with environment.rollout_env applied.
set -euo pipefail

# --- example: a database the task needs -------------------------------------
# pg_isready -h localhost -p 5432 -q

# --- example: compose services that must already be running -----------------
# for svc in postgres recon; do
#   docker compose ps --status running --services | grep -qx "$svc" || exit 1
# done

# --- example: an HTTP service answering -------------------------------------
# curl -fsS --max-time 5 http://localhost:8000/health >/dev/null

# --- example: bring it up yourself, then wait (slower, but self-sufficient) --
# docker compose up -d postgres >/dev/null 2>&1
# for _ in $(seq 30); do pg_isready -q && exit 0; sleep 1; done
# exit 1

exit 0
