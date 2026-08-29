"""OpenAPI contract snapshot — pins the public API surface so accidental
breaking changes (renames, removed/moved routes, dropped request fields)
fail the suite instead of silently breaking the frontend.

Focused on the interface that matters: paths, verbs, tags and the request
schema shapes. Response details are covered by the endpoint tests.
"""

from backend.app import app

SCHEMA = app.openapi()

# (path, [methods], tag)
EXPECTED_ENDPOINTS = [
    ("/api/auth/register", ["post"], "Authentication"),
    ("/api/auth/login", ["post"], "Authentication"),
    ("/api/auth/me", ["get"], "Authentication"),
    ("/api/interviews/start", ["post"], "Interviews"),
    ("/api/interviews/audio-start", ["post"], "Interviews"),
    ("/api/interviews/parse-resume", ["post"], "Interviews"),
    ("/api/interviews", ["get"], "Interviews"),
    ("/api/interviews/{session_id}/question", ["get"], "Interviews"),
    ("/api/interviews/{session_id}/answer", ["post"], "Interviews"),
    ("/api/interviews/{session_id}/audio-answer", ["post"], "Interviews"),
    ("/api/interviews/{session_id}/followup", ["post"], "Interviews"),
    ("/api/interviews/{session_id}/report", ["get"], "Interviews"),
    ("/api/domains", ["get"], "Domains"),
    ("/api/company/dashboard", ["get"], "Company"),
    ("/api/webhooks", ["get", "post"], "Webhooks"),
    ("/api/webhooks/{webhook_id}", ["get", "put", "delete"], "Webhooks"),
    ("/api/campaigns", ["get"], "Campaigns"),
    ("/api/campaigns/upload", ["post"], "Campaigns"),
    ("/api/analytics/sessions", ["get"], "Analytics"),
]

# Publicly-authored schemas that the frontend depends on by name/shape
EXPECTED_SCHEMAS = {
    "StartInterviewRequest": {"domain_slug": "required", "question_count": "optional"},
    "AnswerRequest": {"question_id": "required", "answer_text": "required", "answer_time_seconds": "optional"},
    "FollowupRequest": {"answer_text": "required", "answer_time_seconds": "optional"},
    "RegisterRequest": {"email": "required", "password": "required", "role": "optional"},
    "LoginRequest": {"email": "required", "password": "required"},
    "AuthResponse": {"access_token": "required", "token_type": "optional", "user_id": "required", "role": "required"},
    "UserProfile": {"user_id": "required", "email": "required", "role": "required"},
}


def _required_optional(schema: dict) -> dict:
    required = set(schema.get("required", []))
    return {
        name: ("required" if name in required else "optional")
        for name in schema.get("properties", {})
    }


class TestOpenApiContract:
    def test_metadata(self):
        assert SCHEMA["info"]["title"] == "Interview Agent API"
        assert SCHEMA["info"]["version"] == "2.0.0"
        assert SCHEMA["openapi"].startswith("3.")

    def test_expected_endpoints_present(self):
        paths = SCHEMA["paths"]
        for path, methods, tag in EXPECTED_ENDPOINTS:
            assert path in paths, f"Missing path: {path}"
            for method in methods:
                op = paths[path].get(method)
                assert op is not None, f"Missing {method.upper()} {path}"
                tags = op.get("tags", [])
                assert tag in tags, f"{method.upper()} {path} tagged {tags}, expected '{tag}'"

    def test_request_schema_shapes(self):
        schemas = SCHEMA["components"]["schemas"]
        for name, expectations in EXPECTED_SCHEMAS.items():
            assert name in schemas, f"Missing schema: {name}"
            shape = _required_optional(schemas[name])
            for field, expected in expectations.items():
                assert shape.get(field) == expected, (
                    f"{name}.{field} expected {expected}, got {shape.get(field)}"
                )

    def test_audio_answer_is_multipart_form(self):
        schema = SCHEMA["paths"]["/api/interviews/{session_id}/audio-answer"]["post"]
        assert "multipart/form-data" in schema["requestBody"]["content"]

    def test_no_path_trailing_slash_drift(self):
        # Frontend calls these exact paths; catch accidental suffix changes.
        paths = set(SCHEMA["paths"])
        for endpoint in EXPECTED_ENDPOINTS:
            path = endpoint[0]
            if path.endswith("/"):
                assert path[:-1] in paths, f"trailing-slash drift on {path}"