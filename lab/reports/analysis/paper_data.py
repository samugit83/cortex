#!/usr/bin/env python3
"""paper_data.py — what the paper prints, kept as data in lab/reports/paper-data/.

The paper's sources live outside this repository, so the four scripts that compute what
it prints (gen_numbers.py, gen_tables.py, gen_diagram_data.py, gen_results_data.py) also
write it here: numbers.csv, table-*.csv and figures-*.json. A reader who wonders where a
printed value comes from finds it in one of these files, and the script that wrote it
beside this one.
"""
import csv
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "paper-data"


def plain(s):
    """A LaTeX value as plain text: '6{,}906' -> '6,906', '79.2\\%' -> '79.2%'. The minus
    sign is written as a hyphen, so that a search for -3.3 finds it."""
    s = s.replace(r"\textminus{}", "-").replace("{,}", ",").replace(r"\%", "%").replace(r"\_", "_")
    return re.sub(r"\\(?:cmd|textbf)\{([^{}]*)\}", r"\1", s).strip()


def value(printed):
    """The printed text as a bare number, or '' when it is not one:
    '6,906' -> '6906', '+55.0' -> '55.0', '= 0.0001' -> '0.0001', '79.2%' -> '79.2'."""
    t = re.sub(r"^[=<>]\s*", "", printed).replace(",", "").rstrip("%").lstrip("+")
    return t if re.fullmatch(r"-?\d+(?:\.\d+)?", t) else ""


def _write(name, header, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"-> {OUT / name}")


def write_numbers(M):
    """numbers.csv: one row per macro of paper/generated/numbers.tex, as the paper prints
    it and as a bare number."""
    rows = [(k, plain(v), value(plain(v))) for k, v in sorted(M.items())]
    _write("numbers.csv", ("name", "printed", "value"), rows)


def write_table(name, header, tex_rows):
    """table-<name>.csv: the rows gen_tables.py wrote as LaTeX, cell for cell. An interval
    '[lo, hi]' becomes two cells, and a count loses its thousands separator."""
    rows = []
    for r in tex_rows:
        if "&" not in r:                       # a rule, or the space between two groups
            continue
        cells = []
        for c in r.strip().removesuffix("\\\\").split(" & "):
            c = plain(c)
            m = re.fullmatch(r"\[(\S+), (\S+)\]", c)
            cells += [m.group(1), m.group(2)] if m else [c.replace(",", "") if re.fullmatch(r"[\d,]+", c) else c]
        if len(cells) != len(header):
            raise SystemExit(f"paper_data.py: table {name!r} has a row of {len(cells)} cells, "
                             f"its header has {len(header)}")
        rows.append(cells)
    _write(f"table-{name}.csv", header, rows)


def write_figures(name, data):
    """figures-<name>.json: the numbers a set of the paper's figures draws."""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"figures-{name}.json").write_text(json.dumps(data, indent=1) + "\n")
    print(f"-> {OUT / f'figures-{name}.json'}")
