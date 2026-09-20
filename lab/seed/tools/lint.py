#!/usr/bin/env python3
"""House rules the unit tests cannot see. CI runs this as part of `make verify`.

  money      shop/billing/: no float, `/`, round() or Decimal on amounts
  time       shop/: no datetime.now(), date.today(), time.time() outside shop/clock.py
  exporters  every exporter registered, documented and covered by a golden file

Each rule is explained in CONTRIBUTING.md.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def py_files(folder):
    return sorted(p for p in (ROOT / folder).rglob("*.py") if "__pycache__" not in p.parts)


def rel(path):
    return path.relative_to(ROOT).as_posix()


def parse(path, errors):
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as ex:
        errors.append(f"{rel(path)}:{ex.lineno}: syntax error: {ex.msg}")
        return None


def check_money(errors):
    for path in py_files("shop/billing"):
        if path.name == "money.py":            # the one module allowed to do the arithmetic
            continue
        tree = parse(path, errors)
        for node in ast.walk(tree) if tree else []:
            what = None
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                what = f"float literal {node.value!r}"
            elif isinstance(node, (ast.BinOp, ast.AugAssign)) and isinstance(node.op, ast.Div):
                what = "true division `/`"
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id in ("float", "round", "Decimal", "Fraction"):
                what = f"{node.func.id}()"
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ("Decimal", "Fraction"):
                what = f"{node.func.attr}()"
            elif isinstance(node, ast.Import):
                bad = [a.name for a in node.names if a.name.split(".")[0] in ("decimal", "fractions", "math")]
                what = f"import {bad[0]}" if bad else None
            elif isinstance(node, ast.ImportFrom):
                mod = (node.module or "").split(".")[0]
                what = f"from {mod} import" if mod in ("decimal", "fractions", "math") else None
            if what:
                errors.append(f"{rel(path)}:{node.lineno}: money: {what} — amounts are integer cents; "
                              f"use the helpers in shop/billing/rates.py (CONTRIBUTING.md, Money)")


BANNED_TIME = {("datetime", "now"), ("datetime", "utcnow"), ("datetime", "today"),
               ("date", "today"), ("time", "time")}


def check_time(errors):
    for path in py_files("shop"):
        if rel(path) == "shop/clock.py":
            continue
        tree = parse(path, errors)
        for node in ast.walk(tree) if tree else []:
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                base = node.func.value
                owner = base.id if isinstance(base, ast.Name) else getattr(base, "attr", None)
                if (owner, node.func.attr) in BANNED_TIME:
                    errors.append(f"{rel(path)}:{node.lineno}: time: {owner}.{node.func.attr}() — "
                                  f"use shop.clock.now() / clock.today() (CONTRIBUTING.md, Time)")


def check_exporters(errors):
    try:
        from shop.orders import load_orders
        from shop.plugins.registry import EXPORTERS
    except Exception as ex:                    # a broken plugin must not crash the linter
        errors.append(f"shop/plugins/registry.py: exporters: cannot import the registry: {ex}")
        return
    registered = {cls.__module__ for cls in EXPORTERS.values()}
    for path in sorted((ROOT / "shop" / "plugins").glob("*_export.py")):
        if f"shop.plugins.{path.stem}" not in registered:
            errors.append(f"{rel(path)}: exporters: not registered in EXPORTERS, "
                          f"shop/plugins/registry.py (CONTRIBUTING.md, Exporters)")
    doc = (ROOT / "docs" / "exporters.md").read_text(encoding="utf-8")
    documented = {line.split("|")[1].strip() for line in doc.splitlines()
                  if line.startswith("|") and line.count("|") >= 3}
    orders = load_orders(ROOT / "tests" / "fixtures" / "orders.json")
    for name, cls in sorted(EXPORTERS.items()):
        exporter = cls()
        if name not in documented:
            errors.append(f"docs/exporters.md: exporters: no table row for '{name}' (CONTRIBUTING.md, Exporters)")
        golden = ROOT / "tests" / "golden" / f"order.{exporter.extension}"
        if not golden.exists():
            errors.append(f"{rel(golden)}: exporters: no golden file for '{name}' — run `make golden` "
                          f"(CONTRIBUTING.md, Exporters)")
        elif golden.read_text(encoding="utf-8") != exporter.export(orders):
            errors.append(f"{rel(golden)}: exporters: golden file out of date for '{name}' — run `make golden`")


def main():
    errors = []
    check_money(errors)
    check_time(errors)
    check_exporters(errors)
    for e in errors:
        print(e)
    if errors:
        print(f"lint: {len(errors)} problem(s)")
        return 1
    print("lint: ok (money, time, exporters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
