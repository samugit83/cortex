#!/usr/bin/env python3
"""paper_data.py — what the paper prints, kept as data in the repository.

The paper's sources live outside this repository, so the four scripts that compute what
it prints (gen_numbers.py, gen_tables.py, gen_diagram_data.py, gen_results_data.py) also
write it to lab/reports/paper-data/: numbers.csv, table-*.csv and figures-*.json. Each
of them then rebuilds NUMBERS.csv, at the top of the repository, from those files: one
row per value the paper prints, in its text, its tables and its figures, with the script
that computes it.
"""
import csv
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "paper-data"
MANIFEST = Path(__file__).resolve().parents[3] / "NUMBERS.csv"
HERE = "lab/reports/analysis"
# how many leading columns of each generated table name a row
TABLE_KEYS = {"main": 1, "gates": 2, "kept": 3}
FIGURE_SCRIPT = {"diagrams": "gen_diagram_data.py", "results": "gen_results_data.py"}


class Numbers(dict):
    """The paper's numbers by name. Remembers the line of the script that set each one,
    which NUMBERS.csv gives beside the value."""

    def __init__(self, script):
        super().__init__()
        self.script, self.line = script, {}

    def __setitem__(self, k, v):
        self.line[k] = sys._getframe(1).f_lineno
        super().__setitem__(k, v)


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
    it and as a bare number, with the line that computes it."""
    rows = [(k, plain(v), value(plain(v)), f"{HERE}/{M.script}:{M.line[k]}") for k, v in sorted(M.items())]
    _write("numbers.csv", ("name", "printed", "value", "computed_by"), rows)
    write_manifest()


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
    write_manifest()


def write_figures(name, data):
    """figures-<name>.json: the numbers a set of the paper's figures draws."""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"figures-{name}.json").write_text(json.dumps(data, indent=1) + "\n")
    print(f"-> {OUT / f'figures-{name}.json'}")
    write_manifest()


def _leaves(o, path=""):
    """Every number in a JSON object, with the path that leads to it."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _leaves(v, f"{path}/{k}" if path else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _leaves(v, f"{path}[{i}]")
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield path, o


def write_manifest():
    """NUMBERS.csv, at the top of the repository: every value the paper prints, gathered
    from the files of paper-data/ that exist. `source` names the file a row comes from;
    a table cell is named by its row and its column, a figure value by its path."""
    rows = []
    if (OUT / "numbers.csv").exists():
        for r in csv.DictReader(open(OUT / "numbers.csv", newline="")):
            rows.append(("numbers.csv", r["name"], r["printed"], r["value"], r["computed_by"]))
    for name, keys in TABLE_KEYS.items():
        if not (OUT / f"table-{name}.csv").exists():
            continue
        table = list(csv.reader(open(OUT / f"table-{name}.csv", newline="")))
        for cells in table[1:]:
            for col, cell in list(zip(table[0], cells))[keys:]:
                rows.append((f"table-{name}.csv", f"{' | '.join(cells[:keys])} / {col}", cell, value(cell),
                             f"{HERE}/gen_tables.py"))
    for name, script in FIGURE_SCRIPT.items():
        if not (OUT / f"figures-{name}.json").exists():
            continue
        for path, v in _leaves(json.loads((OUT / f"figures-{name}.json").read_text())):
            rows.append((f"figures-{name}.json", path, repr(v), repr(v), f"{HERE}/{script}"))
    with open(MANIFEST, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(("source", "name", "printed", "value", "computed_by"))
        w.writerows(rows)
    print(f"-> {MANIFEST} ({len(rows)} rows)")
