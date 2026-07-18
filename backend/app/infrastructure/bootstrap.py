from sqlalchemy.orm import Session

from app.infrastructure.models import SenderRule, TransactionType, User


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


# The three confirmed HDFC templates (REQUIREMENTS.md Appendix A; ADR-0010) -- all three share
# one sender address, distinguished only by content. The fourth (credit card credit) is still
# pending a real sample (REQUIREMENTS.md §8) and isn't seeded yet; adding it later is one more
# tuple here, not a code change (BACKLOG.md B2).
_HDFC_SENDER_ADDRESS = "alerts@hdfcbank.bank.in"

HDFC_SENDER_RULES = [
    (_HDFC_SENDER_ADDRESS, "hdfc_upi_debit", TransactionType.UPI_DEBIT),
    (_HDFC_SENDER_ADDRESS, "hdfc_upi_credit", TransactionType.UPI_CREDIT),
    (_HDFC_SENDER_ADDRESS, "hdfc_credit_card_debit", TransactionType.CREDIT_CARD_DEBIT),
]


def ensure_hdfc_sender_rules(session: Session) -> list[SenderRule]:
    """Seed the confirmed HDFC SenderRules (BACKLOG.md B2) if not already present.

    Idempotent -- safe to call on every app startup, matching ensure_default_user's pattern.
    """
    existing = {
        (rule.sender_address, rule.content_pattern_id) for rule in session.query(SenderRule).all()
    }
    for sender_address, content_pattern_id, transaction_type in HDFC_SENDER_RULES:
        if (sender_address, content_pattern_id) in existing:
            continue
        session.add(
            SenderRule(
                sender_address=sender_address,
                content_pattern_id=content_pattern_id,
                transaction_type=transaction_type,
            )
        )
    session.commit()
    return session.query(SenderRule).all()
