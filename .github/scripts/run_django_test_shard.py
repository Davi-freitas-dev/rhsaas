#!/usr/bin/env python
"""Discover the Django suite and run one deterministic CI shard."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Sequence, TypeVar


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
T = TypeVar("T")


def select_shard(
    items: Sequence[T],
    *,
    shard_index: int,
    total_shards: int,
) -> list[T]:
    if total_shards < 1:
        raise ValueError("total_shards must be at least 1")
    if not 1 <= shard_index <= total_shards:
        raise ValueError("shard_index must be between 1 and total_shards")

    start = len(items) * (shard_index - 1) // total_shards
    end = len(items) * shard_index // total_shards
    return list(items[start:end])


def prepare_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.chdir(REPOSITORY_ROOT)
    sys.path.insert(0, str(REPOSITORY_ROOT))

    import django

    django.setup()

    from django.conf import settings
    from django.test.utils import get_runner

    return get_runner(settings)


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
    runner_class = prepare_django()

    if args.list_only:
        from django.test.utils import iter_test_cases

        runner = runner_class(verbosity=0, interactive=False)
        tests = list(iter_test_cases(runner.build_suite([])))
        selected_tests = select_shard(
            tests,
            shard_index=args.shard_index,
            total_shards=args.total_shards,
        )
        print("\n".join(test.id() for test in selected_tests))
        return 0

    from django.test.utils import iter_test_cases

    class ShardedRunner(runner_class):
        def build_suite(self, test_labels=None, *runner_args, **runner_kwargs):
            full_suite = super().build_suite([], *runner_args, **runner_kwargs)
            tests = list(iter_test_cases(full_suite))
            if len(tests) != len({test.id() for test in tests}):
                raise RuntimeError("Django test discovery returned duplicate test IDs")
            selected_tests = select_shard(
                tests,
                shard_index=args.shard_index,
                total_shards=args.total_shards,
            )
            if not selected_tests:
                raise RuntimeError(
                    f"Django shard {args.shard_index}/{args.total_shards} is empty"
                )
            print(
                f"Django shard {args.shard_index}/{args.total_shards}: "
                f"{len(selected_tests)} of {len(tests)} tests.",
                file=sys.stderr,
                flush=True,
            )
            return self.test_suite(selected_tests)

    runner = ShardedRunner(verbosity=args.verbosity, interactive=False)
    return int(bool(runner.run_tests([])))


if __name__ == "__main__":
    raise SystemExit(main())
