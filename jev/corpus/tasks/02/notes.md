apply_discount() was truncating percentage to int part, ignoring decimals like .5 in 12.5%; reuse existing percent_of() from rates module for correct fractional handling

area: none
