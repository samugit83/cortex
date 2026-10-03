"""stats.py — the statistics the pre-registration fixed, and nothing else.

Everything here was chosen in `PREREGISTRATION.md` §11 before any replicate ran.
Two ideas run through all of it:

**Rollouts of one task are not independent.** Five rollouts of `HB4` under one arm
are five draws of the same coin, and a task is a draw from the population of tasks
we could have written. An interval that counts 150 rollouts as 150 independent
observations is far too narrow, so every inferential number here resamples **tasks
and runs**, never rollouts, and Wilson intervals appear only as description with
that caveat attached.

**The comparison is paired.** Arms are measured on the same tasks, so the unit of
analysis is a task's *difference* between two arms, not two independent rates.

Nothing in this file reads a verdict or a hypothesis. It takes rows and returns
numbers.
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
from scipy import stats as sps

RNG_SEED = 20260920          # fixed here so every rebuild gives the same intervals
N_BOOT = 10_000
N_PERM = 10_000


# ------------------------------------------------------------ descriptive --
def wilson(k, n, z=1.96):
    """A binomial interval, for DESCRIPTION only: it treats rollouts as
    independent, which they are not, so it is always labelled as such."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    lo, hi = max(0.0, c - m), min(1.0, c + m)
    # The interval contains p in exact arithmetic. At k = 0 or k = n floating point
    # can leave a bound a hair on the wrong side — 0 of 54 gave lo = 6.9e-18, 90 of
    # 90 gave hi = 0.9999999999999999 — and matplotlib refuses an error bar of
    # -1e-16 outright, which is how F1 and F2 silently stopped regenerating.
    return (min(lo, p), max(hi, p))


def clopper_pearson(k, n, alpha=0.05):
    """Exact interval for a proportion of candidates or runs — the places where n
    is small enough that an approximation would mislead."""
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else sps.beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else sps.beta.ppf(1 - alpha / 2, k + 1, n - k)
    return (float(lo), float(hi))


def one_sided_upper(k, n, alpha=0.05):
    """The number quoted for a false-KEEP rate of 0 out of n: '0/20 -> 14%'."""
    if n == 0:
        return 1.0
    return 1.0 if k == n else float(sps.beta.ppf(1 - alpha, k + 1, n - k))


def fisher(a, b, c, d):
    """positives vs placebos: [[kept_pos, killed_pos], [kept_plac, killed_plac]]."""
    return sps.fisher_exact([[a, b], [c, d]])


def holm(pvalues, names=None):
    """Holm–Bonferroni across the four rule families. Returns adjusted p-values in
    the order given."""
    p = list(pvalues)
    n = len(p)
    order = sorted(range(n), key=lambda i: p[i])
    adj = [0.0] * n
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (n - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj if names is None else dict(zip(names, adj))


# ------------------------------------------------------------------ paired --
def cells(rows, arm_a, arm_b, families=None, split="holdout"):
    """-> {(run, task): (family, p_a, p_b, n_a, n_b)} over VALID rollouts.

    A task appears only when both arms measured it. `p` is that task's pass rate
    under that arm in that run — the unit everything below resamples.
    """
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if not r.get("valid"):
            continue
        if split is not None and r.get("split") != split:
            continue
        if families is not None and r.get("family") not in families:
            continue
        if r.get("arm") not in (arm_a, arm_b):
            continue
        acc[(r["run"], r["task"], r["family"])][r["arm"]].append(r["pass"])
    out = {}
    for (run, task, fam), by_arm in acc.items():
        a, b = by_arm.get(arm_a), by_arm.get(arm_b)
        if not a or not b:
            continue
        out[(run, task)] = (fam, sum(a) / len(a), sum(b) / len(b), len(a), len(b))
    return out


def paired_mean(cs):
    """The statistic: the mean over runs of the mean over that run's tasks of
    (arm_b - arm_a). Averaging within a run first stops a run that measured more
    tasks from weighing more than one that measured fewer."""
    by_run = defaultdict(list)
    for (run, _task), (_f, pa, pb, _na, _nb) in cs.items():
        by_run[run].append(pb - pa)
    if not by_run:
        return float("nan")
    return float(np.mean([np.mean(v) for v in by_run.values()]))


def two_way_bootstrap(cs, n_boot=N_BOOT, seed=RNG_SEED):
    """Resample RUNS and TASKS independently, `n_boot` times; 95 % percentile CI.

    Crossed, not nested: the tasks are the same 30 in every run, so a bootstrap
    that resampled tasks within runs would understate the task-to-task variance
    that is shared across runs. Runs are resampled with replacement and tasks are
    resampled with replacement, and a replicate uses the intersection.
    """
    runs = sorted({run for run, _ in cs})
    tasks = sorted({task for _, task in cs})
    if not runs or not tasks:
        return (float("nan"), float("nan"), [])
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        rs = rng.choice(len(runs), size=len(runs), replace=True)
        ts = rng.choice(len(tasks), size=len(tasks), replace=True)
        per_run = []
        for ri in rs:
            run = runs[ri]
            diffs = [cs[(run, tasks[ti])][2] - cs[(run, tasks[ti])][1]
                     for ti in ts if (run, tasks[ti]) in cs]
            if diffs:
                per_run.append(float(np.mean(diffs)))
        if per_run:
            draws.append(float(np.mean(per_run)))
    if not draws:
        return (float("nan"), float("nan"), [])
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return (float(lo), float(hi), draws)


def permutation_p(rows, arm_a, arm_b, families=None, split="holdout",
                  n_perm=N_PERM, seed=RNG_SEED):
    """Assumption-free p-value: shuffle the ARM LABELS within each task.

    The null is "for this task, which arm a rollout belonged to says nothing about
    whether it passed". Shuffling within a task keeps each task's own difficulty
    fixed, which is the whole point of pairing.
    """
    per_task = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if not r.get("valid"):
            continue
        if split is not None and r.get("split") != split:
            continue
        if families is not None and r.get("family") not in families:
            continue
        if r.get("arm") in (arm_a, arm_b):
            per_task[(r["run"], r["task"])][r["arm"]].append(r["pass"])
    keys = [k for k, v in per_task.items() if v.get(arm_a) and v.get(arm_b)]
    if not keys:
        return (float("nan"), float("nan"), 0)

    def statistic(assign):
        by_run = defaultdict(list)
        for k in keys:
            a, b = assign[k]
            by_run[k[0]].append(sum(b) / len(b) - sum(a) / len(a))
        return float(np.mean([np.mean(v) for v in by_run.values()]))

    observed = statistic({k: (per_task[k][arm_a], per_task[k][arm_b]) for k in keys})
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_perm):
        assign = {}
        for k in keys:
            pool = np.array(per_task[k][arm_a] + per_task[k][arm_b])
            rng.shuffle(pool)
            na = len(per_task[k][arm_a])
            assign[k] = (pool[:na].tolist(), pool[na:].tolist())
        if abs(statistic(assign)) >= abs(observed) - 1e-12:
            hits += 1
    # the +1 is the standard correction: a permutation test never reports p = 0,
    # because the observed assignment is itself one of the permutations
    return (observed, (hits + 1) / (n_perm + 1), len(keys))


def mixed_model(rows, arms, split="holdout"):
    """`pass ~ arm * family + (1|task) + (1|run)` as a robustness check.

    statsmodels has no crossed random effects, so `task` is the group and `run` is
    a variance component inside it — which is the closest thing available and is
    reported as such. With 3-5 runs the run variance is estimated poorly whatever
    is used, and the report says so rather than quoting it as if it were solid.
    """
    import pandas as pd
    import statsmodels.formula.api as smf

    df = pd.DataFrame([r for r in rows
                       if r.get("valid") and r.get("arm") in arms
                       and (split is None or r.get("split") == split)])
    if df.empty or df["arm"].nunique() < 2:
        return {"ok": False, "why": "not enough data"}
    df = df[["run", "task", "family", "arm", "pass"]].copy()
    df["arm"] = pd.Categorical(df["arm"], categories=list(arms))
    try:
        m = smf.mixedlm("Q('pass') ~ arm * family", df, groups=df["task"],
                        vc_formula={"run": "0 + C(run)"})
        fit = m.fit(reml=False, method="lbfgs")
        return {"ok": True, "engine": "statsmodels.MixedLM",
                "note": "task is the group; run enters as a variance component "
                        "(statsmodels has no crossed random effects)",
                "params": {k: float(v) for k, v in fit.params.items()},
                "pvalues": {k: float(v) for k, v in fit.pvalues.items()},
                "summary": str(fit.summary())}
    except Exception as ex:                                   # noqa: BLE001
        return {"ok": False, "why": f"{type(ex).__name__}: {ex}"}


def rate(rows, **where):
    """(passed, n, rate) over valid rollouts matching every key=value."""
    sel = [r for r in rows if r.get("valid")
           and all(r.get(k) == v for k, v in where.items() if v is not None)]
    k = sum(r["pass"] for r in sel)
    return k, len(sel), (k / len(sel) if sel else float("nan"))


def share_recovered(cs_treat, cs_full):
    """H12: what share of `evolved`'s gain over `none` a third arm recovers.

    Returns (share, lo, hi) with the interval from the same two-way bootstrap,
    computed on the ratio of the two paired means so that the numerator and the
    denominator are resampled together rather than separately.
    """
    runs = sorted({r for r, _ in cs_treat} & {r for r, _ in cs_full})
    tasks = sorted({t for _, t in cs_treat} & {t for _, t in cs_full})
    if not runs or not tasks:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(RNG_SEED)

    def one(rs, ts):
        num, den = [], []
        for ri in rs:
            run = runs[ri]
            a = [cs_treat[(run, tasks[ti])][2] - cs_treat[(run, tasks[ti])][1]
                 for ti in ts if (run, tasks[ti]) in cs_treat]
            b = [cs_full[(run, tasks[ti])][2] - cs_full[(run, tasks[ti])][1]
                 for ti in ts if (run, tasks[ti]) in cs_full]
            if a and b:
                num.append(float(np.mean(a)))
                den.append(float(np.mean(b)))
        if not num or abs(float(np.mean(den))) < 1e-9:
            return float("nan")
        return float(np.mean(num)) / float(np.mean(den))

    point = one(range(len(runs)), range(len(tasks)))
    draws = []
    for _ in range(N_BOOT):
        v = one(rng.choice(len(runs), len(runs), replace=True),
                rng.choice(len(tasks), len(tasks), replace=True))
        if not math.isnan(v):
            draws.append(v)
    if not draws:
        return (point, float("nan"), float("nan"))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return (point, float(lo), float(hi))
