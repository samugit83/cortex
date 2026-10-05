# What the paper prints, as data

The paper's LaTeX source is kept outside this repository. Everything in it that is a
result is also written here, by the same scripts and in the same run, so a printed value
can be found without building the paper.

[`NUMBERS.csv`](../../../NUMBERS.csv), at the top of the repository, gathers all of it in
one file: one row per value the paper prints, in its text, its tables and its figures,
with the script that computes it. The files below hold the same values in their own
formats.

| In the paper | File here | Written by |
|---|---|---|
| Every number in the running text, the captions and Tables 1 to 4 | `numbers.csv` | `analysis/gen_numbers.py` |
| Table 5, the held-out gain family by family | `table-main.csv` | `analysis/gen_tables.py` |
| Table 6, the gate test by kind of candidate | `table-gates.csv` | `analysis/gen_tables.py` |
| Table 7, every item the loop kept | `table-kept.csv` | `analysis/gen_tables.py` |
| The charts of the results (Section 5 and Appendix A) | `figures-results.json` | `analysis/gen_results_data.py` |
| The diagrams that show the lab's data (Sections 3 to 5) | `figures-diagrams.json` | `analysis/gen_diagram_data.py` |

## numbers.csv

One row per value the paper's text takes from the data: 419 rows. The paper never types a
number; it names one of these rows, so a number in the PDF is always one of them. A few
rows are computed and checked but not printed as digits in the current text: some the
text states in words ("no item was kept" is a row whose value is 0), some it does not use.

| Column | Example | Meaning |
|---|---|---|
| `name` | `HeldEvoB` | the name the paper's source uses for the value |
| `printed` | `79.2%` | the value as the reader sees it |
| `value` | `79.2` | the same as a bare number: no `%`, no `+`, no thousands separator |
| `computed_by` | `lab/reports/analysis/gen_numbers.py:483` | the script and the line that set the value |

The minus sign is written as a hyphen (`-3.3`). `value` is empty for the 20 rows that are
names and not numbers: a run, a model, a version, the second repository.

## The tables and the figures

`table-*.csv` hold the rows of the three tables the scripts write cell by cell. Rates are
whole percentages, as printed; an interval is two columns; a count has no thousands
separator. `figures-*.json` hold the objects the paper's charts and diagrams are drawn from.

## NUMBERS.csv

| Column | Meaning |
|---|---|
| `source` | the file of this folder the row comes from |
| `name` | the value's name: a row of `numbers.csv`, a table cell as `row / column`, or a figure value as its path in the JSON |
| `printed`, `value` | as in `numbers.csv` |
| `computed_by` | the script that computes it, with the line for a row of `numbers.csv` |

## How these files are made

```bash
PY=lab/reports/analysis/.venv/bin/python        # the environment analysis/run.sh makes
$PY lab/reports/analysis/gen_numbers.py          # numbers.csv
$PY lab/reports/analysis/gen_tables.py           # table-*.csv
$PY lab/reports/analysis/gen_diagram_data.py     # figures-diagrams.json
$PY lab/reports/analysis/gen_results_data.py     # figures-results.json
```

Each of the four also rewrites `NUMBERS.csv` from the files that are here.

The scripts read `lab/reports/data/` and `lab/reports/tables/`, and `gen_numbers.py` also
reads the tag `v1.0-eval`, the Cortex every run used. Each script checks what it computes
against the other sources that state the same number, and stops if they disagree. Run them
in a clone of this release and `git status` shows this folder unchanged.
[`../REPRODUCE.md`](../REPRODUCE.md) has the rest.
