from datetime import date

from app.models.schemas import Customer
from app.services.customer_context import renewal_answer, scope_question

GOLD = Customer(customer_id="C-1", name="Asha", product="Health", tier="Gold", consent=True,
                renewal_date=date(2026, 11, 12), policy_status="ACTIVE")


def test_vague_policy_reference_gets_product_and_tier():
    assert scope_question("what is covered in this customers policy?", GOLD) == \
        "what is covered in Health Gold policy?"
    assert scope_question("Does my policy cover maternity?", GOLD) == "Does Health Gold policy cover maternity?"


def test_specific_question_is_unchanged():
    q = "What is the waiting period for pre-existing diseases?"
    assert scope_question(q, GOLD) == q


def test_renewal_date_answered_from_record():
    a = renewal_answer("When is this customers policy renewing?", GOLD)
    assert "2026-11-12" in a and "Health Gold" in a


def test_clause_question_is_not_a_renewal_date_question():
    assert renewal_answer("What happens in the renewal grace period?", GOLD) is None


from app.services.customer_context import details_answer, record_answer  # noqa: E402


def test_customer_details_answered_from_record():
    a = record_answer("what is this customers details", GOLD)
    assert "Health Gold" in a and "2026-11-12" in a and "Contact consent: Given" in a


def test_premium_and_consent_questions_use_record():
    assert details_answer("Has this customer given consent?", GOLD)
    assert details_answer("What is their premium?", GOLD)


def test_clause_questions_do_not_hit_the_record():
    for q in ["What is the waiting period for pre-existing diseases?",
              "what is covered in this customers policy?",
              "Does the premium increase after a claim?"]:
        assert record_answer(q, GOLD) is None, q
