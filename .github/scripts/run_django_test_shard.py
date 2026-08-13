#!/usr/bin/env python
"""Discover the Django suite and run one deterministic CI shard."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def select_test_labels(
    labels: Sequence[str],
    *,
    shard_index: int,
    total_shards: int,
) -> list[str]:
    if total_shards < 1:
        raise ValueError("total_shards must be at least 1")
    if not 1 <= shard_index <= total_shards:
        raise ValueError("shard_index must be between 1 and total_shards")

    ordered_labels = sorted(labels)
    return ordered_labels[shard_index - 1 :: total_shards]


def discover_test_labels() -> list[str]:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.chdir(REPOSITORY_ROOT)
    sys.path.insert(0, str(REPOSITORY_ROOT))

    import django

    django.setup()

    from django.conf import settings
    from django.test.utils import get_runner, iter_test_cases

    runner = get_runner(settings)(verbosity=0, interactive=False)
    suite = runner.build_suite([])
    labels = [test.id() for test in iter_test_cases(suite)]
    if len(labels) != len(set(labels)):
        raise RuntimeError("Django test discovery returned duplicate test IDs")
    return labels


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard-index", required=True, type=int)
    parser.add_argument("--total-shards", required=True, type=int)
    parser.add_argument("--verbosity", default=1, type=int)
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Print selected test IDs without creating a test database.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    labels = discover_test_labels()
    selected_labels = select_test_labels(
        labels,
        shard_index=args.shard_index,
        total_shards=args.total_shards,
    )
    if not selected_labels:
        raise RuntimeError(
            f"Django shard {args.shard_index}/{args.total_shards} is empty"
        )

    print(
        f"Django shard {args.shard_index}/{args.total_shards}: "
        f"{len(selected_labels)} of {len(labels)} tests.",
        file=sys.stderr,
        flush=True,
    )
    if args.list_only:
        print("\n".join(selected_labels))
        return 0

    command = [
        sys.executable,
        str(REPOSITORY_ROOT / "manage.py"),
        "test",
        *selected_labels,
        "--verbosity",
        str(args.verbosity),
        "--noinput",
    ]
    return subprocess.run(command, cwd=REPOSITORY_ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
