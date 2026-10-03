# `ideal` — the forms the lab's design predicted

Written by hand from `CONTRIBUTING.md` and the family definitions in
`lab/bin/scenarios.py`, before any run of the evaluation programme, and never
from the text of an evolved item. It is the ceiling the loop is measured
against: what someone who already knew all four house rules *and* Cortex's tier
model would have installed on day one.

| Family | Rule | Form | Why that form |
|---|---|---|---|
| A | CHANGELOG for user-visible changes | always-on skill | a **moment** ("before finishing"), not an area |
| B | integer-cent money helpers | rule on `shop/billing/**` | an **area** the agent reads |
| C | the four files a new exporter needs | gated skill on `shop/plugins/**` | an area it **creates in**, named by the task |
| E | read the clock through `shop.clock` | always-on skill | repo-wide, and not tied to any one file |

`swapped/` is the same four rules in the other form, and the pair is the test of
whether the form matters at all (H11).
