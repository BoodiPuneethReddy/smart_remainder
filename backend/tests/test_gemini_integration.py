"""
tests/test_gemini_integration.py — Integration test suite for Gemini API Client & Prompt Engineering
"""

import pytest
from unittest.mock import patch, MagicMock

from app.core.config import Settings
from app.services.ai_client import GeminiAIClient, LocalAIService, get_ai_client
from app.services.prompt_builders import (
    build_tutor_prompt,
    build_planner_explanation_prompt,
    build_reflection_prompt,
    build_chat_recommendation_prompt,
    build_document_analysis_prompt,
)


class TestPromptBuilders:
    def test_build_tutor_prompt(self):
        ctx = {
            "personality": "Socratic Tutor",
            "subject": "DBMS",
            "topic": "Normalization",
            "mastery": 42.0,
            "retention": 80.0,
            "user_answer": "Normalization removes redundancy.",
            "knowledge_graph": {
                "nodes": [{"title": "1NF", "summary": "Atomic values"}]
            },
            "mistakes": [{"topic": "BCNF", "mistake_summary": "Confused BCNF with 3NF"}]
        }
        prompt = build_tutor_prompt(ctx)
        assert "mentor" in prompt.lower()
        assert "DBMS" in prompt
        assert "Normalization" in prompt
        assert "42%" in prompt
        assert "Atomic values" in prompt
        assert "Confused BCNF" in prompt

    def test_build_planner_explanation_prompt(self):
        ctx = {
            "available_minutes": 90,
            "tasks": [
                {"title": "SQL Practice", "subject": "DBMS", "recommended_minutes": 45, "priority_score": 88.0, "days_remaining": 2}
            ]
        }
        prompt = build_planner_explanation_prompt(ctx)
        assert "1h 30m" in prompt
        assert "SQL Practice" in prompt
        assert "88/100" in prompt

    def test_build_reflection_prompt(self):
        ctx = {"available_minutes": 60, "allocated_minutes": 90, "items": [{"title": "t1"}, {"title": "t2"}]}
        prompt = build_reflection_prompt(ctx)
        assert "60m" in prompt
        assert "90m" in prompt

    def test_build_chat_recommendation_prompt(self):
        ctx = {
            "user_query": "What should I study?",
            "intent": "study_planning",
            "subject": "DBMS",
            "analytics": {"completion_rate": 75.0, "burnout_risk_level": "low"},
        }
        prompt = build_chat_recommendation_prompt(ctx)
        assert "What should I study?" in prompt
        assert "DBMS" in prompt
        assert "75%" in prompt

    def test_build_document_analysis_prompt(self):
        prompt = build_document_analysis_prompt("Sample SQL content text", "DBMS.pdf")
        assert "DBMS.pdf" in prompt
        assert "Sample SQL content text" in prompt


class TestGeminiAIClient:
    def test_detects_placeholder_key(self):
        client = GeminiAIClient(api_key="YOUR_GEMINI_API_KEY_HERE")
        assert client._is_placeholder_key() is True

    def test_detects_empty_key(self):
        client = GeminiAIClient(api_key="")
        assert client._is_placeholder_key() is True

    def test_detects_valid_looking_key(self):
        client = GeminiAIClient(api_key="AIzaSyA_RealLookKeyHere_12345")
        assert client._is_placeholder_key() is False

    @patch("app.services.ai_client.get_settings")
    def test_fallback_when_placeholder_key_and_fallback_enabled(self, mock_settings):
        mock_s = Settings()
        mock_s.disable_ai_fallback = False
        mock_settings.return_value = mock_s

        client = GeminiAIClient(api_key="YOUR_GEMINI_API_KEY_HERE")
        ctx = {"subject": "DBMS", "tasks": []}
        response = client.generate("chat_answer", ctx)
        assert isinstance(response, str)
        assert len(response) > 10

    @patch("app.services.ai_client.get_settings")
    def test_raises_exception_when_placeholder_key_and_strict_mode(self, mock_settings):
        mock_s = Settings()
        mock_s.disable_ai_fallback = True
        mock_settings.return_value = mock_s

        client = GeminiAIClient(api_key="YOUR_GEMINI_API_KEY_HERE")
        ctx = {"subject": "DBMS", "tasks": []}
        with pytest.raises(RuntimeError, match="Gemini API Error"):
            client.generate("chat_answer", ctx)

    @patch("httpx.post")
    def test_successful_gemini_api_call(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Gemini generated reasoning text for DBMS."}]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        client = GeminiAIClient(api_key="AIzaSyA_TestKey_123456789")
        ctx = {"user_query": "Explain normalization", "subject": "DBMS"}
        result = client.generate("chat_answer", ctx)

        assert result == "Gemini generated reasoning text for DBMS."
        assert mock_post.called

    @patch("app.services.ai_client.get_settings")
    @patch("httpx.post")
    def test_gemini_api_retry_and_fallback_on_error(self, mock_post, mock_settings):
        mock_s = Settings()
        mock_s.disable_ai_fallback = False
        mock_settings.return_value = mock_s
        mock_post.side_effect = Exception("Network timeout")

        client = GeminiAIClient(api_key="AIzaSyA_TestKey_123456789")
        ctx = {"subject": "DBMS", "tasks": []}
        result = client.generate("chat_answer", ctx)

        assert isinstance(result, str)
        assert len(result) > 10


class TestFactoryIntegration:
    @patch("app.services.ai_client.get_settings")
    def test_factory_returns_gemini_client_when_key_present(self, mock_settings):
        mock_s = Settings()
        mock_s.use_gemini = True
        mock_s.gemini_api_key = "AIzaSyA_TestKey_12345"
        mock_s.ai_service_mode = "local"
        mock_settings.return_value = mock_s

        client = get_ai_client()
        assert isinstance(client, GeminiAIClient)

    @patch("app.services.ai_client.get_settings")
    def test_factory_returns_local_client_when_local_mode(self, mock_settings):
        mock_s = Settings()
        mock_s.use_gemini = False
        mock_s.gemini_api_key = ""
        mock_s.ai_service_mode = "local"
        mock_settings.return_value = mock_s

        client = get_ai_client()
        assert isinstance(client, LocalAIService)
