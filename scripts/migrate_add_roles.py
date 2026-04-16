"""
Migrate existing database to 5-role RBAC system.

Run BEFORE deploying new app code:
  python scripts/migrate_add_roles.py

Idempotent: safe to run multiple times.
"""
import os
import sys

from sqlalchemy import inspect, text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.db.database import engine, Base
# Import all models so create_all picks them up
from app.models.user import User  # noqa: F401
from app.models.session import Session  # noqa: F401
from app.models.login_token import LoginToken  # noqa: F401
from app.models.upload_log import UploadLog  # noqa: F401
from app.models.role import Role, Permission, RolePermission  # noqa: F401


ROLES = [
    (1, "ученик",     "Ученик"),
    (2, "куратор",    "Куратор"),
    (3, "модератор",  "Модератор"),
    (4, "админ",      "Админ"),
    (5, "суперадмин", "Суперадмин"),
]

PERMISSIONS = [
    ("upload_photos",        "Загрузка фото"),
    ("view_own_gallery",     "Просмотр своей галереи"),
    ("view_upload_history",  "История загрузок"),
    ("take_exam",            "Прохождение экзамена"),
    ("view_own_students",    "Список своих студентов"),
    ("view_student_photos",  "Просмотр фото студентов"),
    ("comment_rate_work",    "Комментарии и оценки работ"),
    ("issue_magic_links",    "Выдача одноразовых ссылок"),
    ("view_all_students",    "Все студенты системы"),
    ("manage_curators",      "Управление кураторами"),
    ("ban_unban_users",      "Блокировка пользователей"),
    ("view_upload_stats",    "Статистика загрузок"),
    ("manage_tariffs",       "Управление тарифами"),
    ("assign_roles",         "Назначение ролей"),
    ("full_admin_panel",     "Полная административная панель"),
    ("manage_admins",        "Управление администраторами"),
]

# role_name → list of permission codenames (cumulative)
ROLE_PERMISSIONS = {
    "ученик": [
        "upload_photos", "view_own_gallery", "view_upload_history", "take_exam",
    ],
    "куратор": [
        "upload_photos", "view_own_gallery", "view_upload_history", "take_exam",
        "view_own_students", "view_student_photos", "comment_rate_work", "issue_magic_links",
    ],
    "модератор": [
        "upload_photos", "view_own_gallery", "view_upload_history", "take_exam",
        "view_own_students", "view_student_photos", "comment_rate_work", "issue_magic_links",
        "view_all_students", "manage_curators", "ban_unban_users", "view_upload_stats",
    ],
    "админ": [
        "upload_photos", "view_own_gallery", "view_upload_history", "take_exam",
        "view_own_students", "view_student_photos", "comment_rate_work", "issue_magic_links",
        "view_all_students", "manage_curators", "ban_unban_users", "view_upload_stats",
        "manage_tariffs", "assign_roles", "full_admin_panel",
    ],
    "суперадмин": [
        "upload_photos", "view_own_gallery", "view_upload_history", "take_exam",
        "view_own_students", "view_student_photos", "comment_rate_work", "issue_magic_links",
        "view_all_students", "manage_curators", "ban_unban_users", "view_upload_stats",
        "manage_tariffs", "assign_roles", "full_admin_panel",
        "manage_admins",
    ],
}


def migrate() -> None:
    # Step 1: Create new tables via ORM
    Base.metadata.create_all(bind=engine)
    print("Tables ensured.")

    with engine.begin() as conn:
        inspector = inspect(conn)

        # Step 2: Add role_id column to users if missing
        user_columns = {col["name"] for col in inspector.get_columns("users")}
        if "role_id" not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN role_id INTEGER REFERENCES roles(id)"))
            print("Added users.role_id column.")
        else:
            print("users.role_id already exists.")

        # Step 3: Seed roles
        for rank, name, display_name in ROLES:
            conn.execute(text(
                "INSERT INTO roles (rank, name, display_name) VALUES (:rank, :name, :display_name) "
                "ON CONFLICT (name) DO NOTHING"
            ), {"rank": rank, "name": name, "display_name": display_name})
        print("Roles seeded.")

        # Step 4: Seed permissions
        for codename, description in PERMISSIONS:
            conn.execute(text(
                "INSERT INTO permissions (codename, description) VALUES (:codename, :description) "
                "ON CONFLICT (codename) DO NOTHING"
            ), {"codename": codename, "description": description})
        print("Permissions seeded.")

        # Step 5: Seed role_permissions
        for role_name, perm_codenames in ROLE_PERMISSIONS.items():
            role_row = conn.execute(
                text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}
            ).fetchone()
            if not role_row:
                continue
            role_id = role_row[0]
            for codename in perm_codenames:
                perm_row = conn.execute(
                    text("SELECT id FROM permissions WHERE codename = :codename"),
                    {"codename": codename}
                ).fetchone()
                if not perm_row:
                    continue
                conn.execute(text(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :perm_id) "
                    "ON CONFLICT DO NOTHING"
                ), {"role_id": role_id, "perm_id": perm_row[0]})
        print("Role permissions seeded.")

        # Step 6: Migrate existing users
        superadmin_row = conn.execute(
            text("SELECT id FROM roles WHERE name = 'суперадмин'")
        ).fetchone()
        student_row = conn.execute(
            text("SELECT id FROM roles WHERE name = 'ученик'")
        ).fetchone()

        if superadmin_row:
            result = conn.execute(text(
                "UPDATE users SET role_id = :role_id WHERE is_admin = TRUE AND role_id IS NULL"
            ), {"role_id": superadmin_row[0]})
            print(f"Migrated {result.rowcount} admin(s) → суперадмин.")

        if student_row:
            result = conn.execute(text(
                "UPDATE users SET role_id = :role_id "
                "WHERE is_group_member = TRUE AND is_admin = FALSE AND role_id IS NULL"
            ), {"role_id": student_row[0]})
            print(f"Migrated {result.rowcount} group member(s) → ученик.")

    print("Migration complete.")


if __name__ == "__main__":
    migrate()
