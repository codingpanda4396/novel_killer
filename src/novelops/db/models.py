from __future__ import annotations

from typing import Optional

from sqlalchemy import Column, Integer, String, text
from sqlmodel import Field, SQLModel


class HotItem(SQLModel, table=True):
    __tablename__ = "hot_items"

    signal_id: str = Field(primary_key=True)
    source: str
    source_type: str
    platform: str
    rank_type: Optional[str] = None
    rank_position: Optional[int] = None
    title: str
    author: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None
    hot_score: Optional[float] = None
    comment_count: Optional[int] = None
    like_count: Optional[int] = None
    read_count: Optional[int] = None
    collected_at: str
    raw_payload: str


class MarketReport(SQLModel, table=True):
    __tablename__ = "market_reports"

    report_id: str = Field(primary_key=True)
    hot_item_id: Optional[str] = Field(default=None, index=True)
    source: str
    source_type: str
    platform: str
    rank_type: Optional[str] = None
    rank_position: Optional[int] = None
    title: str
    author: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None
    hot_score: Optional[float] = None
    comment_count: Optional[int] = None
    like_count: Optional[int] = None
    read_count: Optional[int] = None
    collected_at: str
    raw_payload: str
    genre: Optional[str] = None
    protagonist_template: Optional[str] = None
    golden_finger: Optional[str] = None
    hook: Optional[str] = None
    core_desire: Optional[str] = None
    reader_emotion: Optional[str] = None
    risk: Optional[str] = None
    shuang_points: Optional[str] = None
    risk_points: Optional[str] = None
    platform_fit_score: float = 0.0
    competition_score: float = 0.0
    writing_difficulty_score: float = 0.0
    commercial_potential_score: float = 0.0
    final_score: Optional[float] = None
    model: Optional[str] = None
    analyzed_at: str
    analyzer_version: str
    report_json: Optional[str] = None


class StoryProject(SQLModel, table=True):
    __tablename__ = "story_projects"

    id: str = Field(primary_key=True)
    name: str
    genre: Optional[str] = None
    path: str
    target_platform: Optional[str] = None
    current_volume: Optional[int] = None
    next_chapter: Optional[int] = None
    updated_at: Optional[str] = None


class ChapterPlan(SQLModel, table=True):
    __tablename__ = "chapter_plans"

    project_id: str = Field(primary_key=True)
    chapter: int = Field(primary_key=True)
    plan_path: str = Field(primary_key=True)
    goal: Optional[str] = None
    hook: Optional[str] = None
    status: Optional[str] = None
    generated_at: Optional[str] = None


class Chapter(SQLModel, table=True):
    __tablename__ = "chapters"

    project_id: str = Field(primary_key=True)
    chapter: int = Field(primary_key=True)
    source_type: str = Field(primary_key=True)
    content_path: str = Field(primary_key=True)
    path: Optional[str] = None
    title: Optional[str] = None
    word_count: Optional[int] = None
    status: Optional[str] = None


class GenerationRun(SQLModel, table=True):
    __tablename__ = "generation_runs"

    project_id: str = Field(primary_key=True)
    chapter: int = Field(primary_key=True)
    artifact_dir: str = Field(primary_key=True)
    final_stage: Optional[str] = None
    llm_used: int = 0
    final_score: Optional[float] = None
    status: Optional[str] = None


class Review(SQLModel, table=True):
    __tablename__ = "reviews"

    project_id: str = Field(primary_key=True)
    chapter: int = Field(primary_key=True)
    report_path: str = Field(primary_key=True)
    score: Optional[float] = None
    threshold_value: Optional[float] = None
    passed: int = 0
    action: Optional[str] = None
    model: Optional[str] = None
    fallback_reason: Optional[str] = None


class FeedbackLog(SQLModel, table=True):
    __tablename__ = "feedback_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True)
    chapter: int = Field(index=True)
    platform: str
    impressions: Optional[int] = None
    clicks: Optional[int] = None
    reads: Optional[int] = None
    favorites: Optional[int] = None
    comments: Optional[int] = None
    record_date: str
    raw_payload: Optional[str] = None


class UserProject(SQLModel, table=True):
    __tablename__ = "user_projects"

    user_id: str = Field(primary_key=True)
    project_id: str = Field(primary_key=True)
    created_at: Optional[str] = Field(default=None, sa_column=Column(String, server_default=text("CURRENT_TIMESTAMP")))
    is_default: int = Field(default=0, sa_column=Column(Integer, server_default=text("0")))


class RevisionQueue(SQLModel, table=True):
    __tablename__ = "revision_queue"

    project_id: str = Field(primary_key=True)
    chapter: int = Field(primary_key=True)
    path: str = Field(primary_key=True)
    reason: Optional[str] = None
    source_report: Optional[str] = None
    status: Optional[str] = None


class RawSignalObservation(SQLModel, table=True):
    __tablename__ = "raw_signal_observations"

    observation_id: Optional[int] = Field(default=None, primary_key=True)
    signal_id: str = Field(index=True)
    source: str
    platform: str
    rank_type: Optional[str] = None
    rank_position: Optional[int] = None
    hot_score: Optional[float] = None
    rank_metric_name: Optional[str] = None
    rank_metric_value: Optional[float] = None
    source_url: Optional[str] = None
    snapshot_date: str
    collected_at: str
    raw_payload: str
