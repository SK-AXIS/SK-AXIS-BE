
from fastapi import Depends
from sqlalchemy.orm import Session
import redis

from app.db.session import get_db, get_redis