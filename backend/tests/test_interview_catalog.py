"""
Unit tests for app/interview_catalog.py.

All tests are offline — purely structural checks on the catalog data.
"""
import pytest

from app.interview_catalog import (
    CATEGORY_LABELS,
    QUESTIONS,
    Question,
    get_all_questions,
    get_by_category,
    get_by_id,
)

VALID_CATEGORIES = set(CATEGORY_LABELS.keys())
VALID_ANSWER_TYPES = {"bool", "choice", "number", "text"}


# ─── Structural integrity ─────────────────────────────────────────────────────

def test_no_duplicate_ids():
    ids = [q.id for q in QUESTIONS]
    assert len(ids) == len(set(ids)), "Duplicate question IDs found"


def test_all_categories_valid():
    for q in QUESTIONS:
        assert q.category in VALID_CATEGORIES, (
            f"{q.id}: unknown category {q.category!r}"
        )


def test_all_answer_types_valid():
    for q in QUESTIONS:
        assert q.answer_type in VALID_ANSWER_TYPES, (
            f"{q.id}: unknown answer_type {q.answer_type!r}"
        )


def test_choice_questions_have_options():
    for q in QUESTIONS:
        if q.answer_type == "choice":
            assert q.options and len(q.options) >= 2, (
                f"{q.id}: choice question must have at least 2 options"
            )


def test_non_choice_questions_have_no_options():
    for q in QUESTIONS:
        if q.answer_type != "choice":
            assert q.options is None, (
                f"{q.id}: non-choice question must not have options"
            )


def test_condition_references_known_id():
    """Every condition must reference a question that exists in the catalog."""
    all_ids = {q.id for q in QUESTIONS}
    for q in QUESTIONS:
        if q.condition is not None:
            ref_id, _ = q.condition
            assert ref_id in all_ids, (
                f"{q.id}: condition references unknown question {ref_id!r}"
            )


def test_condition_not_self_referential():
    for q in QUESTIONS:
        if q.condition is not None:
            ref_id, _ = q.condition
            assert ref_id != q.id, f"{q.id}: condition references itself"


def test_all_categories_have_at_least_one_question():
    for cat in VALID_CATEGORIES:
        qs = get_by_category(cat)
        assert len(qs) >= 1, f"Category {cat!r} has no questions"


# ─── Public API ───────────────────────────────────────────────────────────────

def test_get_all_questions_returns_all():
    assert get_all_questions() == QUESTIONS


def test_get_by_id_known():
    q = get_by_id("work.homeoffice")
    assert q.id == "work.homeoffice"
    assert q.category == "arbeit"
    assert q.answer_type == "bool"


def test_get_by_id_unknown_raises():
    with pytest.raises(KeyError):
        get_by_id("does.not.exist")


def test_get_by_category_returns_only_that_category():
    qs = get_by_category("basis")
    assert all(q.category == "basis" for q in qs)
    assert len(qs) > 0


# ─── Spot-checks on key questions ────────────────────────────────────────────

def test_homeoffice_room_conditioned_on_homeoffice():
    q = get_by_id("work.homeoffice_room")
    assert q.condition == ("work.homeoffice", True)


def test_commute_km_conditioned_on_employment_list():
    q = get_by_id("work.commute_km")
    ref_id, expected = q.condition
    assert ref_id == "base.employment"
    assert isinstance(expected, list)
    assert "Angestellt" in expected
    assert "Beamter" in expected


def test_childcare_double_conditioned():
    """base.childcare_costs should only appear after children_under_14=True."""
    q = get_by_id("base.childcare_costs")
    assert q.condition == ("base.children_under_14", True)


def test_energy_renovation_conditioned_on_ownership():
    q = get_by_id("home.energy_renovation")
    assert q.condition == ("home.owns_property", True)


def test_rental_questions_conditioned_on_has_rental():
    rental_qs = [q for q in get_by_category("vermietung") if q.id != "rental.has_rental"]
    for q in rental_qs:
        assert q.condition is not None, (
            f"{q.id}: rental sub-question must have a condition"
        )
        ref_id, _ = q.condition
        assert ref_id == "rental.has_rental", (
            f"{q.id}: expected condition on rental.has_rental"
        )


def test_disability_degree_conditioned_on_disability():
    q = get_by_id("health.disability_degree")
    assert q.condition == ("health.disability", True)


def test_rag_hints_are_known_laws():
    known_laws = {"EStG", "AO", "UStG", "LStR", "BMF", "BFH",
                  "EStDV", "SolzG", "GewStG", "KStG", "ErbStG"}
    for q in QUESTIONS:
        for hint in q.rag_hint:
            assert hint in known_laws, (
                f"{q.id}: unknown rag_hint {hint!r}"
            )
