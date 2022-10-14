import pathlib

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine(f'sqlite:///{pathlib.Path("../../db.sqlite3")}')

Base = declarative_base()


def setup(engn):
    Base.metadata.create_all(engn, checkfirst=True)