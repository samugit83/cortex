# Time

Never call `datetime.now()`, `datetime.utcnow()`, `date.today()` or `time.time()`
anywhere under `shop/`.

- `shop.clock.now()` — the current instant, UTC and timezone-aware
- `shop.clock.today()` — the current date

Tests freeze it with `clock.freeze()`, which is why the direct calls are rejected.
`make lint` checks this over the whole of `shop/`.
