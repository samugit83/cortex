# T2 · Scenario inventory

A scenario is excluded from a run when, on that run's final code, its test does not fail or its reference fix does not apply and pass (PREREGISTRATION.md §5.1). Exclusion is identical in every arm.

| id | family | split | title | round | test | rule-breaking fix | excluded from |
|---|---|---|---|---|---|---|---|
| B01 | B | train | fractional tax rates | 1 | tests.test_tax_rates | yes | — |
| B02 | B | train | fractional discounts | 1 | tests.test_discount_rates | yes | — |
| B03 | B | train | four-decimal exchange rates | 1 | tests.test_fx_rates | yes | — |
| B04 | B | train | pro-rata shipping by weight | 6 | tests.test_shipping_weights | yes | — |
| B05 | B | train | exact prorated refunds | 7 | tests.test_refund_proration | yes | — |
| B06 | B | train | price per kilo labels | 9 | tests.test_price_per_kg | yes | — |
| HB1 | B | holdout | fractional loyalty point value | — | tests.test_loyalty_value | yes | — |
| HB2 | B | holdout | installment fees and exact split | — | tests.test_installment_fees | yes | — |
| HB3 | B | holdout | net price at reduced VAT rates | — | tests.test_vat_reduced | yes | — |
| D01 | D | train | slugify with accents | 5 | tests.test_slugify_accents | — | — |
| D02 | D | train | truncate respects the width | 5 | tests.test_truncate_width | — | — |
| D03 | D | train | pluralize zero | 5 | tests.test_pluralize_zero | — | — |
| D04 | D | train | business days skip Saturdays | 8 | tests.test_business_days_weekend | — | — |
| HD1 | D | holdout | e-mail needs a domain dot | — | tests.test_email_domain | — | — |
| HD2 | D | holdout | phone numbers keep the plus | — | tests.test_phone_prefix | — | — |
| HD3 | D | holdout | search ignores case | — | tests.test_search_case | — | — |
| A01 | A | train | list cheapest first by default | 2 | tests.test_list_default_sort | yes | — |
| A02 | A | train | thousands separator in prices | 2 | tests.test_money_display | yes | — |
| A03 | A | train | report total row | 2 | tests.test_report_total | yes | — |
| A04 | A | train | out of stock label | 6 | tests.test_show_out_of_stock | yes | — |
| A05 | A | train | list --limit | 7 | tests.test_list_limit | yes | — |
| A06 | A | train | ISO dates in the report | 9 | tests.test_report_iso_dates | yes | — |
| HA1 | A | holdout | cart summary wording | — | tests.test_cart_summary | yes | — |
| HA2 | A | holdout | unknown product error | — | tests.test_show_unknown | yes | — |
| HA3 | A | holdout | list --category | — | tests.test_list_category | yes | — |
| C01 | C | train | XML export | 3 | tests.test_export_xml | yes | — |
| C02 | C | train | Markdown export | 3 | tests.test_export_markdown | yes | — |
| C03 | C | train | TSV export | 3 | tests.test_export_tsv | yes | — |
| C04 | C | train | NDJSON export | 6 | tests.test_export_ndjson | yes | — |
| C05 | C | train | HTML export | 8 | tests.test_export_html | yes | — |
| C06 | C | train | YAML export | 10 | tests.test_export_yaml | yes | — |
| HC1 | C | holdout | text receipt export | — | tests.test_export_receipt | yes | — |
| HC2 | C | holdout | INI export | — | tests.test_export_ini | yes | — |
| HC3 | C | holdout | LaTeX export | — | tests.test_export_latex | yes | — |
| E01 | E | train | invoice due date | 4 | tests.test_due_date | yes | — |
| E02 | E | train | cart reservation expiry | 4 | tests.test_cart_reservation | yes | — |
| E03 | E | train | archive old orders | 4 | tests.test_order_archive | yes | — |
| E04 | E | train | new arrivals | 7 | tests.test_new_arrivals | yes | — |
| HE1 | E | holdout | orders in the last N days | — | tests.test_report_period | yes | — |
| HE2 | E | holdout | loyalty points expire | — | tests.test_points_expiry | yes | — |
| HE3 | E | holdout | stale stock | — | tests.test_stale_stock | yes | — |
| HA4 | A | holdout | export to a file | — | tests.test_export_output | yes | — |
| HA5 | A | holdout | invoice item count | — | tests.test_invoice_items | yes | — |
| HA6 | A | holdout | show the restock date | — | tests.test_show_restocked | yes | R4 |
| HB4 | B | holdout | store credit with a bonus factor | — | tests.test_credit_bonus | yes | — |
| HB5 | B | holdout | refunds that add up exactly | — | tests.test_refund_installments | yes | — |
| HB6 | B | holdout | VAT-inclusive price from a net price | — | tests.test_vat_gross | yes | — |
| HC4 | C | holdout | SQL export | — | tests.test_export_sql | yes | — |
| HC5 | C | holdout | TOML export | — | tests.test_export_toml | yes | — |
| HC6 | C | holdout | reStructuredText export | — | tests.test_export_rst | yes | — |
| HD4 | D | holdout | pages are numbered from one | — | tests.test_paginate | — | — |
| HD5 | D | holdout | an emptied cart line disappears | — | tests.test_cart_remove | — | — |
| HD6 | D | holdout | European dates are day first | — | tests.test_parse_date_eu | — | — |
| HE4 | E | holdout | days until a date | — | tests.test_days_until | yes | — |
| HE5 | E | holdout | expired payment cards | — | tests.test_card_expiry | yes | — |
| HE6 | E | holdout | orders nobody has paid | — | tests.test_overdue_orders | yes | — |
