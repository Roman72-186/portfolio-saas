from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class UploadLog(Base):
    __tablename__ = "upload_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tariff: Mapped[str] = mapped_column(String(50), nullable=False)
    month: Mapped[str] = mapped_column(String(20), nullable=False)
    photo_type: Mapped[str] = mapped_column(String(10), nullable=False)
    photo_count: Mapped[int] = mapped_column(Integer, default=1)
    drive_file_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")

    __table_args__ = (
        # Ускоряет запросы: WHERE user_id=X AND status='success' ORDER BY uploaded_at DESC
        Index("ix_upload_log_user_status_uploaded", "user_id", "status", "uploaded_at"),
    )
