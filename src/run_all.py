"""Rebuild public-data cohorts, estimates, figures and articles."""

import argparse
from .common import ROOT
from . import (
    data,
    events,
    turnover_cost,
    timeout_reset,
    quarter_clock,
    figures,
    publish,
)


def run(fetch=False):
    for name in ["data/raw", "results", "figures"]:
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    if fetch:
        data.fetch()
    for name, fn in [
        ("Event audit", events.run),
        ("Turnovers", turnover_cost.run),
        ("Timeouts", timeout_reset.run),
        ("Quarter clock", quarter_clock.run),
        ("SQL", data.database),
        ("Figures", figures.run),
        ("Articles", publish.run),
    ]:
        fn()
        print(name, "complete", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--fetch", action="store_true")
    run(p.parse_args().fetch)
