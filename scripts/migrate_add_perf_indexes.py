"""Add composite performance indexes to works and users tables.

Run inside Docker container:
    docker exec portfolio-saas-app-1 python scripts/migrate_add_perf_indexes.py
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

import psycopg2

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("ERROR: DATABASE_URL not set", file=sys.stderr)
    sys.exit(1)

INDEXES = [
    # Works — ускоряет batch load куратора и recent uploads в superadmin
    ("ix_works_user_status_created", "works", "(user_id, status, created_at DESC)"),
    # Works — ускоряет агрегации по типам на dashboard superadmin
    ("ix_works_type_status",         "works", "(work_type, status)"),
    # Works — ускоряет запрос последних 10 загрузок
    ("ix_works_status_created",      "works", "(status, created_at DESC)"),
    # Users — ускоряет выборку студентов куратора
    ("ix_users_curator_active",      "users", "(curator_id, is_active)"),
    # Users — ускоряет role breakdown в superadmin
    ("ix_users_active_role",         "users", "(is_active, role_id)"),
]

conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

for name, table, cols in INDEXES:
    cur.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname = %s", (name,)
    )
    if cur.fetchone():
        print(f"  skip  {name} (already exists)")
    else:
        print(f"  create {name} ...", end="", flush=True)
        cur.execute(f"CREATE INDEX CONCURRENTLY {name} ON {table} {cols}")
        print(" done")

cur.close()
conn.close()
print("\nAll indexes applied.")
