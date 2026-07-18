import pytest

from app.infrastructure.bootstrap import HDFC_SENDER_RULES, ensure_hdfc_sender_rules
from app.infrastructure.db import Base, make_engine, make_session_factory
from app.infrastructure.models import SenderRule, TransactionType


@pytest.fixture()
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY_PATH", str(tmp_path / "secret.key"))
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    Session = make_session_factory(engine)
    yield Session()


def test_seeds_the_three_confirmed_hdfc_templates(session):
    rules = ensure_hdfc_sender_rules(session)

    assert len(rules) == 3
    assert {rule.sender_address for rule in rules} == {"alerts@hdfcbank.bank.in"}
    assert {rule.transaction_type for rule in rules} == {
        TransactionType.UPI_DEBIT,
        TransactionType.UPI_CREDIT,
        TransactionType.CREDIT_CARD_DEBIT,
    }
    # Credit card credit (the pending 4th template, REQUIREMENTS.md §8) must not be guessed at.
    assert TransactionType.CREDIT_CARD_CREDIT not in {rule.transaction_type for rule in rules}


def test_matches_the_module_level_rule_definitions_exactly(session):
    rules = ensure_hdfc_sender_rules(session)
    seeded = {(rule.sender_address, rule.content_pattern_id, rule.transaction_type) for rule in rules}
    assert seeded == set(HDFC_SENDER_RULES)


def test_is_idempotent_does_not_duplicate_rows_on_repeated_calls(session):
    ensure_hdfc_sender_rules(session)
    ensure_hdfc_sender_rules(session)
    ensure_hdfc_sender_rules(session)

    assert session.query(SenderRule).count() == 3


def test_adding_a_fourth_rule_requires_no_code_change_to_the_seed_function(session, monkeypatch):
    # Validates BACKLOG.md B2's extensibility criterion directly: appending one tuple to the
    # rule list (simulating the 4th template, once its real sample arrives) is picked up as-is.
    import app.infrastructure.bootstrap as bootstrap_module

    extra_rule = ("alerts@icicibank.com", "icici_upi_debit", TransactionType.UPI_DEBIT)
    monkeypatch.setattr(
        bootstrap_module, "HDFC_SENDER_RULES", bootstrap_module.HDFC_SENDER_RULES + [extra_rule]
    )

    rules = ensure_hdfc_sender_rules(session)

    assert len(rules) == 4
    assert extra_rule in {(r.sender_address, r.content_pattern_id, r.transaction_type) for r in rules}
