cart.reserve() and cart.is_expired() were using datetime.now(timezone.utc) directly instead of shop.clock.now(), violating the project's time handling convention

area: check-changelog-on-shop-edits
