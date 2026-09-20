#!/usr/bin/env bash
# MUST exit 0 when solved, non-zero when not. Nothing else matters.
#
# BE SPECIFIC. This is the single most common way to ruin a task:
#   BAD :  pytest -q                       (passes trivially, measures nothing)
#   GOOD:  pytest tests/test_broker.py::test_t2_allowed -q
#
# It must run from the repo root and depend on nothing you did not record.
set -euo pipefail
pytest path/to/test_file.py::test_name -q
