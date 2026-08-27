#!/usr/bin/env python3
"""Measure what a plan really cost, without anyone writing anything down.

It exists because nobody starts a stopwatch: any measurement that depends on
remembering does not get recorded. These two series already exist and nobody
has to be asked for them:

  - `pacto exec` stamps the time on every task it closes (in `tasks.md`)
  - `git` stamps the time on every commit

With both, a gap between activity is one of three things, and they have to be
told apart because they mean opposite things:

  | Gap                       | What it is                                   |
  |---------------------------|----------------------------------------------|
  | Ends in a closed task     | PLAN WORK                                    |
  | Ends in an unrelated commit | COLLATERAL: real effort, on something else |
  | Longer than the threshold | NO ACTIVITY: neither commits nor tasks       |

Measured 2026-08-20: between two tasks of the `estados-de-ejecucion` plan,
2 h 48 min went by. A stopwatch would have said that task cost three hours. It
cost five minutes: the gap held a test fix, a production 500 and a migration.
It was neither the task nor a break.

A LIMIT WORTH KNOWING: thinking leaves no commits. A long stretch of analysis,
of reading code or of deciding with someone looks exactly like lunch, and falls
into "no activity". That is why the column is NOT called break: it says the
only thing that can be claimed, that no trace was left. The effort figure is a
FLOOR.

    base-harness time <slug>    # one plan
    base-harness pace           # the real pace across every closed plan
    base-harness time --autotest  # check the arithmetic
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# The project is set by the CLI before calling `main`. Current directory by
# default, so `python3 -m base_harness.plan_time` still works from a project
# root without going through the CLI.
PROG = "base-harness time"

ROOT = Path.cwd()
PLANS = ROOT / ".pacto" / "plans"


def configure(root: Path) -> None:
    """Set which project is being worked on. Called by `bin/base-harness`."""
    global ROOT, PLANS
    ROOT = root
    PLANS = root / ".pacto" / "plans"


# `pacto exec` leaves this line when it closes a task. The leading `[N.M]` is
# not pacto's: it is the convention of the `plan-task` skill, and it is the only
# thing that tells which task each timestamp belongs to.
EVIDENCE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})\s+`?\[?(\d+\.\d+)?\]?", re.M)
TASK = re.compile(r"^- \[([ x])\] (\d+\.\d+) (.+)$", re.M)

# --- Language of the plans -------------------------------------------------
# This script reads plans written in Spanish. If yours are in another language,
# this block is the ONLY thing to translate.
#
# And it has to be translated, because not translating it **raises no error**:
# the script keeps running, classifies every task as "build" and produces a
# believable, empty breakdown, which is worse than having none. `ESTIMATE_WORD`
# must also match the one `plans_check.py` looks for.
ESTIMATE_WORD = r"Estimaci[oó]n"
DECIDE_WORDS = r"resolver|decidir|declarar|reconocimiento|enumerar|checklist|acotar"
VERIFY_WORDS = r"verificar|confirmar|revisar|comprobar"
CLOSING_WORD = "cierra"   # in a commit subject: marks it as belonging to the plan

ESTIMATE = re.compile(rf"^- {ESTIMATE_WORD}:\s*([\d.,]+)\s*h", re.M | re.I)

# What kind of work each task is, judged by what it says. It answers the
# question that changes how people work the most: whether the time goes into
# deciding or into building.
DECIDE = re.compile(DECIDE_WORDS, re.I)
VERIFY = re.compile(VERIFY_WORDS, re.I)

KINDS = ("decide", "build", "verify")


def kind_of(text: str) -> str:
    if DECIDE.search(text):
        return "decide"
    if VERIFY.search(text):
        return "verify"
    return "build"


def find_plan(slug: str) -> Path | None:
    for tasks in PLANS.glob(f"*/{slug}/tasks.md"):
        return tasks
    return None


def commits_between(since: datetime, until: datetime, slug: str):
    """Commits in the interval, marking which ones belong to the plan.

    A commit belongs to the plan if it names its slug or says it closes a task.
    The rest is collateral: real work that happened meanwhile, on something else.
    """
    output = subprocess.run(
        ["git", "log", "--since", since.isoformat(), "--until", until.isoformat(),
         "--pretty=%at%x09%s%x09%b", "--all"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    found = []
    for line in output.splitlines():
        timestamp, _, rest = line.partition("\t")
        try:
            when = datetime.fromtimestamp(int(timestamp))
        except ValueError:
            continue
        text = rest.lower()
        own = slug in text or CLOSING_WORD in text
        found.append((when, "plan" if own else "collateral", None))
    return found


def split_gaps(events, threshold_min: int):
    """The core: split the gaps across the three buckets.

    Kept separate on purpose so it can be checked without git or files
    (--autotest). Getting it wrong produces believable, false numbers, which is
    the worst thing that can happen to a measurement.
    """
    threshold = timedelta(minutes=threshold_min)
    buckets = {"plan": timedelta(), "collateral": timedelta(), "no_activity": timedelta()}
    by_kind: dict[str, timedelta] = {}

    for (t0, _, _), (t1, bucket, kind) in zip(events, events[1:]):
        gap = t1 - t0
        if gap > threshold:
            buckets["no_activity"] += gap
        elif bucket == "plan":
            buckets["plan"] += gap
            if kind:
                by_kind[kind] = by_kind.get(kind, timedelta()) + gap
        else:
            buckets["collateral"] += gap
    return buckets, by_kind


def measure(tasks: Path, slug: str, threshold_min: int):
    text = tasks.read_text()

    kinds = {number: kind_of(title) for _, number, title in TASK.findall(text)}

    marks = []
    for day, hour, number in EVIDENCE.findall(text):
        marks.append((datetime.strptime(f"{day} {hour}", "%Y-%m-%d %H:%M"),
                      "plan", kinds.get(number) if number else None))
    if len(marks) < 2:
        return None

    # Sorted by date, breaking ties with text and **never with the raw kind**:
    # an execution note without the `[N.M]` prefix has no task, so its kind is
    # None, and as soon as it shared a date with another mark the sort compared
    # None against a string and blew up. Seen 2026-08-25 closing
    # `brain-agente-maestro`, which is exactly when this script is needed.
    events = sorted(
        marks + commits_between(
            min(m[0] for m in marks),
            max(m[0] for m in marks) + timedelta(minutes=1),
            slug),
        key=lambda event: (event[0], str(event[1] or ""), str(event[2] or "")),
    )
    buckets, by_kind = split_gaps(events, threshold_min)

    tasks_found = TASK.findall(text)
    estimate = ESTIMATE.search(text)
    return {
        "state": tasks.parent.parent.name,
        "tasks": len(tasks_found),
        "closed": sum(1 for mark, _, _ in tasks_found if mark == "x"),
        "start": min(m[0] for m in marks),
        "end": max(m[0] for m in marks),
        "numbered": sum(1 for _, _, kind in marks if kind),
        **buckets,
        "by_kind": by_kind,
        "estimate": float(estimate.group(1).replace(",", ".")) if estimate else None,
    }


def hours(delta: timedelta) -> float:
    return round(delta.total_seconds() / 3600, 1)


def measured_pace(threshold_min: int):
    """The real pace across plans already closed.

    This is what makes the system tune itself: the next plan's estimate comes
    from what the previous ones cost, not from anyone's judgement.
    """
    total_minutes = 0.0
    total_tasks = 0
    plans = []
    discarded = []
    for tasks in sorted(PLANS.glob("done/*/tasks.md")):
        result = measure(tasks, tasks.parent.name, threshold_min)
        if not result or not result["closed"]:
            continue
        minutes = result["plan"].total_seconds() / 60
        effort = result["plan"] + result["collateral"]

        # A plan executed in dribs and drabs over weeks cannot be measured this
        # way: almost everything falls into "no activity" and the little time
        # left produces a false pace. Better to drop it and say so than to
        # average garbage.
        if effort.total_seconds() and result["no_activity"] > effort * 5:
            discarded.append((tasks.parent.name, "run in scattered bits, not in sessions"))
            continue

        total_minutes += minutes
        total_tasks += result["closed"]
        plans.append((tasks.parent.name, result["closed"], minutes / result["closed"]))
    return plans, (total_minutes / total_tasks if total_tasks else None), discarded


def report(slug: str, threshold_min: int) -> int:
    tasks = find_plan(slug)
    if tasks is None:
        print(f"cannot find the plan '{slug}'")
        return 1
    result = measure(tasks, slug, threshold_min)
    if result is None:
        print(f"{slug}: fewer than two closed tasks, nothing to measure yet")
        return 0

    total = result["plan"] + result["collateral"]
    print(f"\n{slug}  ({result['closed']}/{result['tasks']} tasks · {result['state']})")
    print(f"  from {result['start']:%d/%m %H:%M} to {result['end']:%d/%m %H:%M}")
    print()
    print(f"  plan work            {hours(result['plan']):6.1f} h")
    print(f"  collateral           {hours(result['collateral']):6.1f} h", end="")
    print(f"   ({100 * result['collateral'] / total:.0f}% of the effort)"
          if total.total_seconds() else "")
    print(f"  no activity          {hours(result['no_activity']):6.1f} h   "
          f"(rest, or analysis leaving no commits)")
    print(f"  {'-' * 30}")
    print(f"  recorded effort      {hours(total):6.1f} h   (a floor: what left a trace)")

    if result["by_kind"]:
        print("\n  where the plan's time went:")
        for kind in KINDS:
            if kind in result["by_kind"]:
                spent = result["by_kind"][kind]
                print(f"    {kind:11} {hours(spent):5.1f} h  ({100 * spent / result['plan']:.0f}%)")
    elif result["closed"]:
        print("\n  no breakdown: the evidence does not start with `[N.M]` (see the plan-task skill)")

    if result["closed"]:
        pace = result["plan"].total_seconds() / 60 / result["closed"]
        print(f"\n  pace: {pace:.0f} min per task")
        _, average, _ = measured_pace(threshold_min)
        if average:
            print(f"  average across closed plans: {average:.0f} min per task")

    if result["estimate"]:
        real = hours(result["plan"])
        drift = 100 * (real - result["estimate"]) / result["estimate"]
        print(f"\n  estimated {result['estimate']:.1f} h  ->  {real:.1f} h so far   drift {drift:+.0f}%")

        # A mid-flight warning: knowing the drift once the plan is over is
        # useless. With half of it done it can already be projected.
        remaining = result["tasks"] - result["closed"]
        if remaining and result["closed"]:
            projection = real / result["closed"] * result["tasks"]
            print(f"  projection over {result['tasks']} tasks: {projection:.1f} h", end="")
            if projection > result["estimate"] * 1.2:
                print(f"   <-- heading {100 * (projection / result['estimate'] - 1):.0f}% over")
            else:
                print("   (within the estimate)")
    else:
        print("\n  no estimate written: add `- Estimación: N h` to the metadata of tasks.md")
    return 0


def autotest() -> int:
    """Check the gap split with made-up times.

    Interval arithmetic fails silently: it produces believable, false numbers.
    This pins it down.
    """
    at = lambda hour, minute: datetime(2026, 1, 1, hour, minute)
    events = [
        (at(9, 0), "plan", "decide"),      # start
        (at(9, 30), "plan", "decide"),     # 30 min deciding
        (at(9, 50), "collateral", None),   # 20 min on something else
        (at(12, 0), "plan", "build"),      # 130 min of nothing -> no activity
        (at(12, 20), "plan", "build"),     # 20 min building
    ]
    buckets, kinds = split_gaps(events, 60)
    failures = []
    expected = {"plan": 50, "collateral": 20, "no_activity": 130}
    for bucket, minutes in expected.items():
        real = buckets[bucket].total_seconds() / 60
        if real != minutes:
            failures.append(f"{bucket}: expected {minutes} min, got {real:.0f}")
    if kinds.get("decide", timedelta()).total_seconds() / 60 != 30:
        failures.append("decide: expected 30 min")
    if kinds.get("build", timedelta()).total_seconds() / 60 != 20:
        failures.append("build: expected 20 min")

    for failure in failures:
        print(f"  FAIL  {failure}")
    print("  autotest: correct" if not failures else f"  autotest: {len(failures)} failures")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=PROG)
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--threshold", type=int, default=60,
                        help="minutes without activity beyond which time is not counted (default 60)")
    parser.add_argument("--pace", action="store_true", help="real pace across plans already closed")
    parser.add_argument("--autotest", action="store_true", help="check the gap-split arithmetic")
    args = parser.parse_args(argv)

    if args.autotest:
        return autotest()

    if args.pace:
        plans, average, discarded = measured_pace(args.threshold)
        if not plans:
            print("no closed plans with measurement yet")
            return 0
        print("\nreal pace across closed plans")
        for name, tasks, pace in plans:
            print(f"  {name:34} {tasks:3} tasks   {pace:5.1f} min/task")
        print(f"\n  average: {average:.1f} min per task   "
              f"({sum(plan[1] for plan in plans)} tasks measured)")
        print(f"  use this figure to estimate the next plan, not one from the past")
        for name, why in discarded:
            print(f"\n  discarded {name}: {why}")
        return 0

    if not args.slug:
        parser.print_help()
        return 1
    return report(args.slug, args.threshold)


if __name__ == "__main__":
    sys.exit(main())
