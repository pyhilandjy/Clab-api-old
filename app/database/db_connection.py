# import os
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


Base = declarative_base()


class DBConnection:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    @contextmanager
    def get_db(self):
        db_session = self.SessionLocal()
        try:
            yield db_session
        finally:
            db_session.close()


postgresql_connection = DBConnection(settings.postgresql_url)


# from supabase import create_client, Client

# url: str = settings.postgresql_url
# key: str = settings.supabase_key
# postgresql_connection = Client = create_client(url, key)
