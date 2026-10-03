import os
import json
import uuid
import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Video(Base):
    __tablename__ = 'videos'
    id = Column(String(128), primary_key=True)
    user_id = Column(String(64), nullable=True)
    title = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=True)
    video_url = Column(String(512), nullable=False)
    caption_content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Quiz(Base):
    __tablename__ = 'quizzes'
    quiz_id = Column(String(128), primary_key=True)
    video_id = Column(String(128), nullable=False)
    questions_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/vidi_q")
engine = None
SessionLocal = None
ACTIVE_DB_TYPE = "postgres"

def get_normalized_db_url(url):
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url

def init_db():
    global engine, SessionLocal, ACTIVE_DB_TYPE
    effective_url = get_normalized_db_url(DB_URL)
    try:
        # Try connecting to PostgreSQL
        test_engine = create_engine(effective_url, pool_pre_ping=True)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine = test_engine
        ACTIVE_DB_TYPE = "postgres"
        print(f"[DB] Connected successfully to local PostgreSQL: {effective_url}")
    except Exception as e:
        print(f"[DB Warning] Could not connect to PostgreSQL ({e}).")
        print("[DB Notice] Falling back to local SQLite database (vidi_q_local.db) for smooth local development.")
        sqlite_url = "sqlite:///vidi_q_local.db"
        engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        ACTIVE_DB_TYPE = "sqlite"

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    print(f"[DB] Database tables verified ({ACTIVE_DB_TYPE}).")

def get_session():
    if SessionLocal is None:
        init_db()
    return SessionLocal()

def create_user(email, password, name="", phone=""):
    session = get_session()
    try:
        existing = session.query(User).filter(User.email == email).first()
        if existing:
            return None, "User with this email already exists"
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password=password,
            name=name,
            phone=phone
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "phone": user.phone,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }, None
    except Exception as e:
        session.rollback()
        return None, str(e)
    finally:
        session.close()

def authenticate_user(email, password):
    session = get_session()
    try:
        user = session.query(User).filter(User.email == email).first()
        if not user or user.password != password:
            return None, "Invalid email or password"
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "phone": user.phone,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }, None
    finally:
        session.close()

def save_video_record(video_id, title, prompt, video_url, caption_content, user_id=None):
    session = get_session()
    try:
        existing = session.query(Video).filter(Video.id == video_id).first()
        if existing:
            existing.title = title
            existing.prompt = prompt
            existing.video_url = video_url
            existing.caption_content = caption_content
        else:
            video = Video(
                id=video_id,
                user_id=user_id,
                title=title,
                prompt=prompt,
                video_url=video_url,
                caption_content=caption_content
            )
            session.add(video)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[DB Error] Failed to save video record: {e}")
    finally:
        session.close()

def get_all_videos():
    session = get_session()
    try:
        videos = session.query(Video).order_by(Video.created_at.desc()).all()
        return [
            {
                "id": v.id,
                "title": v.title,
                "prompt": v.prompt,
                "video_url": v.video_url,
                "created_at": int(v.created_at.timestamp() * 1000) if v.created_at else 0
            }
            for v in videos
        ]
    finally:
        session.close()

def get_video_record(video_id):
    session = get_session()
    try:
        v = session.query(Video).filter(Video.id == video_id).first()
        if not v:
            return None
        return {
            "id": v.id,
            "title": v.title,
            "prompt": v.prompt,
            "video_url": v.video_url,
            "caption_content": v.caption_content,
            "created_at": int(v.created_at.timestamp() * 1000) if v.created_at else 0
        }
    finally:
        session.close()

def save_quiz_record(quiz_id, video_id, questions):
    session = get_session()
    try:
        q_json = json.dumps(questions) if not isinstance(questions, str) else questions
        existing = session.query(Quiz).filter(Quiz.quiz_id == quiz_id).first()
        if existing:
            existing.questions_json = q_json
        else:
            quiz = Quiz(
                quiz_id=quiz_id,
                video_id=video_id,
                questions_json=q_json
            )
            session.add(quiz)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[DB Error] Failed to save quiz record: {e}")
    finally:
        session.close()

def get_quiz_record(video_id):
    session = get_session()
    try:
        quiz = session.query(Quiz).filter(Quiz.video_id == video_id).order_by(Quiz.created_at.desc()).first()
        if not quiz:
            return None
        return {
            "quiz_id": quiz.quiz_id,
            "video_id": quiz.video_id,
            "questions": json.loads(quiz.questions_json)
        }
    finally:
        session.close()
