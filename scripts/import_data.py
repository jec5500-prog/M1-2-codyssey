"""Validate a CSV and insert missing deterministic records without deleting data."""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from models import DataPointCreate


def read_rows(path: Path) -> list[dict]:
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        rows = [DataPointCreate.model_validate(r).model_dump() for r in csv.DictReader(f)]
    if not rows:
        raise ValueError('CSV must not be empty')
    dates = [r['date'] for r in rows]
    if len(set(dates)) != len(dates):
        raise ValueError('CSV has duplicate dates')
    return sorted(rows, key=lambda r:r['date'])


def import_rows(rows: list[dict], db) -> dict:
    if db.project != 'm1-2-cody':
        raise ValueError('Refusing import: unexpected Firebase project')
    valid = [DataPointCreate.model_validate(row).model_dump() for row in rows]
    if len({r['date'] for r in valid}) != len(valid):
        raise ValueError('duplicate dates')
    created = skipped = 0
    from google.api_core.exceptions import AlreadyExists
    for row in valid:
        ref = db.collection('data').document('seoul-temperature-' + row['date'])
        if ref.get(timeout=10).exists:
            skipped += 1
            continue
        now = datetime.now(timezone.utc).isoformat()
        try:
            ref.create({**row,'created_at':now,'updated_at':now}, timeout=10)
            created += 1
        except AlreadyExists:
            skipped += 1
    return {'created':created,'skipped':skipped,'input_count':len(valid)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', nargs='?', default=str(Path(__file__).resolve().parents[1]/'datasets'/'seoul-temperature.csv'))
    parser.add_argument('--apply',action='store_true',help='Actually insert into the named project; default is validation only')
    args=parser.parse_args()
    rows=read_rows(Path(args.csv))
    if args.apply:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parents[1]/'backend'/'.env', override=False)
        from database import get_db
        print(import_rows(rows,get_db()))
    else:
        print({'validated':len(rows),'first_date':rows[0]['date'],'last_date':rows[-1]['date'],'writes':0})
