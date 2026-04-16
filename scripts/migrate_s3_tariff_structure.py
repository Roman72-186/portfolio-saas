"""One-time migration: move all existing S3 files to the new tariff-based structure.

New structure:
  Портфолио/{тариф}/{тариф}_{vk_id}/До/{тариф}_{vk_id}_{random8}.ext
  Портфолио/{тариф}/{тариф}_{vk_id}/После/{тариф}_{vk_id}_{random8}.ext
  Пробники/{тариф}/{тариф}_{vk_id}/{YYYY-MM}/{тариф}_{vk_id}_{random8}.ext

Usage:
    python scripts/migrate_s3_tariff_structure.py          # live run
    python scripts/migrate_s3_tariff_structure.py --dry-run  # preview only, no changes
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import SessionLocal
from app.models.user import User
from app.models.work import Work, WORK_TYPE_BEFORE, WORK_TYPE_AFTER, WORK_TYPE_MOCK_EXAM
from app.services import s3 as s3_service
from datetime import datetime, timezone

BATCH_SIZE = 50


def build_new_path(work: Work, vk_id: int, tariff: str) -> str | None:
    src = work.s3_path or ""
    current_name = src.rsplit("/", 1)[-1] if src else (work.filename or "photo.jpg")
    new_name = s3_service._make_filename(tariff, vk_id, current_name)
    tf = s3_service.tariff_display(tariff)

    if work.work_type == WORK_TYPE_BEFORE:
        return f"Портфолио/{tf}/{tf}_{vk_id}/До/{new_name}"
    if work.work_type == WORK_TYPE_AFTER:
        return f"Портфолио/{tf}/{tf}_{vk_id}/После/{new_name}"
    if work.work_type == WORK_TYPE_MOCK_EXAM:
        ym = datetime.now(timezone.utc).strftime("%Y-%m")
        for part in src.split("/"):
            if len(part) == 7 and part[4:5] == "-":
                ym = part
                break
        return f"Пробники/{tf}/{tf}_{vk_id}/{ym}/{new_name}"
    return None


def main(dry_run: bool) -> None:
    if not s3_service.is_configured():
        print("S3 is not configured — nothing to migrate.")
        return

    db = SessionLocal()
    try:
        works = (
            db.query(Work)
            .filter(Work.s3_path.isnot(None))
            .all()
        )
        print(f"Found {len(works)} works with s3_path.")

        moved = 0
        skipped = 0
        failed = 0
        batch_dirty = []

        for work in works:
            user = db.query(User).filter(User.id == work.user_id).first()
            if not user:
                print(f"  SKIP  work_id={work.id}: user not found")
                skipped += 1
                continue

            tariff = work.tariff or user.tariff
            new_path = build_new_path(work, user.vk_id, tariff)
            if not new_path:
                print(f"  SKIP  work_id={work.id}: unknown work_type={work.work_type!r}")
                skipped += 1
                continue

            if new_path == work.s3_path:
                skipped += 1
                continue

            print(f"  {'DRY ' if dry_run else ''}MOVE  {work.s3_path}")
            print(f"       → {new_path}")

            if not dry_run:
                ok = s3_service.move_s3_object(work.s3_path, new_path)
                if ok:
                    work.s3_path = new_path
                    work.s3_url = s3_service.s3_public_url(new_path)
                    work.tariff = tariff
                    batch_dirty.append(work)
                    moved += 1
                else:
                    print(f"  FAIL  work_id={work.id}")
                    failed += 1

                if len(batch_dirty) >= BATCH_SIZE:
                    db.commit()
                    batch_dirty.clear()
            else:
                moved += 1

        if not dry_run and batch_dirty:
            db.commit()

        print(f"\nDone. moved={moved}, skipped={skipped}, failed={failed}")
        if dry_run:
            print("(dry-run: no changes were made)")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
