import uuid
from datetime import datetime, timezone, date

from sqlalchemy import String, Text, DateTime, Date, Integer, Boolean, JSON, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    identity: Mapped[str] = mapped_column(String(160), unique=True)
    nickname: Mapped[str] = mapped_column(String(80))
    space_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Space(Base):
    __tablename__ = "spaces"
    __table_args__ = (CheckConstraint("member_count >= 0 AND member_count <= 2"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    member_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Invitation(Base):
    __tablename__ = "invitations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    space_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    visibility: Mapped[str] = mapped_column(String(10), default="private")


class Memory(Base):
    __tablename__ = "memories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    space_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(Text, default="")
    occurred_on: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(16))
    visibility: Mapped[str] = mapped_column(String(10), default="private")
    place: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    photo_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Media(Base):
    __tablename__ = "media"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(100), unique=True)
    mime: Mapped[str] = mapped_column(String(32))
    size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Anniversary(Base):
    __tablename__ = "anniversaries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(160))
    date: Mapped[date] = mapped_column(Date)
    repeat_yearly: Mapped[bool] = mapped_column(Boolean, default=True)


class Wish(Base):
    __tablename__ = "wishes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    text: Mapped[str] = mapped_column(String(1000))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DailyQuestion(Base):
    __tablename__ = "daily_questions"
    __table_args__ = (UniqueConstraint("space_id", "day"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"))
    question_text: Mapped[str] = mapped_column(String(1000))


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("daily_id", "author_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    daily_id: Mapped[str] = mapped_column(ForeignKey("daily_questions.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    answer: Mapped[str] = mapped_column(Text)


class Mood(Base):
    __tablename__ = "moods"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    space_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    day: Mapped[date] = mapped_column(Date)
    mood: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text, default="")
    visibility: Mapped[str] = mapped_column(String(10), default="private")


class Habit(Base):
    __tablename__ = "habits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))


class Checkin(Base):
    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("habit_id", "author_id", "day"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    habit_id: Mapped[str] = mapped_column(ForeignKey("habits.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    day: Mapped[date] = mapped_column(Date)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Audit(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
