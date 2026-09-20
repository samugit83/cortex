#!/usr/bin/env python3
"""harness.py — the routing layer: which skills and rules exist, when each one
loads, and what a rollout actually loaded.

Claude Code decides what enters context. Cortex only has to know the rules it
uses, verified against Claude Code 2.1.276:

  skill, no `paths`        description always listed; the model chooses it
  skill with `paths`       invisible until a matching file is Read or Written
  rule with `paths`        body injected when a matching file is Read, or is
                           @-mentioned in the prompt. Never on Write.
  glob without a `/`       matches the file name at any depth
  glob with a `/`          anchored at the repository root
  a directory match        covers everything below it (`lib/*` loads for
                           lib/x/c.py; `src/*.py` does not for src/sub/b.py)
  `*` and `**`             match dotfiles and dot-directories too
  `{a,b}`                  brace alternatives are expanded

Subcommands (all read-only except where noted):

  check [--candidate N] [--replace "A B"] [--tasks "01 02"] [--quiet]
        validate every live skill and rule (and a candidate), print the routing
        table. Exit 1 on errors. Live items only WARN: files Cortex did not
        write must never block it. The candidate gets the strict rules.
  summary                         one JSON object for `cortex status`
  hash                            fingerprint of the live harness
  touching <fix.patch>            which items cover the files a fix touched
  fixpatch [--base SHA] [--head SHA]
                                  the fix as a patch, NEW files included
                                  (`git diff` drops them)
  transcripts [--days N] [--dir]  THIS project's session transcripts (last
                                  lookback_days), newest first — never another project's
  evolve-phase [--json]           where the /evolve cycle stands (A, B, C, D,
                                  relaunch, prune), decided from the files
  task new --base SHA [--head SHA] [--title T]
                                  create the next .evolve/tasks/NN/ with
                                  fix.patch and task.yaml (used by /harvest)
  observe <stream> <harness> <sandbox> <prompt.txt>
                                  what one rollout loaded (used by sweep.sh)
  candidate-info <name>           {"kind": "skill"|"rule", "tier": ...}
  cli-version [--min V]           installed Claude Code version; exit 1 when
                                  below V, 2 when it cannot be determined
  parallel --kind rollouts|preflight [--jobs N] [--override auto|N] [--json]
                                  how many run at once: a number from config, or
                                  auto — sized from ram_percent of the RAM
                                  available now (used by sweep.sh, preflight.sh)
  usage [--days N] [--json]       how each item was used in your real sessions
                                  over N days, and which tasks can measure it.
                                  ADVISORY: it decides what /prune tests and on
                                  which tasks — never what gets deleted
  prune plan|approve|cancel|next|record|finish|status|estimate
                                  the /prune pass: a plan with a cost estimate
                                  that runs only after the user approves it

Stdlib only, and never a shell: every git call is an argument list.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

NAME_STRICT = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_LOOSE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SHA = re.compile(r"^[0-9a-f]{7,40}$")
MAX_DESC = 1536          # Claude Code truncates description + when_to_use here
MAX_BRACE = 256          # a pattern expanding past this is refused, not matched
DEFAULT_BUDGET = 3000
# project memory Claude Code loads at session start, every turn
ALWAYS_LOADED_MEMORY = ("CLAUDE.md", os.path.join(".claude", "CLAUDE.md"), "CLAUDE.local.md")


# --------------------------------------------------------------- utilities --
def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def repo_root():
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode != 0:
        die("not inside a git repository")
    return r.stdout.strip()


def die(msg, code=1):
    print(f"harness: {msg}", file=sys.stderr)
    sys.exit(code)


def load_config(repo):
    """config.json, recompiled first when config.yaml is newer — as sweep.sh
    does — so a plan's estimate and a sweep never read two different k's."""
    ev = os.path.join(repo, ".evolve")
    src, dst = os.path.join(ev, "config.yaml"), os.path.join(ev, "config.json")
    if os.path.exists(src) and (not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst)):
        comp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compile-config.py")
        subprocess.run([sys.executable, comp, repo, "--quiet"], capture_output=True)
    try:
        with open(dst) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def valid_loose(name):
    return bool(name) and name not in (".", "..") and bool(NAME_LOOSE.match(name))


def within(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


# ------------------------------------------------------------- frontmatter --
class FrontmatterError(Exception):
    pass


def _strip_comment(v):
    """drop a trailing YAML comment (' # ...', or a whole '# ...') that is not
    inside quotes"""
    q = None
    for i, ch in enumerate(v):
        if q:
            if ch == q:
                q = None
            continue
        if ch in "\"'" and (i == 0 or v[i - 1] in " \t[,"):
            q = ch
        elif ch == "#" and (i == 0 or v[i - 1] in " \t"):
            return v[:i].rstrip()
    return v


def _unquote(v, lineno):
    v = _strip_comment(v.strip())
    if len(v) >= 2 and v[0] == v[-1] == '"':
        try:
            return json.loads(v)          # YAML double-quote escapes are JSON's
        except ValueError:
            return v[1:-1]
    if len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1].replace("''", "'")
    if v[:1] in ('"', "'"):
        raise FrontmatterError(f"line {lineno}: unterminated quote")
    # plain scalar: reject what real YAML rejects, because Claude Code would
    # then silently drop the whole item (or treat a rule as unconditional)
    if v.startswith("&") and " " in v:          # an anchor: '&name value' is just value
        v = v.split(" ", 1)[1].strip()
    if v[:1] in ("*", "&", "!", "{", "[", "%", "@", "`") or v.startswith("? ") or v == "?":
        raise FrontmatterError(f"line {lineno}: unquoted value starts with '{v[0]}': quote it")
    if ": " in v or v.endswith(":"):
        raise FrontmatterError(f"line {lineno}: unquoted value contains ': ': quote it")
    return v


def _split_top(s, sep=","):
    """split on sep outside {} [] and quotes"""
    out, cur, depth, q = [], "", 0, None
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = None
            continue
        if ch in "\"'":
            q = ch
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def _block_scalar(indicator, lines):
    """fold (>) or keep (|) indented lines, YAML-style, with default chomping"""
    body = [ln for ln in lines]
    while body and not body[-1].strip():
        body.pop()
    ind = min((len(l) - len(l.lstrip()) for l in body if l.strip()), default=0)
    body = [l[ind:] if l.strip() else "" for l in body]
    if indicator.startswith("|"):
        text = "\n".join(body)
    else:
        paras, cur = [], []
        for l in body:
            if l == "":
                paras.append(" ".join(cur))
                cur = []
            else:
                cur.append(l.strip())
        paras.append(" ".join(cur))
        text = "\n".join(paras)
    return text if indicator.endswith("-") else text + "\n" if text else text


def parse_frontmatter(text):
    """-> (fields: dict, body: str). Raises FrontmatterError.

    A file without a leading '---' has no frontmatter; that is not an error
    (a rule may be plain markdown)."""
    text = text.lstrip("﻿").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}, text
    end = re.search(r"^---[ \t]*$", text[4:], re.M)
    if not end:
        raise FrontmatterError("frontmatter is never closed with '---'")
    raw = text[4:4 + end.start()].split("\n")
    body = text[4 + end.end():].lstrip("\n")
    fields, i = {}, 0
    while i < len(raw):
        line, lineno = raw[i], i + 2
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line[0] in " \t":
            raise FrontmatterError(f"line {lineno}: unexpected indentation")
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:(.*)$", line)
        if not m:
            raise FrontmatterError(f"line {lineno}: cannot parse {line!r}")
        key, val = m.group(1), _strip_comment(m.group(2).strip())
        if key in fields:     # strict YAML loaders reject this; which copy wins is undefined
            raise FrontmatterError(f"line {lineno}: duplicate key '{key}'")
        i += 1
        block = []
        while i < len(raw) and (not raw[i].strip() or raw[i][0] in " \t"):
            block.append(raw[i])
            i += 1
        if val in (">", ">-", ">+", "|", "|-", "|+"):
            fields[key] = _block_scalar(val, block)
        elif val == "":
            items = [_strip_comment(b.strip()) for b in block]
            items = [x for x in items if x]
            if items and all(x.startswith("- ") or x == "-" for x in items):
                fields[key] = [_unquote(x[2:], lineno) for x in items if x != "-"]
            elif items:   # a nested mapping (metadata:): keep it, unvalidated
                fields[key] = {x.split(":", 1)[0].strip(): x.split(":", 1)[1].strip()
                               for x in items if ":" in x}
            else:
                fields[key] = ""
        elif val.startswith("["):
            if not val.endswith("]"):
                raise FrontmatterError(f"line {lineno}: unterminated flow list")
            fields[key] = [_unquote(x, lineno) for x in _split_top(val[1:-1])]
        else:
            fields[key] = _unquote(val, lineno)
            if block and any(b.strip() for b in block):
                # a plain scalar continued on indented lines: YAML folds it
                fields[key] = " ".join([fields[key]] + [b.strip() for b in block if b.strip()])
    return fields, body


def split_paths(value):
    if value is None or value == "":
        return []
    if isinstance(value, list):
        out = []
        for v in value:
            out.extend(_split_top(v) if isinstance(v, str) and "," in v and "{" not in v else [v])
        return [p.strip() for p in out if p and p.strip()]
    if isinstance(value, str):
        return _split_top(value)
    return []


# -------------------------------------------------------------------- globs --
def expand_braces(pat, cap=MAX_BRACE):
    """{a,b} expansion, nested. Raises ValueError past `cap` patterns."""
    depth, start = 0, None
    for i, ch in enumerate(pat):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0:
                alts = _split_top(pat[start + 1:i])
                if len(alts) < 2 and "," not in pat[start + 1:i]:
                    continue          # "{x}" is literal
                out = []
                for alt in (alts or [""]):
                    out.extend(expand_braces(pat[:start] + alt + pat[i + 1:], cap))
                    if len(out) > cap:
                        raise ValueError(f"brace expansion of {pat!r} exceeds {cap} patterns")
                return out
    return [pat]


def glob_to_regex(pat):
    p = pat.strip()
    while p.startswith("./"):
        p = p[2:]
    p = p.lstrip("/")
    if p.endswith("/"):
        p += "**"
    if "/" not in p:            # verified: a slash-less pattern matches at any depth
        p = "**/" + p
    out, i = "", 0
    while i < len(p):
        c = p[i]
        if p.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif p.startswith("**", i):
            out += ".*"
            i += 2
        elif c == "*":
            out += "[^/]*"
            i += 1
        elif c == "?":
            out += "[^/]"
            i += 1
        elif c == "[":
            j = p.find("]", i + 1)
            if j == -1:
                out += re.escape(c)
                i += 1
            else:
                cls = p[i + 1:j]
                if cls.startswith("!"):
                    cls = "^" + cls[1:]
                out += "[" + cls.replace("\\", "\\\\") + "]"
                i = j + 1
        else:
            out += re.escape(c)
            i += 1
    return re.compile("^" + out + "$")


class Globs:
    def __init__(self, patterns):
        self.patterns = list(patterns)
        self.regexes, self.error = [], None
        try:
            for p in self.patterns:
                for e in expand_braces(p):
                    self.regexes.append(glob_to_regex(e))
        except (ValueError, re.error) as ex:
            self.error = str(ex)
            self.regexes = []

    def match(self, path):
        """Claude Code matches a file when the pattern matches the file OR any
        directory containing it (verified: `lib/*` loads for lib/x/c.py, a bare
        `src` for src/sub/a.py; `src/*.py` does NOT load for src/sub/b.py)."""
        while path.startswith("./"):
            path = path[2:]
        parts = path.split("/")
        cands = ["/".join(parts[:i]) for i in range(len(parts), 0, -1)]
        return any(r.match(c) for c in cands for r in self.regexes)

    def any_of(self, paths):
        return [p for p in paths if self.match(p)]


# -------------------------------------------------------------------- items --
class Item:
    """a skill (.claude/skills/<n>/SKILL.md) or a rule (.claude/rules/<n>.md)"""

    def __init__(self, kind, name, path, root_for_symlinks, owner="live"):
        self.kind, self.name, self.path, self.owner = kind, name, path, owner
        self.fields, self.body, self.problems, self.warnings = {}, "", [], []
        self.globs = Globs([])
        try:
            with open(path, encoding="utf-8") as fh:
                self.fields, self.body = parse_frontmatter(fh.read())
        except FrontmatterError as ex:
            self.problems.append(f"frontmatter: {ex}")
        except (OSError, UnicodeDecodeError) as ex:
            self.problems.append(f"cannot read: {ex}")
        self.patterns = split_paths(self.fields.get("paths"))
        self.globs = Globs(self.patterns)
        if self.globs.error:
            self.problems.append(f"paths: {self.globs.error}")
        self._symlinks(root_for_symlinks)

    def _symlinks(self, repo):
        top = os.path.dirname(self.path) if self.kind == "skill" else self.path
        walk = [top] if os.path.isfile(top) else [top] + [
            os.path.join(d, f) for d, ds, fs in os.walk(top) for f in fs + ds]
        for p in walk:
            if os.path.islink(p) and not within(p, repo):
                self.problems.append(
                    f"symlink {os.path.relpath(p, repo)} points outside the repository "
                    f"({os.path.realpath(p)}): a sweep would copy it into the sandbox")

    @property
    def description(self):
        d = self.fields.get("description", "")
        return d if isinstance(d, str) else ""

    @property
    def tier(self):
        if self.kind == "rule":
            return "rule" if self.patterns else "rule-always"
        if str(self.fields.get("disable-model-invocation", "")).lower() == "true":
            return "manual"
        return "gated" if self.patterns else "always"

    @property
    def always_on_chars(self):
        if self.tier == "always":
            w = self.fields.get("when_to_use", "")
            return min(len(self.description) + len(w if isinstance(w, str) else ""), MAX_DESC)
        if self.tier == "rule-always":
            return len(self.body)
        return 0

    @property
    def trigger(self):
        if self.kind == "rule":
            first = next((l.strip("# ").strip() for l in self.body.splitlines() if l.strip()), "")
            return first[:60]
        return re.split(r"(?<=[.!?])\s", self.description.strip(), 1)[0][:60]

    def validate(self, repo):
        """item-local checks. For a candidate they are errors, for a live item
        warnings: Cortex must not refuse to run because of files it did not write."""
        if not NAME_STRICT.match(self.name.split("/")[-1]) or len(self.name) > 64:
            self.problems.append(f"name '{self.name}' is not lowercase-hyphenated (a-z, 0-9, -) "
                                 "of at most 64 characters")
        if self.kind == "skill":
            fname = self.fields.get("name")
            if fname and fname != self.name:
                self.problems.append(f"frontmatter name '{fname}' differs from its directory '{self.name}'")
            if self.tier in ("always", "gated") and not self.description.strip():
                self.problems.append("no description: it can never be chosen")
            w = self.fields.get("when_to_use", "")
            n = len(self.description) + len(w if isinstance(w, str) else "")
            if n > MAX_DESC:
                self.problems.append(f"description + when_to_use is {n} characters; "
                                     f"Claude Code cuts it at {MAX_DESC}")
            if os.path.exists(os.path.join(repo, ".claude", "commands", self.name + ".md")):
                self.problems.append(f"'{self.name}' is also a command in .claude/commands/: they collide")
        if self.kind == "rule" and not self.patterns:
            self.warnings.append("no `paths`: this rule is loaded on every turn — it belongs in CLAUDE.md")
        for p in self.cited_paths(repo):
            self.warnings.append(f"cites {p}, which does not exist (drift: the code moved, the text did not)")

    def cited_paths(self, repo):
        """Repository paths named in the body (markdown links, `backticked`)
        that do not resolve. Conservative: only tokens that look like a real
        relative file path, so commands and placeholders never warn."""
        missing = set()
        for m in re.finditer(r"\]\(([^)\s]+)\)|`([^`\s]+)`", self.body):
            p = (m.group(1) or m.group(2) or "").split("#")[0]
            if (not p or "/" not in p or p.startswith(("http:", "https:", "mailto:", "/", "~", "-", "$", "."))
                    or re.search(r"[<>*{}$|?\[\]=:@]", p)
                    or not re.search(r"\.[A-Za-z0-9]{1,6}$", p)):
                continue
            if not any(os.path.exists(os.path.join(b, p)) for b in (repo, os.path.dirname(self.path))):
                missing.add(p)
        return sorted(missing)


def load_live(repo):
    items, notes = [], []
    sdir = os.path.join(repo, ".claude", "skills")
    if os.path.isdir(sdir):
        for n in sorted(os.listdir(sdir)):
            d = os.path.join(sdir, n)
            if not os.path.isdir(d):
                continue
            f = os.path.join(d, "SKILL.md")
            if not os.path.isfile(f):
                notes.append(f".claude/skills/{n}/ has no SKILL.md: Claude Code ignores it")
                continue
            items.append(Item("skill", n, f, repo))
    rdir = os.path.join(repo, ".claude", "rules")
    if os.path.isdir(rdir):
        # Claude Code follows symlinks in .claude/rules, so this does too; a
        # link that leaves the repository is refused by scan_symlinks().
        seen = set()
        for d, ds, fs in sorted(os.walk(rdir, followlinks=True)):
            real = os.path.realpath(d)
            if real in seen:            # a symlink loop
                ds[:] = []
                continue
            seen.add(real)
            ds.sort()
            for f in sorted(fs):
                if not f.endswith(".md"):
                    continue
                rel = os.path.relpath(os.path.join(d, f), rdir)[:-3]
                it = Item("rule", rel, os.path.join(d, f), repo)
                if "/" in rel:
                    it.warnings.append("rule in a sub-directory: it is measured as part of the "
                                       "harness, but /prune cannot address it — move it to "
                                       f".claude/rules/{rel.split('/')[-1]}.md to manage it")
                items.append(it)
    nested = [p for p in git(repo, "ls-files", check=False).splitlines()
              if re.match(r"^.+/\.claude/skills/[^/]+/SKILL\.md$", p)]
    for p in nested:
        notes.append(f"{p}: a nested .claude/skills is loaded by Claude Code but never "
                     "snapshotted by a sweep — use `paths:` in .claude/skills/ instead")
    return items, notes


def scan_symlinks(repo):
    """Every symlink anywhere under .claude/skills and .claude/rules (and the
    two folders themselves) must resolve inside the repository. The sweep
    copies these trees dereferenced into the sandbox an unattended agent works
    in; a link out of the repo would carry a file from your home directory
    there. Dangling links are refused too: they would break the copy."""
    bad = []
    for top in (os.path.join(repo, ".claude", "skills"), os.path.join(repo, ".claude", "rules")):
        if not os.path.lexists(top):
            continue
        entries = [top]
        if os.path.isdir(top):
            for d, ds, fs in os.walk(top):          # followlinks=False: inspect, never enter
                entries += [os.path.join(d, x) for x in ds + fs]
        for p in entries:
            if not os.path.islink(p):
                continue
            rel = os.path.relpath(p, repo)
            if not os.path.exists(p):
                bad.append(f"symlink {rel} is dangling ({os.readlink(p)}): a sweep could not copy it")
            elif not within(p, repo):
                bad.append(f"symlink {rel} points outside the repository ({os.path.realpath(p)}): "
                           "a sweep would copy that file into the sandbox")
    return bad


def load_candidate(repo, name):
    d = os.path.join(repo, ".evolve", "candidate", name)
    if not os.path.isdir(d):
        return None, [f"no such candidate: .evolve/candidate/{name}"]
    has_s = os.path.isfile(os.path.join(d, "SKILL.md"))
    has_r = os.path.isfile(os.path.join(d, "RULE.md"))
    if has_s == has_r:
        return None, [f"candidate {name} must contain exactly one of SKILL.md (a skill) "
                      "or RULE.md (a rule)"]
    if has_s:
        return Item("skill", name, os.path.join(d, "SKILL.md"), repo, owner="candidate"), []
    extra = [f for f in os.listdir(d) if f != "RULE.md"]
    it = Item("rule", name, os.path.join(d, "RULE.md"), repo, owner="candidate")
    if extra:
        it.problems.append(f"a rule is a single file; remove {', '.join(sorted(extra))}")
    return it, []


# -------------------------------------------------------------------- tasks --
class Tasks:
    def __init__(self, repo):
        self.repo, self._trees = repo, {}

    def ids(self, wanted):
        tdir = os.path.join(self.repo, ".evolve", "tasks")
        if wanted:
            return wanted.split()
        if not os.path.isdir(tdir):
            return []
        return sorted(t for t in os.listdir(tdir)
                      if t != "_broken" and os.path.isdir(os.path.join(tdir, t)))

    def sha(self, tid):
        try:
            with open(os.path.join(self.repo, ".evolve", "tasks", tid, "task.yaml")) as fh:
                for line in fh:
                    if line.startswith("base_sha:"):
                        return line.split(":", 1)[1].strip().strip("'\"")
        except OSError:
            return None
        return None

    def tree(self, sha):
        if sha not in self._trees:
            self._trees[sha] = git(self.repo, "ls-tree", "-r", "--name-only", sha, "--",
                                   check=False).splitlines()
        return self._trees[sha]

    def patch_paths(self, tid):
        p = os.path.join(self.repo, ".evolve", "tasks", tid, "fix.patch")
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                return patch_files(fh.read())
        except OSError:
            return [], []


def patch_files(text):
    """-> (paths before the fix, paths after it). Skips /dev/null."""
    before, after = [], []

    def clean(p):
        p = p.split("\t")[0].strip()
        if p.startswith('"') and p.endswith('"'):
            try:
                p = json.loads(p)
            except ValueError:
                p = p[1:-1]
        return p

    for line in text.splitlines():
        if line.startswith("--- "):
            p = clean(line[4:])
            if p != "/dev/null":
                before.append(p[2:] if p.startswith("a/") else p)
        elif line.startswith("+++ "):
            p = clean(line[4:])
            if p != "/dev/null":
                after.append(p[2:] if p.startswith("b/") else p)
        elif line.startswith("rename from "):
            before.append(clean(line[12:]))
        elif line.startswith("rename to "):
            after.append(clean(line[10:]))
    return sorted(set(before)), sorted(set(after))


# ------------------------------------------------------------------ repair --
def repair_suggestion(repo, pattern):
    """A dead glob usually means its directory was renamed. Find the rename in
    git history and propose the same glob on the new path."""
    literal = []
    for part in pattern.strip("/").split("/"):
        if re.search(r"[*?\[{]", part):
            break
        literal.append(part)
    prefix = "/".join(literal)
    if not prefix:
        return None
    last = git(repo, "log", "-1", "--format=%H", "--", prefix, check=False).strip()
    if not SHA.match(last):
        return None
    before = f"{last}^"
    old = Globs([pattern]).any_of(git(repo, "ls-tree", "-r", "--name-only", before, "--",
                                      check=False).splitlines())
    if not old:
        return None
    renamed = {}
    for line in git(repo, "diff", "-M", "--name-status", before, "HEAD", "--", check=False).splitlines():
        cols = line.split("\t")
        if len(cols) == 3 and cols[0].startswith("R") and cols[1] in old:
            renamed[cols[1]] = cols[2]
    if not renamed:
        return None
    new_dirs = {os.path.dirname(n) for n in renamed.values()}
    old_dirs = {os.path.dirname(o) for o in renamed}
    common_new = os.path.commonpath(list(new_dirs)) if new_dirs else ""
    common_old = os.path.commonpath(list(old_dirs)) if old_dirs else ""
    if common_old != prefix and not common_old.startswith(prefix + "/"):
        return None                     # "src/a" must not claim "src/ab/..."
    suffix = common_old[len(prefix):]
    new_prefix = common_new[:len(common_new) - len(suffix)] if suffix and common_new.endswith(suffix) else common_new
    cand = pattern.replace(prefix, new_prefix, 1)
    head = git(repo, "ls-files", check=False).splitlines()
    if not Globs([cand]).any_of(head):
        return None
    return cand, last[:10]


# -------------------------------------------------------------------- check --
def cmd_check(argv):
    cand_name, replace, tasks_arg, quiet = None, [], None, False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--candidate", "--replace", "--tasks") and i + 1 >= len(argv):
            die(f"check: {a} needs a value", 2)
        if a == "--candidate":
            cand_name = argv[i + 1]; i += 2
        elif a == "--replace":
            replace = argv[i + 1].split(); i += 2
        elif a == "--tasks":
            tasks_arg = argv[i + 1]; i += 2
        elif a == "--quiet":
            quiet = True; i += 1
        elif a == "--check":
            i += 1
        else:
            die(f"check: unknown argument {a}", 2)
    repo = repo_root()
    cfg = load_config(repo)
    budget = int(cfg.get("always_on_budget_chars", DEFAULT_BUDGET))
    errors, warnings = [], []

    for n in ([cand_name] if cand_name else []) + replace:
        if not valid_loose(n):
            errors.append(f"invalid skill name: '{n}'")
    if errors:
        return report(repo, [], errors, warnings, quiet, budget)

    items, notes = load_live(repo)
    warnings.extend(notes)
    errors.extend(scan_symlinks(repo))
    head = git(repo, "ls-files", check=False).splitlines()
    by_name = {}
    for it in items:
        it.validate(repo)
        by_name.setdefault(it.name, []).append(it)
        for p in it.problems:
            if not p.startswith("symlink"):   # symlinks: reported once by scan_symlinks
                warnings.append(f"{it.kind} {it.name}: {p}")
        for w in it.warnings:
            warnings.append(f"{it.kind} {it.name}: {w}")
        it.status = "ok"
        if it.patterns and not it.globs.error:
            dead = [p for p in it.patterns if not Globs([p]).any_of(head)]
            if dead and len(dead) == len(it.patterns):
                it.status = "DEAD"
            for p in dead:
                sug = repair_suggestion(repo, p)
                hint = (f" — repair: '{p}' -> '{sug[0]}' (renamed in {sug[1]})" if sug
                        else " — nothing in git history explains it: fix or remove the glob by hand")
                warnings.append(f"{it.kind} {it.name}: DEAD glob '{p}' matches no tracked file{hint}")
        home = os.path.expanduser("~")
        for other in (os.path.join(home, ".claude", "skills", it.name),
                      os.path.join(home, ".claude", "rules", it.name + ".md")):
            if os.path.exists(other):
                warnings.append(f"{it.kind} {it.name}: {other} has the same name; "
                                "its firing would be counted as this one's")
    for n, group in by_name.items():
        if len({g.kind for g in group}) > 1:
            errors.append(f"'{n}' is both a skill and a rule: firing cannot be attributed — rename one")

    for r in replace:
        g = by_name.get(r, [])
        if not g:
            errors.append(f"--replace: no live skill or rule called '{r}'")

    cand = None
    if cand_name:
        cand, cerr = load_candidate(repo, cand_name)
        errors.extend(cerr)
        if cand:
            cand.validate(repo)
            errors.extend(f"candidate {cand.name}: {p}" for p in cand.problems)
            warnings.extend(f"candidate {cand.name}: {w}" for w in cand.warnings)
            live_same = by_name.get(cand.name, [])
            if live_same and cand.name not in replace:
                errors.append(f"a live {live_same[0].kind} is already called '{cand.name}': "
                              f"pass --replace {cand.name} to test a new version of it")
            others = [g for g in live_same if g.kind != cand.kind and g.name not in replace]
            if others:
                errors.append(f"'{cand.name}' would exist as both a skill and a rule")
            if cand.tier == "manual":
                errors.append(f"candidate {cand.name}: disable-model-invocation is set, so no "
                              "rollout can ever load it — the sweep could only measure nothing")
            if cand.patterns and not cand.globs.error:
                errors.extend(reach_errors(repo, cand, tasks_arg))
            # A live item over exactly the same files is either a different rule
            # for that area (fine) or the same idea in another tier (not an
            # addition at all: a replacement, and /prune Step 5 decides it).
            same_area = [it for it in items
                         if it.name not in replace and it.name != cand.name
                         and sorted(it.patterns) == sorted(cand.patterns) and cand.patterns]
            for it in same_area:
                warnings.append(f"candidate {cand.name}: the live {it.kind} '{it.name}' covers exactly the "
                                f"same files ({', '.join(cand.patterns)}). If this is that same idea in "
                                f"another tier, it is a REPLACEMENT (--replace {it.name}), not an addition: "
                                f"two items saying the same thing both load. If it is a different rule for "
                                f"the same area, carry on")
    rows = [it for it in items if it.name not in replace]
    if cand:
        cand.status = "candidate"
        rows.append(cand)
    return report(repo, rows, errors, warnings, quiet, budget)


def reach_errors(repo, cand, tasks_arg):
    """Can any task in THIS sweep make the candidate load? If not, every
    rollout would measure nothing, so refuse before a token is spent."""
    tasks = Tasks(repo)
    ids, reached, usable = tasks.ids(tasks_arg), [], 0
    errs = []
    for tid in ids:
        if not valid_loose(tid):
            errs.append(f"invalid task id: '{tid}'")
            continue
        sha = tasks.sha(tid)
        if sha is None:
            continue                       # missing or quarantined mid-run: skip
        if not SHA.match(sha):
            errs.append(f"task {tid}: base_sha '{sha}' is not a commit id")
            continue
        usable += 1
        files = list(tasks.tree(sha))
        if cand.kind == "skill":            # a Write also reveals a path-gated skill
            files += tasks.patch_paths(tid)[1]
        if cand.globs.any_of(files):
            reached.append(tid)
    if errs:
        return errs
    if usable == 0:
        return ["no usable task in the set: nothing could measure the candidate"]
    if not reached:
        verb = "reads" if cand.kind == "rule" else "reads or writes"
        return [f"candidate {cand.name}: no task in this sweep ({' '.join(ids)}) {verb} a file "
                f"matching {cand.patterns} — it could never load, so the sweep would measure "
                "nothing. Widen `paths`, or sweep tasks that touch that area."]
    return []


def report(repo, rows, errors, warnings, quiet, budget):
    total = sum(r.always_on_chars for r in rows)
    for f in ALWAYS_LOADED_MEMORY:
        try:
            total += os.path.getsize(os.path.join(repo, f))
        except OSError:
            pass
    if total > budget:
        warnings.append(f"always-on context is {total} characters, over the budget of {budget} "
                        "(collection.always_on_budget_chars): gate or prune something")
    if not quiet:
        order = {"always": 0, "rule-always": 1, "gated": 2, "rule": 3, "manual": 4}
        rows = sorted(rows, key=lambda r: (order.get(r.tier, 9), r.name))
        print(f"routing  always-on {total}/{budget} chars   "
              f"(always-on skills + path-less rules + CLAUDE.md)")
        if rows:
            w = max(len(r.name) for r in rows)
            print(f"  {'TIER':<12} {'NAME':<{w}}  {'STATUS':<9} {'ALWAYS':>6}  PATHS / TRIGGER")
            for r in rows:
                what = ", ".join(r.patterns) if r.patterns else r.trigger
                print(f"  {r.tier:<12} {r.name:<{w}}  {getattr(r, 'status', 'ok'):<9} "
                      f"{r.always_on_chars:>6}  {what}")
        else:
            print("  (no skills or rules)")
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"check: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


# ------------------------------------------------------------ small commands --
def cmd_summary(argv):
    repo = repo_root()
    cfg = load_config(repo)
    items, _ = load_live(repo)
    tiers = {}
    for it in items:
        tiers[it.tier] = tiers.get(it.tier, 0) + 1
    total = sum(it.always_on_chars for it in items)
    for f in ALWAYS_LOADED_MEMORY:
        try:
            total += os.path.getsize(os.path.join(repo, f))
        except OSError:
            pass
    head = git(repo, "ls-files", check=False).splitlines()
    dead = sum(1 for it in items if it.patterns and not it.globs.error
               and not it.globs.any_of(head))
    print(json.dumps({"tiers": tiers, "always_on_chars": total,
                      "budget": int(cfg.get("always_on_budget_chars", DEFAULT_BUDGET)),
                      "dead": dead, "hash": harness_hash(repo, cfg)}, sort_keys=True))
    return 0


def harness_hash(repo, cfg):
    files, seen = [], set()
    for top in (os.path.join(".claude", "skills"), os.path.join(".claude", "rules")):
        for d, ds, fs in os.walk(os.path.join(repo, top), followlinks=True):
            if os.path.realpath(d) in seen:     # a symlink loop
                ds[:] = []
                continue
            seen.add(os.path.realpath(d))
            for f in fs:
                files.append(os.path.relpath(os.path.join(d, f), repo))
    for f in cfg.get("harness_files", ["CLAUDE.md"]):
        if os.path.isfile(os.path.join(repo, f)):
            files.append(os.path.normpath(f))
    if not files:
        return "empty"
    h = hashlib.sha256()
    for rel in sorted(set(files), key=lambda s: s.encode()):
        try:
            with open(os.path.join(repo, rel), "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
        except OSError:
            continue
        h.update(f"{digest}  ./{rel}\n".encode())
    return h.hexdigest()[:16]


def cmd_hash(argv):
    repo = repo_root()
    print(harness_hash(repo, load_config(repo)))
    return 0


def cmd_touching(argv):
    if not argv:
        die("usage: harness.py touching <fix.patch>", 2)
    repo = repo_root()
    try:
        with open(argv[0], encoding="utf-8", errors="replace") as fh:
            before, after = patch_files(fh.read())
    except OSError as ex:
        die(f"touching: {ex}")
    items, _ = load_live(repo)
    hit = []
    for it in items:
        if not it.patterns or it.globs.error:
            continue
        paths = before if it.kind == "rule" else before + after
        if it.globs.any_of(paths):
            hit.append(it.name)
    print("area: " + (", ".join(sorted(hit)) if hit else "none"))
    return 0


def _commit(repo, ref, flag):
    if ref != "HEAD" and not SHA.match(ref):
        die(f"{flag} {ref!r} is not a commit id", 2)
    r = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        die(f"{ref} is not a commit in this repository")
    return r.stdout.strip()


def _is_ancestor(repo, a, b):
    return a == b or subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", a, b]).returncode == 0


def build_fixpatch(repo, base, head=None):
    """(patch bytes, [(status, path)], full base sha) — everything that changed from
    `base` to the working tree: committed, uncommitted AND new files. `git diff`
    alone silently drops untracked files, so a fix that creates one (a new module,
    a fixture) would harvest a patch that no longer fixes anything.

    With `head`, only the commits base..head: a late harvest, when the session's
    work was committed and other work came after it, must not sweep that in too.

    A throwaway index does the staging, so the user's own index is never touched.
    .evolve/, .claude/ and the harness_files are left out: they are the
    experiment, not the fix. Dies when `base` is not a commit or nothing changed."""
    base_full = _commit(repo, base, "--base")
    excluded = [".evolve", ".claude"] + [f for f in load_config(repo).get("harness_files", ["CLAUDE.md"])
                                         if f and not f.startswith((".evolve", ".claude"))]
    spec = ["--", "."] + [f":(exclude){e}" for e in excluded]
    if head:
        head_full = _commit(repo, head, "--head")
        if not _is_ancestor(repo, base_full, head_full):
            die(f"{base_full[:12]} is not an ancestor of {head_full[:12]}: --base is where the session "
                f"started, --head its last commit")

        def run(*args):
            p = subprocess.run(["git", "-C", repo, *args], capture_output=True)
            if p.returncode != 0:
                die(f"git {args[0]}: {p.stderr.decode(errors='replace').strip()}")
            return p.stdout
        patch = run("diff", "--binary", "--no-color", "--no-ext-diff", base_full, head_full, *spec)
        names = run("diff", "--name-status", "--no-renames", base_full, head_full, *spec).decode(errors="replace")
        until = head_full[:12]
    else:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="cortex-fixpatch-") as tmp:
            env = dict(os.environ, GIT_INDEX_FILE=os.path.join(tmp, "index"))

            def run(*args):
                p = subprocess.run(["git", "-C", repo, *args], capture_output=True, env=env)
                if p.returncode != 0:
                    die(f"git {args[0]}: {p.stderr.decode(errors='replace').strip()}")
                return p.stdout
            run("read-tree", "HEAD")
            run("add", "-A", *spec)
            patch = run("diff", "--cached", "--binary", "--no-color", "--no-ext-diff", base_full, *spec)
            names = run("diff", "--cached", "--name-status", "--no-renames", base_full, *spec).decode(errors="replace")
        until = "the working tree"
    if not patch.strip():
        die(f"nothing changed between {base_full[:12]} and {until} "
            f"(outside {', '.join(excluded)})")
    rows = [tuple(ln.split("\t", 1)) for ln in names.splitlines() if "\t" in ln]
    return patch, rows, base_full


def _opt(argv, name, usage):
    if name not in argv:
        return None
    i = argv.index(name)
    if i + 1 >= len(argv):
        die(usage, 2)
    return argv[i + 1]


def _patch_summary(rows, base_full):
    return (f"{len(rows)} file(s) since {base_full[:12]}, {sum(1 for s, _ in rows if s == 'A')} new, "
            f"{sum(1 for s, _ in rows if s == 'D')} deleted")


def cmd_fixpatch(argv):
    """The fix as a patch on stdout (see build_fixpatch)."""
    usage = "usage: harness.py fixpatch [--base <sha>] [--head <sha>]"
    base = _opt(argv, "--base", usage) or "HEAD"
    patch, rows, base_full = build_fixpatch(repo_root(), base, _opt(argv, "--head", usage))
    sys.stdout.buffer.write(patch)
    print(f"fixpatch: {_patch_summary(rows, base_full)}", file=sys.stderr)
    return 0


def cmd_task(argv):
    """task new --base <sha> [--head <sha>] [--title "..."] — the mechanical half of /harvest.

    Creates the next free .evolve/tasks/NN/ with fix.patch (from build_fixpatch:
    every change since base_sha, new files included — or, with --head, exactly the
    commits base..head) and task.yaml. A model left to write these by hand reaches
    for `git diff`, picks the files itself, and silently leaves out the ones the
    fix created; this refuses to guess. Both commits must be in HEAD's history:
    the base is the commit the session started from, not one after the fix or on
    another branch."""
    usage = 'usage: cortex task new --base <sha> [--head <sha>] [--title "short title"]'
    if not argv or argv[0] != "new":
        die(usage, 2)
    base = _opt(argv, "--base", usage)
    until = _opt(argv, "--head", usage)
    title = _opt(argv, "--title", usage) or ""
    if not base:
        die(usage, 2)
    repo = repo_root()
    head = git(repo, "rev-parse", "HEAD").strip()
    for ref, flag in ((base, "--base"), (until, "--head")):
        if ref and not _is_ancestor(repo, _commit(repo, ref, flag), head):
            die(f"{ref} is not in the history of HEAD: base_sha must be the commit the "
                f"session started from (the broken state), not a later or unrelated one"
                if flag == "--base" else f"--head {ref} is not in the history of HEAD")
    patch, rows, base_full = build_fixpatch(repo, base, until)
    tasks = os.path.join(repo, ".evolve", "tasks")
    used = []
    for d in (tasks, os.path.join(tasks, "_broken")):
        if os.path.isdir(d):
            used += [int(n) for n in os.listdir(d) if n.isdigit()]
    nn = f"{(max(used) + 1) if used else 1:02d}"
    tdir = os.path.join(tasks, nn)
    os.makedirs(tdir)
    with open(os.path.join(tdir, "fix.patch"), "wb") as fh:
        fh.write(patch)
    timeout = int(load_config(repo).get("rollout_timeout_s", 600))
    with open(os.path.join(tdir, "task.yaml"), "w") as fh:
        fh.write(f"id: {nn}\ntitle: {title or 'TODO: short title'}\nbase_sha: {base_full}\n"
                 f"timeout_s: {timeout}\nharvested: {datetime.now().strftime('%Y-%m-%d')}\n")
    print(f"created .evolve/tasks/{nn}/  fix.patch ({_patch_summary(rows, base_full)}), task.yaml")
    print(f"now write .evolve/tasks/{nn}/prompt.txt, check.sh and notes.md")
    return 0


def cmd_candidate_info(argv):
    if not argv:
        die("usage: harness.py candidate-info <name>", 2)
    repo = repo_root()
    it, err = load_candidate(repo, argv[0])
    if not it:
        print(json.dumps({"kind": None, "tier": None, "error": err[0]}))
        return 1
    print(json.dumps({"kind": it.kind, "tier": it.tier}))
    return 0


def _run_start(path):
    try:
        with open(path) as fh:
            for line in fh:
                e = json.loads(line)
                if e.get("event") == "start":
                    return e
    except (OSError, ValueError):
        pass
    return {}


def _run_ended(path):
    try:
        with open(path) as fh:
            return any(json.loads(l).get("event") in ("done", "truncated", "incomplete") for l in fh if l.strip())
    except (OSError, ValueError):
        return False


def _sweep_running(repo):
    """sweep.sh holds .evolve/runs/.lock for its whole run."""
    import fcntl
    lock = os.path.join(repo, ".evolve", "runs", ".lock")
    if not os.path.exists(lock):
        return False
    with open(lock) as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return True
        fcntl.flock(fh, fcntl.LOCK_UN)
    return False


def evolve_phase(repo):
    """Where an /evolve cycle stands, from the files alone. A model reading a
    decision table once took the newest results (a finished, already-promoted
    confirm) for its own and replayed the previous cycle's ending."""
    ev = os.path.join(repo, ".evolve")
    cdir = os.path.join(ev, "candidate")
    cands = sorted(n for n in os.listdir(cdir) if not n.startswith(".")) if os.path.isdir(cdir) else []
    rdir = os.path.join(ev, "runs")
    runs = sorted(os.path.join(rdir, n) for n in os.listdir(rdir) if n.endswith(".jsonl")) if os.path.isdir(rdir) else []
    running = _sweep_running(repo)
    newest = runs[-1] if runs else None
    ns = _run_start(newest) if newest else {}
    if newest and running and ns.get("mode") == "replace":
        return {"phase": "prune", "why": "a /prune sweep is running: stop, and try again later"}
    if not cands:
        return {"phase": "A", "why": "no candidate: a fresh cycle. Results already in .evolve/runs/ belong to finished cycles"}
    if len(cands) > 1:
        return {"phase": "error", "why": f"more than one candidate ({', '.join(cands)}): one change per cycle — bury all but one"}
    c = cands[0]
    mine = [f for f in runs if _run_start(f).get("candidate") == c]
    if mine and _run_start(mine[-1]).get("mode") == "replace":
        return {"phase": "prune", "candidate": c,
                "why": f"{c} is a /prune replacement (its sweep is a replace): leave it and finish /prune"}
    adds = [f for f in mine if _run_start(f).get("mode", "add") == "add"]
    if not adds:
        return {"phase": "B", "candidate": c, "why": "the candidate is written and was never swept: launch the screen"}
    f = adds[-1]
    st = _run_start(f)
    sweep = {"file": os.path.relpath(f, repo), "phase": st.get("phase"), "tasks": st.get("tasks"), "k": st.get("k")}
    if _run_ended(f):
        return {"phase": "D", "candidate": c, "sweep": sweep,
                "why": f"its {st.get('phase')} sweep has ended: read the verdict ("
                       + ("D2" if st.get("phase") == "screen" else "D3") + ")"}
    if running:
        return {"phase": "C", "candidate": c, "sweep": sweep, "why": "its sweep is running: poll it"}
    return {"phase": "relaunch", "candidate": c, "sweep": sweep,
            "why": "its sweep stopped without finishing and nothing is running: launch the same sweep again"}


def sandbox_dir(repo, cfg=None):
    """This repository's own folder under sandbox_root (sweep.sh and preflight.sh
    compute the same: the first 12 hex digits of sha256 of the repo path)."""
    root = (cfg or load_config(repo)).get("sandbox_root", "/tmp/cortex-evolve")
    return os.path.join(root, hashlib.sha256(repo.encode()).hexdigest()[:12])


def cmd_transcripts(argv):
    """THIS project's session transcripts of the last lookback_days, newest first.
    /evolve was told to read "this project's transcripts under transcripts_dir"
    and searched the whole folder, reading other projects' files."""
    repo = repo_root()
    cfg = load_config(repo)
    tdir = os.path.expanduser(cfg.get("transcripts_dir", "~/.claude/projects"))
    pdir = os.path.join(tdir, escape_project(repo))
    days = int(cfg.get("lookback_days", 7))
    if "--days" in argv:
        days = int(argv[argv.index("--days") + 1])
    cutoff = time.time() - days * 86400
    files = []
    if os.path.isdir(pdir):
        files = sorted((f for f in (os.path.join(pdir, n) for n in os.listdir(pdir) if n.endswith(".jsonl"))
                        if os.path.getmtime(f) >= cutoff), key=os.path.getmtime, reverse=True)
    if "--dir" in argv:
        print(pdir)
        return 0
    for f in files:
        print(f)
    if not files:
        print(f"harness: no transcripts of this project in the last {days} day(s) under {pdir}", file=sys.stderr)
    return 0


def cmd_sandbox_dir(argv):
    print(sandbox_dir(repo_root()))
    return 0


def cmd_evolve_phase(argv):
    p = evolve_phase(repo_root())
    print(json.dumps(p) if "--json" in argv else f"phase {p['phase']}: {p['why']}"
          + (f"\n  candidate {p['candidate']}" if p.get("candidate") else "")
          + (f"\n  sweep {p['sweep']['phase']} {p['sweep']['file']} tasks \"{p['sweep']['tasks']}\" k={p['sweep']['k']}"
             if p.get("sweep") else ""))
    return 0 if p["phase"] != "error" else 1


def claude_version():
    try:
        r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.match(r"\s*(\d+(?:\.\d+)+)", r.stdout or "")
    return m.group(1) if (r.returncode == 0 and m) else None


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


def cmd_cli_version(argv):
    minimum = argv[argv.index("--min") + 1] if "--min" in argv and argv.index("--min") + 1 < len(argv) else None
    if minimum is not None and not re.fullmatch(r"\d+(\.\d+)+", minimum):
        print(f"harness: --min {minimum!r} is not a version", file=sys.stderr)
        return 2                    # fail closed: an unreadable bound is not a pass
    v = claude_version()
    if v is None:
        print("unknown")
        return 2
    print(v)
    if minimum and vtuple(v) < vtuple(minimum):
        return 1
    return 0


# ------------------------------------------------------------------ observe --
def installed(harness_dir):
    skills, rules = {}, {}
    sdir = os.path.join(harness_dir, "skills")
    if os.path.isdir(sdir):
        for n in os.listdir(sdir):
            if os.path.isfile(os.path.join(sdir, n, "SKILL.md")):
                skills[n] = True
    rdir = os.path.join(harness_dir, "rules")
    if os.path.isdir(rdir):
        for d, _, fs in os.walk(rdir):
            for f in fs:
                if f.endswith(".md"):
                    p = os.path.join(d, f)
                    rel = os.path.relpath(p, rdir)[:-3]
                    try:
                        with open(p, encoding="utf-8") as fh:
                            fields, _ = parse_frontmatter(fh.read())
                        rules[rel] = Globs(split_paths(fields.get("paths")))
                    except (OSError, UnicodeDecodeError, FrontmatterError):
                        rules[rel] = Globs([])   # unparsable: Claude Code would load it always
    return skills, rules


def to_relative(p, roots):
    if not isinstance(p, str) or not p:
        return None
    if not os.path.isabs(p):
        rel = os.path.normpath(p)
        return None if rel.startswith("..") else rel
    for cand in (os.path.normpath(p), os.path.realpath(p)):
        for root in roots:
            if cand.startswith(root + os.sep):
                return cand[len(root) + 1:]
    return None


def observe(stream, harness_dir, sandbox, prompt_file):
    init, result, fired, visible_names, reads, errored = None, None, set(), set(), [], set()
    with open(stream, encoding="utf-8", errors="replace") as fh:
        events = []
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except ValueError:
                continue         # a line cut by a timeout, or stray output
    for ev in events:
        if not isinstance(ev, dict):
            continue
        t, st = ev.get("type"), ev.get("subtype")
        if t == "system" and st == "init" and init is None:
            init = ev
        elif t == "result":
            result = ev
        elif t == "system" and st == "commands_changed":
            for c in ev.get("commands") or []:
                if isinstance(c, dict) and isinstance(c.get("name"), str):
                    visible_names.add(c["name"])
        elif t in ("assistant", "user"):
            for c in (ev.get("message") or {}).get("content") or []:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use" and c.get("name") == "Skill":
                    s = (c.get("input") or {}).get("skill")
                    if isinstance(s, str):
                        fired.add(s)
                elif c.get("type") == "tool_use" and c.get("name") == "Read":
                    reads.append((c.get("id"), (c.get("input") or {}).get("file_path")))
                elif c.get("type") == "tool_result" and c.get("is_error"):
                    errored.add(c.get("tool_use_id"))
    if init is None:
        raise ValueError("no system/init event: the stream is not a Claude Code transcript")
    for s in init.get("skills") or []:
        visible_names.add(s if isinstance(s, str) else (s or {}).get("name", ""))

    roots = []
    for r in (sandbox, init.get("cwd")):
        if isinstance(r, str) and r:
            roots += [os.path.normpath(r), os.path.realpath(r)]
    touched = [to_relative(p, roots) for i, p in reads if i not in errored]
    try:
        with open(prompt_file, encoding="utf-8", errors="replace") as fh:
            for m in re.finditer(r"(?:^|\s)@([^\s]+)", fh.read()):
                touched.append(to_relative(m.group(1).rstrip(".,;:!?)'\""), roots))
    except OSError:
        pass
    touched = [t for t in touched if t]

    skills, rules = installed(harness_dir)
    rules_fired = sorted(n for n, g in rules.items() if not g.patterns or g.any_of(touched))
    names = set(skills) | set(rules)
    visible = sorted((visible_names | fired | set(rules_fired)) & names)
    tokens, cost = None, None
    if isinstance(result, dict):     # real usage of this rollout, for cost estimates
        u = result.get("usage") or {}
        parts = [u.get(k) for k in ("input_tokens", "output_tokens",
                                    "cache_creation_input_tokens", "cache_read_input_tokens")]
        if any(isinstance(x, int) for x in parts):
            tokens = sum(x for x in parts if isinstance(x, int))
        if isinstance(result.get("total_cost_usd"), (int, float)):
            cost = round(float(result["total_cost_usd"]), 6)
    return {"skills": sorted(fired | set(rules_fired)), "rules": rules_fired,
            "visible": visible, "cli_version": init.get("claude_code_version"),
            "tokens": tokens, "cost_usd": cost}


def cmd_observe(argv):
    if len(argv) != 4:
        die("usage: harness.py observe <stream> <harness_dir> <sandbox> <prompt.txt>", 2)
    try:
        out = observe(*argv)
    except Exception as ex:          # unknown is not "never fired": say unknown
        print(json.dumps({"skills": None, "rules": None, "visible": None,
                          "cli_version": None, "tokens": None, "cost_usd": None,
                          "error": str(ex)[:200]}))
        return 2
    print(json.dumps(out, sort_keys=True))
    return 0


# -------------------------------------------------------------------- usage --
# Evidence for CHOOSING what /prune measures and on which tasks. It is never a
# reason to delete: a skill for something that happens twice a year looks
# unused in between, and is exactly the one that matters when it happens.
DEFAULT_USAGE_DAYS = 30
DEFAULT_MAX_ITEMS = 3
FALLBACK_SECS, FALLBACK_TOKENS = 120, 150_000     # used only with no measured history


def escape_project(path):
    """Claude Code names a project's transcript folder after its path, with
    every non-alphanumeric character replaced by '-' (verified)."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def _ts(ev):
    t = ev.get("timestamp")
    if not isinstance(t, str):
        return None
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def session_files(repo, tdir, cutoff):
    """This repo's transcripts (sessions started in it or in a sub-folder).
    Rollouts run in the sandbox, a different folder, so they never count."""
    if not os.path.isdir(tdir):
        return []
    prefixes = {escape_project(repo), escape_project(os.path.realpath(repo))}
    out = []
    for d in sorted(os.listdir(tdir)):
        if not any(d == p or d.startswith(p + "-") for p in prefixes):
            continue
        full = os.path.join(tdir, d)
        for f in sorted(os.listdir(full)) if os.path.isdir(full) else []:
            p = os.path.join(full, f)
            if f.endswith(".jsonl") and os.path.isfile(p) and os.path.getmtime(p) >= cutoff:
                out.append(p)
    return out


def _top_folder(path, depth=2):
    parts = path.split("/")[:-1]
    return "/".join(parts[:depth]) + "/" if parts else "(root)"


def scan_sessions(repo, tdir, cutoff):
    """-> list of sessions: {skills: Counter-like dict, reads: [...], touched: [...], last: ts}"""
    roots = [os.path.normpath(repo), os.path.realpath(repo)]
    sessions = []
    for path in session_files(repo, tdir, cutoff):
        s = {"skills": {}, "reads": [], "touched": [], "last": 0}
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(ev, dict):
                    continue
                ts = _ts(ev)
                if ts is not None and ts < cutoff:
                    continue
                cwd = ev.get("cwd")
                if isinstance(cwd, str) and cwd and not within(cwd, repo):
                    continue                  # a sibling folder sharing the prefix
                msg = ev.get("message") or {}
                content = msg.get("content") if isinstance(msg, dict) else None
                if isinstance(content, str) and ev.get("type") == "user":
                    content = [{"type": "text", "text": content}]
                for c in content or []:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "tool_use":
                        inp = c.get("input") or {}
                        if c.get("name") == "Skill" and isinstance(inp.get("skill"), str):
                            s["skills"][inp["skill"]] = s["skills"].get(inp["skill"], 0) + 1
                            s["last"] = max(s["last"], ts or 0)
                        fp = inp.get("file_path") or inp.get("notebook_path")
                        rel = to_relative(fp, roots) if isinstance(fp, str) else None
                        if rel:
                            if c.get("name") == "Read":
                                s["reads"].append((rel, ts or 0))
                            if c.get("name") in ("Read", "Write", "Edit", "MultiEdit", "NotebookEdit"):
                                s["touched"].append(rel)
                    elif c.get("type") == "text" and ev.get("type") == "user":
                        for m in re.finditer(r"(?:^|\s)@([^\s]+)", c.get("text") or ""):
                            rel = to_relative(m.group(1).rstrip(".,;:!?)'\""), roots)
                            if rel:
                                s["reads"].append((rel, ts or 0))
        if s["skills"] or s["reads"] or s["touched"]:
            sessions.append(s)
    return sessions


def sweep_history(repo):
    """What past sweeps saw, per item, in the BASE arm (the live harness):
    tasks where it loaded, and whether it was ever live at all."""
    fired, seen = {}, set()
    runs = os.path.join(repo, ".evolve", "runs")
    for f in sorted(os.listdir(runs)) if os.path.isdir(runs) else []:
        if not f.endswith(".jsonl"):
            continue
        try:
            fh = open(os.path.join(runs, f), encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(r, dict) or r.get("v") != "base" or r.get("valid") != 1:
                    continue
                for n in r.get("visible") or []:
                    seen.add(n)
                for n in r.get("skills") or []:
                    seen.add(n)
                    fired.setdefault(n, set()).add(str(r.get("t")))
    return fired, seen


# ------------------------------------------------------------- parallel --
# How many rollouts (or preflight checks) run at once. A number in config is
# taken as given. `auto` is sized when the run starts: ram_percent of the RAM
# available THEN, divided by what one worker needs — and never more than the
# CPUs, the jobs there are, or (rollouts) max_rollouts: past a point, parallel
# agents only meet the API's rate limits, and a rate-limited rollout is invalid.
PARALLEL_DEFAULTS = {"parallel_rollouts": "auto", "parallel_preflight": "auto",
                     "parallel_ram_percent": 50, "parallel_ram_per_rollout_mb": 1024,
                     "parallel_ram_per_check_mb": 512, "parallel_max_rollouts": 16,
                     "parallel_cpus_per_rollout": 1}
PREFLIGHT_MAX = 32          # preflight spends no tokens: only CPUs bound it


def _read(path):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return None


def _cgroup_candidates():
    """(version, directory) pairs whose limits bind this process: its own cgroup
    AND every parent (a limit set higher up — a container, a systemd slice — binds
    too), for cgroup v2 and v1. CORTEX_CGROUP_DIR names one directory instead
    (tests). On a hybrid host the v2 line exists while the limits live in v1: both
    are read, never one instead of the other."""
    env = os.environ.get("CORTEX_CGROUP_DIR")
    if env:
        return [("v2", env)]
    lines = (_read("/proc/self/cgroup") or "").splitlines()
    out = []
    for ln in lines:
        parts = ln.split(":", 2)
        if len(parts) != 3:
            continue
        hid, ctrls, path = parts
        rel = path.strip("/")
        if hid == "0" and ctrls == "":                   # the v2 unified hierarchy
            base = "/sys/fs/cgroup"
            cur = os.path.join(base, rel) if rel else base
            while True:
                out.append(("v2", cur))
                if cur == base or len(cur) <= len(base):
                    break
                cur = os.path.dirname(cur)
        else:
            for c in ctrls.split(","):
                if c in ("memory", "cpu"):
                    root = os.path.join("/sys/fs/cgroup", c)
                    for d in ((os.path.join(root, rel), root) if rel else (root,)):
                        out.append(("v1" + c, d))
    return out


def _cgroup_available_mb():
    """Memory left under the tightest cgroup limit that applies, or None when
    none does. MemAvailable alone reports the whole host inside a container."""
    best = None
    for ver, d in _cgroup_candidates():
        try:
            if ver == "v2":
                lim = _read(os.path.join(d, "memory.max"))
                if lim is None or lim == "max":
                    continue
                cur = int(_read(os.path.join(d, "memory.current")))
            elif ver == "v1memory":
                lim = _read(os.path.join(d, "memory.limit_in_bytes"))
                if lim is None or int(lim) >= 1 << 60:           # "unlimited"
                    continue
                cur = int(_read(os.path.join(d, "memory.usage_in_bytes")))
            else:
                continue
            avail = max(0, (int(lim) - cur) // (1024 * 1024))
        except (TypeError, ValueError):
            continue
        best = avail if best is None else min(best, avail)
    return best


def _cgroup_cpu_quota():
    """CPUs the tightest CPU quota allows (cgroup v2 cpu.max, v1 cfs quota), or
    None. A 2-CPU container on a 32-core host must not be sized as 32."""
    best = None
    for ver, d in _cgroup_candidates():
        try:
            if ver == "v2":
                raw = _read(os.path.join(d, "cpu.max"))
                if not raw:
                    continue
                q, _, per = raw.partition(" ")
                if q == "max":
                    continue
                n = int(q) / int(per or 100000)
            elif ver == "v1cpu":
                q = _read(os.path.join(d, "cpu.cfs_quota_us"))
                if q is None or int(q) <= 0:
                    continue
                n = int(q) / int(_read(os.path.join(d, "cpu.cfs_period_us")) or 100000)
            else:
                continue
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        best = n if best is None else min(best, n)
    return best


def mem_available_mb():
    """(MB available now, where the number came from), or (None, why)."""
    env = os.environ.get("CORTEX_MEM_AVAILABLE_MB")    # tests, and a manual override
    if env == "unknown":
        return None, "available RAM unknown (CORTEX_MEM_AVAILABLE_MB=unknown)"
    if env:
        try:
            return int(env), "CORTEX_MEM_AVAILABLE_MB"
        except ValueError:
            pass
    host = None
    try:
        with open("/proc/meminfo") as fh:
            for ln in fh:
                if ln.startswith("MemAvailable:"):
                    host = int(ln.split()[1]) // 1024
                    break
    except (OSError, ValueError, IndexError):
        host = None
    if host is None:
        try:                                           # macOS and other BSDs
            out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout
            page = int(re.search(r"page size of (\d+) bytes", out).group(1))
            pages = sum(int(re.search(rf"{k}:\s+(\d+)", out).group(1))
                        for k in ("Pages free", "Pages inactive", "Pages speculative"))
            host = pages * page // (1024 * 1024)
        except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
            return None, "available RAM unknown on this system"
    cg = _cgroup_available_mb()
    if cg is not None and cg < host:
        return cg, "cgroup limit"
    return host, "MemAvailable"


def cpu_count():
    """CPUs this process may really use: its affinity, cut down by a cgroup CPU
    quota (sched_getaffinity alone sees every core of the host)."""
    env = os.environ.get("CORTEX_CPUS")
    if env:
        try:
            return max(1, int(env))
        except ValueError:
            pass
    try:
        n = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        n = os.cpu_count() or 1
    quota = _cgroup_cpu_quota()
    if quota is not None:
        n = min(n, int(quota))                             # 2.5 CPUs of quota = 2 whole ones
    return max(1, n)


def resolve_workers(cfg, kind, jobs, override=None):
    """{workers, setting, ...why}: how many of `kind` run at once for `jobs` jobs."""
    c = dict(PARALLEL_DEFAULTS, **{k: v for k, v in (cfg or {}).items() if k.startswith("parallel_")})
    jobs = max(1, int(jobs or 1))
    setting = override if override not in (None, "") else c[f"parallel_{kind}"]
    setting = str(setting).strip().lower()
    out = {"kind": kind, "setting": setting, "jobs": jobs}
    if setting != "auto":
        try:
            n = int(setting)
        except ValueError:
            raise SystemExit(f"parallel: {kind} must be auto or a number, not {setting!r}")
        if not 1 <= n <= 64:
            raise SystemExit(f"parallel: {kind} must be between 1 and 64, not {n}")
        out.update(workers=min(n, jobs), limited_by="jobs" if jobs < n else "setting", cpus=cpu_count(),
                   why=f"{n} (fixed)" + (f", only {jobs} job(s)" if jobs < n else ""))
        return out
    per = int(c["parallel_ram_per_rollout_mb"] if kind == "rollouts" else c["parallel_ram_per_check_mb"])
    pct = int(c["parallel_ram_percent"])
    cap = int(c["parallel_max_rollouts"]) if kind == "rollouts" else PREFLIGHT_MAX
    avail, source = mem_available_mb()
    cpus = cpu_count()
    # a rollout is an agent AND the tests it runs, which may keep several CPUs busy
    cpr = max(1, int(c.get("parallel_cpus_per_rollout", 1))) if kind == "rollouts" else 1
    by_cpu = max(1, cpus // cpr)
    out.update(ram_percent=pct, per_worker_mb=per, cpus=cpus, cpus_per_rollout=cpr, max=cap)
    if avail is None:
        out.update(workers=1, limited_by="unknown RAM", ram_available_mb=None,
                   why=f"auto: {source}, so 1 at a time")
        return out
    budget = avail * pct // 100
    by_ram = max(1, budget // per)
    limits = {"ram": by_ram, "cpus": by_cpu, "max": cap, "jobs": jobs}
    workers = min(limits.values())
    limited_by = min(limits, key=lambda k: (limits[k], ["ram", "cpus", "max", "jobs"].index(k)))
    out.update(workers=workers, limited_by=limited_by, ram_available_mb=avail, ram_source=source,
               ram_budget_mb=budget, by_ram=by_ram,
               why=(f"auto: {pct}% of {avail / 1024:.1f} GB available = {budget / 1024:.1f} GB, "
                    f"{per} MB each -> {by_ram}; capped by {cpus} CPU(s)"
                    + (f" / {cpr} per rollout = {by_cpu}" if cpr > 1 else "")
                    + f", max {cap}, {jobs} job(s)"
                    f" -> {workers} (limited by {limited_by})"))
    return out


def cmd_parallel(argv):
    usage = "usage: harness.py parallel --kind rollouts|preflight [--jobs N] [--override auto|N] [--json]"
    kind = _opt(argv, "--kind", usage)
    if kind not in ("rollouts", "preflight"):
        die(usage, 2)
    jobs = _opt(argv, "--jobs", usage) or "1"
    if not re.fullmatch(r"\d{1,6}", jobs):
        die(usage, 2)
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    cfg = load_config(top.stdout.strip()) if top.returncode == 0 else {}   # doctor may run outside one
    r = resolve_workers(cfg, kind, int(jobs), _opt(argv, "--override", usage))
    print(json.dumps(r) if "--json" in argv else r["workers"])
    return 0


def rollout_estimate(repo):
    """Average cost of one rollout, measured from this repo's own sweeps."""
    secs, toks, cost = [], [], []
    runs = os.path.join(repo, ".evolve", "runs")
    for f in sorted(os.listdir(runs)) if os.path.isdir(runs) else []:
        if not f.endswith(".jsonl"):
            continue
        try:
            fh = open(os.path.join(runs, f), encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(r, dict) or r.get("v") is None or r.get("agent_rc") is None:
                    continue               # an invalid row never ran an agent
                w = r.get("wall_secs", r.get("secs"))
                if isinstance(w, (int, float)) and w > 0:
                    secs.append(w)
                if isinstance(r.get("tokens"), int):
                    toks.append(r["tokens"])
                if isinstance(r.get("cost_usd"), (int, float)):
                    cost.append(r["cost_usd"])
    avg = lambda xs: sum(xs) / len(xs) if xs else None
    return {"secs": avg(secs) or FALLBACK_SECS, "tokens": avg(toks) or FALLBACK_TOKENS,
            "cost_usd": avg(cost), "samples": len(secs), "token_samples": len(toks),
            "measured": bool(secs)}


def valid_task_ids(repo):
    tasks = Tasks(repo)
    out = []
    for t in tasks.ids(None):
        sha = tasks.sha(t)
        if valid_loose(t) and sha and SHA.match(sha):
            out.append(t)
    return out


def reachable_tasks(repo, item, ids):
    """Tasks whose broken state holds a file matching the item's paths (and,
    for a skill, a file the fix writes): the only tasks where it can load."""
    tasks, out = Tasks(repo), []
    for t in ids:
        sha = tasks.sha(t)
        files = list(tasks.tree(sha))
        if item.kind == "skill":
            files += tasks.patch_paths(t)[1]
        if item.globs.any_of(files):
            out.append(t)
    return out


def usage_rows(repo, days):
    cfg = load_config(repo)
    tdir = cfg.get("transcripts_dir") or os.path.expanduser("~/.claude/projects")
    cutoff = time.time() - days * 86400
    items, _ = load_live(repo)
    sessions = scan_sessions(repo, tdir, cutoff)
    fired, seen = sweep_history(repo)
    ids = valid_task_ids(repo)
    rows = []
    for it in items:
        uses, sess, last, folders = 0, 0, 0, {}
        for s in sessions:
            if it.kind == "skill":
                n = s["skills"].get(it.name, 0)
                hits = s["touched"] if n else []
            else:
                if not it.patterns:        # a path-less rule is always loaded
                    continue
                matched = [(p, ts) for p, ts in s["reads"] if it.globs.match(p)]
                n = len(matched)
                hits = [p for p, _ in matched]
                last = max([last] + [ts for _, ts in matched])
            if n:
                uses += n
                sess += 1
                if it.kind == "skill":
                    last = max(last, s["last"])
                for p in hits:
                    folders[_top_folder(p)] = folders.get(_top_folder(p), 0) + 1
        top, share = None, 0.0
        if folders:
            top = max(folders, key=folders.get)
            share = folders[top] / sum(folders.values())
        loaded = sorted(fired.get(it.name, set()) & set(ids))
        reach = reachable_tasks(repo, it, ids) if it.patterns and not it.globs.error else None
        rows.append({"name": it.name, "kind": it.kind, "tier": it.tier,
                     "always_on_chars": it.always_on_chars, "sessions": sess, "uses": uses,
                     "last_used": datetime.fromtimestamp(last, timezone.utc).strftime("%Y-%m-%d") if last else None,
                     "top_folder": top, "top_share": round(share, 2),
                     "loaded_in_tasks": loaded, "ever_live_in_sweeps": it.name in seen,
                     "reachable_tasks": reach, "hint": usage_hint(it, uses, top, share, loaded, reach)})
    return rows, len(sessions)


def usage_hint(it, uses, top, share, loaded, reach):
    if it.tier == "manual":
        return "manual: only you invoke it — nothing to measure"
    measurable = bool(loaded) or bool(reach)
    if uses and not measurable:
        return "used, but no task can load it: the suite is blind here — harvest a task"
    if not uses and not measurable:
        return "no use, no task: a removal can only come out UNMEASURED"
    if it.tier == "always" and uses >= 3 and top and share >= 0.8 and top != "(root)":
        return f"narrowing candidate: {int(share * 100)}% of its use is in {top}"
    return ""


def cmd_usage(argv):
    repo = repo_root()
    cfg = load_config(repo)
    days = int(cfg.get("prune_usage_days", DEFAULT_USAGE_DAYS))
    as_json = "--json" in argv
    if "--days" in argv:
        i = argv.index("--days")
        if i + 1 >= len(argv) or not argv[i + 1].isdigit() or int(argv[i + 1]) < 1:
            die("usage: --days needs a positive whole number", 2)
        days = int(argv[i + 1])
    rows, nsess = usage_rows(repo, days)
    if as_json:
        print(json.dumps({"days": days, "sessions_scanned": nsess, "items": rows}, sort_keys=True))
        return 0
    print(f"usage  last {days} days · {nsess} session(s) of this repo  "
          "(advisory: chooses what /prune tests — never a reason to delete)")
    if not rows:
        print("  (no skills or rules)")
        return 0
    w = max(len(r["name"]) for r in rows)
    print(f"  {'TIER':<12} {'NAME':<{w}}  {'SESS':>4} {'USES':>4}  {'LAST USE':<10}  {'TOP FOLDER':<22} TASKS THAT CAN MEASURE IT")
    for r in rows:
        if r["tier"] == "manual":
            tasks = "—"
        elif r["loaded_in_tasks"]:
            tasks = "loaded in " + " ".join(r["loaded_in_tasks"])
        elif r["reachable_tasks"]:
            tasks = "reachable: " + " ".join(r["reachable_tasks"])
        elif r["reachable_tasks"] is None and not r["ever_live_in_sweeps"]:
            tasks = "no sweep data yet"
        else:
            tasks = "none"
        top = f"{r['top_folder']} ({int(r['top_share'] * 100)}%)" if r["top_folder"] else "-"
        print(f"  {r['tier']:<12} {r['name']:<{w}}  {r['sessions']:>4} {r['uses']:>4}  "
              f"{r['last_used'] or '-':<10}  {top:<22} {tasks}")
        if r["hint"]:
            print(f"  {'':<12} {'':<{w}}  ↳ {r['hint']}")
    return 0


# -------------------------------------------------------------------- prune --
def _plan_path(repo):
    return os.path.join(repo, ".evolve", "prune-plan.json")


def _load_plan(repo):
    try:
        with open(_plan_path(repo)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _save_plan(repo, plan):
    p = _plan_path(repo)
    with open(p + ".tmp", "w") as fh:
        json.dump(plan, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(p + ".tmp", p)          # never a half-written plan


def _state(repo):
    try:
        with open(os.path.join(repo, ".evolve", "state.json")) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _baseline_model(repo):
    try:
        with open(os.path.join(repo, ".evolve", "baseline.json")) as fh:
            return json.load(fh).get("model")
    except (OSError, ValueError, AttributeError):
        return None


def model_upgrade(repo, cfg):
    """A pass after a model change tests EVERYTHING. Changed = the pinned model
    differs from the one the last completed pass ran on (or, before any pass,
    from the one the baseline was measured on)."""
    model = cfg.get("model") or ""
    if not model:
        return False, "the model is not pinned (baseline.model), so a model change cannot be detected"
    last = _state(repo).get("last_prune_model")
    ref = last or _baseline_model(repo)
    if ref and ref not in ("unspecified", "default") and ref != model:
        return True, f"the pinned model changed: {ref} -> {model}"
    return False, ""


def _fmt_secs(s):
    s = int(round(s))
    if s < 3600:
        return f"~{max(1, round(s / 60))} min"
    return f"~{s // 3600} h {round((s % 3600) / 60):02d} min"


def _fmt_tokens(t):
    return f"~{t / 1e6:.1f}M" if t >= 1e6 else f"~{int(round(t / 1e3))}k"


def plan_estimate(repo, rollouts):
    e = rollout_estimate(repo)
    # a sweep runs `workers` rollouts at once: wall time is the rounds of them
    workers = resolve_workers(load_config(repo), "rollouts", rollouts)["workers"]
    est = {"rollouts": rollouts, "workers": workers,
           "seconds": -(-rollouts // workers) * e["secs"], "tokens": int(rollouts * e["tokens"]),
           "cost_usd": round(rollouts * e["cost_usd"], 2) if e["cost_usd"] is not None else None,
           "per_rollout": {"seconds": round(e["secs"]), "tokens": int(e["tokens"]),
                           "cost_usd": round(e["cost_usd"], 4) if e["cost_usd"] is not None else None}}
    if e["measured"]:
        est["basis"] = (f"measured: {e['samples']} past rollouts of this repo (avg {round(e['secs'])} s"
                        + (f", {int(e['tokens'] / 1000)}k tokens" if e["token_samples"] else "")
                        + (f", ${e['cost_usd']:.2f}" if e["cost_usd"] is not None else "") + ")")
    else:
        est["basis"] = (f"defaults — no sweep has run in this repo yet ({FALLBACK_SECS} s, "
                        f"{FALLBACK_TOKENS // 1000}k tokens per rollout); the first sweep replaces them")
    return est


def _est_line(est):
    cost = f" · ~${est['cost_usd']:.2f}" if est["cost_usd"] is not None else ""
    w = est.get("workers", 1)
    return (f"{est['rollouts']} rollouts · {_fmt_secs(est['seconds'])} "
            f"({'one at a time' if w == 1 else f'{w} at a time'}) · "
            f"{_fmt_tokens(est['tokens'])} tokens{cost}")


def build_plan(repo, names, whys):
    cfg = load_config(repo)
    k = int(cfg.get("k_confirm", 3))
    maxruns = int(cfg.get("max_runs_per_cycle", 60))
    max_items = int(cfg.get("prune_max_items", DEFAULT_MAX_ITEMS))
    upgrade, why_mode = model_upgrade(repo, cfg)
    items, _ = load_live(repo)
    addressable = {it.name: it for it in items if "/" not in it.name}
    if upgrade:
        if names:
            die(f"model upgrade ({why_mode}): every item is tested — run `cortex prune plan` "
                "without --items", 2)
        # biggest permanent context first: if the pass is stopped early, the
        # tests that could save the most have already run
        tier_rank = {"always": 0, "rule-always": 1, "gated": 2, "rule": 3, "manual": 4}
        names = sorted(addressable, key=lambda n: (tier_rank.get(addressable[n].tier, 9),
                                                   -addressable[n].always_on_chars, n))
    else:
        if not names:
            die("choose what to test: cortex prune plan --items \"<a> [b]\" "
                f"(at most prune.max_items = {max_items})", 2)
        if len(names) > max_items:
            die(f"{len(names)} items, but prune.max_items is {max_items}: choose the ones you "
                "doubt most, or raise prune.max_items in .evolve/config.yaml", 2)
        for n in names:
            if n not in addressable:
                die(f"no live top-level skill or rule called '{n}'", 2)
    ids = valid_task_ids(repo)
    fired, seen = sweep_history(repo)
    rows, total = [], 0
    for n in names:
        it = addressable[n]
        row = {"name": n, "kind": it.kind, "tier": it.tier, "why": whys.get(n, ""),
               "tasks": [], "tasks_basis": "", "rollouts": 0, "state": "pending",
               "verdict": None, "results": None}
        if it.tier == "manual":
            row.update(state="skipped", note="manual: the model never invokes it — nothing to measure")
        elif it.patterns and not it.globs.error:
            row["tasks"] = reachable_tasks(repo, it, ids)
            row["tasks_basis"] = "reach: its paths exist in these tasks"
            if not row["tasks"]:
                row.update(state="skipped", note="no task touches its paths — a removal can only be UNMEASURED; harvest a task in that area")
        elif it.kind == "rule":                 # path-less rule: loaded in every task
            row["tasks"], row["tasks_basis"] = ids, "path-less rule: loaded everywhere"
        else:                                   # always-on skill
            loaded = sorted(fired.get(n, set()) & set(ids))
            if loaded:
                row["tasks"], row["tasks_basis"] = loaded, "loaded here in past sweeps"
            elif n in seen:
                row.update(state="skipped", note="live in past sweeps but never loaded — a removal can only be UNMEASURED")
            else:
                row["tasks"], row["tasks_basis"] = ids, "no sweep data yet: every task"
        if row["state"] == "pending":
            row["rollouts"] = len(row["tasks"]) * k * 2
            if row["rollouts"] > maxruns:
                row.update(state="blocked", note=f"needs {row['rollouts']} rollouts, over "
                           f"max_runs_per_cycle ({maxruns}) — the sweep would refuse")
            else:
                total += row["rollouts"]
        rows.append(row)
    plan = {"version": 1, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "proposed", "mode": "model-upgrade" if upgrade else "routine",
            "mode_reason": why_mode, "model": cfg.get("model") or "", "k": k,
            "max_items": None if upgrade else max_items, "items": rows,
            "estimate": plan_estimate(repo, total)}
    return plan


def item_sweep(repo, name, since_iso):
    """The newest removal sweep of exactly this item started after the plan was
    approved: None, or {file, finished}. Lets /prune resume across turns."""
    try:
        since = datetime.fromisoformat(since_iso).timestamp() if since_iso else 0
    except ValueError:
        since = 0
    runs = os.path.join(repo, ".evolve", "runs")
    best = None
    for f in sorted(os.listdir(runs)) if os.path.isdir(runs) else []:
        p = os.path.join(runs, f)
        if not f.endswith(".jsonl") or os.path.getmtime(p) < since:
            continue
        start, finished = None, False
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if isinstance(ev, dict) and ev.get("event") == "start" and start is None:
                    start = ev
                elif isinstance(ev, dict) and ev.get("event") in ("done", "truncated"):
                    finished = True
        if (start and start.get("mode") == "replace" and start.get("replaced") == [name]
                and not start.get("candidate")):
            if best is None or f > best["file"].rsplit("/", 1)[-1]:
                best = {"file": os.path.relpath(p, repo), "finished": finished}
    return best


def print_plan(plan):
    mode = ("MODEL UPGRADE — every item is tested (" + plan["mode_reason"] + ")"
            if plan["mode"] == "model-upgrade" else f"routine — at most {plan['max_items']} items")
    print(f"prune plan  {mode}")
    if plan["mode"] == "routine" and plan.get("mode_reason"):
        print(f"            note: {plan['mode_reason']}")
    rows = plan["items"]
    w = max([len(r["name"]) for r in rows] + [4])
    print(f"  #  {'ITEM':<{w}}  {'TIER':<11} {'STATE':<9} {'ROLLOUTS':>8}  TASKS")
    i = 0
    for r in rows:
        runs = r["state"] in ("pending", "running", "decided")
        i += 1 if runs else 0
        num = str(i) if runs else "-"
        tasks = " ".join(r["tasks"]) if r["tasks"] else "—"
        state = r["state"] if r["state"] != "decided" else (r.get("verdict") or "decided")
        print(f"  {num:<2} {r['name']:<{w}}  {r['tier']:<11} {state:<9} "
              f"{r['rollouts'] if runs else '—':>8}  {tasks}")
        for extra in (r.get("why"), r.get("note")):
            if extra:
                print(f"     {'':<{w}}  ↳ {extra}")
    tested = [r for r in rows if r["state"] in ("pending", "running", "decided")]
    print(f"\n  will test {len(tested)} item(s) · {_est_line(plan['estimate'])}")
    print(f"  estimate basis: {plan['estimate']['basis']}")
    st = plan["status"]
    if st == "proposed":
        print("\n  status: PROPOSED — nothing runs until you approve.  Approve: cortex prune approve   "
              "Cancel: cortex prune cancel")
    else:
        print(f"\n  status: {st.upper()}")


def cmd_prune(argv):
    if not argv:
        die("usage: harness.py prune plan|approve|cancel|next|record|finish|status|estimate", 2)
    sub, rest = argv[0], argv[1:]
    repo = repo_root()
    plan = _load_plan(repo)
    active = plan is not None and plan.get("status") in ("proposed", "approved")

    if sub == "plan":
        if active:
            die("a prune plan is already " + plan["status"] + " — see `cortex prune status`, "
                "or `cortex prune cancel` it first", 1)
        names, whys, i = [], {}, 0
        while i < len(rest):
            if rest[i] == "--items" and i + 1 < len(rest):
                names += rest[i + 1].split(); i += 2
            elif rest[i] == "--why" and i + 1 < len(rest) and "=" in rest[i + 1]:
                k, v = rest[i + 1].split("=", 1); whys[k.strip()] = v.strip(); i += 2
            else:
                die(f"prune plan: bad argument {rest[i]!r} (use --items \"a b\" and --why \"a=reason\")", 2)
        for n in names:
            if not valid_loose(n):
                die(f"invalid skill name: '{n}'", 2)
        if len(set(names)) != len(names):
            die("an item is listed twice", 2)
        plan = build_plan(repo, names, whys)
        _save_plan(repo, plan)
        print_plan(plan)
        return 0

    if sub == "estimate":
        tasks = rest[rest.index("--tasks") + 1].split() if "--tasks" in rest and rest.index("--tasks") + 1 < len(rest) else valid_task_ids(repo)
        k = int(load_config(repo).get("k_confirm", 3))
        est = plan_estimate(repo, len(tasks) * k * 2)
        print(f"estimate  {len(tasks)} task(s) × k={k} × 2 arms = {_est_line(est)}")
        print(f"  basis: {est['basis']}")
        return 0

    if sub == "status":
        if plan is None:
            print("no prune plan — start one with `cortex prune plan`")
            return 0
        print_plan(plan)
        return 0

    if plan is None:
        die("no prune plan — start one with `cortex prune plan`", 1)

    if sub == "approve":
        if plan["status"] != "proposed":
            die(f"the plan is {plan['status']}, not proposed", 1)
        plan["status"], plan["approved"] = "approved", datetime.now(timezone.utc).isoformat(timespec="seconds")
        _save_plan(repo, plan)
        print(f"approved: {_est_line(plan['estimate'])}")
        return 0

    if sub == "cancel":
        if not active:
            die(f"the plan is already {plan['status']}", 1)
        plan["status"] = "cancelled"
        _save_plan(repo, plan)
        print("prune plan cancelled — nothing else will run")
        return 0

    if sub == "next":
        if plan["status"] != "approved":
            die(f"the plan is {plan['status']}: nothing runs until the user approves it "
                "(cortex prune approve)", 1)
        for r in plan["items"]:
            if r["state"] in ("pending", "running"):
                cmd = (f"cortex sweep --replace {r['name']} --tasks \"{' '.join(r['tasks'])}\" "
                       "--phase confirm")
                sweep = item_sweep(repo, r["name"], plan.get("approved"))
                if "--json" in rest:
                    print(json.dumps({"name": r["name"], "kind": r["kind"], "tasks": r["tasks"],
                                      "rollouts": r["rollouts"], "command": cmd, "sweep": sweep}))
                elif sweep:
                    state = "finished — decide it" if sweep["finished"] else "running"
                    print(f"next: {r['name']} — its sweep is {state}: {sweep['file']}")
                else:
                    print(f"next: {r['name']} ({r['kind']}, {r['rollouts']} rollouts)\n  {cmd} --dry-run\n  {cmd} --detach")
                return 0
        print("nothing left to test — run `cortex prune finish`")
        return 3

    if sub == "record":
        if plan["status"] != "approved":
            die(f"the plan is {plan['status']}, not approved", 1)
        if not rest or rest[0].startswith("-"):
            die("usage: cortex prune record <item> --verdict ACCEPT|REJECT|UNMEASURED [--results FILE] [--action TEXT]", 2)
        name, verdict, results, action = rest[0], None, None, ""
        i = 1
        while i < len(rest):
            if rest[i] in ("--verdict", "--results", "--action") and i + 1 < len(rest):
                if rest[i] == "--verdict":
                    verdict = rest[i + 1]
                elif rest[i] == "--results":
                    results = rest[i + 1]
                else:
                    action = rest[i + 1]
                i += 2
            else:
                die(f"prune record: bad argument {rest[i]!r}", 2)
        if verdict not in ("ACCEPT", "REJECT", "UNMEASURED"):
            die("--verdict must be ACCEPT, REJECT or UNMEASURED (a RERUN is not a decision: "
                "sweep again)", 2)
        for r in plan["items"]:
            if r["name"] == name and r["state"] in ("pending", "running"):
                r.update(state="decided", verdict=verdict, results=results, action=action)
                _save_plan(repo, plan)
                left = sum(1 for x in plan["items"] if x["state"] in ("pending", "running"))
                print(f"recorded {name}: {verdict} — {left} item(s) left")
                return 0
        die(f"'{name}' is not a pending item of this plan", 1)

    if sub == "finish":
        left = [r["name"] for r in plan["items"] if r["state"] in ("pending", "running")]
        if plan["status"] != "approved":
            die(f"the plan is {plan['status']}, not approved", 1)
        if left and "--force" not in rest:
            die(f"still to test: {' '.join(left)} (or `cortex prune finish --force` to stop here)", 1)
        plan["status"], plan["finished"] = "done", datetime.now(timezone.utc).isoformat(timespec="seconds")
        _save_plan(repo, plan)
        if plan.get("model"):                   # the next pass compares against this
            sp = os.path.join(repo, ".evolve", "state.json")
            st = _state(repo)
            st["last_prune_model"] = plan["model"]
            st["last_prune_at"] = plan["finished"]
            with open(sp + ".tmp", "w") as fh:
                json.dump(st, fh)
            os.replace(sp + ".tmp", sp)
        d = [r for r in plan["items"] if r["state"] == "decided"]
        print(f"prune pass done: tested {len(d)}, "
              f"accepted {sum(1 for r in d if r['verdict'] == 'ACCEPT')}, "
              f"rejected {sum(1 for r in d if r['verdict'] == 'REJECT')}, "
              f"unmeasured {sum(1 for r in d if r['verdict'] == 'UNMEASURED')}, "
              f"skipped {sum(1 for r in plan['items'] if r['state'] in ('skipped', 'blocked'))}"
              + (f", stopped early: {' '.join(left)}" if left else ""))
        return 0

    die(f"prune: unknown subcommand {sub!r}", 2)


COMMANDS = {
    "check": cmd_check, "summary": cmd_summary, "hash": cmd_hash,
    "touching": cmd_touching, "observe": cmd_observe, "fixpatch": cmd_fixpatch, "task": cmd_task,
    "evolve-phase": cmd_evolve_phase, "sandbox-dir": cmd_sandbox_dir,
    "transcripts": cmd_transcripts,
    "candidate-info": cmd_candidate_info, "cli-version": cmd_cli_version, "parallel": cmd_parallel,
    "usage": cmd_usage, "prune": cmd_prune,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)
    sys.exit(COMMANDS[sys.argv[1]](sys.argv[2:]))
