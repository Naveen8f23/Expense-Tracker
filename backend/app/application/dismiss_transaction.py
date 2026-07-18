"""DismissTransaction use case (BACKLOG.md E4; REQUIREMENTS.md COR-4).

Hides a misclassified transaction from search/analytics (E1's `list_transactions` already
excludes dismissed rows) without deleting it or its source email -- the audit trail stays intact.
"""

from sqlalchemy.orm import Session

from app.application.transaction_errors import TransactionNotFoundError
from app.infrastructure.models import Transaction


def dismiss_transaction(session: Session, user_id: int, transaction_id: int) -> Transaction:
    txn = session.get(Transaction, transaction_id)
    if txn is None or txn.user_id != user_id:
        raise TransactionNotFoundError(f"No transaction with id {transaction_id}")
    txn.dismissed = True
    session.commit()
    session.refresh(txn)
    return txn
