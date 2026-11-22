# -*- coding: utf-8 -*-
"""数据访问层：只做数据库读写，不含业务编排。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.models import Document, User


def get_user(db: Session, uid: int) -> User | None:
    return db.get(User, uid)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user(db: Session, email: str, password: str) -> User:
    u = User(email=email, password_hash=hash_password(password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def create_document(db: Session, *, user_id: int, title: str, source_type: str,
                    content_hash: str, storage_key: str, size: int, mime: str) -> Document:
    d = Document(user_id=user_id, title=title, source_type=source_type, content_hash=content_hash,
                 storage_key=storage_key, size=size, mime=mime, status="pending")
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def get_document(db: Session, doc_id: int, user_id: int) -> Document | None:
    """带租户过滤：只能取到自己的文档。"""
    return db.scalar(select(Document).where(Document.id == doc_id, Document.user_id == user_id))


def list_documents(db: Session, user_id: int, limit: int = 50) -> list[Document]:
    return list(db.scalars(select(Document).where(Document.user_id == user_id)
                           .order_by(Document.id.desc()).limit(limit)))


def find_by_hash(db: Session, user_id: int, content_hash: str) -> Document | None:
    return db.scalar(select(Document).where(Document.user_id == user_id,
                                            Document.content_hash == content_hash))
