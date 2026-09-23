import json
import numpy as np
import pandas as pd
from .common import ROOT, save_json
from .statistics import mean_ci


def match(d, pre_caliper=0):
    rows = []
    audit = []
    for _, t in d[d.treated.eq(1)].iterrows():
        controls = d[
            (d.treated.eq(0))
            & d.game_id.eq(t.game_id)
            & d.period.eq(t.period)
            & d.seconds.sub(t.seconds).abs().between(90, 240)
            & d.margin.sub(t.margin).abs().le(6)
            & d.pre_net.sub(t.pre_net).abs().le(pre_caliper)
        ].copy()
        controls["distance"] = (
            ((controls.seconds - t.seconds) / 120) ** 2
            + ((controls.margin - t.margin) / 5) ** 2
            + ((controls.pre_net - t.pre_net) / 4) ** 2
        )
        controls = controls.sort_values(["distance", "event_id"]).head(3)
        audit.append(
            dict(
                game_id=int(t.game_id), event_id=int(t.event_id), controls=len(controls)
            )
        )
        for _, c in controls.iterrows():
            row = dict(
                game_id=int(t.game_id),
                event_id=int(t.event_id),
                control_id=int(c.event_id),
                weight=1 / len(controls),
                distance=c.distance,
            )
            for col in [
                "pre_net",
                "post_net",
                "margin",
                "seconds",
                "post_allowed",
                "post_scored",
                "later_timeout",
            ]:
                row["treated_" + col] = t[col]
                row["control_" + col] = c[col]
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(audit)


def run():
    d = pd.read_csv(ROOT / "data/timeout_candidates.csv.gz")
    pairs, audit = match(d)
    pairs.to_csv(ROOT / "results/timeout_pairs.csv", index=False)
    audit.to_csv(ROOT / "results/timeout_match_audit.csv", index=False)
    observations = []
    for (game, event), g in pairs.groupby(["game_id", "event_id"]):
        row = dict(game_id=game, event_id=event)
        for col in [
            "pre_net",
            "post_net",
            "margin",
            "seconds",
            "post_allowed",
            "post_scored",
            "later_timeout",
        ]:
            row["treated_" + col] = g["treated_" + col].iloc[0]
            row["control_" + col] = (g.weight * g["control_" + col]).sum()
        row["difference"] = row["treated_post_net"] - row["control_post_net"]
        row["change_difference"] = row["difference"] - (
            row["treated_pre_net"] - row["control_pre_net"]
        )
        observations.append(row)
    matched = pd.DataFrame(observations)
    matched.to_csv(ROOT / "results/timeout_matched.csv", index=False)
    rows = []
    for group in ["treated", "control"]:
        for phase in ["pre", "post"]:
            value, lo, hi = mean_ci(matched, f"{group}_{phase}_net")
            rows.append(dict(group=group, phase=phase, net=value, lower=lo, upper=hi))
    pd.DataFrame(rows).to_csv(ROOT / "results/timeout_trajectories.csv", index=False)
    balance = []
    for col in ["pre_net", "margin", "seconds"]:
        before = d[d.treated.eq(1)][col].mean() - d[d.treated.eq(0)][col].mean()
        after = (matched["treated_" + col] - matched["control_" + col]).mean()
        scale = d[col].std()
        balance.append(dict(variable=col, before=before / scale, after=after / scale))
    pd.DataFrame(balance).to_csv(ROOT / "results/timeout_balance.csv", index=False)
    effect, lo, hi = mean_ci(matched, "difference")
    did, dlo, dhi = mean_ci(matched, "change_difference")
    sensitivity = []
    for caliper in [0, 1, 2]:
        sample, _ = match(d, caliper)
        effects = []
        for (game, event), g in sample.groupby(["game_id", "event_id"]):
            effects.append(
                dict(
                    game_id=game,
                    difference=g.treated_post_net.iloc[0]
                    - (g.weight * g.control_post_net).sum(),
                    pre_difference=g.treated_pre_net.iloc[0]
                    - (g.weight * g.control_pre_net).sum(),
                )
            )
        ef = pd.DataFrame(effects)
        value, l, h = mean_ci(ef, "difference")
        sensitivity.append(
            dict(
                pre_caliper=caliper,
                timeouts=len(ef),
                games=ef.game_id.nunique(),
                estimate=value,
                lower=l,
                upper=h,
                pre_difference=ef.pre_difference.mean(),
            )
        )
    pd.DataFrame(sensitivity).to_csv(
        ROOT / "results/timeout_sensitivity.csv", index=False
    )
    raw = []
    for treated, g in d.groupby("treated"):
        raw.append(
            dict(
                treated=int(treated),
                events=len(g),
                pre_net=g.pre_net.mean(),
                post_net=g.post_net.mean(),
            )
        )
    pd.DataFrame(raw).to_csv(ROOT / "results/timeout_unmatched.csv", index=False)
    summary = {
        "eligible_timeouts": int(d.treated.sum()),
        "matched_timeouts": len(matched),
        "matched_games": matched.game_id.nunique(),
        "unique_controls": len(pairs[["game_id", "control_id"]].drop_duplicates()),
        "matched_difference": effect,
        "lower": lo,
        "upper": hi,
        "change_difference": did,
        "change_lower": dlo,
        "change_upper": dhi,
        "later_timeout_treated_share": matched.treated_later_timeout.mean(),
        "later_timeout_control_share": matched.control_later_timeout.mean(),
        "trajectories": rows,
    }
    save_json("timeout_summary.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
