---
name: prefer-pathlib-over-os-path
description: When a function handles filesystem paths, build them with pathlib.Path
---

# Paths

`pathlib.Path` reads better than string joining and carries its own helpers.

1. Take `Path` objects in signatures that accept a path, and accept `str` only
   at the edge where a caller hands one in.
2. Build a child path with the `/` operator: `root / "data" / "catalog.json"`.
3. Read and write through `Path.read_text()` and `Path.write_text()` with an
   explicit `encoding="utf-8"` rather than opening a file by hand.
4. Use `Path.resolve()` once, at the boundary, and pass the resolved path down
   instead of resolving it again in every function that receives it.

A signature that accepts both a string and a Path should say so in its
annotation (`str | Path`) so a reader knows which forms are handled.
