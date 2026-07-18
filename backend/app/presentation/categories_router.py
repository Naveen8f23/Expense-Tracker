"""Categories API (BACKLOG.md E6; REQUIREMENTS.md EXT-2, §5)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application.manage_categories import (
    CategoryAlreadyExistsError,
    CategoryInUseError,
    CategoryNotFoundError,
    create_category,
    delete_category,
    list_categories,
    rename_category,
)
from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.db import get_db
from app.infrastructure.models import Category

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryCreateRequest(BaseModel):
    name: str


class CategoryRenameRequest(BaseModel):
    name: str


def _serialize_category(category: Category) -> dict:
    return {"id": category.id, "name": category.name}


@router.get("")
def list_categories_endpoint(session: Session = Depends(get_db)) -> dict:
    user = ensure_default_user(session)
    return {"items": [_serialize_category(c) for c in list_categories(session, user)]}


@router.post("", status_code=201)
def create_category_endpoint(
    body: CategoryCreateRequest, session: Session = Depends(get_db)
) -> dict:
    user = ensure_default_user(session)
    try:
        category = create_category(session, user, body.name)
    except CategoryAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_category(category)


@router.patch("/{category_id}")
def rename_category_endpoint(
    category_id: int, body: CategoryRenameRequest, session: Session = Depends(get_db)
) -> dict:
    try:
        category = rename_category(session, category_id, body.name)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CategoryAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_category(category)


@router.delete("/{category_id}", status_code=204)
def delete_category_endpoint(
    category_id: int,
    reassign_to: Optional[int] = Query(default=None),
    session: Session = Depends(get_db),
) -> None:
    try:
        delete_category(session, category_id, reassign_to=reassign_to)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CategoryInUseError as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "transaction_count": exc.transaction_count},
        ) from exc
