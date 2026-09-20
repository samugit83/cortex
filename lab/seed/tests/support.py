"""Helpers shared by the tests."""
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
CATALOG = FIXTURES / "catalog.json"
ORDERS = FIXTURES / "orders.json"
CART = FIXTURES / "cart.json"


def run_cli(*args):
    """Run `shop <args>` in-process against the test catalog -> (exit code, stdout, stderr)."""
    from shop.cli import main
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = main(["--catalog", str(CATALOG), *[str(a) for a in args]])
        except SystemExit as ex:
            code = ex.code if isinstance(ex.code, int) else 1
    return code, out.getvalue(), err.getvalue()
