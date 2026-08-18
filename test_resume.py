import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import pytest
from resume_parser import (
    extract_text, extract_contact, extract_name, extract_skills,
    extract_experience, extract_education, detect_experience_level,
    score_resume_quality, parse_resume
)
from skills_database import ALL_SKILLS, MARKETING_SKILLS

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "test_resumes")


class TestExtractText:
    def test_extract_from_txt(self):
        path = os.path.join(SAMPLE_DIR, "sample_senior.txt")
        text = extract_text(path)
        assert len(text) > 100
        assert "Priya Sharma" in text

    def test_extract_from_nonexistent_file(self):
        text = extract_text("nonexistent.pdf")
        assert text == ""

    def test_extract_from_unsupported_format(self):
        path = os.path.join(SAMPLE_DIR, "sample_senior.txt")
        os.rename(path, path + ".bak")
        text = extract_text(path + ".bak")
        os.rename(path + ".bak", path)
        assert text == ""


class TestExtractContact:
    def test_valid_email(self):
        text = "John Doe\njohn@example.com\n+91 98765 43210"
        contact = extract_contact(text)
        assert contact["email"] == "john@example.com"

    def test_no_email(self):
        text = "John Doe\nNo contact info here"
        contact = extract_contact(text)
        assert contact["email"] is None

    def test_phone_extraction(self):
        text = "John Doe\njohn@test.com\n+91 98765 43210"
        contact = extract_contact(text)
        assert contact["phone"] is not None


class TestExtractName:
    def test_name_from_first_line(self):
        text = "Priya Sharma\npriya@gmail.com"
        name = extract_name(text)
        assert name == "Priya Sharma"

    def test_name_skips_email(self):
        text = "priya@gmail.com\nPriya Sharma"
        name = extract_name(text)
        assert name == "Priya Sharma"

    def test_name_skips_phone(self):
        text = "+91 98765 43210\nPriya Sharma"
        name = extract_name(text)
        assert name == "Priya Sharma"


class TestExtractSkills:
    def test_finds_known_skills(self):
        text = "Experience with SEO, Google Ads, and social media marketing"
        result = extract_skills(text)
        assert "seo" in result["skills"]
        assert "google ads" in result["skills"]
        assert result["skill_count"] >= 2

    def test_finds_categories(self):
        text = "Skills in SEO, content marketing, and copywriting"
        result = extract_skills(text)
        assert "digital_marketing" in result["categories"]
        assert "content" in result["categories"]

    def test_no_skills(self):
        text = "I like cooking and reading books"
        result = extract_skills(text)
        assert result["skill_count"] == 0

    def test_case_insensitive(self):
        text = "Experience with SEO and GOOGLE ADS"
        result = extract_skills(text)
        assert "seo" in result["skills"]
        assert "google ads" in result["skills"]


class TestExtractExperience:
    def test_years_from_text(self):
        text = "5 years of experience in digital marketing"
        result = extract_experience(text)
        assert result["years"] == 5

    def test_years_with_plus(self):
        text = "3+ years experience in SEO"
        result = extract_experience(text)
        assert result["years"] == 3

    def test_no_years(self):
        text = "Fresh graduate looking for opportunities"
        result = extract_experience(text)
        assert result["years"] is None

    def test_job_titles(self):
        text = "Marketing Manager at Company\nSocial Media Executive at Startup"
        result = extract_experience(text)
        assert result["title_count"] >= 2


class TestExtractEducation:
    def test_finds_education(self):
        text = "MBA in Marketing | Delhi University | 2019\nB.Com | Delhi University | 2017"
        result = extract_education(text)
        assert result["has_education"] is True
        assert len(result["entries"]) >= 2

    def test_no_education(self):
        text = "Looking for a job in marketing"
        result = extract_education(text)
        assert result["has_education"] is False


class TestDetectExperienceLevel:
    def test_fresher_by_years(self):
        exp = {"years": 0, "job_titles": []}
        assert detect_experience_level(exp) == "fresher"

    def test_mid_by_years(self):
        exp = {"years": 3, "job_titles": []}
        assert detect_experience_level(exp) == "mid"

    def test_senior_by_years(self):
        exp = {"years": 7, "job_titles": []}
        assert detect_experience_level(exp) == "senior"

    def test_senior_by_title(self):
        exp = {"years": None, "job_titles": ["Marketing Director at Corp"]}
        assert detect_experience_level(exp) == "senior"

    def test_mid_by_title(self):
        exp = {"years": None, "job_titles": ["Marketing Manager at Corp"]}
        assert detect_experience_level(exp) == "mid"

    def test_fresher_by_title(self):
        exp = {"years": None, "job_titles": ["Marketing Intern at Startup"]}
        assert detect_experience_level(exp) == "fresher"

    def test_unknown(self):
        exp = {"years": None, "job_titles": []}
        assert detect_experience_level(exp) == "unknown"


class TestScoreResumeQuality:
    def test_high_quality_resume(self):
        resume = {
            "name": "Priya Sharma",
            "contact": {"email": "priya@gmail.com", "phone": "+91 98765 43210"},
            "skills": {"skill_count": 15, "skills": ["seo", "sem"]},
            "experience": {"years": 5, "job_titles": ["Marketing Manager"]},
            "education": {"has_education": True},
            "raw_text": " ".join(["word"] * 200)
        }
        result = score_resume_quality(resume)
        assert result["score"] >= 80

    def test_low_quality_resume(self):
        resume = {
            "name": "Unknown",
            "contact": {"email": None, "phone": None},
            "skills": {"skill_count": 0, "skills": []},
            "experience": {"years": None, "job_titles": []},
            "education": {"has_education": False},
            "raw_text": "short text"
        }
        result = score_resume_quality(resume)
        assert result["score"] <= 20

    def test_medium_quality_resume(self):
        resume = {
            "name": "John",
            "contact": {"email": "john@test.com", "phone": None},
            "skills": {"skill_count": 3, "skills": ["seo"]},
            "experience": {"years": None, "job_titles": ["Marketing Intern"]},
            "education": {"has_education": True},
            "raw_text": " ".join(["word"] * 100)
        }
        result = score_resume_quality(resume)
        assert 30 <= result["score"] <= 70


class TestParseResume:
    def test_parse_senior_resume(self):
        path = os.path.join(SAMPLE_DIR, "sample_senior.txt")
        result = parse_resume(path)
        assert result is not None
        assert result["name"] == "Priya Sharma"
        assert result["contact"]["email"] == "priya.sharma@gmail.com"
        assert result["skills"]["skill_count"] >= 10
        assert result["experience"]["years"] == 5
        assert result["experience_level"] == "senior"
        assert result["quality"]["score"] >= 70

    def test_parse_fresher_resume(self):
        path = os.path.join(SAMPLE_DIR, "sample_fresher.txt")
        result = parse_resume(path)
        assert result is not None
        assert result["name"] == "Rahul Verma"
        assert result["skills"]["skill_count"] >= 1
        assert result["experience_level"] == "fresher"

    def test_parse_bad_resume(self):
        path = os.path.join(SAMPLE_DIR, "sample_bad.txt")
        result = parse_resume(path)
        assert result is not None
        assert result["quality"]["score"] <= 40
        assert result["skills"]["skill_count"] == 0

    def test_parse_nonexistent_file(self):
        result = parse_resume("nonexistent.pdf")
        assert result is None

    def test_output_schema(self):
        path = os.path.join(SAMPLE_DIR, "sample_senior.txt")
        result = parse_resume(path)
        required_keys = ["file_path", "name", "contact", "skills",
                         "experience", "education", "experience_level",
                         "raw_text", "quality"]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"


class TestSkillsDatabase:
    def test_all_skills_not_empty(self):
        assert len(ALL_SKILLS) > 0

    def test_skill_categories_populated(self):
        from skills_database import SKILL_CATEGORIES
        assert len(SKILL_CATEGORIES) > 0

    def test_marketing_skills_structure(self):
        for cat, skills in MARKETING_SKILLS.items():
            assert isinstance(skills, list)
            assert len(skills) > 0
