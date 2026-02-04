"""
AI Service for MWCS - generates justifications using Anthropic Claude or OpenAI.
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class JustificationResult:
    """Result of AI justification generation."""

    justification: str
    confidence_score: float
    provider: AIProvider
    model: str
    tokens_used: int = 0
    error: Optional[str] = None


class AIService:
    """Service for generating AI-powered justifications for maintenance decisions."""

    JUSTIFICATION_PROMPT_TEMPLATE = """You are a maintenance work categorization assistant. Analyze the following maintenance work item and provide a clear, concise justification for the categorization decision.

## Work Item Details
{row_data}

## Decision Context
- **Final Decision**: {decision}
- **Rules that matched**: {matched_rules}
- **Rule evaluation details**: {rule_details}
{lookup_context}

## Instructions
1. Provide a 2-4 sentence plain-English explanation for why this maintenance work was categorized as {decision}.
2. Focus on the key factors that influenced the decision.
3. Be specific about values and thresholds when relevant.
4. Keep the justification between 500-1000 characters.

## Response Format
Respond with ONLY a JSON object in this exact format (no markdown, no extra text):
{{"justification": "Your 2-4 sentence explanation here.", "confidence_score": 85}}

## Examples
For ACCEPTED: {{"justification": "Maintenance work accepted. Priority is High, estimated hours (12) within quarterly budget (50 available), asset criticality Medium.", "confidence_score": 92}}
For REJECTED: {{"justification": "Maintenance work rejected. Estimated cost ($5,000) exceeds remaining departmental budget ($2,000).", "confidence_score": 88}}
For RECONSIDER: {{"justification": "Requires review. Scheduled maintenance overdue (18 months), but resource availability limited to 8 hours this period.", "confidence_score": 65}}

Provide your response:"""

    def __init__(
        self,
        provider: AIProvider = AIProvider.ANTHROPIC,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize the AI service."""
        self.provider = provider
        self._api_key = api_key
        self._model = model
        self._client = None

        # Set defaults based on provider
        if self.provider == AIProvider.ANTHROPIC:
            self._default_model = "claude-3-sonnet-20240229"
        else:
            self._default_model = "gpt-4-turbo-preview"

    def _get_api_key(self) -> str:
        """Get API key from parameter or environment."""
        if self._api_key:
            return self._api_key

        if self.provider == AIProvider.ANTHROPIC:
            key = os.environ.get("ANTHROPIC_API_KEY")
        else:
            key = os.environ.get("OPENAI_API_KEY")

        if not key:
            raise ValueError(
                f"API key not found. Set {self.provider.value.upper()}_API_KEY environment variable."
            )
        return key

    def _get_model(self) -> str:
        """Get model name from parameter or environment."""
        if self._model:
            return self._model

        if self.provider == AIProvider.ANTHROPIC:
            return os.environ.get("ANTHROPIC_MODEL", self._default_model)
        else:
            return os.environ.get("OPENAI_MODEL", self._default_model)

    def _init_client(self) -> None:
        """Initialize the API client."""
        if self._client is not None:
            return

        api_key = self._get_api_key()

        if self.provider == AIProvider.ANTHROPIC:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        else:
            try:
                import openai

                self._client = openai.OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")

    def _format_row_data(self, row: pd.Series) -> str:
        """Format row data for the prompt."""
        lines = []
        for col, value in row.items():
            if pd.notna(value):
                lines.append(f"- **{col}**: {value}")
        return "\n".join(lines)

    def _format_rule_details(self, rule_details: dict[str, Any]) -> str:
        """Format rule evaluation details for the prompt."""
        if not rule_details:
            return "No specific rule details available."

        summary_lines = []
        for rule_name, details in rule_details.items():
            if "error" in details:
                summary_lines.append(f"- {rule_name}: Error - {details['error']}")
            elif "all_match" in details:
                status = "matched" if details["all_match"] else "did not match"
                summary_lines.append(f"- {rule_name}: {status}")
            elif "if_matched" in details:
                status = "IF condition met" if details["if_matched"] else "IF condition not met"
                summary_lines.append(f"- {rule_name}: {status}")

        return "\n".join(summary_lines) if summary_lines else "Rules evaluated successfully."

    def _format_lookup_context(self, lookup_results: dict[str, Any]) -> str:
        """Format lookup results for the prompt."""
        if not lookup_results:
            return ""

        lines = ["\n## Lookup Results"]
        for key, value in lookup_results.items():
            lines.append(f"- {key}: {value}")

        return "\n".join(lines)

    def generate_justification(
        self,
        row: pd.Series,
        decision: str,
        matched_rules: list[str],
        rule_details: dict[str, Any],
        lookup_results: Optional[dict[str, Any]] = None,
    ) -> JustificationResult:
        """Generate a justification for a single row's decision."""
        self._init_client()

        prompt = self.JUSTIFICATION_PROMPT_TEMPLATE.format(
            row_data=self._format_row_data(row),
            decision=decision,
            matched_rules=", ".join(matched_rules) if matched_rules else "Default rule (no specific matches)",
            rule_details=self._format_rule_details(rule_details),
            lookup_context=self._format_lookup_context(lookup_results or {}),
        )

        try:
            if self.provider == AIProvider.ANTHROPIC:
                return self._call_anthropic(prompt)
            else:
                return self._call_openai(prompt)
        except Exception as e:
            logger.error(f"AI service error: {e}")
            return JustificationResult(
                justification=f"Categorized as {decision} based on rule evaluation.",
                confidence_score=50.0,
                provider=self.provider,
                model=self._get_model(),
                error=str(e),
            )

    def _call_anthropic(self, prompt: str) -> JustificationResult:
        """Call Anthropic Claude API."""
        import json

        model = self._get_model()

        response = self._client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        # Parse JSON response
        try:
            result = json.loads(content)
            justification = result.get("justification", content)
            confidence = float(result.get("confidence_score", 70))
        except json.JSONDecodeError:
            # If not valid JSON, use the raw content
            justification = content
            confidence = 70.0

        return JustificationResult(
            justification=justification,
            confidence_score=confidence,
            provider=AIProvider.ANTHROPIC,
            model=model,
            tokens_used=tokens_used,
        )

    def _call_openai(self, prompt: str) -> JustificationResult:
        """Call OpenAI API."""
        import json

        model = self._get_model()

        response = self._client.chat.completions.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        # Parse JSON response
        try:
            result = json.loads(content)
            justification = result.get("justification", content)
            confidence = float(result.get("confidence_score", 70))
        except json.JSONDecodeError:
            justification = content
            confidence = 70.0

        return JustificationResult(
            justification=justification,
            confidence_score=confidence,
            provider=AIProvider.OPENAI,
            model=model,
            tokens_used=tokens_used,
        )

    def generate_batch_justifications(
        self,
        df: pd.DataFrame,
        evaluation_results: list,
        progress_callback: Optional[callable] = None,
    ) -> list[JustificationResult]:
        """Generate justifications for a batch of rows."""
        results = []
        total = len(df)

        for idx, (row_idx, row) in enumerate(df.iterrows()):
            eval_result = evaluation_results[idx]

            result = self.generate_justification(
                row=row,
                decision=eval_result.outcome.value,
                matched_rules=eval_result.matched_rules,
                rule_details=eval_result.rule_details,
                lookup_results=eval_result.lookup_results,
            )
            results.append(result)

            if progress_callback and idx % 10 == 0:
                progress_callback(idx + 1, total)

        return results

    def test_connection(self) -> bool:
        """Test the API connection."""
        try:
            self._init_client()

            if self.provider == AIProvider.ANTHROPIC:
                response = self._client.messages.create(
                    model=self._get_model(),
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Test"}],
                )
                return response is not None
            else:
                response = self._client.chat.completions.create(
                    model=self._get_model(),
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Test"}],
                )
                return response is not None

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    @staticmethod
    def get_fallback_justification(
        decision: str,
        matched_rules: list[str],
        row: pd.Series,
    ) -> str:
        """Generate a simple fallback justification without AI."""
        if not matched_rules:
            return f"Work item categorized as {decision} based on default rules."

        # Extract key fields for justification
        priority = row.get("Priority", "Unknown")
        category = row.get("Category", "Unknown")
        hours = row.get("Estimated Hours", "Unknown")

        if decision == "ACCEPTED":
            return (
                f"Maintenance work accepted. Priority is {priority}, "
                f"category is {category}, estimated hours: {hours}. "
                f"Matched rules: {', '.join(matched_rules[:3])}."
            )
        elif decision == "REJECTED":
            return (
                f"Maintenance work rejected. Priority is {priority}, "
                f"category is {category}. "
                f"Matched rejection rules: {', '.join(matched_rules[:3])}."
            )
        else:
            return (
                f"Requires review. Priority is {priority}, "
                f"category is {category}. "
                f"Further evaluation needed based on: {', '.join(matched_rules[:3])}."
            )
