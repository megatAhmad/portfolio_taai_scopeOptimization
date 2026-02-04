"""
Unit tests for the AI Service module.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock

from src.ai_service import AIService, AIProvider, JustificationResult


@pytest.fixture
def sample_row():
    """Create a sample row for testing."""
    return pd.Series(
        {
            "Work ID": "WO-00001",
            "Description": "Replace worn bearings on conveyor system",
            "Priority": "High",
            "Category": "Preventive Maintenance",
            "Estimated Hours": 12,
            "Cost Estimate": 3500.00,
            "Risk Level": "Medium",
        }
    )


@pytest.fixture
def sample_rule_details():
    """Create sample rule details."""
    return {
        "High Priority Accept": {
            "conditions_evaluated": [
                {"condition": {"field": "Priority", "value": "High"}, "match": True}
            ],
            "all_match": True,
        }
    }


class TestAIService:
    """Tests for AIService class."""

    def test_init_default_provider(self):
        """Test initialization with default provider."""
        service = AIService()
        assert service.provider == AIProvider.ANTHROPIC

    def test_init_openai_provider(self):
        """Test initialization with OpenAI provider."""
        service = AIService(provider=AIProvider.OPENAI)
        assert service.provider == AIProvider.OPENAI

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        service = AIService(api_key="test-key")
        assert service._api_key == "test-key"

    def test_init_with_model(self):
        """Test initialization with custom model."""
        service = AIService(model="claude-3-opus-20240229")
        assert service._model == "claude-3-opus-20240229"

    def test_format_row_data(self, sample_row):
        """Test row data formatting."""
        service = AIService()
        formatted = service._format_row_data(sample_row)

        assert "Work ID" in formatted
        assert "WO-00001" in formatted
        assert "Priority" in formatted
        assert "High" in formatted

    def test_format_rule_details(self, sample_rule_details):
        """Test rule details formatting."""
        service = AIService()
        formatted = service._format_rule_details(sample_rule_details)

        assert "High Priority Accept" in formatted
        assert "matched" in formatted

    def test_format_rule_details_empty(self):
        """Test formatting empty rule details."""
        service = AIService()
        formatted = service._format_rule_details({})

        assert formatted == "No specific rule details available."

    def test_format_lookup_context_empty(self):
        """Test formatting empty lookup context."""
        service = AIService()
        formatted = service._format_lookup_context({})

        assert formatted == ""

    def test_format_lookup_context_with_data(self):
        """Test formatting lookup context with data."""
        service = AIService()
        lookup_results = {"asset_criticality": "High", "budget_remaining": 5000}
        formatted = service._format_lookup_context(lookup_results)

        assert "Lookup Results" in formatted
        assert "asset_criticality" in formatted
        assert "High" in formatted

    def test_fallback_justification_accepted(self, sample_row):
        """Test fallback justification for accepted decision."""
        justification = AIService.get_fallback_justification(
            "ACCEPTED",
            ["High Priority Accept"],
            sample_row,
        )

        assert "accepted" in justification.lower()
        assert "High" in justification
        assert "High Priority Accept" in justification

    def test_fallback_justification_rejected(self, sample_row):
        """Test fallback justification for rejected decision."""
        justification = AIService.get_fallback_justification(
            "REJECTED",
            ["Cost Over Budget"],
            sample_row,
        )

        assert "rejected" in justification.lower()
        assert "Cost Over Budget" in justification

    def test_fallback_justification_reconsider(self, sample_row):
        """Test fallback justification for reconsider decision."""
        justification = AIService.get_fallback_justification(
            "RECONSIDER",
            ["Borderline Priority"],
            sample_row,
        )

        assert "review" in justification.lower()

    def test_fallback_justification_no_rules(self, sample_row):
        """Test fallback justification when no rules matched."""
        justification = AIService.get_fallback_justification(
            "RECONSIDER",
            [],
            sample_row,
        )

        assert "default rules" in justification.lower()


class TestJustificationResult:
    """Tests for JustificationResult dataclass."""

    def test_create_justification_result(self):
        """Test creating a JustificationResult."""
        result = JustificationResult(
            justification="Test justification",
            confidence_score=85.0,
            provider=AIProvider.ANTHROPIC,
            model="claude-3-sonnet-20240229",
        )

        assert result.justification == "Test justification"
        assert result.confidence_score == 85.0
        assert result.provider == AIProvider.ANTHROPIC
        assert result.model == "claude-3-sonnet-20240229"
        assert result.tokens_used == 0
        assert result.error is None

    def test_create_justification_result_with_error(self):
        """Test creating a JustificationResult with error."""
        result = JustificationResult(
            justification="Fallback justification",
            confidence_score=50.0,
            provider=AIProvider.ANTHROPIC,
            model="claude-3-sonnet-20240229",
            error="API error occurred",
        )

        assert result.error == "API error occurred"


class TestAIServiceIntegration:
    """Integration tests for AI service (mocked)."""

    @patch("src.ai_service.anthropic")
    def test_generate_justification_anthropic(
        self, mock_anthropic, sample_row, sample_rule_details
    ):
        """Test justification generation with Anthropic (mocked)."""
        # Set up mock
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"justification": "Test justification", "confidence_score": 85}'
            )
        ]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        # Create service and generate
        service = AIService(api_key="test-key")
        result = service.generate_justification(
            row=sample_row,
            decision="ACCEPTED",
            matched_rules=["High Priority Accept"],
            rule_details=sample_rule_details,
        )

        assert isinstance(result, JustificationResult)
        assert result.justification == "Test justification"
        assert result.confidence_score == 85
        assert result.provider == AIProvider.ANTHROPIC
        assert result.tokens_used == 150

    @patch("src.ai_service.openai")
    def test_generate_justification_openai(
        self, mock_openai, sample_row, sample_rule_details
    ):
        """Test justification generation with OpenAI (mocked)."""
        # Set up mock
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = (
            '{"justification": "OpenAI test", "confidence_score": 90}'
        )
        mock_response.choices = [mock_choice]
        mock_response.usage.total_tokens = 120
        mock_client.chat.completions.create.return_value = mock_response

        # Create service and generate
        service = AIService(provider=AIProvider.OPENAI, api_key="test-key")
        result = service.generate_justification(
            row=sample_row,
            decision="ACCEPTED",
            matched_rules=["High Priority Accept"],
            rule_details=sample_rule_details,
        )

        assert isinstance(result, JustificationResult)
        assert result.justification == "OpenAI test"
        assert result.confidence_score == 90
        assert result.provider == AIProvider.OPENAI

    def test_generate_justification_api_error(self, sample_row, sample_rule_details):
        """Test handling of API errors."""
        service = AIService(api_key="invalid-key")

        # This should return a fallback result instead of raising
        result = service.generate_justification(
            row=sample_row,
            decision="ACCEPTED",
            matched_rules=["High Priority Accept"],
            rule_details=sample_rule_details,
        )

        assert isinstance(result, JustificationResult)
        assert result.error is not None or result.confidence_score == 50.0

    @patch("src.ai_service.anthropic")
    def test_batch_justifications(
        self, mock_anthropic, sample_row, sample_rule_details
    ):
        """Test batch justification generation."""
        # Set up mock
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"justification": "Batch test", "confidence_score": 80}'
            )
        ]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        # Create test data
        df = pd.DataFrame([sample_row.to_dict()] * 3)

        # Mock evaluation results
        from src.rules import DecisionOutcome

        mock_eval_results = []
        for _ in range(3):
            mock_eval = MagicMock()
            mock_eval.outcome = DecisionOutcome.ACCEPTED
            mock_eval.matched_rules = ["Test Rule"]
            mock_eval.rule_details = sample_rule_details
            mock_eval.lookup_results = {}
            mock_eval_results.append(mock_eval)

        # Generate batch
        service = AIService(api_key="test-key")
        results = service.generate_batch_justifications(df, mock_eval_results)

        assert len(results) == 3
        assert all(isinstance(r, JustificationResult) for r in results)


class TestPromptGeneration:
    """Tests for prompt generation."""

    def test_prompt_contains_required_elements(self, sample_row, sample_rule_details):
        """Test that generated prompt contains all required elements."""
        service = AIService()

        prompt = service.JUSTIFICATION_PROMPT_TEMPLATE.format(
            row_data=service._format_row_data(sample_row),
            decision="ACCEPTED",
            matched_rules="High Priority Accept",
            rule_details=service._format_rule_details(sample_rule_details),
            lookup_context="",
        )

        # Check required elements
        assert "Work Item Details" in prompt
        assert "Decision Context" in prompt
        assert "ACCEPTED" in prompt
        assert "Instructions" in prompt
        assert "Response Format" in prompt
        assert "Examples" in prompt
        assert "JSON" in prompt

    def test_prompt_examples_include_all_outcomes(self):
        """Test that prompt examples include all possible outcomes."""
        service = AIService()
        prompt = service.JUSTIFICATION_PROMPT_TEMPLATE

        assert "ACCEPTED" in prompt
        assert "REJECTED" in prompt
        assert "RECONSIDER" in prompt
