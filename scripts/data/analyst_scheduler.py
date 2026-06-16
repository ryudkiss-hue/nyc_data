#!/usr/bin/env python
"""APScheduler wrapper: run `socrata analyst run` on a cron schedule."""

from __future__ import annotations

import os
import subprocess
import sys

from apscheduler.schedulers.blocking import BlockingScheduler

def run_pack() -> None:
    profile = os.environ.get("ANALYST_PROFILE", "config/analyst_profile.yaml")
    subprocess.run(
        [sys.executable, "-m", "socrata_toolkit.core.cli", "analyst", "run", "--profile", profile],
        check=False,
    )

def main() -> None:
    cron = os.environ.get("ANALYST_CRON", "0 6 * * 1").split()
    if len(cron) != 5:
        raise SystemExit("ANALYST_CRON must be five fields: min hour day month dow")
    run_pack()
    sched = BlockingScheduler()
    sched.add_job(
        run_pack,
        "cron",
        minute=cron[0],
        hour=cron[1],
        day=cron[2],
        month=cron[3],
        day_of_week=cron[4],
    )
    sched.start()

if __name__ == "__main__":
    main()
