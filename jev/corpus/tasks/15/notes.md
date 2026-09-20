truncate() was concatenating text[:width] + ellipsis instead of text[:width - len(ellipsis)] + ellipsis, producing strings longer than the specified width
area: check-changelog-on-shop-edits
