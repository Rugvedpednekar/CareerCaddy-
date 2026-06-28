from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import get_database_url

DATABASE_URL = get_database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    from . import models
    Base.metadata.create_all(bind=engine)

def ensure_schema_upgrades():
    dialect = engine.dialect.name
    json_type = "JSONB" if dialect == "postgresql" else "JSON"
    upgrades = {
        "users": {
            "username": "VARCHAR(80)", "full_name": "VARCHAR(255)", "profile_type": "VARCHAR(255)",
            "target_roles": json_type, "password_hash": "TEXT", "availability": "VARCHAR(255)",
            "salary_expectation": "VARCHAR(255)",
        },
        "applications": {"generated_answer_sources": json_type, "missing_fields": json_type},
        "resumes": {"parsed_resume_data": json_type, "parse_status": "VARCHAR(40)"},
    }
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table, columns in upgrades.items():
            if table not in existing_tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, column_type in columns.items():
                if name not in existing:
                    connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {column_type}'))
