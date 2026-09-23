"""Small, explicit estimators with game-level resampling."""

import numpy as np
import pandas as pd
from .common import SEED


def mean_ci(d, value, reps=2000):
    g = d.groupby("game_id")[value].agg(["sum", "count"]).to_numpy()
    rng = np.random.default_rng(SEED)
    chosen = rng.integers(0, len(g), (reps, len(g)))
    a = g[chosen].sum(axis=1)
    return (
        float(d[value].mean()),
        *np.quantile(a[:, 0] / a[:, 1], [0.025, 0.975]).tolist(),
    )


def fixed_effect(d, outcome, reps=2000):
    d = d.copy()
    both = d.groupby("game_id").live.nunique()
    d = d[d.game_id.isin(both[both.eq(2)].index)].copy()
    d["margin_scaled"] = d.margin.clip(-25, 25) / 25
    d["margin_squared"] = d.margin_scaled**2
    d["clock_scaled"] = d.seconds / 720
    cols = ["live", "margin_scaled", "margin_squared", "clock_scaled"]
    for n in sorted(d.period.unique())[1:]:
        name = f"period_{n}"
        d[name] = d.period.eq(n).astype(int)
        cols.append(name)
    v = d[cols + [outcome]].astype(float)
    v = v - v.groupby(d.game_id).transform("mean")
    xx = []
    xy = []
    for _, g in v.groupby(d.game_id):
        x = g[cols].to_numpy()
        y = g[outcome].to_numpy()
        xx.append(x.T @ x)
        xy.append(x.T @ y)
    xx = np.array(xx)
    xy = np.array(xy)
    b = (np.linalg.pinv(xx.sum(axis=0)) @ xy.sum(axis=0))[0]
    rng = np.random.default_rng(SEED)
    values = []
    for _ in range(reps):
        i = rng.integers(0, len(xx), len(xx))
        values.append((np.linalg.pinv(xx[i].sum(axis=0)) @ xy[i].sum(axis=0))[0])
    lo, hi = np.quantile(values, [0.025, 0.975])
    return dict(
        estimate=b, lower=lo, upper=hi, games=d.game_id.nunique(), events=len(d)
    )


def loss(y, p):
    p = np.clip(np.asarray(p), 1e-6, 1 - 1e-6)
    y = np.asarray(y)
    return -(y * np.log(p) + (1 - y) * np.log1p(-p))
