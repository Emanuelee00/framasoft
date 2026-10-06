#!/usr/bin/env python3
"""Classify a Gatling run's results into: requests that actually reached and
were handled by the server, vs requests blocked before ever reaching it
(client/network-side limits), vs requests that reached it but timed out
waiting for a response, vs requests the server answered with an error.

Gatling's own summary only gives raw exception messages grouped by count; this
script buckets those messages by what they actually mean, so you don't have
to re-derive it by hand every time.

Reads the most recently generated report under target/gatling/<sim>-<timestamp>/.
"""
import re
import sys
from pathlib import Path

GATLING_DIR = Path(__file__).parent / "target" / "gatling"

# (category label, keywords that identify it in the exception message)
CATEGORIES = [
    (
        "Never reached the server (client/network limit)",
        ["Connection refused", "Cannot assign requested address",
         "Premature close", "No route to host"],
    ),
    (
        "Reached the server but it didn't answer in time (likely overloaded)",
        ["ConnectTimeoutException", "Request timeout", "timed out"],
    ),
    (
        "Server answered, but with an error status",
        ["status.find.in"],
    ),
]


def find_latest_run() -> Path:
    runs = [p for p in GATLING_DIR.glob("*") if p.is_dir()]
    if not runs:
        print(f"No Gatling run found under {GATLING_DIR}")
        sys.exit(1)
    return max(runs, key=lambda p: p.stat().st_mtime)


def parse_global_counts(stats_js: Path) -> tuple[int, int, int]:
    text = stats_js.read_text()
    m = re.search(
        r'"numberOfRequests":\s*\{\s*"total":\s*"(\d+)",\s*"ok":\s*"(\d+)",\s*"ko":\s*"(\d+)"',
        text,
    )
    if not m:
        print("Could not find request counts in stats.js")
        sys.exit(1)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def parse_errors(index_html: Path) -> list[tuple[str, int]]:
    text = index_html.read_text()
    # [^<]* (not .*?) keeps each match confined to a single <td>, so it can't
    # drift across row/table boundaries (e.g. into the separate Assertions
    # table, which reuses similar class names but isn't the error breakdown).
    rows = re.findall(
        r'<td class="[^"]*error-col-1[^"]*">([^<]*)<span[^<]*</span></td>\s*'
        r'<td class="[^"]*error-col-2[^"]*">(\d+)</td>',
        text,
    )
    return [(msg.strip(), int(count)) for msg, count in rows]


def classify(message: str) -> str:
    for label, keywords in CATEGORIES:
        if any(k in message for k in keywords):
            return label
    return "Other / unclassified failure"


def main() -> None:
    run_dir = find_latest_run()
    total, ok, ko = parse_global_counts(run_dir / "js" / "stats.js")
    errors = parse_errors(run_dir / "index.html")

    buckets: dict[str, int] = {}
    for message, count in errors:
        buckets.setdefault(classify(message), 0)
        buckets[classify(message)] += count

    print()
    print(f"==> Result breakdown for {run_dir.name}")
    print(f"    Total requests sent:              {total:>8}")
    print(f"    Handled successfully by server:   {ok:>8}  ({ok / total * 100:.1f}%)")
    for label, _ in CATEGORIES + [("Other / unclassified failure", [])]:
        count = buckets.get(label, 0)
        if count:
            print(f"    {label}: {count:>8}  ({count / total * 100:.1f}%)")
    unclassified_sum = sum(buckets.values())
    if unclassified_sum != ko:
        print(f"    (warning: classified {unclassified_sum} failures, but Gatling reports {ko} KO total)")
    print(f"    Full report: file://{(run_dir / 'index.html').resolve()}")
    print()


if __name__ == "__main__":
    main()
