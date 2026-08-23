from backend.app.domains.base import BaseDomain
from typing import List, Dict, Any


class SoftwareEngineeringDomain(BaseDomain):

    @property
    def slug(self) -> str:
        return "software_engineering"

    @property
    def name(self) -> str:
        return "Software Engineering"

    @property
    def description(self) -> str:
        return "DSA, system design, OOP, databases, APIs, and software architecture"

    @property
    def topics(self) -> List[str]:
        return [
            "dsa", "system_design", "oop", "databases", "api_design",
            "algorithms", "data_structures", "testing", "devops",
            "security", "performance", "code_review",
        ]

    @property
    def scoring_dimensions(self) -> List[str]:
        return ["technical_depth", "problem_solving", "communication", "code_quality"]

    def get_questions(self) -> List[Dict[str, Any]]:
        return [
            {"id": "se_01", "topic": "dsa", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is the difference between an array and a linked list? When would you use each?"},
            {"id": "se_02", "topic": "dsa", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Explain the time complexity of quicksort. What is its worst case and how can you avoid it?"},
            {"id": "se_03", "topic": "dsa", "difficulty": "hard", "roles": ["senior"], "question": "Design a LRU cache with O(1) get and put operations. What data structures would you use?"},
            {"id": "se_04", "topic": "system_design", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How would you design a URL shortener like bit.ly? Walk me through the architecture."},
            {"id": "se_05", "topic": "system_design", "difficulty": "hard", "roles": ["senior"], "question": "Design a real-time chat application like WhatsApp. Handle millions of concurrent users."},
            {"id": "se_06", "topic": "system_design", "difficulty": "hard", "roles": ["senior"], "question": "How would you design a rate limiter? Compare token bucket, sliding window, and leaky bucket approaches."},
            {"id": "se_07", "topic": "oop", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "Explain the four pillars of OOP with real-world examples."},
            {"id": "se_08", "topic": "oop", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is the difference between inheritance and composition? When would you prefer one over the other?"},
            {"id": "se_09", "topic": "oop", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Explain SOLID principles. Give an example of violating each principle."},
            {"id": "se_10", "topic": "databases", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is the difference between SQL and NoSQL databases? When would you use each?"},
            {"id": "se_11", "topic": "databases", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do database indexes work? What are the tradeoffs of adding too many indexes?"},
            {"id": "se_12", "topic": "databases", "difficulty": "hard", "roles": ["senior"], "question": "Explain database normalization up to 3NF. When would you intentionally denormalize?"},
            {"id": "se_13", "topic": "api_design", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is REST? What makes an API RESTful?"},
            {"id": "se_14", "topic": "api_design", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is the difference between REST and GraphQL? When would you choose GraphQL?"},
            {"id": "se_15", "topic": "api_design", "difficulty": "hard", "roles": ["senior"], "question": "How do you version a REST API without breaking existing clients?"},
            {"id": "se_16", "topic": "algorithms", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Explain dynamic programming with an example. How do you identify if a problem can be solved with DP?"},
            {"id": "se_17", "topic": "algorithms", "difficulty": "hard", "roles": ["senior"], "question": "When would you use BFS vs DFS? Give a real-world problem for each."},
            {"id": "se_18", "topic": "data_structures", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is a hash map? How does it handle collisions?"},
            {"id": "se_19", "topic": "testing", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is the difference between unit testing, integration testing, and end-to-end testing?"},
            {"id": "se_20", "topic": "testing", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is test-driven development? What are its pros and cons?"},
            {"id": "se_21", "topic": "devops", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is CI/CD? How would you set up a pipeline for a Python application?"},
            {"id": "se_22", "topic": "devops", "difficulty": "hard", "roles": ["senior"], "question": "Explain containerization with Docker. How does it differ from virtual machines?"},
            {"id": "se_23", "topic": "security", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is SQL injection? How do you prevent it?"},
            {"id": "se_24", "topic": "security", "difficulty": "hard", "roles": ["senior"], "question": "How do you implement authentication and authorization in a web application? Compare JWT and session-based auth."},
            {"id": "se_25", "topic": "performance", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you optimize a slow API endpoint? Walk me through your debugging process."},
            {"id": "se_26", "topic": "performance", "difficulty": "hard", "roles": ["senior"], "question": "What is caching? Compare Redis, Memcached, and in-memory caching. When would you use each?"},
            {"id": "se_27", "topic": "code_review", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What do you look for when reviewing someone's code?"},
            {"id": "se_28", "topic": "code_review", "difficulty": "medium", "roles": ["mid", "senior"], "question": "A PR has 2000 lines of changes. How do you approach reviewing it?"},
            {"id": "se_29", "topic": "dsa", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Explain the difference between a stack and a queue. Give a real-world use case for each."},
            {"id": "se_30", "topic": "system_design", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How would you design a notification system that supports email, SMS, and push notifications?"},
        ]

    def get_skills(self) -> Dict[str, List[str]]:
        return {
            "programming_languages": [
                "python", "java", "javascript", "typescript", "c++", "go", "rust",
                "kotlin", "swift", "ruby", "php", "scala",
            ],
            "web_frameworks": [
                "react", "next.js", "vue", "angular", "node.js", "express",
                "fastapi", "django", "flask", "spring boot", "rails",
            ],
            "databases": [
                "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
                "sqlite", "dynamodb", "cassandra", "neo4j",
            ],
            "cloud_devops": [
                "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
                "ci/cd", "jenkins", "github actions", "nginx",
            ],
            "tools": [
                "git", "linux", "vscode", "jira", "confluence",
                "postman", "figma", "swagger",
            ],
            "concepts": [
                "data structures", "algorithms", "system design", "oop",
                "design patterns", "rest api", "graphql", "microservices",
                "testing", "security", "caching", "message queues",
            ],
        }

    def get_job_titles(self) -> Dict[str, List[str]]:
        return {
            "fresher": ["intern", "trainee", "junior developer", "associate engineer", "graduate engineer"],
            "mid": ["software engineer", "senior developer", "full stack developer", "backend developer", "frontend developer"],
            "senior": ["staff engineer", "principal engineer", "architect", "engineering manager", "tech lead", "cto"],
        }

    def get_evaluation_prompt(self, question: str, answer: str) -> str:
        return f"""You are a strict but fair software engineering interviewer.

Evaluate the candidate's answer.

Question: {question}
Answer: {answer}

Scoring rules (ALL scores MUST be integers 0-10. NEVER use 0-100):
- If answer is abusive, irrelevant, nonsense, or empty -> very low scores (0-2)
- If answer is generic but somewhat relevant -> medium scores (4-6)
- If answer is technically accurate, well-structured, and includes examples -> high scores (7-10)

IMPORTANT: Use ONLY integers between 0 and 10 for ALL scores.
DO NOT use a 0-100 scale.

If the overall_score is below 6, write a 2-3 sentence ideal model answer in "ideal_answer".
If the overall_score is 6 or above, leave "ideal_answer" as an empty string.

Return ONLY valid JSON in this exact format:
{{
  "technical_depth": 0,
  "problem_solving": 0,
  "communication": 0,
  "code_quality": 0,
  "overall_score": 0,
  "strengths": ["", ""],
  "weaknesses": ["", ""],
  "ideal_answer": "",
  "follow_up": "",
  "is_serious": true
}}"""

    def get_recommendation(self, topic: str, score: float) -> str:
        tips = {
            "dsa": "Practice problems on LeetCode/HackerRank. Focus on arrays, trees, and graphs.",
            "system_design": "Study system design interview books. Practice designing real systems.",
            "oop": "Review SOLID principles with code examples. Practice refactoring code.",
            "databases": "Practice SQL queries. Learn about indexing, normalization, and transactions.",
            "api_design": "Build REST APIs. Learn about status codes, versioning, and error handling.",
            "algorithms": "Study Big-O notation. Practice sorting, searching, and graph algorithms.",
            "data_structures": "Implement linked lists, trees, and hash maps from scratch.",
            "testing": "Write unit tests for your projects. Learn about mocking and test coverage.",
            "devops": "Set up CI/CD for a project. Learn Docker basics.",
            "security": "Study OWASP Top 10. Practice input validation and authentication.",
            "performance": "Learn profiling tools. Study caching strategies and database optimization.",
            "code_review": "Review open source PRs. Practice giving constructive feedback.",
        }
        return tips.get(topic, f"Study {topic} fundamentals and practice with real projects.")


domain = SoftwareEngineeringDomain()
