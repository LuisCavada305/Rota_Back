#!/usr/bin/env python
"""Benchmark database query performance for repository methods."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from statistics import mean
from time import perf_counter
from typing import Any, Callable, Iterable, Optional

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.db import session_scope
from app.models.lk_enrollment_status import LkEnrollmentStatus as LkEnrollmentStatusORM
from app.models.lk_item_type import LkItemType as LkItemTypeORM
from app.models.lk_progress_status import LkProgressStatus as LkProgressStatusORM
from app.models.lookups import LkRole, LkSex, LkColor
from app.models.trail_items import TrailItems as TrailItemsORM
from app.models.trail_sections import TrailSections as TrailSectionsORM
from app.models.trails import Trails as TrailsORM
from app.models.user_item_progress import UserItemProgress as UserItemProgressORM
from app.models.user_trails import UserTrails as UserTrailsORM
from app.models.users import Sex, SkinColor
from app.models.roles import RolesEnum
from app.repositories.TrailsRepository import TrailsRepository
from app.repositories.UserProgressRepository import UserProgressRepository
from app.repositories.UserTrailsRepository import UserTrailsRepository
from app.repositories.UsersRepository import UsersRepository
from app.services.security import hash_password


@dataclass
class BenchmarkContext:
    trail_id: Optional[int]
    section_id: Optional[int]
    item_id: Optional[int]
    form_item_id: Optional[int]
    user_id: Optional[int]
    email: str
    username: str
    password: str


@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    total_time: float
    mean_ms: float
    ops_per_second: float
    ops_per_minute: float
    rows_per_second: float
    rows_processed: float


@dataclass
class BenchmarkCase:
    name: str
    func: Callable[[Session, BenchmarkContext], Any]
    requires: tuple[str, ...] = ()
    writes: bool = False


LOOKUP_VALUES = {
    LkSex: ("MC", "MT", "WC", "WT", "OT", "NS"),
    LkColor: ("BR", "PR", "PA", "AM", "IN", "OU", "NS"),
    LkRole: ("Admin", "User", "Manager"),
    LkItemTypeORM: ("DOC", "VIDEO", "FORM"),
    LkEnrollmentStatusORM: ("ENROLLED", "IN_PROGRESS", "COMPLETED"),
    LkProgressStatusORM: ("NOT_STARTED", "IN_PROGRESS", "COMPLETED"),
}


def ensure_lookup_values(session: Session) -> None:
    for model, codes in LOOKUP_VALUES.items():
        existing = set(session.execute(select(model.code)).scalars())
        missing = [code for code in codes if code not in existing]
        if not missing:
            continue
        session.execute(insert(model), [{"code": code} for code in missing])
    session.commit()


def ensure_benchmark_user(session: Session, email: str, password: str) -> User:
    repo = UsersRepository(session)
    user = repo.GetUserByEmail(email)
    if user:
        return user
    username = email.split("@")[0]
    user = repo.CreateUser(
        email=email,
        password_hash=hash_password(password),
        name_for_certificate="Performance Bench",
        username=username,
        sex=Sex.ManCis,
        color=SkinColor.White,
        role=RolesEnum.User,
        birthday="1990-01-01",
    )
    return user


def gather_sample_data(email: str, password: str) -> BenchmarkContext:
    with session_scope() as session:
        ensure_lookup_values(session)
        user = ensure_benchmark_user(session, email, password)

        trail_id = session.scalars(select(TrailsORM.id).limit(1)).first()
        section_id = None
        item_id = None
        form_item_id = None

        if trail_id is not None:
            section_id = session.scalars(
                select(TrailSectionsORM.id)
                .where(TrailSectionsORM.trail_id == trail_id)
                .order_by(TrailSectionsORM.order_index, TrailSectionsORM.id)
                .limit(1)
            ).first()
            item_id = session.scalars(
                select(TrailItemsORM.id)
                .where(TrailItemsORM.trail_id == trail_id)
                .order_by(TrailItemsORM.order_index, TrailItemsORM.id)
                .limit(1)
            ).first()
            form_item_id = session.scalars(
                select(TrailItemsORM.id)
                .join(LkItemTypeORM, TrailItemsORM.type)
                .where(TrailItemsORM.trail_id == trail_id, LkItemTypeORM.code == "FORM")
                .order_by(TrailItemsORM.order_index, TrailItemsORM.id)
                .limit(1)
            ).first()

            UserTrailsRepository(session).ensure_enrollment(user.user_id, trail_id)

        return BenchmarkContext(
            trail_id=trail_id,
            section_id=section_id,
            item_id=item_id,
            form_item_id=form_item_id,
            user_id=user.user_id,
            email=email,
            username=user.username,
            password=password,
        )


def infer_size(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (list, tuple, set)):
        if (
            isinstance(value, tuple)
            and len(value) == 2
            and isinstance(value[1], (int, float))
        ):
            return infer_size(value[0])
        return float(len(value))
    if isinstance(value, dict):
        return float(len(value))
    if isinstance(value, UserItemProgressORM):
        return 1.0
    if isinstance(value, UserTrailsORM):
        return 1.0
    return 1.0


def run_case(
    case: BenchmarkCase, iterations: int, warmup: int, ctx: BenchmarkContext
) -> BenchmarkResult:
    durations: list[float] = []
    rows_processed = 0.0
    total_iterations = iterations + warmup

    for index in range(total_iterations):
        with session_scope() as session:
            start = perf_counter()
            result = case.func(session, ctx)
            elapsed = perf_counter() - start
        if index < warmup:
            continue
        durations.append(elapsed)
        rows_processed += infer_size(result)

    executed = len(durations)
    total_time = sum(durations)
    mean_ms = mean(durations) * 1000 if durations else 0.0
    ops_per_second = executed / total_time if total_time > 0 else 0.0
    ops_per_minute = ops_per_second * 60.0
    rows_per_second = rows_processed / total_time if total_time > 0 else 0.0

    return BenchmarkResult(
        name=case.name,
        iterations=executed,
        total_time=total_time,
        mean_ms=mean_ms,
        ops_per_second=ops_per_second,
        ops_per_minute=ops_per_minute,
        rows_per_second=rows_per_second,
        rows_processed=rows_processed,
    )


def requirements_met(ctx: BenchmarkContext, requirements: Iterable[str]) -> bool:
    for key in requirements:
        if getattr(ctx, key, None) is None:
            return False
    return True


def create_cases() -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = [
        BenchmarkCase(
            name="TrailsRepository.list_showcase",
            func=lambda session, ctx: TrailsRepository(session).list_showcase(limit=6),
        ),
        BenchmarkCase(
            name="TrailsRepository.list_all",
            func=lambda session, ctx: TrailsRepository(session).list_all(
                offset=0, limit=10
            ),
        ),
        BenchmarkCase(
            name="TrailsRepository.get_trail",
            func=lambda session, ctx: TrailsRepository(session).get_trail(ctx.trail_id),
            requires=("trail_id",),
        ),
        BenchmarkCase(
            name="TrailsRepository.list_sections",
            func=lambda session, ctx: TrailsRepository(session).list_sections(
                ctx.trail_id, offset=0, limit=10
            ),
            requires=("trail_id",),
        ),
        BenchmarkCase(
            name="TrailsRepository.list_section_items",
            func=lambda session, ctx: TrailsRepository(session).list_section_items(
                ctx.trail_id,
                ctx.section_id,
                offset=0,
                limit=10,
            ),
            requires=("trail_id", "section_id"),
        ),
        BenchmarkCase(
            name="TrailsRepository.list_sections_with_items",
            func=lambda session, ctx: TrailsRepository(
                session
            ).list_sections_with_items(ctx.trail_id),
            requires=("trail_id",),
        ),
        BenchmarkCase(
            name="TrailsRepository.list_included_items",
            func=lambda session, ctx: TrailsRepository(session).list_included_items(
                ctx.trail_id
            ),
            requires=("trail_id",),
        ),
        BenchmarkCase(
            name="TrailsRepository.list_requirements",
            func=lambda session, ctx: TrailsRepository(session).list_requirements(
                ctx.trail_id
            ),
            requires=("trail_id",),
        ),
        BenchmarkCase(
            name="TrailsRepository.list_audience",
            func=lambda session, ctx: TrailsRepository(session).list_audience(
                ctx.trail_id
            ),
            requires=("trail_id",),
        ),
        BenchmarkCase(
            name="UserTrailsRepository.count_items_in_trail",
            func=lambda session, ctx: UserTrailsRepository(
                session
            ).count_items_in_trail(ctx.trail_id),
            requires=("trail_id",),
        ),
        BenchmarkCase(
            name="UserTrailsRepository.get_progress_for_user",
            func=lambda session, ctx: UserTrailsRepository(
                session
            ).get_progress_for_user(ctx.user_id, ctx.trail_id),
            requires=("user_id", "trail_id"),
        ),
        BenchmarkCase(
            name="UserTrailsRepository.get_items_progress",
            func=lambda session, ctx: UserTrailsRepository(session).get_items_progress(
                ctx.user_id, ctx.trail_id
            ),
            requires=("user_id", "trail_id"),
        ),
        BenchmarkCase(
            name="UserTrailsRepository.get_sections_progress",
            func=lambda session, ctx: UserTrailsRepository(
                session
            ).get_sections_progress(ctx.user_id, ctx.trail_id),
            requires=("user_id", "trail_id"),
        ),
        BenchmarkCase(
            name="UserTrailsRepository.get_progress_map_for_user",
            func=lambda session, ctx: UserTrailsRepository(
                session
            ).get_progress_map_for_user(ctx.user_id, [ctx.trail_id], sync=False),
            requires=("user_id", "trail_id"),
        ),
        BenchmarkCase(
            name="UsersRepository.GetUserByEmail",
            func=lambda session, ctx: UsersRepository(session).GetUserByEmail(
                ctx.email
            ),
            requires=("email",),
        ),
        BenchmarkCase(
            name="UsersRepository.GetUserByUsername",
            func=lambda session, ctx: UsersRepository(session).GetUserByUsername(
                ctx.username
            ),
            requires=("username",),
        ),
        BenchmarkCase(
            name="UsersRepository.GetUserById",
            func=lambda session, ctx: UsersRepository(session).GetUserById(ctx.user_id),
            requires=("user_id",),
        ),
        BenchmarkCase(
            name="UsersRepository.ExistsEmail",
            func=lambda session, ctx: UsersRepository(session).ExistsEmail(ctx.email),
            requires=("email",),
        ),
        BenchmarkCase(
            name="UsersRepository.ExistsUsername",
            func=lambda session, ctx: UsersRepository(session).ExistsUsername(
                ctx.username
            ),
            requires=("username",),
        ),
        BenchmarkCase(
            name="UserTrailsRepository.ensure_enrollment",
            func=lambda session, ctx: UserTrailsRepository(session).ensure_enrollment(
                ctx.user_id, ctx.trail_id
            )[0],
            requires=("user_id", "trail_id"),
            writes=True,
        ),
        BenchmarkCase(
            name="UserProgressRepository.upsert_item_progress",
            func=lambda session, ctx: UserProgressRepository(
                session
            ).upsert_item_progress(
                ctx.user_id,
                ctx.item_id,
                status_code="COMPLETED",
                progress_value=100,
            ),
            requires=("user_id", "item_id"),
            writes=True,
        ),
    ]

    return cases


def format_number(value: float) -> str:
    if math.isnan(value) or math.isinf(value):
        return "n/a"
    return f"{value:,.2f}"


def print_results(results: list[BenchmarkResult]) -> None:
    if not results:
        print("No benchmarks executed.")
        return

    header = (
        f"{'Query':70} {'Ops/s':>12} {'Ops/m':>12} {'Rows/s':>12} {'Mean (ms)':>12}"
    )
    print(header)
    print("-" * len(header))
    for result in results:
        print(
            f"{result.name:70} {format_number(result.ops_per_second):>12}"
            f" {format_number(result.ops_per_minute):>12} {format_number(result.rows_per_second):>12}"
            f" {format_number(result.mean_ms):>12}"
        )

    total_iterations = sum(r.iterations for r in results)
    total_time = sum(r.total_time for r in results)
    total_rows = sum(r.rows_processed for r in results)
    overall_ops_sec = total_iterations / total_time if total_time > 0 else 0.0
    overall_ops_min = overall_ops_sec * 60.0
    overall_rows_sec = total_rows / total_time if total_time > 0 else 0.0

    print("\nOverall:")
    print(
        f"  Executed iterations: {total_iterations}\n"
        f"  Total runtime: {total_time:.2f}s\n"
        f"  Aggregate OPS: {format_number(overall_ops_sec)} req/s ({format_number(overall_ops_min)} req/min)\n"
        f"  Aggregate throughput: {format_number(overall_rows_sec)} rows/s"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark repository query performance."
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=50,
        help="Number of measured iterations per query",
    )
    parser.add_argument(
        "--warmup", type=int, default=5, help="Warm-up iterations per query"
    )
    parser.add_argument(
        "--include-writes",
        action="store_true",
        help="Include write-heavy benchmarks (may mutate the database).",
    )
    parser.add_argument(
        "--json", dest="json_path", help="Write raw results to the given JSON file"
    )
    parser.add_argument(
        "--user-email",
        default=os.environ.get("PERF_BENCH_EMAIL", "perf-db@example.com"),
        help="Email used for the synthetic benchmark user.",
    )
    parser.add_argument(
        "--user-password",
        default=os.environ.get("PERF_BENCH_PASSWORD", "PerfTest@123"),
        help="Password for the synthetic benchmark user.",
    )
    args = parser.parse_args()

    ctx = gather_sample_data(args.user_email, args.user_password)
    cases = [case for case in create_cases() if args.include_writes or not case.writes]

    results: list[BenchmarkResult] = []
    for case in cases:
        if not requirements_met(ctx, case.requires):
            missing = [req for req in case.requires if getattr(ctx, req, None) is None]
            print(f"Skipping {case.name} (missing: {', '.join(missing)})")
            continue
        result = run_case(case, iterations=args.iterations, warmup=args.warmup, ctx=ctx)
        results.append(result)

    print_results(results)

    if args.json_path:
        payload = [result.__dict__ for result in results]
        with open(args.json_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"Raw results written to {args.json_path}")


if __name__ == "__main__":
    main()
