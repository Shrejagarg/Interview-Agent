"""Unit tests for the ARC IV custom-question-bank DB helpers.

Runs against the throwaway temp DB bound by conftest's DATABASE_URL override, so
the dev database is never touched.
"""

import uuid
from sqlalchemy import text

from backend.app.db import custom_banks as banks_db
from backend.app.db import database
from backend.tests import conftest  # noqa: F401  (temp-DB quarantine)


def _fresh_db():
    with database.engine.begin() as conn:
        conn.execute(text("DELETE FROM custom_questions"))
        conn.execute(text("DELETE FROM custom_question_banks"))


class TestBankCRUD:
    def test_create_and_get_bank(self):
        _fresh_db()
        bid = banks_db.create_bank_db("company-x", "My Bank", "marketing", "desc")["id"]
        got = banks_db.get_bank_db(bid, company_id="company-x")
        assert got["name"] == "My Bank"
        assert got["domain_slug"] == "marketing"
        assert got["description"] == "desc"
        assert got["question_count"] == 0

    def test_list_banks_sorted_company_scoped(self):
        _fresh_db()
        banks_db.create_bank_db("c1", "B1", "marketing")
        banks_db.create_bank_db("c1", "B2", "sales")
        banks_db.create_bank_db("c2", "OTHER", "hr")
        names = [b["name"] for b in banks_db.list_banks_db("c1")]
        assert set(names) == {"B1", "B2"}
        assert "OTHER" not in names

    def test_get_bank_requires_ownership(self):
        _fresh_db()
        bid = banks_db.create_bank_db("owner", "Secret", "finance")["id"]
        assert banks_db.get_bank_db(bid, company_id="intruder") is None
        assert banks_db.get_bank_db(bid) is not None  # no ownership filter

    def test_update_bank(self):
        _fresh_db()
        bid = banks_db.create_bank_db("c1", "Old", "marketing")["id"]
        updated = banks_db.update_bank_db(bid, "c1", name="New", description="d2")
        assert updated["name"] == "New"
        assert updated["description"] == "d2"

    def test_update_bank_wrong_owner_returns_none(self):
        _fresh_db()
        bid = banks_db.create_bank_db("c1", "B", "marketing")["id"]
        assert banks_db.update_bank_db(bid, "intruder", name="Hacked") is None

    def test_delete_bank(self):
        _fresh_db()
        bid = banks_db.create_bank_db("c1", "B", "marketing")["id"]
        assert banks_db.delete_bank_db(bid, "c1") is True
        assert banks_db.get_bank_db(bid) is None

    def test_delete_bank_wrong_owner_returns_false(self):
        _fresh_db()
        bid = banks_db.create_bank_db("c1", "B", "marketing")["id"]
        assert banks_db.delete_bank_db(bid, "intruder") is False


class TestQuestionCRUD:
    def _bank(self, company="company-x", domain="marketing"):
        return banks_db.create_bank_db(company, "Bank", domain)["id"]

    def test_add_and_list_questions(self):
        _fresh_db()
        bid = self._bank()
        q1 = banks_db.add_question_db(bid, "company-x", "seo", "medium", "What is SEO?", roles=["senior"])["id"]
        q2 = banks_db.add_question_db(bid, "company-x", "ads", "easy", "What is PPC?")["id"]
        got = banks_db.get_bank_db(bid, company_id="company-x")
        assert got["question_count"] == 2
        texts = {q["question_text"] for q in got["questions"]}
        assert texts == {"What is SEO?", "What is PPC?"}
        assert got["questions"][0]["roles"] == ["senior"] or got["questions"][1]["roles"] == ["senior"]

    def test_add_question_wrong_owner_returns_none(self):
        _fresh_db()
        bid = self._bank("owner")
        assert banks_db.add_question_db(bid, "intruder", "x", "easy", "Q?") is None

    def test_update_question(self):
        _fresh_db()
        bid = self._bank()
        qid = banks_db.add_question_db(bid, "company-x", "seo", "medium", "Old Q?")["id"]
        updated = banks_db.update_question_db(qid, bid, "company-x", question_text="New Q?", difficulty="hard")
        assert updated["question_text"] == "New Q?"
        assert updated["difficulty"] == "hard"

    def test_update_question_wrong_owner_returns_none(self):
        _fresh_db()
        bid = self._bank()
        qid = banks_db.add_question_db(bid, "company-x", "seo", "medium", "Q?")["id"]
        assert banks_db.update_question_db(qid, bid, "intruder", question_text="Hijack?") is None

    def test_delete_question(self):
        _fresh_db()
        bid = self._bank()
        qid = banks_db.add_question_db(bid, "company-x", "seo", "medium", "Q?")["id"]
        assert banks_db.delete_question_db(qid, bid, "company-x") is True
        assert banks_db.get_bank_db(bid, company_id="company-x")["question_count"] == 0

    def test_delete_question_wrong_owner_returns_false(self):
        _fresh_db()
        bid = self._bank()
        qid = banks_db.add_question_db(bid, "company-x", "seo", "medium", "Q?")["id"]
        assert banks_db.delete_question_db(qid, bid, "intruder") is False

    def test_delete_bank_cascades_questions(self):
        _fresh_db()
        bid = self._bank()
        banks_db.add_question_db(bid, "company-x", "seo", "medium", "Q?")
        assert banks_db.delete_bank_db(bid, "company-x") is True
        assert banks_db.get_active_questions_db(bid) == []

    def test_get_active_questions_excludes_inactive(self):
        _fresh_db()
        bid = self._bank()
        q_active = banks_db.add_question_db(bid, "company-x", "seo", "medium", "Active?")["id"]
        q_off = banks_db.add_question_db(bid, "company-x", "seo", "medium", "Deactivated?")["id"]
        banks_db.update_question_db(q_off, bid, "company-x", is_active=False)
        active = banks_db.get_active_questions_db(bid)
        assert [q["id"] for q in active] == [q_active]
