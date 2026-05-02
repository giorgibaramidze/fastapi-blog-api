from sqlalchemy.orm import DeclarativeBase
from app.db.mixins import UUIDMixin


class Base(DeclarativeBase, UUIDMixin):
    pass
