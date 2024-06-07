from typing import List
from sqlalchemy.orm import Session
from app.db.models import Message


def add_message(db: Session, message: Message) -> Message:
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def remove_message(db: Session, message: Message) -> None:
    db.delete(message)


def get_messages(db: Session) -> List[Message]:
    return db.query(Message).all()


def get_message_by_id(db: Session, id: str) -> Message:
    return db.query(Message).filter(Message.id == id).first()
