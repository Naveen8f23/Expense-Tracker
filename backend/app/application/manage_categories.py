"""ManageCategories use cases (BACKLOG.md E6; REQUIREMENTS.md EXT-2, §5 Data Model).

Categories are fully user-defined for MVP -- no fixed system list is ever seeded.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.models import Category, Payee, Transaction, User


class CategoryNotFoundError(Exception):
    pass


class CategoryAlreadyExistsError(Exception):
    pass


class CategoryInUseError(Exception):
    """Raised when deleting a category still referenced by transactions with no explicit
    reassignment target -- "prompts reassignment rather than leaving orphaned references"
    (BACKLOG.md E6)."""

    def __init__(self, category_id: int, transaction_count: int):
        self.category_id = category_id
        self.transaction_count = transaction_count
        super().__init__(f"Category {category_id} is used by {transaction_count} transaction(s)")


def list_categories(session: Session, user: User) -> list[Category]:
    return (
        session.query(Category)
        .filter(Category.user_id == user.id)
        .order_by(Category.name)
        .all()
    )


def create_category(session: Session, user: User, name: str) -> Category:
    category = Category(user_id=user.id, name=name)
    session.add(category)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise CategoryAlreadyExistsError(f"A category named {name!r} already exists") from exc
    session.refresh(category)
    return category


def rename_category(session: Session, category_id: int, new_name: str) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise CategoryNotFoundError(f"No category with id {category_id}")
    category.name = new_name
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise CategoryAlreadyExistsError(f"A category named {new_name!r} already exists") from exc
    session.refresh(category)
    return category


def delete_category(session: Session, category_id: int, *, reassign_to: int | None = None) -> None:
    category = session.get(Category, category_id)
    if category is None:
        raise CategoryNotFoundError(f"No category with id {category_id}")

    in_use = session.query(Transaction).filter(Transaction.category_id == category_id)
    count = in_use.count()
    if count > 0:
        if reassign_to is None:
            raise CategoryInUseError(category_id, count)
        if session.get(Category, reassign_to) is None:
            raise CategoryNotFoundError(f"No category with id {reassign_to} to reassign to")
        in_use.update({Transaction.category_id: reassign_to})
        # A payee whose remembered default (COR-2) was this category should point at the
        # replacement instead, so its future transactions don't silently lose categorization.
        session.query(Payee).filter(Payee.default_category_id == category_id).update(
            {Payee.default_category_id: reassign_to}
        )

    session.delete(category)
    session.commit()
