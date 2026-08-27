#!/usr/bin/env python3
"""Check that every roadmap plan carries the harness obligations.

It exists because being written in the `create-plan` skill guarantees nothing:
whoever creates a plan without following it, or generates one with another
tool, skips them and nobody notices until the plan runs with no checklist and
no documentation.

It applies to every plan with the four-file layout, but **only blocks roadmap
plans** (the ones carrying `- Fase: N` in their `spec.md`). The rest are
REPORTED. That distinction is not cosmetic: turning the gate on for all of them
at once leaves the repo red, and a red repo ends with someone disabling the
check. Each plan stops being reported when its turn comes.

    base-harness plans      # report everything
    base-harness check      # fail only for roadmap plans
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# The project is set by the CLI before calling `main`. Current directory by
# default, so `python3 -m base_harness.plans_check` still works from a project
# root without going through the CLI.
PROG = "base-harness check"

ROOT = Path.cwd()
PLANS = ROOT / ".pacto" / "plans"


def configure(root: Path) -> None:
    """Set which project is being worked on. Called by `bin/base-harness`."""
    global ROOT, PLANS
    ROOT = root
    PLANS = root / ".pacto" / "plans"


# Each obligation: how it is detected, and why it exists.
#
# The needles stay in Spanish because they match the plan documents, which
# pacto writes in the workspace language. Translating them here would silently
# stop matching anything and every plan would pass.
REQUIRED = [
    ("Estimación:", "estimate in the metadata, written when the plan is created"),
    ("Reconocimiento:", "reconnaissance task before deciding anything"),
    ("YAGNI", "KISS/DRY/YAGNI checklist before writing code"),
    # Once the project has somewhere to declare its capabilities -a catalogue,
    # an API contract, a product harness- add here the obligation to list them
    # when opening the plan and verify them when closing it. Before that place
    # exists, the check would demand text pointing nowhere.
]

# File extensions that count as a `file:line` anchor in a blocker. Add your
# project's: if yours is missing, EVERY legitimate blocker gets reported as
# "no anchor" and the check turns into noise, which is how it ends up disabled.
EXTENSIONS = "|".join([
    "py", "ts", "tsx", "js", "jsx", "go", "rs", "rb", "php", "java", "kt",
    "cs", "swift", "c", "h", "cpp", "sql", "sh", "md", "yml", "yaml", "json",
    "toml", "tf", "html", "css",
])

# Accepts [ ] and [x]: a closed task still exists. With only [ ], a finished
# plan was reported as "no tasks" and references to done tasks looked broken.
TASK = re.compile(r"^\s*-\s*\[[ x]\] (\d+)\.(\d+)", re.M)

# `pacto status` marks a task as blocked by WORD, not by structure: it is
# enough for its text to contain "bloqueado" or "bloqueador" (verified
# 2026-08-20; "bloqueante", "bloqueo" and "bloquear" do not trigger it). The
# reconnaissance task said "...o bloqueador- antes de resolver nada" and left
# all 17 roadmap plans reporting `blocked` forever, so the status stopped
# telling a halted plan apart from one that merely says the word.
BLOCK_TRIGGER = re.compile(r"\bbloquead(?:o|or)\w*\b|\bblock(?:ed|er)\b", re.I)
OPEN_TASK = re.compile(r"^\s*-\s*\[ \] \d+\.\d+.*$", re.M)

# Cross references inside a plan, in the language plans are written in.
CROSS_REFERENCE = re.compile(r"(?:conforme a|segun|según|ver|de|en|con)\s+(\d+\.\d+)\b")
EMPTY_BLOCKER = re.compile(r"- (ninguno|ninguna|sin bloqueador|n/?a)\b", re.I)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=PROG)
    parser.add_argument("--check", action="store_true", help="fail if anything is missing")
    args = parser.parse_args(argv)

    problems: list[str] = []      # roadmap plans: these block
    pending: list[str] = []       # the rest: reported only
    checked = 0

    for spec in sorted(PLANS.glob("*/*/spec.md")):
        roadmap = bool(re.search(r"^- Fase: \d", spec.read_text(), re.M))
        bucket = problems if roadmap else pending
        checked += 1
        slug = spec.parent.name
        tasks_file = spec.parent / "tasks.md"
        if not tasks_file.is_file():
            bucket.append(f"{slug}: no tasks.md")
            continue
        body = tasks_file.read_text()

        for needle, why in REQUIRED:
            if needle not in body:
                bucket.append(f"{slug}: missing {why}")

        # Letters on BOTH sides of the dot. The earlier version only looked
        # after it -catching `1.1b` and letting `1b.1` through- and on
        # 2026-08-21 two whole phases numbered that way slipped in unnoticed.
        malformed = re.findall(
            r"^\s*-\s*\[[ x]\] (\d*[a-z]\w*\.\d+|\d+\.\d*[a-z]\w*) ", body, re.M
        )
        if malformed:
            bucket.append(
                f"{slug}: task numbers `pacto exec` cannot parse -> "
                f"{', '.join(sorted(set(malformed)))}"
            )

        # `pacto exec --step` rejects numbers ending in .0: on 2026-08-20 the 17
        # reconnaissance tasks were added as 1.0 and none was executable. Found
        # when trying to close the first one for real.
        zeros = re.findall(r"^\s*-\s*\[[ x]\] (\d+\.0) ", body, re.M)
        if zeros:
            bucket.append(
                f"{slug}: .0 tasks that `pacto exec --step` cannot target -> "
                f"{', '.join(sorted(set(zeros)))}"
            )

        # Cross references: "conforme a 2.3" must point at a task that exists.
        # On 2026-08-20 a bulk renumbering left 55 references pointing one
        # position ahead, silently: the numbers still existed, they just meant
        # something else.
        existing = {f"{a}.{b}" for a, b in TASK.findall(body)}
        for match in CROSS_REFERENCE.finditer(body):
            if match.group(1) not in existing:
                bucket.append(
                    f"{slug}: reference to task {match.group(1)}, which does not exist"
                )

        # An open task cannot carry the word that triggers the blocked state.
        for line in OPEN_TASK.findall(body):
            if BLOCK_TRIGGER.search(line):
                number = line.split("]", 1)[1].strip().split(" ", 1)[0]
                bucket.append(
                    f"{slug}: task {number} contains 'bloqueado/bloqueador' and "
                    f"`pacto status` counts it as blocked -> rewrite it "
                    f"(impedimento, detenido, obligatorio...)"
                )

        # The blockers section: either empty, or one `- ` line per real blocker.
        # A table makes pacto read the header and the separator as two blockers,
        # and a "none recorded" line declares a plan blocked that says the
        # opposite.
        blockers = re.search(r"^## Bloqueadores\s*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
        if blockers:
            lines = [l.strip() for l in blockers.group(1).strip().splitlines() if l.strip()]
            stray = [l for l in lines if not l.startswith("- ")]
            if stray:
                bucket.append(
                    f"{slug}: the Bloqueadores section must be empty or carry one "
                    f"`- ` line per blocker; `pacto status` reads every line as "
                    f"one -> unexpected {stray[0][:50]!r}"
                )
            # A blocker either names the plan it depends on -and then
            # `pacto status` can say whether it is still alive- or claims
            # something about the code, and then it needs its anchor. Without
            # one of the two it is a guess that looks like a fact, and nobody
            # revisits it.
            for line in lines:
                if not line.startswith("- "):
                    continue
                names_plan = re.search(r"`([a-z0-9]+-[a-z0-9-]+)`", line)
                has_anchor = re.search(r"[\w/.-]+\.(" + EXTENSIONS + r")(:\d+)?", line)
                if not names_plan and not has_anchor:
                    bucket.append(
                        f"{slug}: blocker with no plan or anchor behind it -> {line[:60]!r}. "
                        f"Name the plan it depends on, or give the `file:line` that proves it"
                    )

            declared_empty = [l for l in lines if EMPTY_BLOCKER.match(l)]
            if declared_empty:
                bucket.append(
                    f"{slug}: a 'none recorded' line under Bloqueadores declares the "
                    f"plan blocked; to say there are none, leave the section empty"
                )

        # A closed plan with no real measurement loses the only information that
        # makes the next estimate better. And relying on remembering has failed
        # before: a hook that should have fired on its own and did not, and a
        # documentation checklist nobody reviewed.
        if spec.parent.parent.name == "done" and "Real:" not in body:
            bucket.append(
                f"{slug}: plan closed with no real measurement -> run "
                f"`base-harness time {slug}` and add the result next to the estimate"
            )

        numbers = TASK.findall(body)
        if not numbers:
            bucket.append(f"{slug}: no N.M tasks, `pacto exec` has nothing to target")
        # Repeated numbers break `pacto exec --step`.
        seen = [f"{a}.{b}" for a, b in numbers]
        duplicates = sorted({x for x in seen if seen.count(x) > 1})
        if duplicates:
            bucket.append(f"{slug}: duplicated tasks -> {', '.join(duplicates)}")

    if pending:
        missing = len({p.split(":")[0] for p in pending})
        print(f"[info] {missing} plan(s) outside the roadmap without the obligations.")
        print("       They get fixed one at a time, when brought to contract, not in bulk.\n")

    if not problems:
        print(f"roadmap plans: no problems ({checked} plans reviewed)")
        return 0

    print(f"Roadmap plans with problems ({checked} reviewed):\n")
    for problem in problems:
        print(f"  {problem}")
    print("\nThe obligations live in the `create-plan` skill. This check exists")
    print("because an instruction can be skipped and nobody finds out.")
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
