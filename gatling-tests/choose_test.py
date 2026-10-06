#!/usr/bin/env python3
"""Interactive menu to pick and run a Gatling simulation.

Requires: pip3 install --user questionary
"""
import subprocess
import sys
from pathlib import Path

import questionary

SRC_DIR = Path(__file__).parent / "src" / "test" / "scala"


def list_simulations() -> list[str]:
    sims = []
    for path in sorted(SRC_DIR.rglob("*.scala")):
        relative = path.relative_to(SRC_DIR).with_suffix("")
        sims.append(str(relative).replace("/", "."))
    return sims


def main() -> None:
    sims = list_simulations()
    if not sims:
        print(f"No simulation found in {SRC_DIR}")
        sys.exit(1)

    choice = questionary.select(
        "Which simulation do you want to run?",
        choices=sims,
    ).ask()

    if choice is None:
        print("Cancelled.")
        sys.exit(0)

    cmd = ["mvn", "gatling:test", f"-Dgatling.simulationClass={choice}"]

    if choice == "example.Dos":
        mode = questionary.select(
            "Use the default load profile or set custom values?",
            choices=["Default", "Custom"],
        ).ask()

        if mode is None:
            print("Cancelled.")
            sys.exit(0)

        if mode == "Custom":
            users = questionary.text(
                "How many users?",
                validate=lambda text: text.isdigit() and int(text) > 0,
            ).ask()
            if users is None:
                print("Cancelled.")
                sys.exit(0)

            seconds = questionary.text(
                "Over how many seconds?",
                validate=lambda text: text.isdigit() and int(text) > 0,
            ).ask()
            if seconds is None:
                print("Cancelled.")
                sys.exit(0)

            cmd += [f"-Dusers={users}", f"-Dseconds={seconds}"]

    subprocess.run(
        cmd,
        cwd=Path(__file__).parent,
        check=False,
    )


if __name__ == "__main__":
    main()
