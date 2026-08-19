"""Tests for domain registry system"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.domains import get_registry
from backend.app.domains.base import BaseDomain


class TestDomainRegistry:
    """Test the domain registry singleton."""

    def test_singleton_returns_same_instance(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_all_domains_registered(self):
        registry = get_registry()
        slugs = registry.list_slugs()
        expected = ["marketing", "software_engineering", "finance", "hr", "sales"]
        for slug in expected:
            assert slug in slugs, f"Domain '{slug}' not registered"

    def test_domain_count(self):
        registry = get_registry()
        assert len(registry.list_slugs()) == 5

    def test_get_domain_returns_correct_type(self):
        registry = get_registry()
        domain = registry.get("marketing")
        assert isinstance(domain, BaseDomain)

    def test_get_nonexistent_domain_returns_none(self):
        registry = get_registry()
        assert registry.get("nonexistent") is None


class TestMarketingDomain:
    """Test the marketing domain."""

    def test_slug(self):
        domain = get_registry().get("marketing")
        assert domain.slug == "marketing"

    def test_name(self):
        domain = get_registry().get("marketing")
        assert domain.name == "Marketing"

    def test_has_questions(self):
        domain = get_registry().get("marketing")
        questions = domain.get_questions()
        assert len(questions) >= 50

    def test_has_topics(self):
        domain = get_registry().get("marketing")
        topics = domain.topics
        assert "seo" in topics
        assert "social_media" in topics

    def test_has_skills(self):
        domain = get_registry().get("marketing")
        skills = domain.get_skills()
        assert len(skills) > 0

    def test_get_recommendation_returns_string(self):
        domain = get_registry().get("marketing")
        rec = domain.get_recommendation("seo", 30.0)
        assert isinstance(rec, str)
        assert len(rec) > 10

    def test_evaluation_prompt_contains_question(self):
        domain = get_registry().get("marketing")
        prompt = domain.get_evaluation_prompt("What is SEO?", "SEO is search engine optimization")
        assert "What is SEO?" in prompt
        assert "SEO is search engine optimization" in prompt


class TestSoftwareEngineeringDomain:
    """Test the software engineering domain."""

    def test_slug(self):
        domain = get_registry().get("software_engineering")
        assert domain.slug == "software_engineering"

    def test_has_questions(self):
        domain = get_registry().get("software_engineering")
        assert len(domain.get_questions()) >= 20

    def test_has_dsa_questions(self):
        domain = get_registry().get("software_engineering")
        dsa_questions = [q for q in domain.get_questions() if q["topic"] == "dsa"]
        assert len(dsa_questions) > 0


class TestFinanceDomain:
    """Test the finance domain."""

    def test_slug(self):
        domain = get_registry().get("finance")
        assert domain.slug == "finance"

    def test_has_questions(self):
        domain = get_registry().get("finance")
        assert len(domain.get_questions()) >= 10

    def test_has_valuation_questions(self):
        domain = get_registry().get("finance")
        valuation_q = [q for q in domain.get_questions() if q["topic"] == "valuation"]
        assert len(valuation_q) > 0


class TestHRDomain:
    """Test the HR domain."""

    def test_slug(self):
        domain = get_registry().get("hr")
        assert domain.slug == "hr"

    def test_has_questions(self):
        domain = get_registry().get("hr")
        assert len(domain.get_questions()) >= 10

    def test_has_recruitment_questions(self):
        domain = get_registry().get("hr")
        recruitment_q = [q for q in domain.get_questions() if q["topic"] == "recruitment"]
        assert len(recruitment_q) > 0


class TestSalesDomain:
    """Test the sales domain."""

    def test_slug(self):
        domain = get_registry().get("sales")
        assert domain.slug == "sales"

    def test_has_questions(self):
        domain = get_registry().get("sales")
        assert len(domain.get_questions()) >= 10

    def test_has_negotiation_questions(self):
        domain = get_registry().get("sales")
        negotiation_q = [q for q in domain.get_questions() if q["topic"] == "negotiation"]
        assert len(negotiation_q) > 0


class TestDomainIntegrity:
    """Cross-domain integrity checks."""

    def test_all_domains_implement_base(self):
        registry = get_registry()
        for slug in registry.list_slugs():
            domain = registry.get(slug)
            assert isinstance(domain, BaseDomain), f"{slug} is not a BaseDomain"

    def test_all_domains_have_required_fields(self):
        registry = get_registry()
        for slug in registry.list_slugs():
            domain = registry.get(slug)
            assert domain.slug
            assert domain.name
            assert domain.description
            assert len(domain.topics) > 0
            assert len(domain.scoring_dimensions) > 0

    def test_all_domains_have_questions(self):
        registry = get_registry()
        for slug in registry.list_slugs():
            domain = registry.get(slug)
            questions = domain.get_questions()
            assert len(questions) > 0, f"{slug} has no questions"

    def test_all_questions_have_required_fields(self):
        registry = get_registry()
        required = ["id", "topic", "difficulty", "roles", "question"]
        for slug in registry.list_slugs():
            for q in registry.get(slug).get_questions():
                for field in required:
                    assert field in q, f"{slug}: question '{q.get('id', '?')}' missing '{field}'"

    def test_all_domains_have_skills(self):
        registry = get_registry()
        for slug in registry.list_slugs():
            skills = registry.get(slug).get_skills()
            assert len(skills) > 0, f"{slug} has no skills"

    def test_all_domains_have_job_titles(self):
        registry = get_registry()
        for slug in registry.list_slugs():
            titles = registry.get(slug).get_job_titles()
            assert "fresher" in titles
            assert "mid" in titles
            assert "senior" in titles

    def test_all_domains_have_recommendations(self):
        registry = get_registry()
        for slug in registry.list_slugs():
            domain = registry.get(slug)
            for topic in domain.topics:
                rec = domain.get_recommendation(topic, 30.0)
                assert isinstance(rec, str)
                assert len(rec) > 5
