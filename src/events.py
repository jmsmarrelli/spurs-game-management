"""Build three auditable event cohorts from public NBA records."""

import json
import re
import numpy as np
import pandas as pd
from .common import ROOT, shots, save_json, TEAM

SAS = 1610612759


def seconds(clock):
    m = re.fullmatch(r"PT(\d+)M([\d.]+)S", clock)
    if not m:
        raise ValueError(clock)
    return int(m[1]) * 60 + float(m[2])


def window(p, index, duration, before=False):
    """Score changes on the game clock; include later events at the same timestamp."""
    clock = p.iloc[index].seconds
    if before:
        earlier = p[(p.index < index) & (p.seconds > clock + duration)]
        base = earlier.iloc[-1] if len(earlier) else p.iloc[0]
        end = p.iloc[index]
    else:
        following = p[(p.index >= index) & (p.seconds >= clock - duration)]
        base = p.iloc[index]
        end = following.iloc[-1]
    return float(end.sas_score - base.sas_score), float(end.opp_score - base.opp_score)


def snapshot(p, index):
    e = p.iloc[index]
    return dict(
        game_id=int(e.gameId),
        event_id=int(e.actionNumber),
        period=int(e.period),
        seconds=float(e.seconds),
        date=e.date,
        margin=float(e.sas_score - e.opp_score),
        opponent=e.opponent,
    )


def normalize_team_ids(frame):
    return np.where(
        frame.teamId.gt(0),
        frame.teamId,
        np.where(frame.personId.isin(TEAM), frame.personId, 0),
    )


def return_attempts(p, index):
    after = p[p.index > index]
    opponent = after[
        after.teamId.ne(SAS)
        & after.teamId.gt(0)
        & (
            after.isFieldGoal.eq(1)
            | after.actionType.eq("Turnover")
            | (
                after.actionType.eq("Free Throw")
                & ~after.description.str.contains("Technical", na=False)
            )
        )
    ]
    returning = after.iloc[:0]
    if len(opponent):
        returning = after[
            (after.index > opponent.index[0])
            & after.teamId.eq(SAS)
            & after.isFieldGoal.eq(1)
        ]
    return opponent, returning


def run():
    raw = pd.read_csv(ROOT / "data/raw/nbastatsv3_2025.csv", low_memory=False)
    s = shots(2025)
    games = (
        s.loc[s.team.eq("SAS")]
        .groupby("GAME_ID")
        .agg(
            date=("date", "first"),
            home=("HTM", "first"),
            opponent=("opponent", "first"),
        )
    )
    raw = raw[raw.gameId.isin(games.index)].sort_values(["gameId", "actionId"]).copy()
    raw["seconds"] = raw.clock.map(seconds)
    # Team events (including shot-clock turnovers) can store the club in personId.
    raw["teamId"] = normalize_team_ids(raw)
    audit = []
    valid = []
    for game, g in raw.groupby("gameId"):
        g = g.copy()
        reason = []
        if g.actionId.duplicated().any():
            reason.append("duplicate action order")
        for col in ["scoreHome", "scoreAway"]:
            g[col] = g[col].ffill().fillna(0)
            if g[col].diff().fillna(0).lt(0).any():
                reason.append("score decreased")
            if g[col].diff().fillna(0).gt(4).any():
                reason.append("unexplained score jump")
        meta = games.loc[game]
        is_home = meta.home == "SAS"
        g["sas_score"] = g.scoreHome if is_home else g.scoreAway
        g["opp_score"] = g.scoreAway if is_home else g.scoreHome
        g["date"] = str(meta.date.date())
        g["opponent"] = meta.opponent
        for period, p in g.groupby("period"):
            if p.seconds.diff().fillna(0).gt(0.01).any():
                reason.append("clock reversal")
            if (
                abs(p.seconds.iloc[0] - (720 if period <= 4 else 300)) > 0.01
                or p.seconds.iloc[-1] != 0
            ):
                reason.append("incomplete period")
        fg = g[g.isFieldGoal.eq(1)]
        joined = fg.merge(
            s[s.GAME_ID.eq(game)],
            left_on="actionNumber",
            right_on="GAME_EVENT_ID",
            suffixes=("", "_shot"),
            validate="one_to_one",
        )
        agrees = (
            joined.personId.eq(joined.PLAYER_ID)
            & joined.shotValue.eq(np.where(joined.three, 3, 2))
            & joined.shotResult.eq(np.where(joined.made, "Made", "Missed"))
        )
        if (
            len(joined) != len(fg)
            or len(joined) != int(s.GAME_ID.eq(game).sum())
            or not agrees.all()
        ):
            reason.append("shot feeds disagree")
        # Scoring must reconcile to made shots and made free throws at game level.
        ft = g[
            g.actionType.eq("Free Throw")
            & ~g.description.str.startswith("MISS", na=False)
        ]
        for team, score in [(SAS, g.sas_score.iloc[-1]), (None, g.opp_score.iloc[-1])]:
            rows = fg[fg.teamId.eq(SAS) if team == SAS else ~fg.teamId.eq(SAS)]
            f = ft[ft.teamId.eq(SAS) if team == SAS else ~ft.teamId.eq(SAS)]
            expected = (rows.shotValue * rows.shotResult.eq("Made")).sum() + len(f)
            if expected != score:
                reason.append("scoring events do not reconcile")
        audit.append(
            {
                "game_id": game,
                "status": "; ".join(sorted(set(reason))) if reason else "valid",
                "events": len(g),
                "spurs_points": g.sas_score.iloc[-1],
                "opponent_points": g.opp_score.iloc[-1],
            }
        )
        if not reason:
            valid.append(g)
    events = pd.concat(valid)
    pd.DataFrame(audit).to_csv(ROOT / "results/game_audit.csv", index=False)
    turnovers = []
    timeouts = []
    quarters = []
    subtype_counts = events[
        events.actionType.eq("Turnover") & events.teamId.eq(SAS)
    ].subType.value_counts()
    subtype_counts.rename_axis("subtype").rename("count").to_csv(
        ROOT / "results/turnover_subtypes.csv"
    )
    for (game, period), frame in events.groupby(["gameId", "period"]):
        p = frame.reset_index(drop=True)
        for i, e in p[
            p.actionType.eq("Turnover") & p.teamId.eq(SAS) & p.seconds.ge(16)
        ].iterrows():
            # Steals appear as same-clock auxiliary rows, generally after the turnover.
            nearby = p[(p.seconds == e.seconds) & (p.index >= i) & (p.index <= i + 3)]
            steal = nearby[
                nearby.teamId.ne(SAS)
                & nearby.description.str.contains("STEAL", na=False)
            ]
            if len(steal) > 1:
                raise ValueError("Ambiguous same-clock steal linkage")
            kind = "Steal-linked" if len(steal) else "No linked steal"
            row = {
                **snapshot(p, i),
                "kind": kind,
                "player": e.playerName,
                "player_id": int(e.personId),
                "subtype": e.subType,
            }
            for horizon in [8, 12, 16]:
                own, opp = window(p, i, horizon)
                row[f"allowed_{horizon}"] = opp
                row[f"scored_{horizon}"] = own
            row["steal_event_id"] = int(steal.iloc[0].actionNumber) if len(steal) else 0
            row["timeout_12"] = int(
                p[(p.index > i) & p.seconds.ge(e.seconds - 12)]
                .actionType.eq("Timeout")
                .any()
            )
            turnovers.append(row)
        # Index a decision after an opponent made FG, after all same-clock events.
        for clock, at_clock in p.groupby("seconds", sort=False):
            if not 60 <= clock <= 660 or period > 4:
                continue
            made = at_clock[
                at_clock.isFieldGoal.eq(1)
                & at_clock.shotResult.eq("Made")
                & at_clock.teamId.ne(SAS)
            ]
            if len(made) != 1:
                continue
            stops = at_clock[at_clock.actionType.eq("Timeout")]
            treated = stops.personId.eq(SAS).any()
            if len(stops) and not treated:
                continue
            # Do not pool sequences with two clubs calling a timeout at the same clock.
            if treated and stops.personId.ne(SAS).any():
                continue
            i = at_clock.index[-1]
            row = snapshot(p, i)
            row["event_id"] = int(made.iloc[0].actionNumber)
            own, opp = window(p, i, 60, before=True)
            row.update(treated=int(treated), pre_net=own - opp, pre_allowed=opp)
            own, opp = window(p, i, 60)
            row.update(post_net=own - opp, post_allowed=opp, post_scored=own)
            row["later_timeout"] = int(
                p[(p.index > i) & p.seconds.ge(clock - 60)]
                .actionType.eq("Timeout")
                .any()
            )
            timeouts.append(row)
        if period <= 3:
            choices = p[
                p.teamId.eq(SAS) & p.isFieldGoal.eq(1) & p.seconds.between(20, 40)
            ]
            if len(choices):
                i = choices.index[0]
                e = p.iloc[i]
                row = snapshot(p, i)
                # A return attempt requires an intervening opponent offensive event.
                opp, return_shots = return_attempts(p, i)
                before = p.iloc[max(0, i - 1)]
                end = p.iloc[-1]
                row.update(
                    player=e.playerName,
                    first_points=float(e.shotValue * (e.shotResult == "Made")),
                    first_three=int(e.shotValue == 3),
                    return_attempt=int(len(return_shots) > 0),
                    return_seconds=(
                        float(return_shots.iloc[0].seconds)
                        if len(return_shots)
                        else np.nan
                    ),
                    first_opp_event=int(opp.iloc[0].actionNumber) if len(opp) else 0,
                    return_event=(
                        int(return_shots.iloc[0].actionNumber)
                        if len(return_shots)
                        else 0
                    ),
                    close_scored=float(end.sas_score - before.sas_score),
                    close_allowed=float(end.opp_score - before.opp_score),
                )
                row["margin"] = float(before.sas_score - before.opp_score)
                row["clock_band"] = (
                    "20–<28 seconds"
                    if e.seconds < 28
                    else ("28–<34 seconds" if e.seconds < 34 else "34–40 seconds")
                )
                quarters.append(row)
    for name, rows in [
        ("turnovers", turnovers),
        ("timeout_candidates", timeouts),
        ("quarter_attempts", quarters),
    ]:
        pd.DataFrame(rows).to_csv(ROOT / f"data/{name}.csv.gz", index=False)
    summary = {
        "source_games": len(games),
        "retained_games": len(valid),
        "excluded_games": len(games) - len(valid),
        "turnovers_with_16_seconds": len(turnovers),
        "timeout_candidates": len(timeouts),
        "eligible_timeout_triggers": sum(x["treated"] for x in timeouts),
        "quarter_attempts": len(quarters),
        "first_date": str(events.date.min()),
        "last_date": str(events.date.max()),
    }
    save_json("data_summary.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
