"""Delete completed HEP DAG runs older than N days.

Dry run by default; pass --yes to actually delete.
Run inside an Airflow container (scheduler/worker/api-server):

    python scripts/delete_old_hep_dag_runs.py
    python scripts/delete_old_hep_dag_runs.py --yes
    python scripts/delete_old_hep_dag_runs.py --days 90 --states success --yes
"""

import argparse
from datetime import timedelta

from airflow.models import DagRun
from airflow.utils import timezone
from airflow.utils.session import create_session
from sqlalchemy import delete, func, select

HEP_DAG_IDS = ["hep_create_dag", "hep_manual_merge_dag"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument(
        "--states",
        nargs="+",
        default=["success", "failed"],
        help="DAG run states considered completed",
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--yes", action="store_true", help="Actually delete")
    args = parser.parse_args()

    cutoff = timezone.utcnow() - timedelta(days=args.days)
    conditions = (
        DagRun.dag_id.in_(HEP_DAG_IDS),
        DagRun.state.in_(args.states),
        DagRun.end_date < cutoff,
    )

    with create_session() as session:
        rows = session.execute(
            select(DagRun.dag_id, DagRun.state, func.count())
            .where(*conditions)
            .group_by(DagRun.dag_id, DagRun.state)
            .order_by(DagRun.dag_id, DagRun.state)
        ).all()

    total = 0
    for dag_id, state, count in rows:
        print(f"{dag_id:<30} {state:<10} {count}")
        total += count
    print(f"\nMatching DAG runs ended before {cutoff.isoformat()}: {total}")

    if not args.yes:
        print("Dry run, nothing deleted. Re-run with --yes to delete.")
        return

    deleted = 0
    while True:
        # Task instances, XComs, etc. are removed by the DB-level ON DELETE CASCADE
        with create_session() as session:
            ids = session.scalars(
                select(DagRun.id).where(*conditions).limit(args.batch_size)
            ).all()
            if not ids:
                break
            session.execute(
                delete(DagRun)
                .where(DagRun.id.in_(ids))
                .execution_options(synchronize_session=False)
            )
        deleted += len(ids)
        print(f"Deleted {deleted}/{total}")

    print(f"Done. Deleted {deleted} DAG runs.")


if __name__ == "__main__":
    main()
