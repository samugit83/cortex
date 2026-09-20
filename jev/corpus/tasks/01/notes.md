tax_for() only used whole percentage, ignored fractional part (8.25 → 8), and lacked rounding; solution: delegate to percent_of() helper which handles exact arithmetic
area: none
