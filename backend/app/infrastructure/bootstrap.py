from sqlalchemy.orm import Session

from app.infrastructure.models import User


def ensure_default_user(session: Session) -> User:
    """Single-user v1 (REQUIREMENTS.md Assumption): ensure exactly one User row exists."""
    user = session.query(User).first()
    if user is not None:
        return user
    user = User()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
