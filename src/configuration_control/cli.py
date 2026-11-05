"""Command line interface; run --help for available operations."""

import argparse
import json
import sqlite3

from .core import scan, create_baseline, compare


def main():
    parser = argparse.ArgumentParser(description="configuration-control")
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("scan")
    sub.add_argument("directory")
    sub.add_argument("--exclude", action="append")
    sub = commands.add_parser("baseline")
    sub.add_argument("directory")
    sub.add_argument("snapshot")
    sub.add_argument("id")
    sub.add_argument("approver")
    sub.add_argument("commit")
    sub.add_argument("--previous")
    sub.add_argument("--exclude", action="append")
    sub = commands.add_parser("compare")
    sub.add_argument("directory")
    sub.add_argument("snapshot")
    sub.add_argument("--history")
    sub.add_argument("--report")
    args = parser.parse_args()
    try:
        if args.command == "scan":
            result = scan(args.directory, args.exclude or [])
        if args.command == "baseline":
            result = create_baseline(
                args.directory,
                args.snapshot,
                args.id,
                args.approver,
                args.commit,
                args.previous,
                args.exclude or [],
            )
        if args.command == "compare":
            result = compare(args.directory, args.snapshot, args.history, args.report)
        print(
            json.dumps(result, ensure_ascii=False, indent=2)
            if not isinstance(result, str)
            else result
        )
        if isinstance(result, dict) and result.get("passed") is False:
            return 1
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(2, f"Ошибка: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
