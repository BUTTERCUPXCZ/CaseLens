"""Operator commands.  Inside the api container:

    python -m caselens.manage reparse     # re-read stored pages with the current parser
    python -m caselens.manage refetch     # download again cases whose text was damaged on download
    python -m caselens.manage resume-digests   # start the case digests that waited for the monthly limit
    python -m caselens.manage download-all [--from-year 1987] [--to-year 2026] [--limit N]   # save every listed decision (1 page/second, resumable)
    python -m caselens.manage catalog build|refresh|status   # read Lawphil's monthly lists (about 9 min once)
"""
import argparse
import logging
import sys

from caselens.composition import Services
from caselens.infrastructure.db.session import SessionLocal


def reparse() -> int:
    with SessionLocal() as session:
        report = Services(session).reparse_stored_cases().execute()
    print(f"reparsed {report.updated} case(s), {len(report.failed)} failed")
    for case_id, url, reason in report.failed:
        print(f"  FAILED case {case_id} {url}: {reason}")
    return 1 if report.failed else 0


def refetch() -> int:
    with SessionLocal() as session:
        report = Services(session).refetch_damaged_cases().execute()
    print(f"repaired {report.repaired} case(s), {len(report.failed)} failed")
    for case_id, url, reason in report.failed:
        print(f"  FAILED case {case_id} {url}: {reason}")
    return 1 if report.failed else 0


def resume_digests() -> int:
    from caselens.composition import _job_queue
    from caselens.infrastructure.queue.recovery import requeue_over_limit_digests

    print(f"started {requeue_over_limit_digests(_job_queue())} case digest(s) that were waiting for the monthly limit")
    return 0


def download_all(first_year: int, last_year: int, limit: int | None) -> int:
    import time

    started = time.monotonic()

    def show(report, _cursor) -> None:
        done = report.saved + len(report.failed)
        if done % 25 == 0:
            rate = done / max(time.monotonic() - started, 1)
            print(f"saved {report.saved}, failed {len(report.failed)} ({rate:.2f} pages/s)", flush=True)

    with SessionLocal() as session:
        report = Services(session).download_catalog_cases().execute(first_year, last_year, limit, show)
    print(f"saved {report.saved} new case(s), {len(report.failed)} failed")
    for url, reason in report.failed[:50]:
        print(f"  FAILED {url}: {reason}")
    if report.stopped:
        print(f"STOPPED: {report.stopped}")
    return 1 if report.stopped else 0


def catalog(action: str) -> int:
    from caselens.infrastructure.config import get_settings

    with SessionLocal() as session:
        services = Services(session)
        if action == "status":
            status = services.catalog_status().execute()
            print(f"{status.state}: {status.entries} decisions, {status.months_read} of {status.months_known} monthly lists read ({status.percent}%)")
            return 0
        if action == "build":
            report = services.build_catalog().build(get_settings().catalog_first_year)
        else:
            report = services.build_catalog().refresh()
    print(
        f"read {report.read}, skipped {report.skipped}, {report.entries} decisions, "
        f"{len(report.missing)} missing, {len(report.failed)} failed, {len(report.broken)} broken"
    )
    for url, reason in report.failed:
        print(f"  FAILED {url}: {reason}")
    for url in report.broken:
        print(f"  BROKEN (layout changed?) {url}")
    return 1 if report.failed or report.broken else 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="caselens.manage")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("reparse", help="re-read stored pages with the current parser (no network)")
    commands.add_parser("refetch", help="download again cases whose stored text was damaged (network)")
    dl = commands.add_parser("download-all", help="save every decision of Lawphil's list that is not saved yet (network, resumable)")
    dl.add_argument("--from-year", type=int, default=1987)
    dl.add_argument("--to-year", type=int, default=2100)
    dl.add_argument("--limit", type=int, default=None, help="stop after this many pages (to try it out)")
    commands.add_parser("resume-digests", help="start the case digests that waited for the monthly limit")
    cat = commands.add_parser("catalog", help="the searchable copy of Lawphil's lists (network)")
    cat.add_argument("action", choices=["build", "refresh", "status"])
    args = parser.parse_args(argv)
    if args.command == "download-all":
        return download_all(args.from_year, args.to_year, args.limit)
    if args.command == "catalog":
        return catalog(args.action)
    return {"reparse": reparse, "refetch": refetch, "resume-digests": resume_digests}[args.command]()


if __name__ == "__main__":
    sys.exit(main())
