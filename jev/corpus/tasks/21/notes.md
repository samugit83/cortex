prorated_refund() rounded the daily rate first (amount.cents // days_total) instead of calculating exact refund then rounding, causing €6.69 instead of €6.66; fixed using scale(amount, unused_days, days_total) for exact integer arithmetic

area: check-changelog-on-shop-edits, use-billing-helpers
