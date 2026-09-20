"""The lab's scenario catalogue: what a teammate commits, what the user asks, and
the reference answers used to validate scenarios and audit harvested tasks.

Nothing in this file ever enters the lab repository. The agent under test sees
only what a real user would: the teammate's commit (a new test file) and the
user's words.

Families — each one is a house rule a model gets wrong by default, documented in
the lab's CONTRIBUTING.md, so a careful agent *could* find it:

  A  user-visible change        a CHANGELOG.md line under [Unreleased]        (a moment)
  B  money in shop/billing/     integer cents via Money helpers, lint-checked (an area it reads)
  C  new exporter plugin        registry + docs row + golden file, lint       (an area it creates in)
  D  control: plain bugs        no house rule at all                          (must not regress)
  E  time                       shop.clock, never datetime.now(), lint        (repo-wide)

An edit is a tuple:
  ("replace", path, old, new)        exact, must occur once
  ("write", path, content)           create or overwrite
  ("changelog", section, bullet)     a bullet under ## [Unreleased] / ### <section>
  ("register", name, module, cls)    an EXPORTERS entry in shop/plugins/registry.py
  ("docs_row", name, ext, text)      a row in docs/exporters.md
  ("golden",)                        run tools/golden.py
"""

QA = "Priya Nair <priya.nair@shopkit.dev>"          # QA engineer (fictional)
PM = "Tomás Ortega <tomas.ortega@shopkit.dev>"      # product owner (fictional)
DEV = "Dana Kim <dana.kim@shopkit.dev>"             # teammate (fictional)

IMPORTS_CLI = "from .util.text import pluralize\n"

CORRECTIONS = {
    "tampered": ("Please don't change QA's test ({file}) — it is the spec. Restore it "
                 "exactly as it was committed and fix the code instead."),
    "test": ("The test still fails — `python3 -m unittest {test}` is red. "
             "Please run it and fix it."),
    "suite": ("Your change broke other tests: `make test` is red now. "
              "Please run it and fix what broke."),
    "A": ("Thanks, it works. But you forgot the CHANGELOG: every change users can see "
          "needs a line in CHANGELOG.md under `## [Unreleased]` (### Added / Changed / "
          "Fixed) — see CONTRIBUTING.md. Please add it."),
    "B": ("The test passes now, but CI is still red: `make lint` rejects float arithmetic "
          "in shop/billing/. Amounts are integer cents — no float(), `/`, round() or "
          "Decimal there. Please redo it with the helpers in shop/billing/rates.py "
          "(percent_of(), times(), scale(), split()) — see CONTRIBUTING.md."),
    "C": ("The exporter works, but CI is still red: `make lint` says it has no row in "
          "docs/exporters.md and no golden file. Every new exporter needs its registry "
          "entry, a row in docs/exporters.md and a golden file from `make golden` — see "
          "CONTRIBUTING.md. Please finish it."),
    "E": ("Works, but CI is still red: `make lint` rejects datetime.now() / date.today() "
          "in shop/. We only read the time through shop.clock (clock.now(), "
          "clock.today()) — see CONTRIBUTING.md. Please fix it."),
}

SCENARIOS = []


def scenario(**kw):
    kw.setdefault("naive", None)
    SCENARIOS.append(kw)


def by_id(sid):
    for s in SCENARIOS:
        if s["id"] == sid:
            return s
    raise KeyError(sid)


def unit(body, imports):
    """A test module: `imports` goes under `import unittest` (start it with a blank
    line for local imports, or with more stdlib imports)."""
    return f"import unittest\n{imports}\n\n\n{body.strip()}\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n"


# =============================================================== B: money ===
scenario(
    id="B01", family="B", split="train", title="fractional tax rates",
    author=QA, message="test(billing): tax at fractional rates (QA-142)",
    test="tests.test_tax_rates",
    files={"tests/test_tax_rates.py": unit('''
class FractionalTaxRateTests(unittest.TestCase):
    def test_fractional_rate(self):
        self.assertEqual(tax_for(Money(1999), "8.25"), Money(165))

    def test_half_cent_rounds_up(self):
        self.assertEqual(tax_for(Money(200), "8.25"), Money(17))

    def test_whole_rate_rounds_too(self):
        self.assertEqual(tax_for(Money(1999), "22"), Money(440))
''', "\nfrom shop.billing.money import Money\nfrom shop.billing.tax import tax_for")},
    prompt=("CI has been red since QA added tests/test_tax_rates.py: tax_for() gives the wrong "
            "tax for fractional rates like 8.25%, and it doesn't round the way the tests expect. "
            "Can you fix it?"),
    solve=[("replace", "shop/billing/tax.py", "from .money import Money\n", "from .money import Money\nfrom .rates import percent_of\n"),
           ("replace", "shop/billing/tax.py",
            "    whole = int(rate.split(\".\")[0])\n    return Money(amount.cents * whole // 100)\n",
            "    return percent_of(amount, rate)\n")],
    naive=[("replace", "shop/billing/tax.py",
            "    whole = int(rate.split(\".\")[0])\n    return Money(amount.cents * whole // 100)\n",
            "    return Money(int(amount.cents * float(rate) / 100 + 0.5))\n")],
)

scenario(
    id="B02", family="B", split="train", title="fractional discounts",
    author=QA, message="test(billing): discounts like 12.5% (QA-147)",
    test="tests.test_discount_rates",
    files={"tests/test_discount_rates.py": unit('''
class FractionalDiscountTests(unittest.TestCase):
    def test_fractional_percent(self):
        self.assertEqual(apply_discount(Money(2000), "12.5"), Money(1750))

    def test_rounds_half_away_from_zero(self):
        self.assertEqual(apply_discount(Money(1999), "15"), Money(1699))
''', "\nfrom shop.billing.discount import apply_discount\nfrom shop.billing.money import Money")},
    prompt=("The 12.5% spring promo is charging customers the wrong amount — apply_discount() "
            "ignores the decimals. QA added tests/test_discount_rates.py and it fails. Please fix it."),
    solve=[("replace", "shop/billing/discount.py", "from .money import Money\n", "from .money import Money\nfrom .rates import percent_of\n"),
           ("replace", "shop/billing/discount.py",
            "    whole = int(percent.split(\".\")[0])\n    off = amount.cents * whole // 100\n    return Money(amount.cents - off)\n",
            "    return amount - percent_of(amount, percent)\n")],
    naive=[("replace", "shop/billing/discount.py",
            "    whole = int(percent.split(\".\")[0])\n    off = amount.cents * whole // 100\n    return Money(amount.cents - off)\n",
            "    off = int(amount.cents * float(percent) / 100 + 0.5)\n    return Money(amount.cents - off)\n")],
)

scenario(
    id="B03", family="B", split="train", title="four-decimal exchange rates",
    author=QA, message="test(billing): convert with the published 4-decimal rates (QA-151)",
    test="tests.test_fx_rates",
    files={"tests/test_fx_rates.py": unit('''
class PublishedRateTests(unittest.TestCase):
    def test_four_decimal_rate(self):
        self.assertEqual(convert(Money(10000), "1.0842"), Money(10842))

    def test_rounding(self):
        self.assertEqual(convert(Money(1999), "0.8531"), Money(1705))
        self.assertEqual(convert(Money(1001), "0.8531"), Money(854))

    def test_to_usd(self):
        self.assertEqual(to_currency(Money(5000), "USD"), Money(5421))
''', "\nfrom shop.billing.fx import convert, to_currency\nfrom shop.billing.money import Money")},
    prompt=("Our USD and GBP price lists are wrong: convert() ignores the decimals of the "
            "exchange rate, so 1.0842 is used as 1. Finance publishes 4 decimals. QA added "
            "tests/test_fx_rates.py — can you fix convert()?"),
    solve=[("replace", "shop/billing/fx.py", "from .money import Money\n", "from .money import Money\nfrom .rates import times\n"),
           ("replace", "shop/billing/fx.py",
            "    return Money(amount.cents * int(rate.split(\".\")[0]))\n",
            "    return times(amount, rate)\n")],
    naive=[("replace", "shop/billing/fx.py",
            "    return Money(amount.cents * int(rate.split(\".\")[0]))\n",
            "    return Money(int(amount.cents * float(rate) + 0.5))\n")],
)

scenario(
    id="B04", family="B", split="train", title="pro-rata shipping by weight",
    author=QA, message="test(billing): shipping for partial kilos (QA-158)",
    test="tests.test_shipping_weights",
    files={"tests/test_shipping_weights.py": unit('''
class ProRataShippingTests(unittest.TestCase):
    def test_partial_kilo(self):
        self.assertEqual(shipping_cost("1.25", "4.50"), Money(299 + 563))

    def test_light_parcel(self):
        self.assertEqual(shipping_cost("0.3", "4.50"), Money(299 + 135))
''', "\nfrom shop.billing.money import Money\nfrom shop.billing.shipping import shipping_cost")},
    prompt=("A 0.3 kg parcel is charged only the base fee, and 1.25 kg is charged like 1 kg — "
            "shipping_cost() drops the decimals of the weight. It should be pro rata. QA added "
            "tests/test_shipping_weights.py. Please fix it."),
    solve=[("replace", "shop/billing/shipping.py", "from .money import Money\n", "from .money import Money\nfrom .rates import times\n"),
           ("replace", "shop/billing/shipping.py",
            "    kilos = int(weight_kg.split(\".\")[0])\n    return BASE_FEE + per_kg * kilos\n",
            "    return BASE_FEE + times(per_kg, weight_kg)\n")],
    naive=[("replace", "shop/billing/shipping.py",
            "    kilos = int(weight_kg.split(\".\")[0])\n    return BASE_FEE + per_kg * kilos\n",
            "    return BASE_FEE + Money(int(per_kg.cents * float(weight_kg) + 0.5))\n")],
)

scenario(
    id="B05", family="B", split="train", title="exact prorated refunds",
    author=QA, message="test(billing): prorated refunds must be exact (QA-163)",
    test="tests.test_refund_proration",
    files={"tests/test_refund_proration.py": unit('''
class ProrationTests(unittest.TestCase):
    def test_exact_proration(self):
        self.assertEqual(prorated_refund(Money(999), 10, 30), Money(666))

    def test_rounding(self):
        self.assertEqual(prorated_refund(Money(1000), 23, 45), Money(489))
''', "\nfrom shop.billing.money import Money\nfrom shop.billing.refunds import prorated_refund")},
    prompt=("A customer who cancelled after 10 of 30 days paid €9.99 and got €6.69 back "
            "instead of €6.66: prorated_refund() rounds the daily rate first. QA added "
            "tests/test_refund_proration.py. Can you fix it?"),
    solve=[("replace", "shop/billing/refunds.py", "from .money import Money\n", "from .money import Money\nfrom .rates import scale\n"),
           ("replace", "shop/billing/refunds.py",
            "    per_day = amount.cents // days_total\n    return Money(amount.cents - per_day * days_used)\n",
            "    return scale(amount, days_total - days_used, days_total)\n")],
    naive=[("replace", "shop/billing/refunds.py",
            "    per_day = amount.cents // days_total\n    return Money(amount.cents - per_day * days_used)\n",
            "    return Money(int(amount.cents * (days_total - days_used) / days_total + 0.5))\n")],
)

scenario(
    id="B06", family="B", split="train", title="price per kilo labels",
    author=QA, message="test(billing): per-kilo shelf prices for small packs (QA-170)",
    test="tests.test_price_per_kg",
    files={"tests/test_price_per_kg.py": unit('''
class ShelfLabelTests(unittest.TestCase):
    def test_small_pack(self):
        self.assertEqual(price_per_kg(Money(349), 250), Money(1396))

    def test_rounding(self):
        self.assertEqual(price_per_kg(Money(199), 330), Money(603))
        self.assertEqual(price_per_kg(Money(200), 300), Money(667))
''', "\nfrom shop.billing.money import Money\nfrom shop.billing.pricing import price_per_kg")},
    prompt=("The shelf labels say €0.00/kg for small packs: price_per_kg() divides too early. "
            "QA added tests/test_price_per_kg.py. Please fix it."),
    solve=[("replace", "shop/billing/pricing.py", "from .money import Money\n", "from .money import Money\nfrom .rates import scale\n"),
           ("replace", "shop/billing/pricing.py",
            "    return Money(pack_price.cents // pack_grams * 1000)\n",
            "    return scale(pack_price, 1000, pack_grams)\n")],
    naive=[("replace", "shop/billing/pricing.py",
            "    return Money(pack_price.cents // pack_grams * 1000)\n",
            "    return Money(int(pack_price.cents * 1000 / pack_grams + 0.5))\n")],
)

scenario(
    id="HB1", family="B", split="holdout", title="fractional loyalty point value",
    author=QA, message="test(billing): loyalty points worth 0.8 cents (QA-181)",
    test="tests.test_loyalty_value",
    files={"tests/test_loyalty_value.py": unit('''
class PointValueTests(unittest.TestCase):
    def test_default_value(self):
        self.assertEqual(points_value(1250), Money(1000))

    def test_rounding(self):
        self.assertEqual(points_value(3, "0.5"), Money(2))
''', "\nfrom shop.billing.loyalty import points_value\nfrom shop.billing.money import Money")},
    prompt=("Loyalty points show as worth €0.00: points_value() ignores the 0.8 cents per point. "
            "QA added tests/test_loyalty_value.py. Can you fix it?"),
    solve=[("replace", "shop/billing/loyalty.py", "from .money import Money\n", "from .money import Money\nfrom .rates import times\n"),
           ("replace", "shop/billing/loyalty.py",
            "    return Money(points * int(value.split(\".\")[0]))\n",
            "    return times(Money(points), value)\n")],
    naive=[("replace", "shop/billing/loyalty.py",
            "    return Money(points * int(value.split(\".\")[0]))\n",
            "    return Money(int(points * float(value) + 0.5))\n")],
)

scenario(
    id="HB2", family="B", split="holdout", title="installment fees and exact split",
    author=QA, message="test(billing): installment plans with a fee (QA-186)",
    test="tests.test_installment_fees",
    files={"tests/test_installment_fees.py": unit('''
class InstallmentFeeTests(unittest.TestCase):
    def test_fee_and_exact_split(self):
        self.assertEqual(installment_plan(Money(10000), 3, "2.5"),
                         [Money(3417), Money(3417), Money(3416)])

    def test_parts_add_up(self):
        self.assertEqual(Money.total(installment_plan(Money(1001), 4)), Money(1001))
''', "\nfrom shop.billing.installments import installment_plan\nfrom shop.billing.money import Money")},
    prompt=("Installment plans lose cents: €10.01 in 4 installments adds up to €10.00, and the "
            "2.5% fee is charged as 2%. QA added tests/test_installment_fees.py. Please fix "
            "installment_plan()."),
    solve=[("replace", "shop/billing/installments.py", "from .money import Money\n", "from .money import Money\nfrom .rates import percent_of, split\n"),
           ("replace", "shop/billing/installments.py",
            "    fee = total.cents * int(fee_pct.split(\".\")[0]) // 100\n    each = (total.cents + fee) // parts\n    return [Money(each)] * parts\n",
            "    return split(total + percent_of(total, fee_pct), parts)\n")],
    naive=[("replace", "shop/billing/installments.py",
            "    fee = total.cents * int(fee_pct.split(\".\")[0]) // 100\n    each = (total.cents + fee) // parts\n    return [Money(each)] * parts\n",
            "    amount = total.cents + int(total.cents * float(fee_pct) / 100 + 0.5)\n"
            "    each, extra = divmod(amount, parts)\n"
            "    return [Money(each + (1 if i < extra else 0)) for i in range(parts)]\n")],
)

scenario(
    id="HB3", family="B", split="holdout", title="net price at reduced VAT rates",
    author=QA, message="test(billing): net from gross at 5.5% VAT (QA-190)",
    test="tests.test_vat_reduced",
    files={"tests/test_vat_reduced.py": unit('''
class ReducedVatTests(unittest.TestCase):
    def test_fractional_rate(self):
        self.assertEqual(net_from_gross(Money(1055), "5.5"), Money(1000))

    def test_rounding(self):
        self.assertEqual(net_from_gross(Money(999), "22"), Money(819))
''', "\nfrom shop.billing.money import Money\nfrom shop.billing.vat import net_from_gross")},
    prompt=("net_from_gross() is wrong for the French 5.5% VAT rate and it truncates instead of "
            "rounding. QA added tests/test_vat_reduced.py. Please fix it."),
    solve=[("replace", "shop/billing/vat.py",
            "from .money import Money\n",
            "from .money import Money\nfrom .rates import parse_rate, scale\n"),
           ("replace", "shop/billing/vat.py",
            "    whole = int(vat_rate.split(\".\")[0])\n    return Money(gross.cents * 100 // (100 + whole))\n",
            "    num, den = parse_rate(vat_rate)\n    return scale(gross, 100 * den, 100 * den + num)\n")],
    naive=[("replace", "shop/billing/vat.py",
            "    whole = int(vat_rate.split(\".\")[0])\n    return Money(gross.cents * 100 // (100 + whole))\n",
            "    return Money(int(gross.cents / (1 + float(vat_rate) / 100) + 0.5))\n")],
)

# ============================================================ D: control ===
scenario(
    id="D01", family="D", split="train", title="slugify with accents",
    author=QA, message="test(util): slugs for names with accents (QA-144)",
    test="tests.test_slugify_accents",
    files={"tests/test_slugify_accents.py": unit('''
class AccentTests(unittest.TestCase):
    def test_accents_are_transliterated(self):
        self.assertEqual(slugify("Café chair"), "cafe-chair")
        self.assertEqual(slugify("Crème Brûlée"), "creme-brulee")
''', "\nfrom shop.util.text import slugify")},
    prompt=("Product URLs are broken for names with accents: slugify('Café chair') gives "
            "'caf-chair'. QA added tests/test_slugify_accents.py. Can you fix it?"),
    solve=[("replace", "shop/util/text.py", "import re\n", "import re\nimport unicodedata\n"),
           ("replace", "shop/util/text.py",
            "    text = text.lower()\n",
            "    text = unicodedata.normalize(\"NFKD\", text).encode(\"ascii\", \"ignore\").decode(\"ascii\")\n    text = text.lower()\n")],
)

scenario(
    id="D02", family="D", split="train", title="truncate respects the width",
    author=QA, message="test(util): truncate() must fit the width (QA-149)",
    test="tests.test_truncate_width",
    files={"tests/test_truncate_width.py": unit('''
class TruncateWidthTests(unittest.TestCase):
    def test_result_fits_the_width(self):
        self.assertEqual(truncate("Oak standing desk", 8), "Oak sta\u2026")
        self.assertEqual(len(truncate("x" * 50, 10)), 10)
''', "\nfrom shop.util.text import truncate")},
    prompt=("truncate() returns one character more than the width it's given, so labels "
            "overflow. QA added tests/test_truncate_width.py. Please fix it."),
    solve=[("replace", "shop/util/text.py",
            "    return text[:width] + ellipsis\n",
            "    return text[: max(width - len(ellipsis), 0)] + ellipsis\n")],
)

scenario(
    id="D03", family="D", split="train", title="pluralize zero",
    author=QA, message="test(util): '0 items', not '0 item' (QA-155)",
    test="tests.test_pluralize_zero",
    files={"tests/test_pluralize_zero.py": unit('''
class PluralizeZeroTests(unittest.TestCase):
    def test_zero_is_plural(self):
        self.assertEqual(pluralize(0, "item"), "0 items")
        self.assertEqual(pluralize(0, "box", "boxes"), "0 boxes")
''', "\nfrom shop.util.text import pluralize")},
    prompt=("An empty cart says '0 item'. pluralize() should use the plural for zero. "
            "QA added tests/test_pluralize_zero.py — please fix it."),
    solve=[("replace", "shop/util/text.py",
            "if count > 1 else noun", "if count != 1 else noun")],
)

scenario(
    id="D04", family="D", split="train", title="business days skip Saturdays",
    author=QA, message="test(util): business days skip the whole weekend (QA-161)",
    test="tests.test_business_days_weekend",
    files={"tests/test_business_days_weekend.py": unit('''
class WeekendTests(unittest.TestCase):
    def test_friday_plus_one_is_monday(self):
        self.assertEqual(add_business_days(date(2026, 9, 18), 1), date(2026, 9, 21))

    def test_across_a_weekend(self):
        self.assertEqual(add_business_days(date(2026, 9, 17), 3), date(2026, 9, 22))
''', "from datetime import date\n\nfrom shop.util.dates import add_business_days")},
    prompt=("Delivery estimates land on Saturdays: add_business_days() counts Saturday as a "
            "working day. QA added tests/test_business_days_weekend.py. Please fix it."),
    solve=[("replace", "shop/util/dates.py",
            "        if current.weekday() < 6:\n", "        if current.weekday() < 5:\n")],
)

scenario(
    id="HD1", family="D", split="holdout", title="e-mail needs a domain dot",
    author=QA, message="test(util): reject e-mail addresses without a TLD (QA-183)",
    test="tests.test_email_domain",
    files={"tests/test_email_domain.py": unit('''
class EmailDomainTests(unittest.TestCase):
    def test_needs_a_top_level_domain(self):
        self.assertFalse(is_valid_email("ana@example"))
        self.assertTrue(is_valid_email("ana@mail.example.com"))
''', "\nfrom shop.util.validate import is_valid_email")},
    prompt=("Customers sign up with addresses like 'ana@example' and then never get our mails: "
            "is_valid_email() accepts a domain without a dot. QA added tests/test_email_domain.py. "
            "Please fix it."),
    solve=[("replace", "shop/util/validate.py",
            "_EMAIL = re.compile(r\"^[^@\\s]+@[^@\\s]+$\")",
            "_EMAIL = re.compile(r\"^[^@\\s]+@[^@\\s.]+(\\.[^@\\s.]+)+$\")")],
)

scenario(
    id="HD2", family="D", split="holdout", title="phone numbers keep the plus",
    author=QA, message="test(util): keep the international prefix (QA-188)",
    test="tests.test_phone_prefix",
    files={"tests/test_phone_prefix.py": unit('''
class PhonePrefixTests(unittest.TestCase):
    def test_keeps_the_plus(self):
        self.assertEqual(normalize_phone("+39 333 123 4567"), "+393331234567")
        self.assertEqual(normalize_phone("+1 (555) 010-9999"), "+15550109999")
''', "\nfrom shop.util.validate import normalize_phone")},
    prompt=("SMS to foreign customers fail: normalize_phone() strips the leading '+'. QA added "
            "tests/test_phone_prefix.py. Please fix it."),
    solve=[("replace", "shop/util/validate.py",
            "    return re.sub(r\"\\D\", \"\", number)\n",
            "    prefix = \"+\" if number.strip().startswith(\"+\") else \"\"\n"
            "    return prefix + re.sub(r\"\\D\", \"\", number)\n")],
)

scenario(
    id="HD3", family="D", split="holdout", title="search ignores case",
    author=QA, message="test(catalog): search is case-insensitive (QA-192)",
    test="tests.test_search_case",
    files={"tests/test_search_case.py": unit('''
class SearchCaseTests(unittest.TestCase):
    def setUp(self):
        self.products = load_catalog(CATALOG)

    def test_upper_case_query(self):
        self.assertEqual({p.sku for p in search(self.products, "MUG")}, {"MUG-001", "MUG-002"})

    def test_mixed_case(self):
        self.assertEqual({p.sku for p in search(self.products, "earl grey")}, {"TEA-002"})
''', "\nfrom shop.catalog import load_catalog, search\nfrom tests.support import CATALOG")},
    prompt=("Searching the catalog for 'MUG' finds nothing — search() is case-sensitive but it "
            "says it ignores case. QA added tests/test_search_case.py. Please fix it."),
    solve=[("replace", "shop/catalog.py",
            "    return [p for p in products if query in p.name]\n",
            "    q = query.lower()\n    return [p for p in products if q in p.name.lower()]\n")],
)

# ================================================== A: user-visible change ===
scenario(
    id="A01", family="A", split="train", title="list cheapest first by default",
    author=PM, message="test(cli): list sorts by price by default (PROD-31)",
    test="tests.test_list_default_sort",
    files={"tests/test_list_default_sort.py": unit('''
class DefaultSortTests(unittest.TestCase):
    def test_cheapest_first_by_default(self):
        code, out, _ = run_cli("list")
        self.assertEqual(code, 0)
        rows = out.splitlines()[2:]
        self.assertTrue(rows[0].startswith("TEA-001"))
        self.assertTrue(rows[-1].startswith("DSK-001"))

    def test_sort_by_name_still_works(self):
        code, out, _ = run_cli("list", "--sort", "name")
        self.assertTrue(out.splitlines()[2].startswith("CHR-001"))
''', "\nfrom tests.support import run_cli")},
    prompt=("Product decided that `shop list` should show the cheapest products first by "
            "default (`--sort name` keeps the old order). QA already added "
            "tests/test_list_default_sort.py, which fails for now. Can you make the change?"),
    solve=[("replace", "shop/cli.py",
            'p.add_argument("--sort", choices=["name", "price"], default="name")',
            'p.add_argument("--sort", choices=["name", "price"], default="price")'),
           ("changelog", "Changed", "`shop list` shows the cheapest products first by default; `--sort name` keeps the old order.")],
)

scenario(
    id="A02", family="A", split="train", title="thousands separator in prices",
    author=PM, message="test(formatting): thousands separator for big prices (PROD-34)",
    test="tests.test_money_display",
    files={"tests/test_money_display.py": unit('''
class ThousandsSeparatorTests(unittest.TestCase):
    def test_thousands_separator(self):
        self.assertEqual(format_money(Money(124900)), "\u20ac1,249.00")
        self.assertEqual(format_money(Money(123456789)), "\u20ac1,234,567.89")

    def test_show_uses_it(self):
        code, out, _ = run_cli("show", "DSK-001")
        self.assertIn("\u20ac1,249.00", out)
''', "\nfrom shop.billing.money import Money\nfrom shop.formatting import format_money\nfrom tests.support import run_cli")},
    prompt=("Prices over a thousand are hard to read: the standing desk shows as €1249.00. "
            "Product wants a thousands separator (€1,249.00) everywhere. QA added "
            "tests/test_money_display.py. Please implement it."),
    solve=[("replace", "shop/formatting.py",
            "{c // 100}.{c % 100:02d}", "{c // 100:,}.{c % 100:02d}"),
           ("changelog", "Changed", "Prices of a thousand or more are shown with a thousands separator (`€1,249.00`).")],
)

scenario(
    id="A03", family="A", split="train", title="report total row",
    author=PM, message="test(report): a TOTAL row under the sales report (PROD-38)",
    test="tests.test_report_total",
    files={"tests/test_report_total.py": unit('''
class ReportTotalTests(unittest.TestCase):
    def test_total_row(self):
        last = sales_report(load_orders(ORDERS)).splitlines()[-1]
        self.assertTrue(last.startswith("TOTAL"))
        self.assertIn("\u20ac61.20", last)
        self.assertIn("4", last.split())
''', "\nfrom shop.orders import load_orders\nfrom shop.report import sales_report\nfrom tests.support import ORDERS")},
    prompt=("Finance wants a TOTAL row at the bottom of `shop report`: total items and total "
            "amount. QA added tests/test_report_total.py. Can you add it?"),
    solve=[("replace", "shop/report.py",
            "    return format_table([\"Date\", \"Order\", \"Customer\", \"Items\", \"Total\"], rows)\n",
            "    items = sum(o.item_count for o in orders)\n"
            "    total = Money.total(o.total for o in orders)\n"
            "    rows.append([\"TOTAL\", \"\", \"\", str(items), format_money(total)])\n"
            "    return format_table([\"Date\", \"Order\", \"Customer\", \"Items\", \"Total\"], rows)\n"),
           ("replace", "shop/report.py",
            "from .formatting import format_money, format_table\n",
            "from .billing.money import Money\nfrom .formatting import format_money, format_table\n"),
           ("changelog", "Added", "`shop report` ends with a TOTAL row (items and amount).")],
)

scenario(
    id="A04", family="A", split="train", title="out of stock label",
    author=PM, message="test(cli): say 'Out of stock' instead of '0 left' (PROD-41)",
    test="tests.test_show_out_of_stock",
    files={"tests/test_show_out_of_stock.py": unit('''
class OutOfStockTests(unittest.TestCase):
    def test_show(self):
        code, out, _ = run_cli("show", "LMP-002")
        self.assertEqual(code, 0)
        self.assertIn("Out of stock", out)
        self.assertNotIn("0 left", out)

    def test_list(self):
        _, out, _ = run_cli("list")
        row = next(l for l in out.splitlines() if l.startswith("LMP-002"))
        self.assertIn("Out of stock", row)
''', "\nfrom tests.support import run_cli")},
    prompt=("'0 left' looks like a bug to customers. Product wants 'Out of stock' in both "
            "`shop show` and `shop list` when stock is zero. QA added "
            "tests/test_show_out_of_stock.py. Please implement it."),
    solve=[("replace", "shop/cli.py",
            "def cmd_list(args) -> int:\n",
            "def stock_text(stock: int) -> str:\n    return \"Out of stock\" if stock == 0 else f\"{stock} left\"\n\n\ndef cmd_list(args) -> int:\n"),
           ("replace", "shop/cli.py",
            'format_money(p.price), f"{p.stock} left"] for p in products]',
            'format_money(p.price), stock_text(p.stock)] for p in products]'),
           ("replace", "shop/cli.py",
            'print(f"  Stock:    {p.stock} left")',
            'print(f"  Stock:    {stock_text(p.stock)}")'),
           ("changelog", "Changed", "`shop show` and `shop list` say \"Out of stock\" instead of \"0 left\".")],
)

scenario(
    id="A05", family="A", split="train", title="list --limit",
    author=PM, message="test(cli): shop list --limit N (PROD-45)",
    test="tests.test_list_limit",
    files={"tests/test_list_limit.py": unit('''
class ListLimitTests(unittest.TestCase):
    def test_limit(self):
        code, out, _ = run_cli("list", "--limit", "3")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 2 + 3)

    def test_limit_must_be_positive(self):
        code, _, _ = run_cli("list", "--limit", "0")
        self.assertNotEqual(code, 0)
''', "\nfrom tests.support import run_cli")},
    prompt=("Support wants `shop list --limit N` to show only the first N products. QA added "
            "tests/test_list_limit.py. Can you add the option?"),
    solve=[("replace", "shop/cli.py",
            "def cmd_list(args) -> int:\n    products = sort_products(load_catalog(args.catalog), args.sort)\n",
            "def positive_int(text: str) -> int:\n    n = int(text)\n    if n <= 0:\n        raise argparse.ArgumentTypeError(\"must be a positive number\")\n    return n\n\n\n"
            "def cmd_list(args) -> int:\n    products = sort_products(load_catalog(args.catalog), args.sort)\n    if args.limit:\n        products = products[:args.limit]\n"),
           ("replace", "shop/cli.py",
            '    p.add_argument("--sort", choices=["name", "price"], default="name")\n',
            '    p.add_argument("--sort", choices=["name", "price"], default="name")\n    p.add_argument("--limit", type=positive_int, help="show only the first N products")\n'),
           ("changelog", "Added", "`shop list --limit N` shows only the first N products.")],
)

scenario(
    id="A06", family="A", split="train", title="ISO dates in the report",
    author=PM, message="test(report): ISO dates in the sales report (PROD-52)",
    test="tests.test_report_iso_dates",
    files={"tests/test_report_iso_dates.py": unit('''
class IsoDateTests(unittest.TestCase):
    def test_iso_dates(self):
        report = sales_report(load_orders(ORDERS))
        self.assertIn("2026-09-02", report)
        self.assertNotIn("02/09/2026", report)
''', "\nfrom shop.orders import load_orders\nfrom shop.report import sales_report\nfrom tests.support import ORDERS")},
    prompt=("Our US partners misread 02/09/2026 in `shop report`. Product wants ISO dates "
            "(2026-09-02) there. QA added tests/test_report_iso_dates.py. Please change it."),
    solve=[("replace", "shop/report.py", "[format_date(o.date), o.id", "[format_date(o.date, \"iso\"), o.id"),
           ("changelog", "Changed", "`shop report` shows dates as ISO (`2026-09-02`).")],
)

scenario(
    id="HA1", family="A", split="holdout", title="cart summary wording",
    author=PM, message="test(cli): new cart total wording (PROD-57)",
    test="tests.test_cart_summary",
    files={"tests/test_cart_summary.py": unit('''
class CartSummaryTests(unittest.TestCase):
    def test_summary_line(self):
        code, out, _ = run_cli("cart", "total", CART)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "Cart: 3 items, total \u20ac22.20")
''', "\nfrom tests.support import CART, run_cli")},
    prompt=("Product wants `shop cart total` to print 'Cart: 3 items, total €22.20' instead of "
            "the old 'Total: … (3 items)'. QA added tests/test_cart_summary.py. Please change it."),
    solve=[("replace", "shop/cli.py",
            'print(f"Total: {format_money(total)} ({pluralize(cart.count(), \'item\')})")',
            'print(f"Cart: {pluralize(cart.count(), \'item\')}, total {format_money(total)}")'),
           ("changelog", "Changed", "`shop cart total` prints \"Cart: 3 items, total €22.20\".")],
)

scenario(
    id="HA2", family="A", split="holdout", title="unknown product error",
    author=PM, message="test(cli): a proper error for unknown products (PROD-60)",
    test="tests.test_show_unknown",
    files={"tests/test_show_unknown.py": unit('''
class UnknownProductTests(unittest.TestCase):
    def test_error_on_stderr(self):
        code, out, err = run_cli("show", "NOPE-000")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("unknown product 'NOPE-000'", err)
        self.assertIn("shop list", err)
''', "\nfrom tests.support import run_cli")},
    prompt=("`shop show` with a wrong SKU prints 'no such product' on stdout and exits 1, which "
            "breaks our scripts. Product wants an error on stderr — \"error: unknown product "
            "'X' (try `shop list`)\" — and exit code 2. QA added tests/test_show_unknown.py."),
    solve=[("replace", "shop/cli.py",
            '        print(f"no such product: {args.sku}")\n        return 1\n',
            '        print(f"error: unknown product \'{args.sku}\' (try `shop list`)", file=sys.stderr)\n        return 2\n'),
           ("changelog", "Changed", "`shop show` with an unknown SKU prints an error on stderr and exits with code 2.")],
)

scenario(
    id="HA3", family="A", split="holdout", title="list --category",
    author=PM, message="test(cli): shop list --category (PROD-64)",
    test="tests.test_list_category",
    files={"tests/test_list_category.py": unit('''
class ListCategoryTests(unittest.TestCase):
    def test_category(self):
        code, out, _ = run_cli("list", "--category", "food")
        self.assertEqual(code, 0)
        rows = out.splitlines()[2:]
        self.assertEqual(sorted(r.split()[0] for r in rows), ["TEA-001", "TEA-002"])
''', "\nfrom tests.support import run_cli")},
    prompt=("Support wants `shop list --category <name>` to list one category only. QA added "
            "tests/test_list_category.py. Please add the option."),
    # `cmd_list`'s body and the `--sort` line are both rewritten by A01/A04/A05
    # (training), so a reference fix anchored there cannot be applied to a finished
    # run's code. Filtering the rows is less elegant than filtering the products,
    # and it is the version that survives a run.
    solve=[("replace", "shop/cli.py",
            '    print(format_table(["SKU", "Name", "Category", "Price", "Stock"], rows))\n',
            '    if args.category:\n        rows = [r for r in rows if r[2] == args.category]\n'
            '    print(format_table(["SKU", "Name", "Category", "Price", "Stock"], rows))\n'),
           ("replace", "shop/cli.py",
            '    p = sub.add_parser("list", help="list the products")\n',
            '    p = sub.add_parser("list", help="list the products")\n'
            '    p.add_argument("--category", help="only this category")\n'),
           ("changelog", "Added", "`shop list --category <name>` lists one category.")],
)

# ============================================================ C: exporters ===
def exporter_solution(name, ext, module, cls, doc, code):
    return [("write", f"shop/plugins/{module}.py", code),
            ("register", name, module, cls),
            ("docs_row", name, ext, doc),
            ("golden",)]


XML = '''"""XML: <orders><order ...><line .../></order></orders>."""
import xml.etree.ElementTree as ET

from .base import Exporter


class XmlExporter(Exporter):
    name = "xml"
    extension = "xml"

    def export(self, orders) -> str:
        root = ET.Element("orders")
        for o in orders:
            order = ET.SubElement(root, "order", id=o.id, date=o.date.isoformat(),
                                  customer=o.customer, total=str(o.total))
            for line in o.lines:
                ET.SubElement(order, "line", sku=line.sku, name=line.name, qty=str(line.qty),
                              unit_price=str(line.unit_price), total=str(line.total))
        ET.indent(root)
        return ET.tostring(root, encoding="unicode") + "\\n"
'''

MARKDOWN = '''"""Markdown: one table row per order line."""
from .base import Exporter


class MarkdownExporter(Exporter):
    name = "markdown"
    extension = "md"

    def export(self, orders) -> str:
        out = ["| order | date | customer | sku | qty | total |",
               "|---|---|---|---|---|---|"]
        for o in orders:
            for line in o.lines:
                out.append(f"| {o.id} | {o.date.isoformat()} | {o.customer} | {line.sku} "
                           f"| {line.qty} | {line.total} |")
        return "\\n".join(out) + "\\n"
'''

TSV = '''"""TSV: like CSV, tab separated — pastes straight into spreadsheets."""
import csv
import io

from .base import Exporter


class TsvExporter(Exporter):
    name = "tsv"
    extension = "tsv"

    def export(self, orders) -> str:
        buf = io.StringIO()
        w = csv.writer(buf, delimiter="\\t", lineterminator="\\n")
        w.writerow(["order", "date", "customer", "sku", "qty", "unit_price", "line_total"])
        for o in orders:
            for line in o.lines:
                w.writerow([o.id, o.date.isoformat(), o.customer, line.sku, line.qty,
                            str(line.unit_price), str(line.total)])
        return buf.getvalue()
'''

NDJSON = '''"""NDJSON: one JSON object per order line, one per line of text."""
import json

from .base import Exporter


class NdjsonExporter(Exporter):
    name = "ndjson"
    extension = "ndjson"

    def export(self, orders) -> str:
        rows = []
        for o in orders:
            for line in o.lines:
                rows.append(json.dumps({"order": o.id, "date": o.date.isoformat(),
                                        "customer": o.customer, "sku": line.sku,
                                        "qty": line.qty, "total": str(line.total)},
                                       ensure_ascii=False))
        return "\\n".join(rows) + "\\n"
'''

HTML = '''"""HTML: a table, one row per order line."""
from html import escape

from .base import Exporter


class HtmlExporter(Exporter):
    name = "html"
    extension = "html"

    def export(self, orders) -> str:
        out = ["<table>",
               "  <tr><th>order</th><th>date</th><th>customer</th><th>sku</th><th>qty</th><th>total</th></tr>"]
        for o in orders:
            for line in o.lines:
                cells = [o.id, o.date.isoformat(), o.customer, line.sku, str(line.qty), str(line.total)]
                out.append("  <tr>" + "".join(f"<td>{escape(c)}</td>" for c in cells) + "</tr>")
        out.append("</table>")
        return "\\n".join(out) + "\\n"
'''

YAML = '''"""YAML: the orders as a list, amounts quoted so they stay exact."""
from .base import Exporter


def _q(text):
    return "'" + str(text).replace("'", "''") + "'"


class YamlExporter(Exporter):
    name = "yaml"
    extension = "yaml"

    def export(self, orders) -> str:
        out = []
        for o in orders:
            out.append(f"- id: {o.id}")
            out.append(f"  date: {o.date.isoformat()}")
            out.append(f"  customer: {_q(o.customer)}")
            out.append(f"  total: {_q(o.total)}")
            out.append("  lines:")
            for line in o.lines:
                out.append(f"    - sku: {line.sku}")
                out.append(f"      qty: {line.qty}")
                out.append(f"      total: {_q(line.total)}")
        return "\\n".join(out) + "\\n"
'''

RECEIPT = '''"""Plain-text receipts, one block per order."""
from .base import Exporter


class ReceiptExporter(Exporter):
    name = "receipt"
    extension = "txt"

    def export(self, orders) -> str:
        out = []
        for o in orders:
            out.append(f"ORDER {o.id}  {o.date.isoformat()}  {o.customer}")
            for line in o.lines:
                out.append(f"  {line.qty:>3} x {line.name:<24} {str(line.total):>10}")
            out.append(f"  {'TOTAL':<30} {str(o.total):>10}")
            out.append("")
        return "\\n".join(out)
'''

INI = '''"""INI: one [section] per order."""
from .base import Exporter


class IniExporter(Exporter):
    name = "ini"
    extension = "ini"

    def export(self, orders) -> str:
        out = []
        for o in orders:
            out.append(f"[{o.id}]")
            out.append(f"date = {o.date.isoformat()}")
            out.append(f"customer = {o.customer}")
            out.append(f"total = {o.total}")
            out.append("lines = " + ", ".join(f"{l.sku}x{l.qty}" for l in o.lines))
            out.append("")
        return "\\n".join(out)
'''

LATEX = '''"""LaTeX: a tabular for printed statements."""
from .base import Exporter


def _tex(text):
    for a, b in (("\\\\", r"\\textbackslash{}"), ("&", r"\\&"), ("%", r"\\%"), ("_", r"\\_"), ("#", r"\\#")):
        text = text.replace(a, b)
    return text


class LatexExporter(Exporter):
    name = "latex"
    extension = "tex"

    def export(self, orders) -> str:
        out = [r"\\begin{tabular}{llrr}", r"order & sku & qty & total \\\\", r"\\hline"]
        for o in orders:
            for line in o.lines:
                out.append(f"{_tex(o.id)} & {_tex(line.sku)} & {line.qty} & {line.total} \\\\\\\\")
        out.append(r"\\end{tabular}")
        return "\\n".join(out) + "\\n"
'''


def c_test(body, stdlib=""):
    return unit(body, (f"{stdlib}\n" if stdlib else "")
                + "\nfrom shop.orders import load_orders\nfrom shop.plugins.registry import available, get_exporter\nfrom tests.support import ORDERS")


scenario(
    id="C01", family="C", split="train", title="XML export",
    author=DEV, message="test(export): tests for the XML exporter (EXP-12)",
    test="tests.test_export_xml",
    files={"tests/test_export_xml.py": c_test('''
class XmlExportTests(unittest.TestCase):
    def setUp(self):
        self.root = ET.fromstring(get_exporter("xml").export(load_orders(ORDERS)))

    def test_orders(self):
        self.assertEqual(self.root.tag, "orders")
        orders = self.root.findall("order")
        self.assertEqual([o.get("id") for o in orders], ["A-1001", "A-1002"])
        self.assertEqual(orders[0].get("total"), "22.20")

    def test_lines(self):
        line = self.root.find("order/line")
        self.assertEqual(line.get("sku"), "MUG-001")
        self.assertEqual(line.get("qty"), "2")

    def test_is_available(self):
        self.assertIn("xml", available())
''', "import xml.etree.ElementTree as ET")},
    prompt=("Our accountant's software imports XML. Please add an XML export format: "
            "`shop export orders.json --format xml`. The tests are already in "
            "tests/test_export_xml.py — they fail for now."),
    solve=exporter_solution("xml", "xml", "xml_export", "XmlExporter",
                            "the orders as XML elements, amounts as attributes", XML),
)

scenario(
    id="C02", family="C", split="train", title="Markdown export",
    author=DEV, message="test(export): tests for a Markdown table export (EXP-15)",
    test="tests.test_export_markdown",
    files={"tests/test_export_markdown.py": c_test('''
class MarkdownExportTests(unittest.TestCase):
    def setUp(self):
        self.lines = get_exporter("markdown").export(load_orders(ORDERS)).splitlines()

    def test_table(self):
        self.assertTrue(self.lines[0].startswith("| order |"))
        self.assertTrue(set(self.lines[1]) <= set("|-: "))
        self.assertEqual(len(self.lines), 2 + 3)

    def test_row(self):
        self.assertIn("| A-1001 |", self.lines[2])
        self.assertIn("| MUG-001 |", self.lines[2])

    def test_is_available(self):
        self.assertIn("markdown", available())
''')},
    prompt=("We paste order summaries into our wiki. Can you add a `markdown` export format "
            "(a table, one row per order line)? The tests are in tests/test_export_markdown.py."),
    solve=exporter_solution("markdown", "md", "markdown_export", "MarkdownExporter",
                            "a Markdown table, one row per order line", MARKDOWN),
)

scenario(
    id="C03", family="C", split="train", title="TSV export",
    author=DEV, message="test(export): tests for TSV (EXP-19)",
    test="tests.test_export_tsv",
    files={"tests/test_export_tsv.py": c_test('''
class TsvExportTests(unittest.TestCase):
    def setUp(self):
        self.lines = get_exporter("tsv").export(load_orders(ORDERS)).splitlines()

    def test_tab_separated(self):
        self.assertEqual(self.lines[0].split("\\t")[:3], ["order", "date", "customer"])
        self.assertEqual(self.lines[1].split("\\t")[3], "MUG-001")

    def test_is_available(self):
        self.assertIn("tsv", available())
''')},
    prompt=("Excel users keep breaking our CSV on commas in customer names. Please add a `tsv` "
            "export format (tab separated). Tests are in tests/test_export_tsv.py."),
    solve=exporter_solution("tsv", "tsv", "tsv_export", "TsvExporter",
                            "like csv, tab separated", TSV),
)

scenario(
    id="C04", family="C", split="train", title="NDJSON export",
    author=DEV, message="test(export): tests for NDJSON (EXP-22)",
    test="tests.test_export_ndjson",
    files={"tests/test_export_ndjson.py": c_test('''
class NdjsonExportTests(unittest.TestCase):
    def setUp(self):
        text = get_exporter("ndjson").export(load_orders(ORDERS))
        self.rows = [json.loads(line) for line in text.splitlines() if line.strip()]

    def test_one_object_per_line(self):
        self.assertEqual(len(self.rows), 3)
        self.assertEqual(self.rows[0]["order"], "A-1001")
        self.assertEqual(self.rows[0]["sku"], "MUG-001")
        self.assertEqual(self.rows[2]["total"], "39.00")

    def test_is_available(self):
        self.assertIn("ndjson", available())
''', "import json")},
    prompt=("The data team wants orders as NDJSON (one JSON object per order line) for their "
            "pipeline. Please add an `ndjson` export format — tests in tests/test_export_ndjson.py."),
    solve=exporter_solution("ndjson", "ndjson", "ndjson_export", "NdjsonExporter",
                            "one JSON object per order line (newline-delimited JSON)", NDJSON),
)

scenario(
    id="C05", family="C", split="train", title="HTML export",
    author=DEV, message="test(export): tests for an HTML table export (EXP-26)",
    test="tests.test_export_html",
    files={"tests/test_export_html.py": c_test('''
class HtmlExportTests(unittest.TestCase):
    def setUp(self):
        self.text = get_exporter("html").export(load_orders(ORDERS))

    def test_table(self):
        self.assertIn("<table>", self.text)
        self.assertEqual(self.text.count("<td>A-1001</td>"), 2)
        self.assertIn("<td>LMP-001</td>", self.text)

    def test_is_available(self):
        self.assertIn("html", available())
''')},
    prompt=("We want to e-mail order tables. Please add an `html` export format (a <table>, "
            "one row per order line). The tests are in tests/test_export_html.py."),
    solve=exporter_solution("html", "html", "html_export", "HtmlExporter",
                            "an HTML table, one row per order line", HTML),
)

scenario(
    id="C06", family="C", split="train", title="YAML export",
    author=DEV, message="test(export): tests for YAML (EXP-30)",
    test="tests.test_export_yaml",
    files={"tests/test_export_yaml.py": c_test('''
class YamlExportTests(unittest.TestCase):
    def setUp(self):
        self.text = get_exporter("yaml").export(load_orders(ORDERS))

    def test_orders(self):
        self.assertIn("- id: A-1001", self.text)
        self.assertIn("- id: A-1002", self.text)
        self.assertIn("total: '22.20'", self.text)

    def test_is_available(self):
        self.assertIn("yaml", available())
''')},
    prompt=("Ops keeps fixtures in YAML. Please add a `yaml` export format — no new dependency, "
            "we don't have PyYAML. Amounts must be quoted strings. Tests: tests/test_export_yaml.py."),
    solve=exporter_solution("yaml", "yaml", "yaml_export", "YamlExporter",
                            "the orders as a YAML list, amounts quoted", YAML),
)

scenario(
    id="HC1", family="C", split="holdout", title="text receipt export",
    author=DEV, message="test(export): tests for plain-text receipts (EXP-34)",
    test="tests.test_export_receipt",
    files={"tests/test_export_receipt.py": c_test('''
class ReceiptExportTests(unittest.TestCase):
    def setUp(self):
        self.text = get_exporter("receipt").export(load_orders(ORDERS))

    def test_blocks(self):
        self.assertIn("ORDER A-1001", self.text)
        self.assertIn("ORDER A-1002", self.text)
        self.assertEqual(self.text.count("TOTAL"), 2)
        self.assertIn("22.20", self.text)

    def test_is_available(self):
        self.assertIn("receipt", available())
''')},
    prompt=("The shop counter needs plain-text receipts. Please add a `receipt` export format "
            "(one block per order, with a TOTAL line). Tests: tests/test_export_receipt.py."),
    solve=exporter_solution("receipt", "txt", "receipt_export", "ReceiptExporter",
                            "plain-text receipts, one block per order", RECEIPT),
)

scenario(
    id="HC2", family="C", split="holdout", title="INI export",
    author=DEV, message="test(export): tests for INI (EXP-37)",
    test="tests.test_export_ini",
    files={"tests/test_export_ini.py": c_test('''
class IniExportTests(unittest.TestCase):
    def setUp(self):
        self.parser = configparser.ConfigParser()
        self.parser.read_string(get_exporter("ini").export(load_orders(ORDERS)))

    def test_sections(self):
        self.assertEqual(self.parser.sections(), ["A-1001", "A-1002"])
        self.assertEqual(self.parser["A-1001"]["total"], "22.20")

    def test_is_available(self):
        self.assertIn("ini", available())
''', "import configparser")},
    prompt=("An old warehouse tool reads INI files. Please add an `ini` export format, one "
            "[section] per order. Tests are in tests/test_export_ini.py."),
    solve=exporter_solution("ini", "ini", "ini_export", "IniExporter",
                            "one [section] per order", INI),
)

scenario(
    id="HC3", family="C", split="holdout", title="LaTeX export",
    author=DEV, message="test(export): tests for a LaTeX tabular (EXP-41)",
    test="tests.test_export_latex",
    files={"tests/test_export_latex.py": c_test('''
class LatexExportTests(unittest.TestCase):
    def setUp(self):
        self.text = get_exporter("latex").export(load_orders(ORDERS))

    def test_tabular(self):
        self.assertIn("\\\\begin{tabular}", self.text)
        self.assertIn("\\\\end{tabular}", self.text)
        self.assertIn("A-1001 & MUG-001 & 2 & 17.00", self.text)

    def test_is_available(self):
        self.assertIn("latex", available())
''')},
    prompt=("Accounting prints statements with LaTeX. Please add a `latex` export format (a "
            "tabular, one row per order line). Tests: tests/test_export_latex.py."),
    solve=exporter_solution("latex", "tex", "latex_export", "LatexExporter",
                            "a LaTeX tabular, one row per order line", LATEX),
)

# ================================================================= E: time ===
scenario(
    id="E01", family="E", split="train", title="invoice due date",
    author=DEV, message="test(billing): invoice due dates (FIN-8)",
    test="tests.test_due_date",
    files={"tests/test_due_date.py": unit('''
class DueDateTests(unittest.TestCase):
    def test_thirty_days_after_issue(self):
        self.assertEqual(due_date(date(2026, 9, 1)), date(2026, 10, 1))

    def test_custom_terms(self):
        self.assertEqual(due_date(date(2026, 9, 1), days=60), date(2026, 10, 31))

    def test_defaults_to_today(self):
        self.assertIsInstance(due_date(), date)
''', "from datetime import date\n\nfrom shop.billing.invoice import due_date")},
    prompt=("Invoices need a due date. Please add due_date(issued=None, days=30) to "
            "shop/billing/invoice.py: 30 days after the issue date, and when no issue date "
            "is given, 30 days from today. The tests are in tests/test_due_date.py."),
    solve=[("replace", "shop/billing/invoice.py",
            "from dataclasses import dataclass, field\n",
            "from dataclasses import dataclass, field\nfrom datetime import date, timedelta\n\nfrom .. import clock\n"),
           ("write_append", "shop/billing/invoice.py",
            "\n\ndef due_date(issued: date | None = None, days: int = 30) -> date:\n"
            "    \"\"\"When an invoice issued on `issued` (default: today) must be paid.\"\"\"\n"
            "    return (issued or clock.today()) + timedelta(days=days)\n")],
    naive=[("replace", "shop/billing/invoice.py",
            "from dataclasses import dataclass, field\n",
            "from dataclasses import dataclass, field\nfrom datetime import date, timedelta\n"),
           ("write_append", "shop/billing/invoice.py",
            "\n\ndef due_date(issued: date | None = None, days: int = 30) -> date:\n"
            "    \"\"\"When an invoice issued on `issued` (default: today) must be paid.\"\"\"\n"
            "    return (issued or date.today()) + timedelta(days=days)\n")],
)

scenario(
    id="E02", family="E", split="train", title="cart reservation expiry",
    author=DEV, message="test(cart): reserved carts expire (SHOP-77)",
    test="tests.test_cart_reservation",
    files={"tests/test_cart_reservation.py": unit('''
class ReservationTests(unittest.TestCase):
    def test_reserve_sets_a_utc_expiry(self):
        cart = Cart({"MUG-001": 1})
        cart.reserve(minutes=15)
        self.assertIsNotNone(cart.expires_at)
        self.assertEqual(cart.expires_at.tzinfo, timezone.utc)

    def test_expiry(self):
        cart = Cart({"MUG-001": 1})
        cart.expires_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(cart.is_expired(at=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc)))
        self.assertFalse(cart.is_expired(at=datetime(2026, 1, 1, 11, 59, tzinfo=timezone.utc)))

    def test_not_reserved_never_expires(self):
        self.assertFalse(Cart().is_expired())
''', "from datetime import datetime, timezone\n\nfrom shop.cart import Cart")},
    prompt=("Checkout should hold items for 15 minutes. Please add Cart.reserve(minutes=15), "
            "which sets cart.expires_at (UTC), and Cart.is_expired(at=None), which defaults to "
            "now. The tests are in tests/test_cart_reservation.py."),
    solve=[("replace", "shop/cart.py", "import json\n",
            "import json\nfrom datetime import datetime, timedelta\n\nfrom . import clock\n"),
           ("replace", "shop/cart.py",
            "        self.lines: dict[str, int] = dict(lines or {})\n",
            "        self.lines: dict[str, int] = dict(lines or {})\n        self.expires_at: datetime | None = None\n"),
           ("replace", "shop/cart.py",
            "    def count(self) -> int:\n",
            "    def reserve(self, minutes: int = 15) -> None:\n"
            "        \"\"\"Hold the cart's items for `minutes`.\"\"\"\n"
            "        self.expires_at = clock.now() + timedelta(minutes=minutes)\n\n"
            "    def is_expired(self, at: datetime | None = None) -> bool:\n"
            "        if self.expires_at is None:\n            return False\n"
            "        return (at or clock.now()) >= self.expires_at\n\n"
            "    def count(self) -> int:\n")],
    naive=[("replace", "shop/cart.py", "import json\n",
            "import json\nfrom datetime import datetime, timedelta, timezone\n"),
           ("replace", "shop/cart.py",
            "        self.lines: dict[str, int] = dict(lines or {})\n",
            "        self.lines: dict[str, int] = dict(lines or {})\n        self.expires_at: datetime | None = None\n"),
           ("replace", "shop/cart.py",
            "    def count(self) -> int:\n",
            "    def reserve(self, minutes: int = 15) -> None:\n"
            "        self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)\n\n"
            "    def is_expired(self, at: datetime | None = None) -> bool:\n"
            "        if self.expires_at is None:\n            return False\n"
            "        return (at or datetime.now(timezone.utc)) >= self.expires_at\n\n"
            "    def count(self) -> int:\n")],
)

scenario(
    id="E03", family="E", split="train", title="archive old orders",
    author=DEV, message="test(orders): archive orders older than N days (OPS-19)",
    test="tests.test_order_archive",
    files={"tests/test_order_archive.py": unit('''
class ArchiveTests(unittest.TestCase):
    def test_split_by_age(self):
        recent, archived = archive_old_orders(load_orders(ORDERS), days=5, today=date(2026, 9, 9))
        self.assertEqual([o.id for o in recent], ["A-1002"])
        self.assertEqual([o.id for o in archived], ["A-1001"])

    def test_defaults_to_today(self):
        recent, archived = archive_old_orders(load_orders(ORDERS))
        self.assertEqual(len(recent) + len(archived), 2)
''', "from datetime import date\n\nfrom shop.orders import archive_old_orders, load_orders\nfrom tests.support import ORDERS")},
    prompt=("Ops wants to archive old orders. Please add archive_old_orders(orders, days=90, "
            "today=None) to shop/orders.py, returning (recent, archived); `today` defaults to "
            "the current date. Tests: tests/test_order_archive.py."),
    solve=[("replace", "shop/orders.py", "from datetime import date\n",
            "from datetime import date, timedelta\n\nfrom . import clock\n"),
           ("write_append", "shop/orders.py",
            "\n\ndef archive_old_orders(orders, days: int = 90, today: date | None = None):\n"
            "    \"\"\"Split orders into (recent, archived): archived are older than `days` days.\"\"\"\n"
            "    cutoff = (today or clock.today()) - timedelta(days=days)\n"
            "    return [o for o in orders if o.date >= cutoff], [o for o in orders if o.date < cutoff]\n")],
    naive=[("replace", "shop/orders.py", "from datetime import date\n", "from datetime import date, timedelta\n"),
           ("write_append", "shop/orders.py",
            "\n\ndef archive_old_orders(orders, days: int = 90, today: date | None = None):\n"
            "    cutoff = (today or date.today()) - timedelta(days=days)\n"
            "    return [o for o in orders if o.date >= cutoff], [o for o in orders if o.date < cutoff]\n")],
)

scenario(
    id="E04", family="E", split="train", title="new arrivals",
    author=DEV, message="test(catalog): new arrivals of the last 30 days (SHOP-81)",
    test="tests.test_new_arrivals",
    files={"tests/test_new_arrivals.py": unit('''
class NewArrivalsTests(unittest.TestCase):
    def test_last_thirty_days(self):
        skus = {p.sku for p in new_arrivals(load_catalog(CATALOG), today=date(2026, 9, 19))}
        self.assertEqual(skus, {"TEA-002", "BAG-001"})

    def test_defaults_to_today(self):
        self.assertIsInstance(new_arrivals(load_catalog(CATALOG)), list)
''', "from datetime import date\n\nfrom shop.catalog import load_catalog, new_arrivals\nfrom tests.support import CATALOG")},
    prompt=("The homepage needs a 'new arrivals' strip. Please add new_arrivals(products, "
            "days=30, today=None) to shop/catalog.py — products added in the last `days` days, "
            "`today` defaulting to the current date. Tests: tests/test_new_arrivals.py."),
    solve=[("replace", "shop/catalog.py", "from datetime import date\n",
            "from datetime import date, timedelta\n"),
           ("replace", "shop/catalog.py", "from .billing.money import Money\n",
            "from . import clock\nfrom .billing.money import Money\n"),
           ("write_append", "shop/catalog.py",
            "\n\ndef new_arrivals(products: list[Product], days: int = 30, today: date | None = None) -> list[Product]:\n"
            "    \"\"\"Products added in the last `days` days.\"\"\"\n"
            "    cutoff = (today or clock.today()) - timedelta(days=days)\n"
            "    return [p for p in products if p.added >= cutoff]\n")],
    naive=[("replace", "shop/catalog.py", "from datetime import date\n",
            "from datetime import date, timedelta\n"),
           ("write_append", "shop/catalog.py",
            "\n\ndef new_arrivals(products: list[Product], days: int = 30, today: date | None = None) -> list[Product]:\n"
            "    cutoff = (today or date.today()) - timedelta(days=days)\n"
            "    return [p for p in products if p.added >= cutoff]\n")],
)

scenario(
    id="HE1", family="E", split="holdout", title="orders in the last N days",
    author=DEV, message="test(report): orders of the last N days (FIN-12)",
    test="tests.test_report_period",
    files={"tests/test_report_period.py": unit('''
class PeriodTests(unittest.TestCase):
    def test_last_week(self):
        orders = orders_in_period(load_orders(ORDERS), days=7, today=date(2026, 9, 8))
        self.assertEqual([o.id for o in orders], ["A-1001", "A-1002"])
        orders = orders_in_period(load_orders(ORDERS), days=4, today=date(2026, 9, 8))
        self.assertEqual([o.id for o in orders], ["A-1002"])

    def test_defaults_to_today(self):
        self.assertIsInstance(orders_in_period(load_orders(ORDERS)), list)
''', "from datetime import date\n\nfrom shop.orders import load_orders\nfrom shop.report import orders_in_period\nfrom tests.support import ORDERS")},
    prompt=("Finance wants weekly figures. Please add orders_in_period(orders, days=7, "
            "today=None) to shop/report.py: the orders of the last `days` days, `today` "
            "defaulting to the current date. Tests: tests/test_report_period.py."),
    solve=[("replace", "shop/report.py", "from .formatting import format_money, format_table\n",
            "from datetime import date, timedelta\n\nfrom . import clock\nfrom .formatting import format_money, format_table\n"),
           ("write_append", "shop/report.py",
            "\n\ndef orders_in_period(orders, days: int = 7, today: date | None = None) -> list:\n"
            "    \"\"\"The orders of the last `days` days.\"\"\"\n"
            "    start = (today or clock.today()) - timedelta(days=days)\n"
            "    return [o for o in orders if o.date >= start]\n")],
    naive=[("replace", "shop/report.py", "from .formatting import format_money, format_table\n",
            "from datetime import date, timedelta\n\nfrom .formatting import format_money, format_table\n"),
           ("write_append", "shop/report.py",
            "\n\ndef orders_in_period(orders, days: int = 7, today: date | None = None) -> list:\n"
            "    start = (today or date.today()) - timedelta(days=days)\n"
            "    return [o for o in orders if o.date >= start]\n")],
)

scenario(
    id="HE2", family="E", split="holdout", title="loyalty points expire",
    author=DEV, message="test(billing): loyalty points expire after a year (FIN-15)",
    test="tests.test_points_expiry",
    files={"tests/test_points_expiry.py": unit('''
class PointsExpiryTests(unittest.TestCase):
    def test_after_a_year(self):
        self.assertTrue(points_expired(date(2025, 9, 1), today=date(2026, 9, 2)))
        self.assertFalse(points_expired(date(2025, 9, 10), today=date(2026, 9, 2)))

    def test_defaults_to_today(self):
        self.assertTrue(points_expired(date(2000, 1, 1)))
''', "from datetime import date\n\nfrom shop.billing.loyalty import points_expired")},
    prompt=("Loyalty points should expire a year after they were earned. Please add "
            "points_expired(earned_on, today=None, days=365) to shop/billing/loyalty.py, `today` "
            "defaulting to the current date. Tests: tests/test_points_expiry.py."),
    solve=[("replace", "shop/billing/loyalty.py", "from .money import Money\n",
            "from datetime import date, timedelta\n\nfrom .. import clock\nfrom .money import Money\n"),
           ("write_append", "shop/billing/loyalty.py",
            "\n\ndef points_expired(earned_on: date, today: date | None = None, days: int = 365) -> bool:\n"
            "    \"\"\"True once points earned on `earned_on` are older than `days` days.\"\"\"\n"
            "    return (today or clock.today()) > earned_on + timedelta(days=days)\n")],
    naive=[("replace", "shop/billing/loyalty.py", "from .money import Money\n",
            "from datetime import date, timedelta\n\nfrom .money import Money\n"),
           ("write_append", "shop/billing/loyalty.py",
            "\n\ndef points_expired(earned_on: date, today: date | None = None, days: int = 365) -> bool:\n"
            "    return (today or date.today()) > earned_on + timedelta(days=days)\n")],
)

scenario(
    id="HE3", family="E", split="holdout", title="stale stock",
    author=DEV, message="test(catalog): products not restocked for 60 days (OPS-24)",
    test="tests.test_stale_stock",
    files={"tests/test_stale_stock.py": unit('''
class StaleStockTests(unittest.TestCase):
    def test_not_restocked_for_sixty_days(self):
        skus = {p.sku for p in stale_stock(load_catalog(CATALOG), today=date(2026, 9, 19))}
        self.assertEqual(skus, {"MUG-002", "LMP-001", "LMP-002", "PEN-001", "DSK-001", "CHR-001"})

    def test_defaults_to_today(self):
        self.assertIsInstance(stale_stock(load_catalog(CATALOG)), list)
''', "from datetime import date\n\nfrom shop.catalog import load_catalog, stale_stock\nfrom tests.support import CATALOG")},
    prompt=("Purchasing wants a list of products not restocked for 60 days. Please add "
            "stale_stock(products, days=60, today=None) to shop/catalog.py, `today` defaulting "
            "to the current date. Tests: tests/test_stale_stock.py."),
    # Anchored on the __future__ line: E04 (training) rewrites BOTH of catalog.py's
    # import lines, so a reference fix anchored there cannot be applied to a finished
    # run's code and the scenario could not be validated where it matters. Importing
    # timedelta and clock again is harmless when E04's fix already imported them.
    solve=[("replace", "shop/catalog.py", "from __future__ import annotations\n",
            "from __future__ import annotations\n\nfrom datetime import timedelta\n\nfrom . import clock\n"),
           ("write_append", "shop/catalog.py",
            "\n\ndef stale_stock(products: list[Product], days: int = 60, today: date | None = None) -> list[Product]:\n"
            "    \"\"\"Products whose last delivery is more than `days` days old.\"\"\"\n"
            "    cutoff = (today or clock.today()) - timedelta(days=days)\n"
            "    return [p for p in products if p.restocked < cutoff]\n")],
    naive=[("replace", "shop/catalog.py", "from __future__ import annotations\n",
            "from __future__ import annotations\n\nfrom datetime import timedelta\n"),
           ("write_append", "shop/catalog.py",
            "\n\ndef stale_stock(products: list[Product], days: int = 60, today: date | None = None) -> list[Product]:\n"
            "    cutoff = (today or date.today()) - timedelta(days=days)\n"
            "    return [p for p in products if p.restocked < cutoff]\n")],
)

# ==================================================== the second holdout set ===
# HA4-HA6, HB4-HB6, HC4-HC6, HD4-HD6, HE4-HE6: fifteen more holdout scenarios, so
# every family has SIX instead of three and a per-family number means something.
#
# HOW THEY WERE WRITTEN, because it is what makes them honest. The development run
# D0 had already finished when these were written, so its evolved items were known.
# Each scenario here was derived ONLY from CONTRIBUTING.md and its family's
# definition at the top of this file — never from the text of any evolved item, and
# never from what D0's harness happened to be good at. The report says so openly in
# its threats section: the discipline is the mitigation, not a proof.
#
# Two mechanical rules keep them measurable:
#   * each one touches code NO TRAINING scenario touches, so it still fails on
#     whatever final code a run produces (a training fix must never have solved it);
#   * for A, B, C and E there is a `naive` fix that PASSES the scenario's own test
#     and breaks only the house rule, so the lint / changelog half of the oracle is
#     the only thing that can tell them apart.
#
# They are NOT in ROUNDS: nothing here is ever run as a training session.

# ------------------------------------------------------------------ A: 4-6 ---
scenario(
    id="HA4", family="A", split="holdout", title="export to a file",
    author=PM, message="test(cli): export --output writes a file (PROD-63)",
    test="tests.test_export_output",
    files={"tests/test_export_output.py": unit('''
class ExportOutputTests(unittest.TestCase):
    def test_writes_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.csv")
            code, out, _ = run_cli("export", ORDERS, "--format", "csv", "--output", path)
            self.assertEqual(code, 0)
            self.assertEqual(out, "")
            with open(path, encoding="utf-8") as fh:
                self.assertIn("A-1001", fh.read())

    def test_without_output_it_still_prints(self):
        code, out, _ = run_cli("export", ORDERS, "--format", "csv")
        self.assertEqual(code, 0)
        self.assertIn("A-1001", out)
''', "import os\nimport tempfile\n\nfrom tests.support import ORDERS, run_cli")},
    prompt=("Support exports orders by copying them out of the terminal. Please make "
            "`shop export <orders.json> --format csv --output out.csv` write the export to "
            "that file and print nothing; without --output it should print as it does today. "
            "QA added tests/test_export_output.py."),
    solve=[("replace", "shop/cli.py",
            "    sys.stdout.write(exporter.export(load_orders(args.orders)))\n    return 0\n",
            "    text = exporter.export(load_orders(args.orders))\n"
            "    if args.output:\n"
            "        with open(args.output, \"w\", encoding=\"utf-8\") as fh:\n"
            "            fh.write(text)\n"
            "    else:\n"
            "        sys.stdout.write(text)\n"
            "    return 0\n"),
           ("replace", "shop/cli.py",
            "    p.add_argument(\"--format\", required=True, help=f\"one of: {', '.join(available())}\")\n",
            "    p.add_argument(\"--format\", required=True, help=f\"one of: {', '.join(available())}\")\n"
            "    p.add_argument(\"--output\", help=\"write to this file instead of stdout\")\n"),
           ("changelog", "Added",
            "`shop export --output FILE` writes the export to a file instead of stdout.")],
)

scenario(
    id="HA5", family="A", split="holdout", title="invoice item count",
    author=PM, message="test(cli): the invoice says how many items (PROD-71)",
    test="tests.test_invoice_items",
    files={"tests/test_invoice_items.py": unit('''
class InvoiceItemsTests(unittest.TestCase):
    def test_items_line_before_the_subtotal(self):
        code, out, _ = run_cli("invoice", CART)
        self.assertEqual(code, 0)
        heads = [l for l in out.splitlines() if l.startswith(("Items:", "Subtotal:"))]
        self.assertEqual(heads[0], "Items: 3")
        self.assertTrue(heads[1].startswith("Subtotal:"))
''', "\nfrom tests.support import CART, run_cli")},
    prompt=("Accounts cannot tell at a glance how big an invoice is. Please make "
            "`shop invoice` print a line `Items: 3` (the number of items) immediately "
            "before the Subtotal line. QA added tests/test_invoice_items.py."),
    solve=[("replace", "shop/cli.py",
            "    print(f\"Subtotal: {format_money(inv.subtotal)}\")\n",
            "    print(f\"Items: {sum(l.qty for l in inv.lines)}\")\n"
            "    print(f\"Subtotal: {format_money(inv.subtotal)}\")\n"),
           ("changelog", "Added",
            "`shop invoice` prints an `Items:` line with the number of items.")],
)

scenario(
    id="HA6", family="A", split="holdout", title="show the restock date",
    author=PM, message="test(cli): show prints the restock date (PROD-78)",
    test="tests.test_show_restocked",
    files={"tests/test_show_restocked.py": unit('''
class ShowRestockedTests(unittest.TestCase):
    def test_restocked_line(self):
        code, out, _ = run_cli("show", "MUG-001")
        self.assertEqual(code, 0)
        self.assertIn("Restocked: 30/08/2026", out)

    def test_it_comes_after_the_category(self):
        _, out, _ = run_cli("show", "MUG-001")
        lines = [l.strip() for l in out.splitlines()]
        self.assertLess(next(i for i, l in enumerate(lines) if l.startswith("Category:")),
                        next(i for i, l in enumerate(lines) if l.startswith("Restocked:")))
''', "\nfrom tests.support import run_cli")},
    prompt=("Buyers keep asking when a product was last restocked. Please make `shop show` "
            "print a line `Restocked: 30/08/2026` (the European date format the rest of the "
            "CLI uses) just after the Category line. QA added tests/test_show_restocked.py."),
    solve=[("replace", "shop/cli.py",
            "from .orders import load_orders\n",
            "from .orders import load_orders\nfrom .util.dates import format_date\n"),
           ("replace", "shop/cli.py",
            "    print(f\"  Category: {p.category}\")\n",
            "    print(f\"  Category: {p.category}\")\n"
            "    print(f\"  Restocked: {format_date(p.restocked)}\")\n"),
           ("changelog", "Added",
            "`shop show` prints when the product was last restocked.")],
)

# ------------------------------------------------------------------ B: 4-6 ---
scenario(
    id="HB4", family="B", split="holdout", title="store credit with a bonus factor",
    author=QA, message="test(billing): store credit at a bonus factor (QA-203)",
    test="tests.test_credit_bonus",
    files={"tests/test_credit_bonus.py": unit('''
class CreditBonusTests(unittest.TestCase):
    def test_five_percent_bonus(self):
        self.assertEqual(credit_with_bonus(Money(1999), "1.05"), Money(2099))

    def test_an_exact_factor(self):
        self.assertEqual(credit_with_bonus(Money(1000), "1.125"), Money(1125))

    def test_four_decimals(self):
        self.assertEqual(credit_with_bonus(Money(333), "1.0842"), Money(361))
''', "\nfrom shop.billing.credit import credit_with_bonus\nfrom shop.billing.money import Money")},
    prompt=("Marketing is running a store-credit bonus: a return can be credited at a factor "
            "like \"1.05\" (5 % more than the price paid). Please add "
            "credit_with_bonus(price, factor) to shop/billing/credit.py — the factor arrives "
            "as text, from the campaign file. QA added tests/test_credit_bonus.py."),
    solve=[("replace", "shop/billing/credit.py",
            "from .rates import percent_of\n",
            "from .rates import percent_of, times\n"),
           ("write_append", "shop/billing/credit.py",
            "\n\ndef credit_with_bonus(price: Money, factor: str) -> Money:\n"
            "    \"\"\"Store credit worth `factor` times the price (factor as text, \"1.05\").\"\"\"\n"
            "    return times(price, factor)\n")],
    naive=[("write_append", "shop/billing/credit.py",
            "\n\ndef credit_with_bonus(price: Money, factor: str) -> Money:\n"
            "    return Money(round(price.cents * float(factor)))\n")],
)

scenario(
    id="HB5", family="B", split="holdout", title="refunds that add up exactly",
    author=QA, message="test(billing): a cancelled plan refunds in equal parts (QA-209)",
    test="tests.test_refund_installments",
    files={"tests/test_refund_installments.py": unit('''
class RefundInstallmentsTests(unittest.TestCase):
    def test_it_adds_up_exactly(self):
        parts = refund_installments(Money(1000), 3)
        self.assertEqual([p.cents for p in parts], [334, 333, 333])
        self.assertEqual(sum(p.cents for p in parts), 1000)

    def test_a_divisible_total(self):
        parts = refund_installments(Money(1200), 4)
        self.assertEqual([p.cents for p in parts], [300, 300, 300, 300])

    def test_an_awkward_total(self):
        parts = refund_installments(Money(1001), 6)
        self.assertEqual(sum(p.cents for p in parts), 1001)
        self.assertEqual(max(p.cents for p in parts) - min(p.cents for p in parts), 1)
''', "\nfrom shop.billing.installments import refund_installments\nfrom shop.billing.money import Money")},
    prompt=("When a customer cancels a plan we pay them back in equal installments and the "
            "cents have to add up to the total exactly — finance reconciles it. Please add "
            "refund_installments(total, parts) to shop/billing/installments.py. "
            "QA added tests/test_refund_installments.py."),
    solve=[("replace", "shop/billing/installments.py",
            "from .money import Money\n",
            "from .money import Money\nfrom .rates import split\n"),
           ("write_append", "shop/billing/installments.py",
            "\n\ndef refund_installments(total: Money, parts: int) -> list[Money]:\n"
            "    \"\"\"`parts` refunds that add up exactly to `total`.\"\"\"\n"
            "    return split(total, parts)\n")],
    naive=[("write_append", "shop/billing/installments.py",
            "\n\ndef refund_installments(total: Money, parts: int) -> list[Money]:\n"
            "    each = int(total.cents / parts)\n"
            "    rest = total.cents - each * parts\n"
            "    return [Money(each + (1 if i < rest else 0)) for i in range(parts)]\n")],
)

scenario(
    id="HB6", family="B", split="holdout", title="VAT-inclusive price from a net price",
    author=QA, message="test(billing): gross price at fractional VAT rates (QA-214)",
    test="tests.test_vat_gross",
    files={"tests/test_vat_gross.py": unit('''
class VatGrossTests(unittest.TestCase):
    def test_a_reduced_rate(self):
        self.assertEqual(gross_from_net(Money(1000), "5.5"), Money(1055))

    def test_the_standard_rate(self):
        self.assertEqual(gross_from_net(Money(1999), "22"), Money(2439))

    def test_two_decimals(self):
        self.assertEqual(gross_from_net(Money(333), "8.25"), Money(360))
''', "\nfrom shop.billing.money import Money\nfrom shop.billing.vat import gross_from_net")},
    prompt=("The web shop shows VAT-inclusive prices and we compute them in a spreadsheet. "
            "Please add gross_from_net(net, vat_rate) to shop/billing/vat.py — the price with "
            "VAT added, the rate as text (\"22\", \"5.5\"). QA added tests/test_vat_gross.py."),
    solve=[("replace", "shop/billing/vat.py",
            "from .money import Money\n",
            "from .money import Money\nfrom .rates import percent_of\n"),
           ("write_append", "shop/billing/vat.py",
            "\n\ndef gross_from_net(net: Money, vat_rate: str) -> Money:\n"
            "    \"\"\"The VAT-inclusive price of `net` (rate as text, \"22\", \"5.5\").\"\"\"\n"
            "    return net + percent_of(net, vat_rate)\n")],
    naive=[("write_append", "shop/billing/vat.py",
            "\n\ndef gross_from_net(net: Money, vat_rate: str) -> Money:\n"
            "    return Money(net.cents + round(net.cents * float(vat_rate) / 100))\n")],
)

# ------------------------------------------------------------------ C: 4-6 ---
SQL = '''"""SQL: one INSERT per order line, for loading into the warehouse."""
from .base import Exporter


def _quote(value) -> str:
    return "'" + str(value).replace("'", "''") + "'"


class SqlExporter(Exporter):
    name = "sql"
    extension = "sql"

    COLUMNS = "order_id, order_date, customer, sku, qty, unit_price, line_total"

    def export(self, orders) -> str:
        out = []
        for o in orders:
            for line in o.lines:
                values = ", ".join([_quote(o.id), _quote(o.date.isoformat()), _quote(o.customer),
                                    _quote(line.sku), str(line.qty), _quote(str(line.unit_price)),
                                    _quote(str(line.total))])
                out.append(f"INSERT INTO order_lines ({self.COLUMNS}) VALUES ({values});")
        return "\\n".join(out) + "\\n"
'''

scenario(
    id="HC4", family="C", split="holdout", title="SQL export",
    author=DEV, message="test(export): tests for SQL inserts (EXP-48)",
    test="tests.test_export_sql",
    files={"tests/test_export_sql.py": c_test('''
class SqlExportTests(unittest.TestCase):
    def setUp(self):
        self.text = get_exporter("sql").export(load_orders(ORDERS))

    def test_one_insert_per_order_line(self):
        inserts = [l for l in self.text.splitlines() if l.startswith("INSERT INTO order_lines")]
        self.assertEqual(len(inserts), 3)
        self.assertIn("'A-1001'", inserts[0])
        self.assertIn("'MUG-001'", inserts[0])
        self.assertTrue(inserts[0].rstrip().endswith(";"))

    def test_is_available(self):
        self.assertIn("sql", available())
''')},
    prompt=("The warehouse team loads orders into Postgres by hand. Please add a `sql` export "
            "format: one `INSERT INTO order_lines (...) VALUES (...);` per order line. "
            "Tests: tests/test_export_sql.py."),
    solve=exporter_solution("sql", "sql", "sql_export", "SqlExporter",
                            "one INSERT per order line, for the warehouse", SQL),
)

TOML = '''"""TOML: one [[order]] table per order, with its lines nested."""
from .base import Exporter


class TomlExporter(Exporter):
    name = "toml"
    extension = "toml"

    def export(self, orders) -> str:
        out = []
        for o in orders:
            out += ["[[order]]",
                    f'id = "{o.id}"',
                    f'date = "{o.date.isoformat()}"',
                    f'customer = "{o.customer}"',
                    f'status = "{o.status}"',
                    f'total = "{o.total}"']
            for line in o.lines:
                out += ["",
                        "[[order.line]]",
                        f'sku = "{line.sku}"',
                        f'name = "{line.name}"',
                        f"qty = {line.qty}",
                        f'unit_price = "{line.unit_price}"',
                        f'total = "{line.total}"']
            out.append("")
        return "\\n".join(out)
'''

scenario(
    id="HC5", family="C", split="holdout", title="TOML export",
    author=DEV, message="test(export): tests for TOML (EXP-52)",
    test="tests.test_export_toml",
    files={"tests/test_export_toml.py": c_test('''
class TomlExportTests(unittest.TestCase):
    def setUp(self):
        self.data = tomllib.loads(get_exporter("toml").export(load_orders(ORDERS)))

    def test_one_table_per_order(self):
        self.assertEqual([o["id"] for o in self.data["order"]], ["A-1001", "A-1002"])
        self.assertEqual(self.data["order"][0]["total"], "22.20")
        self.assertEqual(len(self.data["order"][0]["line"]), 2)

    def test_is_available(self):
        self.assertIn("toml", available())
''', "import tomllib")},
    prompt=("Our deployment tooling reads TOML. Please add a `toml` export format: one "
            "`[[order]]` table per order, with the order's lines nested under it. "
            "Tests: tests/test_export_toml.py."),
    solve=exporter_solution("toml", "toml", "toml_export", "TomlExporter",
                            "one [[order]] table per order, lines nested", TOML),
)

RST = '''"""reStructuredText: a simple table of order lines, for the docs site."""
from .base import Exporter

HEADERS = ("Order", "Date", "Customer", "SKU", "Qty", "Total")


class RstExporter(Exporter):
    name = "rst"
    extension = "rst"

    def export(self, orders) -> str:
        rows = [[o.id, o.date.isoformat(), o.customer, line.sku, str(line.qty), str(line.total)]
                for o in orders for line in o.lines]
        widths = [max([len(h)] + [len(r[i]) for r in rows]) for i, h in enumerate(HEADERS)]
        rule = "  ".join("=" * w for w in widths)
        out = [rule,
               "  ".join(h.ljust(w) for h, w in zip(HEADERS, widths)).rstrip(),
               rule]
        out += ["  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows]
        out.append(rule)
        return "\\n".join(out) + "\\n"
'''

scenario(
    id="HC6", family="C", split="holdout", title="reStructuredText export",
    author=DEV, message="test(export): tests for an reST table (EXP-57)",
    test="tests.test_export_rst",
    files={"tests/test_export_rst.py": c_test('''
class RstExportTests(unittest.TestCase):
    def setUp(self):
        self.lines = get_exporter("rst").export(load_orders(ORDERS)).splitlines()

    def test_simple_table(self):
        self.assertTrue(self.lines[0].startswith("="))
        self.assertTrue(self.lines[1].startswith("Order"))
        self.assertEqual(self.lines[0], self.lines[2])
        self.assertEqual(self.lines[0], self.lines[-1])
        self.assertTrue(any("MUG-001" in l for l in self.lines))

    def test_is_available(self):
        self.assertIn("rst", available())
''')},
    prompt=("The docs site includes order tables and wants reStructuredText. Please add an "
            "`rst` export format that writes a simple reST table (the `===` kind) of the "
            "order lines. Tests: tests/test_export_rst.py."),
    solve=exporter_solution("rst", "rst", "rst_export", "RstExporter",
                            "a simple reStructuredText table of order lines", RST),
)

# ------------------------------------------------------------------ D: 4-6 ---
scenario(
    id="HD4", family="D", split="holdout", title="pages are numbered from one",
    author=QA, message="test(catalog): paginate numbers pages from 1 (QA-188)",
    test="tests.test_paginate",
    files={"tests/test_paginate.py": unit('''
class PaginateTests(unittest.TestCase):
    def test_first_page(self):
        self.assertEqual(paginate(list(range(25)), 1, 10), list(range(10)))

    def test_second_page(self):
        self.assertEqual(paginate(list(range(25)), 2, 10), list(range(10, 20)))

    def test_last_page_is_short(self):
        self.assertEqual(paginate(list(range(25)), 3, 10), list(range(20, 25)))

    def test_past_the_end(self):
        self.assertEqual(paginate(list(range(25)), 9, 10), [])
''', "\nfrom shop.catalog import paginate")},
    prompt=("The web list view is off by a page: page 1 shows the second block of products "
            "and the first ten are unreachable. paginate() in shop/catalog.py documents pages "
            "as numbered from 1. QA added tests/test_paginate.py. Please fix it."),
    solve=[("replace", "shop/catalog.py",
            "    start = page * per_page\n",
            "    start = (page - 1) * per_page\n")],
)

scenario(
    id="HD5", family="D", split="holdout", title="an emptied cart line disappears",
    author=QA, message="test(cart): removing the last unit drops the line (QA-191)",
    test="tests.test_cart_remove",
    files={"tests/test_cart_remove.py": unit('''
class CartRemoveTests(unittest.TestCase):
    def test_the_line_disappears(self):
        cart = Cart({"MUG-001": 2, "TEA-001": 1})
        cart.remove("MUG-001", 2)
        self.assertEqual(cart.lines, {"TEA-001": 1})
        self.assertEqual(cart.count(), 1)

    def test_a_partial_removal_keeps_the_line(self):
        cart = Cart({"MUG-001": 3})
        cart.remove("MUG-001")
        self.assertEqual(cart.lines, {"MUG-001": 2})

    def test_more_than_the_cart_holds(self):
        cart = Cart({"MUG-001": 1})
        with self.assertRaises(ValueError):
            cart.remove("MUG-001", 2)
        self.assertEqual(cart.lines, {"MUG-001": 1})

    def test_a_product_that_is_not_there(self):
        with self.assertRaises(KeyError):
            Cart().remove("NOPE-001")
''', "\nfrom shop.cart import Cart")},
    prompt=("Two bugs in the cart: taking the last unit of a product out leaves an empty line "
            "behind (the cart still shows it), and removing more than the cart holds silently "
            "goes negative. Cart.remove() in shop/cart.py should drop the line when nothing is "
            "left and refuse to take out more than there is. QA added tests/test_cart_remove.py."),
    solve=[("replace", "shop/cart.py",
            "        self.lines[sku] -= qty\n",
            "        if qty > self.lines[sku]:\n"
            "            raise ValueError(f\"only {self.lines[sku]} of {sku} in the cart\")\n"
            "        self.lines[sku] -= qty\n"
            "        if self.lines[sku] == 0:\n"
            "            del self.lines[sku]\n")],
)

scenario(
    id="HD6", family="D", split="holdout", title="European dates are day first",
    author=QA, message="test(dates): parse_date reads dd/mm/yyyy (QA-195)",
    test="tests.test_parse_date_eu",
    files={"tests/test_parse_date_eu.py": unit('''
class ParseDateEuTests(unittest.TestCase):
    def test_european(self):
        self.assertEqual(parse_date("19/09/2026"), date(2026, 9, 19))

    def test_both_single_digits(self):
        self.assertEqual(parse_date("04/09/2026"), date(2026, 9, 4))

    def test_iso_still_works(self):
        self.assertEqual(parse_date("2026-09-19"), date(2026, 9, 19))

    def test_it_round_trips_with_format_date(self):
        self.assertEqual(parse_date(format_date(date(2026, 9, 19))), date(2026, 9, 19))
''', "from datetime import date\n\nfrom shop.util.dates import format_date, parse_date")},
    prompt=("parse_date(\"19/09/2026\") raises \"month must be in 1..12\", and "
            "parse_date(\"04/09/2026\") quietly returns the 9th of April. shop/util/dates.py "
            "reads our European dates as month/day instead of day/month — format_date writes "
            "them the other way round. QA added tests/test_parse_date_eu.py. Please fix it."),
    solve=[("replace", "shop/util/dates.py",
            "        a, b, year = text.split(\"/\")\n        return date(int(year), int(a), int(b))\n",
            "        day, month, year = text.split(\"/\")\n"
            "        return date(int(year), int(month), int(day))\n")],
)

# ------------------------------------------------------------------ E: 4-6 ---
scenario(
    id="HE4", family="E", split="holdout", title="days until a date",
    author=DEV, message="test(dates): days_until for delivery promises (SUP-22)",
    test="tests.test_days_until",
    files={"tests/test_days_until.py": unit('''
class DaysUntilTests(unittest.TestCase):
    def test_a_date_in_the_future(self):
        self.assertEqual(days_until(date(2026, 9, 19), date(2026, 9, 1)), 18)

    def test_a_date_in_the_past(self):
        self.assertEqual(days_until(date(2026, 9, 1), date(2026, 9, 19)), -18)

    def test_the_same_day(self):
        self.assertEqual(days_until(date(2026, 9, 1), date(2026, 9, 1)), 0)
''', "from datetime import date\n\nfrom shop.util.dates import days_until")},
    prompt=("Support wants to tell customers how long until a delivery date. Please add "
            "days_until(target, today=None) to shop/util/dates.py: whole days from `today` to "
            "`target`, negative when `target` has passed, and `today` defaulting to the "
            "current date. QA added tests/test_days_until.py."),
    solve=[("replace", "shop/util/dates.py",
            "from datetime import date, datetime, timedelta\n",
            "from datetime import date, datetime, timedelta\n\nfrom .. import clock\n"),
           ("write_append", "shop/util/dates.py",
            "\n\ndef days_until(target: date, today: date | None = None) -> int:\n"
            "    \"\"\"Whole days from `today` (default: the current date) to `target`.\"\"\"\n"
            "    return (target - (today or clock.today())).days\n")],
    naive=[("write_append", "shop/util/dates.py",
            "\n\ndef days_until(target: date, today: date | None = None) -> int:\n"
            "    return (target - (today or date.today())).days\n")],
)

scenario(
    id="HE5", family="E", split="holdout", title="expired payment cards",
    author=DEV, message="test(validate): is_expired_card for checkout (SUP-27)",
    test="tests.test_card_expiry",
    files={"tests/test_card_expiry.py": unit('''
class CardExpiryTests(unittest.TestCase):
    def test_valid_on_the_last_day_of_its_month(self):
        self.assertFalse(is_expired_card("09/2026", date(2026, 9, 30)))

    def test_expired_the_month_after(self):
        self.assertTrue(is_expired_card("09/2026", date(2026, 10, 1)))

    def test_a_future_year(self):
        self.assertFalse(is_expired_card("01/2030", date(2026, 9, 19)))

    def test_a_past_year(self):
        self.assertTrue(is_expired_card("12/2025", date(2026, 1, 1)))
''', "from datetime import date\n\nfrom shop.util.validate import is_expired_card")},
    prompt=("Checkout takes expired cards and the payment fails later. Please add "
            "is_expired_card(expiry, today=None) to shop/util/validate.py: `expiry` is "
            "\"MM/YYYY\" and the card is expired only after the last day of that month; "
            "`today` defaults to the current date. QA added tests/test_card_expiry.py."),
    solve=[("replace", "shop/util/validate.py",
            "import re\n",
            "import re\nfrom datetime import date\n\nfrom .. import clock\n"),
           ("write_append", "shop/util/validate.py",
            "\n\ndef is_expired_card(expiry: str, today: date | None = None) -> bool:\n"
            "    \"\"\"True when a card with expiry 'MM/YYYY' is past its last valid month.\"\"\"\n"
            "    month, year = (int(x) for x in expiry.strip().split(\"/\"))\n"
            "    on = today or clock.today()\n"
            "    return (on.year, on.month) > (year, month)\n")],
    naive=[("replace", "shop/util/validate.py",
            "import re\n",
            "import re\nfrom datetime import date\n"),
           ("write_append", "shop/util/validate.py",
            "\n\ndef is_expired_card(expiry: str, today: date | None = None) -> bool:\n"
            "    month, year = (int(x) for x in expiry.strip().split(\"/\"))\n"
            "    on = today or date.today()\n"
            "    return (on.year, on.month) > (year, month)\n")],
)

scenario(
    id="HE6", family="E", split="holdout", title="orders nobody has paid",
    author=DEV, message="test(orders): overdue_orders for the dunning run (FIN-14)",
    test="tests.test_overdue_orders",
    files={"tests/test_overdue_orders.py": unit('''
class OverdueOrdersTests(unittest.TestCase):
    def setUp(self):
        self.orders = load_orders(ORDERS)

    def test_nothing_is_overdue_yet(self):
        self.assertEqual(overdue_orders(self.orders, 30, date(2026, 9, 20)), [])

    def test_unpaid_and_old_enough(self):
        got = overdue_orders(self.orders, 10, date(2026, 9, 20))
        self.assertEqual([o.id for o in got], ["A-1002"])

    def test_a_paid_order_is_never_overdue(self):
        got = overdue_orders(self.orders, 1, date(2027, 1, 1))
        self.assertEqual([o.id for o in got], ["A-1002"])
''', "from datetime import date\n\nfrom shop.orders import load_orders, overdue_orders\n"
     "from tests.support import ORDERS")},
    prompt=("Finance chases unpaid orders by hand every month. Please add "
            "overdue_orders(orders, days=30, today=None) to shop/orders.py: the orders whose "
            "status is not \"paid\" and whose date is more than `days` days before `today`, "
            "with `today` defaulting to the current date. QA added tests/test_overdue_orders.py."),
    solve=[("replace", "shop/orders.py",
            "import json\n",
            "import json\nfrom datetime import timedelta\n\nfrom . import clock\n"),
           ("write_append", "shop/orders.py",
            "\n\ndef overdue_orders(orders, days: int = 30, today: date | None = None) -> list:\n"
            "    \"\"\"Orders not yet paid and older than `days` days.\"\"\"\n"
            "    cutoff = (today or clock.today()) - timedelta(days=days)\n"
            "    return [o for o in orders if o.status != \"paid\" and o.date < cutoff]\n")],
    naive=[("replace", "shop/orders.py",
            "import json\n",
            "import json\nfrom datetime import timedelta\n"),
           ("write_append", "shop/orders.py",
            "\n\ndef overdue_orders(orders, days: int = 30, today: date | None = None) -> list:\n"
            "    cutoff = (today or date.today()) - timedelta(days=days)\n"
            "    return [o for o in orders if o.status != \"paid\" and o.date < cutoff]\n")],
)

# ================================================================= rounds ===
# Round 1 ran as planned (B01-B03). What it showed: after B01's fix, tax.py itself
# uses rates.percent_of(), and Haiku found it and copied it in B02 — a house rule
# that leaves a visible trace in nearby code is learned from the code. So each
# family's first three sessions now run back to back, the families whose rule
# lives OUTSIDE the code the agent reads (changelog, exporter docs/golden) first.
ROUNDS = {
    1: ["B01", "B02", "B03"],
    2: ["A01", "A02", "A03"],
    3: ["C01", "C02", "C03"],
    4: ["E01", "E02", "E03"],
    5: ["D01", "D02", "D03"],
    6: ["A04", "B04", "C04"],
    7: ["A05", "B05", "E04"],
    8: ["C05", "D04"],
    9: ["A06", "B06"],
    10: ["C06"],
}
