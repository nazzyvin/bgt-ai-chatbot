from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, email: str, hashed_password: str, role: str = "customer") -> User:
    user = User(email=email, hashed_password=hashed_password, role=role)
    db.add(user)
    db.flush()
    return user