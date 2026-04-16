"""Issue a one-time login link from local CLI."""
import argparse
import os
import sys
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

try:
    from app.config import settings
    from app.db.database import SessionLocal
    from app.models.user import User
    from app.services.auth_links import issue_one_time_login_link
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Project dependencies are missing. Install them first, for example: pip install -r requirements.txt"
    ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue a one-time login link")
    parser.add_argument("--vk-id", type=int, required=True, help="VK ID used as stable student identifier")
    parser.add_argument("--name", required=True, help="Student name shown in the cabinet")
    parser.add_argument("--tariff", default="УВЕРЕННЫЙ", help="Tariff for new user")
    parser.add_argument("--photo-url", default=None, help="Optional avatar URL")
    parser.add_argument("--base-url", default=None, help="Public app base URL")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.vk_id == args.vk_id).first()
        if user:
            user.name = args.name
            if args.photo_url is not None:
                user.photo_url = args.photo_url
            user.is_group_member = True
            user.last_vk_check_at = datetime.now(timezone.utc)
        else:
            user = User(
                vk_id=args.vk_id,
                name=args.name,
                photo_url=args.photo_url,
                tariff=args.tariff,
                is_group_member=True,
                last_vk_check_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.flush()

        base_url = args.base_url or f"https://{settings.domain}"
        link, _ = issue_one_time_login_link(
            db,
            user=user,
            base_url=base_url,
            issued_by="cli",
        )
        print(link)
    finally:
        db.close()


if __name__ == "__main__":
    main()
