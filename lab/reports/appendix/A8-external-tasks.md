# A8 · The second repository's tasks

Mined from `structlog`'s own history at base `73393f34b4`: 12 validated, 10 rejected. For each, the implementation is reverted at its own commit and the tests are kept as the specification.

## X01 · stdlib: Add snake_case shims for isEnabledFor & getEffectiveLevel (#818)

- commit `0eef50d9dc`, parent `f194271d99`
- implementation reverted: `src/structlog/stdlib.py`
- the check: `python -m pytest -q tests/test_stdlib.py`
- broken state: `2 failed, 139 passed in 0.34s`
- rest of the suite on the broken state: `790 passed, 17 skipped, 2 warnings in 1.16s`

**What the user asks**

> Add snake_case shims for isEnabledFor & getEffectiveLevel (#818). The tests for this are in tests/test_stdlib.py and they are failing. Please fix it.

## X02 · Correctly unpickle WriteLogger (#811)

- commit `c6e7cad18f`, parent `de5dcd4127`
- implementation reverted: `src/structlog/_output.py`
- the check: `python -m pytest -q tests/test_output.py`
- broken state: `18 failed, 118 passed, 18 warnings in 0.25s`
- rest of the suite on the broken state: `791 passed, 17 skipped, 2 warnings in 1.21s`

**What the user asks**

> Correctly unpickle WriteLogger (#811). The tests for this are in tests/test_output.py and they are failing. Please fix it.

## X03 · Add name attribute to BytesLogger (#786)

- commit `3763c623c1`, parent `2796b22ee1`
- implementation reverted: `src/structlog/_output.py`
- the check: `python -m pytest -q tests/test_output.py tests/test_stdlib.py`
- broken state: `34 failed, 241 passed, 18 warnings in 0.60s`
- rest of the suite on the broken state: `652 passed, 17 skipped, 2 warnings in 0.96s`

**What the user asks**

> Add name attribute to BytesLogger (#786). BytesLogger lacked a `name` attribute, causing `add_logger_name` to raise AttributeError when used with BytesLoggerFactory. The first positional argument passed to BytesLoggerFactory (the logger name from. The tests for this are in tests/test_output.py, tests/test_stdlib.py and they are failing. Please fix it.

## X04 · Monochrome Rich traceback rendering w/ ConsoleRenderer(colors=False) (#794)

- commit `2796b22ee1`, parent `b2f3daf0b5`
- implementation reverted: `src/structlog/dev.py`
- the check: `python -m pytest -q tests/test_dev.py`
- broken state: `1 failed, 95 passed, 4 skipped in 0.23s`
- rest of the suite on the broken state: `817 passed, 13 skipped, 20 warnings in 1.25s`

**What the user asks**

> Monochrome Rich traceback rendering w/ ConsoleRenderer(colors=False) (#794). The tests for this are in tests/test_dev.py and they are failing. Please fix it.

## X05 · Use WeakKeyDictionary for WRITE_LOCKS to prevent file object leaks (#807)

- commit `79032b3f93`, parent `92fd882817`
- implementation reverted: `src/structlog/_output.py`
- the check: `python -m pytest -q tests/test_output.py`
- broken state: `3 failed, 121 passed in 0.15s`
- rest of the suite on the broken state: `786 passed, 17 skipped, 2 warnings in 1.20s`

**What the user asks**

> Use WeakKeyDictionary for WRITE_LOCKS to prevent file object leaks (#807). File objects registered in WRITE_LOCKS were never released, causing a memory leak in long-running processes that open many log files (e.g., task executors creating a per-task BytesLogger or WriteLogger). The tests for this are in tests/test_output.py and they are failing. Please fix it.

## X06 · Deprecate better-exceptions integration (#802)

- commit `f0b2487050`, parent `2c059a0dc0`
- implementation reverted: `src/structlog/dev.py`
- the check: `python -m pytest -q tests/test_dev.py`
- broken state: `2 failed, 91 passed, 4 skipped in 0.24s`
- rest of the suite on the broken state: `814 passed, 13 skipped, 2 warnings in 1.17s`

**What the user asks**

> Deprecate better-exceptions integration (#802). The tests for this are in tests/test_dev.py and they are failing. Please fix it.

## X07 · stdlib: add support for stacklevel (#763)

- commit `ecaa15ac6b`, parent `7f7a221aed`
- implementation reverted: `src/structlog/_frames.py`, `src/structlog/stdlib.py`
- the check: `python -m pytest -q tests/test_frames.py`
- broken state: `2 failed, 12 passed in 0.03s`
- rest of the suite on the broken state: `893 passed, 17 skipped, 2 warnings in 1.30s`

**What the user asks**

> Add support for stacklevel (#763). The tests for this are in tests/test_frames.py and they are failing. Please fix it.

## X08 · dev: add pad_level property

- commit `bac52127fd`, parent `6c11ae9a65`
- implementation reverted: `src/structlog/dev.py`
- the check: `python -m pytest -q tests/test_dev.py`
- broken state: `1 failed, 86 passed, 4 skipped in 0.21s`
- rest of the suite on the broken state: `810 passed, 13 skipped, 2 warnings in 1.16s`

**What the user asks**

> Add pad_level property. The tests for this are in tests/test_dev.py and they are failing. Please fix it.

## X09 · dev: add level-styles properties

- commit `9ac5612725`, parent `1e51f5f6a2`
- implementation reverted: `src/structlog/dev.py`
- the check: `python -m pytest -q tests/test_dev.py`
- broken state: `1 failed, 85 passed, 4 skipped in 0.20s`
- rest of the suite on the broken state: `810 passed, 13 skipped, 2 warnings in 1.11s`

**What the user asks**

> Add level-styles properties. The tests for this are in tests/test_dev.py and they are failing. Please fix it.

## X10 · dev: add colors and force_colors properties (#759)

- commit `1e51f5f6a2`, parent `bf51b4a2a5`
- implementation reverted: `src/structlog/dev.py`
- the check: `python -m pytest -q tests/test_dev.py`
- broken state: `6 failed, 77 passed, 4 skipped in 0.24s`
- rest of the suite on the broken state: `810 passed, 13 skipped, 2 warnings in 1.12s`

**What the user asks**

> Add colors and force_colors properties (#759). The tests for this are in tests/test_dev.py and they are failing. Please fix it.

## X11 · dev: get_active_console_renderer → ConsoleRenderer.get_active

- commit `bc67e8a7c1`, parent `d3e15eb608`
- implementation reverted: `src/structlog/dev.py`
- the check: `python -m pytest -q tests/test_dev.py`
- broken state: `3 failed, 74 passed, 4 skipped in 0.20s`
- rest of the suite on the broken state: `810 passed, 13 skipped, 2 warnings in 1.12s`

**What the user asks**

> Get_active_console_renderer → ConsoleRenderer.get_active. The tests for this are in tests/test_dev.py and they are failing. Please fix it.

## X12 · dev: allow columns to be got and set (#757)

- commit `b0081ac705`, parent `509902ceb2`
- implementation reverted: `src/structlog/dev.py`
- the check: `python -m pytest -q tests/test_dev.py`
- broken state: `1 failed, 76 passed, 4 skipped in 0.19s`
- rest of the suite on the broken state: `810 passed, 13 skipped, 2 warnings in 1.20s`

**What the user asks**

> Allow columns to be got and set (#757). The tests for this are in tests/test_dev.py and they are failing. Please fix it.

