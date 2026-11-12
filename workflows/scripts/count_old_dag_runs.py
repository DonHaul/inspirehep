"""Count completed DAG runs older than N days.

Run inside an Airflow container (scheduler/worker/api-server):

    python scripts/count_old_dag_runs.py
    python scripts/count_old_dag_runs.py --days 90 --states success
    python scripts/count_old_dag_runs.py --dag-id desy_harvest
"""

import argparse
from datetime import timedelta

from airflow.models import DagRun
from airflow.utils import timezone
from airflow.utils.session import create_session
from sqlalchemy import func, select


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument(
        "--states",
        nargs="+",
        default=["success", "failed"],
        help="DAG run states considered completed",
    )
    parser.add_argument("--dag-id", help="Only count runs of this DAG")
    args = parser.parse_args()

    cutoff = timezone.utcnow() - timedelta(days=args.days)

    query = (
        select(DagRun.dag_id, DagRun.state, func.count())
        .where(DagRun.state.in_(args.states), DagRun.end_date < cutoff)
        .group_by(DagRun.dag_id, DagRun.state)
        .order_by(DagRun.dag_id, DagRun.state)
    )
    if args.dag_id:
        query = query.where(DagRun.dag_id == args.dag_id)

    with create_session() as session:
        rows = session.execute(query).all()

    total = 0
    for dag_id, state, count in rows:
        print(f"{dag_id:<50} {state:<10} {count}")
        total += count

    print(f"\nTotal completed DAG runs ended before {cutoff.isoformat()}: {total}")


if __name__ == "__main__":
    main()
