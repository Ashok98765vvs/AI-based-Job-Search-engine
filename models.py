"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_source_extid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), index=True)  # e.g. greenhouse
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    salary_min: Mapped[Optional[float]] = mapped_column(Float)
    salary_max: Mapped[Optional[float]] = mapped_column(Float)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(8), default="USD")
    description: Mapped[Optional[str]] = mapped_column(Text)
    apply_url: Mapped[str] = mapped_column(String(1024))
    posted_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    visa_sponsorship: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    tags: Mapped[Optional[str]] = mapped_column(Text)  # comma-separated

    scores: Mapped[list["MatchScore"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_json: Mapped[Optional[str]] = mapped_column(Text)  # JSON blob of AI analysis
    skills: Mapped[Optional[str]] = mapped_column(Text)  # comma-separated
    target_roles: Mapped[Optional[str]] = mapped_column(Text)
    years_experience: Mapped[Optional[float]] = mapped_column(Float)
    seniority: Mapped[Optional[str]] = mapped_column(String(64))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    applications: Mapped[list["Application"]] = relationship(back_populates="resume")
    scores: Mapped[list["MatchScore"]] = relationship(back_populates="resume", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[str] = mapped_column(String(64), default="saved")  # saved/applied/interview/offer/rejected
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    resume: Mapped[Resume] = relationship(back_populates="applications")


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"), index=True)
    keyword: Mapped[str] = mapped_column(String(128), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class MatchScore(Base):
    __tablename__ = "match_scores"
    __table_args__ = (UniqueConstraint("resume_id", "job_id", name="uq_resume_job"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    ats_score: Mapped[float] = mapped_column(Float, default=0.0)
    semantic_score: Mapped[float] = mapped_column(Float, default=0.0)
    keyword_match_pct: Mapped[float] = mapped_column(Float, default=0.0)
    overall: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    resume: Mapped[Resume] = relationship(back_populates="scores")
    job: Mapped[Job] = relationship(back_populates="scores")
