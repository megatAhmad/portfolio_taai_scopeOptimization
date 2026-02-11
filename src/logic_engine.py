"""
Logic Engine for MWCS - evaluates rules against data rows.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional, Union

import numpy as np
import pandas as pd
from dateutil import parser as date_parser

from .rules import (
    ConditionalRule,
    DecisionOutcome,
    LogicalOperator,
    Rule,
    RuleCondition,
    RuleGroup,
    RuleSet,
    RuleType,
)

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of evaluating a single row."""

    outcome: DecisionOutcome
    score: float  # 0-100
    matched_rules: list[str] = field(default_factory=list)
    rule_details: dict[str, Any] = field(default_factory=dict)
    lookup_results: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchEvaluationResult:
    """Result of evaluating multiple rows."""

    results: list[EvaluationResult]
    total_rows: int
    accepted_count: int
    rejected_count: int
    reconsider_count: int
    processing_time_ms: float
    errors: list[str] = field(default_factory=list)


class LogicEngine:
    """Evaluates rules against data rows to produce categorization decisions."""

    def __init__(self, ruleset: Optional[RuleSet] = None):
        """Initialize the logic engine with an optional ruleset."""
        self._ruleset = ruleset
        self._supporting_data: dict[str, pd.DataFrame] = {}

    @property
    def ruleset(self) -> Optional[RuleSet]:
        """Get the current ruleset."""
        return self._ruleset

    @ruleset.setter
    def ruleset(self, value: RuleSet) -> None:
        """Set the current ruleset."""
        self._ruleset = value

    def set_supporting_data(self, data: dict[str, pd.DataFrame]) -> None:
        """Set supporting datasets for lookup operations."""
        self._supporting_data = data
        logger.info(f"Set {len(data)} supporting datasets")

    def evaluate_row(self, row: pd.Series) -> EvaluationResult:
        """Evaluate a single row against the ruleset."""
        if self._ruleset is None:
            raise ValueError("No ruleset configured. Set a ruleset before evaluation.")

        matched_rules = []
        rule_details = {}
        lookup_results = {}
        outcome = self._ruleset.default_outcome
        highest_priority = -1

        # Sort rules by priority (highest first)
        sorted_rules = sorted(
            [r for r in self._ruleset.rules if r.enabled],
            key=lambda r: r.priority,
            reverse=True,
        )

        for rule in sorted_rules:
            try:
                if isinstance(rule, ConditionalRule):
                    match, details = self._evaluate_conditional_rule(rule, row)
                else:
                    match, details = self._evaluate_rule(rule, row)

                rule_details[rule.name] = details

                if match and rule.priority > highest_priority:
                    outcome = rule.outcome if isinstance(rule, Rule) else details.get("outcome", outcome)
                    highest_priority = rule.priority
                    matched_rules.append(rule.name)

                # Collect lookup results
                if "lookup_results" in details:
                    lookup_results.update(details["lookup_results"])

            except Exception as e:
                logger.warning(f"Error evaluating rule '{rule.name}': {e}")
                rule_details[rule.name] = {"error": str(e)}

        # Calculate confidence score based on matching rules
        score = self._calculate_confidence(matched_rules, rule_details, outcome)

        return EvaluationResult(
            outcome=outcome,
            score=score,
            matched_rules=matched_rules,
            rule_details=rule_details,
            lookup_results=lookup_results,
        )

    def evaluate_batch(
        self,
        df: pd.DataFrame,
        progress_callback: Optional[callable] = None,
    ) -> BatchEvaluationResult:
        """Evaluate all rows in a DataFrame."""
        import time

        start_time = time.time()
        results = []
        errors = []
        accepted = 0
        rejected = 0
        reconsider = 0

        total_rows = len(df)

        for idx, row in df.iterrows():
            try:
                result = self.evaluate_row(row)
                results.append(result)

                if result.outcome == DecisionOutcome.ACCEPTED:
                    accepted += 1
                elif result.outcome == DecisionOutcome.REJECTED:
                    rejected += 1
                else:
                    reconsider += 1

                if progress_callback and idx % 100 == 0:
                    progress_callback(idx + 1, total_rows)

            except Exception as e:
                logger.error(f"Error evaluating row {idx}: {e}")
                errors.append(f"Row {idx}: {str(e)}")
                # Add default result for failed row
                results.append(
                    EvaluationResult(
                        outcome=DecisionOutcome.RECONSIDER,
                        score=0,
                        matched_rules=[],
                        rule_details={"error": str(e)},
                    )
                )
                reconsider += 1

        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000

        return BatchEvaluationResult(
            results=results,
            total_rows=total_rows,
            accepted_count=accepted,
            rejected_count=rejected,
            reconsider_count=reconsider,
            processing_time_ms=processing_time_ms,
            errors=errors,
        )

    def _evaluate_rule(self, rule: Rule, row: pd.Series) -> tuple[bool, dict]:
        """Evaluate a simple rule against a row."""
        details = {"conditions_evaluated": [], "all_match": True}

        for condition in rule.conditions:
            if isinstance(condition, RuleGroup):
                match, group_details = self._evaluate_group(condition, row)
                details["conditions_evaluated"].append(group_details)
            else:
                match = self._evaluate_condition(condition, row)
                details["conditions_evaluated"].append(
                    {"condition": condition.to_dict(), "match": match}
                )

            if not match:
                details["all_match"] = False
                break

        return details["all_match"], details

    def _evaluate_conditional_rule(
        self, rule: ConditionalRule, row: pd.Series
    ) -> tuple[bool, dict]:
        """Evaluate a conditional (IF-THEN-ELSE) rule."""
        details = {"type": "conditional", "if_matched": False}

        # Evaluate IF conditions
        if_match, if_details = self._evaluate_group(rule.if_conditions, row)
        details["if_conditions"] = if_details

        if if_match:
            details["if_matched"] = True
            details["outcome"] = rule.then_outcome
            return True, details
        elif rule.else_rule:
            # Evaluate nested ELSE rule
            return self._evaluate_conditional_rule(rule.else_rule, row)
        elif rule.else_outcome:
            details["outcome"] = rule.else_outcome
            return True, details

        return False, details

    def _evaluate_group(self, group: RuleGroup, row: pd.Series) -> tuple[bool, dict]:
        """Evaluate a group of conditions with logical operators."""
        details = {"operator": group.operator.value, "conditions": []}
        results = []

        for condition in group.conditions:
            if isinstance(condition, RuleGroup):
                match, sub_details = self._evaluate_group(condition, row)
                details["conditions"].append(sub_details)
            else:
                match = self._evaluate_condition(condition, row)
                details["conditions"].append(
                    {"condition": condition.to_dict(), "match": match}
                )
            results.append(match)

        if group.operator == LogicalOperator.AND:
            final_match = all(results)
        elif group.operator == LogicalOperator.OR:
            final_match = any(results)
        elif group.operator == LogicalOperator.NOT:
            final_match = not any(results)
        else:
            final_match = all(results)

        details["match"] = final_match
        return final_match, details

    def _evaluate_condition(self, condition: RuleCondition, row: pd.Series) -> bool:
        """Evaluate a single condition against a row."""
        # Get the field value from the row (case-insensitive)
        field_value = None
        for col in row.index:
            if col.lower() == condition.field.lower():
                field_value = row[col]
                break

        if field_value is None or pd.isna(field_value):
            return False

        rule_type = condition.rule_type
        if isinstance(rule_type, str):
            rule_type = RuleType(rule_type)

        if rule_type == RuleType.NUMERIC:
            return self._evaluate_numeric(field_value, condition)
        elif rule_type == RuleType.TEXT:
            return self._evaluate_text(field_value, condition)
        elif rule_type == RuleType.DATE:
            return self._evaluate_date(field_value, condition)
        elif rule_type == RuleType.LOOKUP:
            return self._evaluate_lookup(field_value, condition, row)
        elif rule_type == RuleType.AGGREGATION:
            return self._evaluate_aggregation(field_value, condition, row)
        else:
            logger.warning(f"Unknown rule type: {rule_type}")
            return False

    def _evaluate_numeric(self, value: Any, condition: RuleCondition) -> bool:
        """Evaluate a numeric condition."""
        try:
            num_value = float(value)
            target_value = float(condition.value)
        except (ValueError, TypeError):
            return False

        operator = condition.operator
        if operator in (">", "gt", "greater_than"):
            return num_value > target_value
        elif operator in ("<", "lt", "less_than"):
            return num_value < target_value
        elif operator in ("=", "==", "eq", "equal"):
            return num_value == target_value
        elif operator in (">=", "gte", "greater_equal"):
            return num_value >= target_value
        elif operator in ("<=", "lte", "less_equal"):
            return num_value <= target_value
        elif operator == "between":
            if condition.value_end is None:
                return False
            end_value = float(condition.value_end)
            return target_value <= num_value <= end_value
        else:
            logger.warning(f"Unknown numeric operator: {operator}")
            return False

    def _evaluate_text(self, value: Any, condition: RuleCondition) -> bool:
        """Evaluate a text condition."""
        str_value = str(value).lower()
        target_value = str(condition.value).lower()

        operator = condition.operator
        if operator in ("contains", "in"):
            return target_value in str_value
        elif operator in ("exact_match", "equals", "=="):
            return str_value == target_value
        elif operator == "regex":
            try:
                return bool(re.search(condition.value, str(value)))
            except re.error:
                return False
        elif operator in ("starts_with", "startswith"):
            return str_value.startswith(target_value)
        elif operator in ("ends_with", "endswith"):
            return str_value.endswith(target_value)
        else:
            logger.warning(f"Unknown text operator: {operator}")
            return False

    def _evaluate_date(self, value: Any, condition: RuleCondition) -> bool:
        """Evaluate a date condition."""
        try:
            if isinstance(value, (datetime, pd.Timestamp)):
                date_value = value
            else:
                date_value = date_parser.parse(str(value))
        except (ValueError, TypeError):
            return False

        operator = condition.operator
        target = condition.value

        if operator == "before":
            try:
                target_date = date_parser.parse(str(target))
                return date_value < target_date
            except (ValueError, TypeError):
                return False

        elif operator == "after":
            try:
                target_date = date_parser.parse(str(target))
                return date_value > target_date
            except (ValueError, TypeError):
                return False

        elif operator == "within_range":
            try:
                start_date = date_parser.parse(str(target))
                end_date = date_parser.parse(str(condition.value_end))
                return start_date <= date_value <= end_date
            except (ValueError, TypeError):
                return False

        elif operator == "within_days":
            try:
                days = int(target)
                now = datetime.now()
                if days < 0:
                    # Negative days means "more than X days ago"
                    threshold = now + timedelta(days=days)
                    return date_value < threshold
                else:
                    threshold = now - timedelta(days=days)
                    return date_value >= threshold
            except (ValueError, TypeError):
                return False

        else:
            logger.warning(f"Unknown date operator: {operator}")
            return False

    def _evaluate_lookup(
        self, value: Any, condition: RuleCondition, row: pd.Series
    ) -> bool:
        """Evaluate a lookup condition against supporting data."""
        if condition.lookup_dataset not in self._supporting_data:
            logger.warning(f"Lookup dataset not found: {condition.lookup_dataset}")
            return False

        lookup_df = self._supporting_data[condition.lookup_dataset]
        lookup_field = condition.lookup_field or condition.field

        operator = condition.operator
        if operator == "match":
            # Check if value exists in the lookup dataset
            if lookup_field not in lookup_df.columns:
                return False
            return value in lookup_df[lookup_field].values

        elif operator == "join":
            # Join and check condition on joined value
            if lookup_field not in lookup_df.columns:
                return False
            matches = lookup_df[lookup_df[lookup_field] == value]
            if matches.empty:
                return False
            # If a target field is specified in value, check it
            if isinstance(condition.value, dict):
                target_field = condition.value.get("field")
                target_value = condition.value.get("value")
                if target_field and target_field in matches.columns:
                    return matches[target_field].iloc[0] == target_value
            return True

        else:
            logger.warning(f"Unknown lookup operator: {operator}")
            return False

    def _evaluate_aggregation(
        self, value: Any, condition: RuleCondition, row: pd.Series
    ) -> bool:
        """Evaluate an aggregation condition."""
        if condition.lookup_dataset not in self._supporting_data:
            logger.warning(f"Aggregation dataset not found: {condition.lookup_dataset}")
            return False

        agg_df = self._supporting_data[condition.lookup_dataset]
        agg_field = condition.lookup_field or condition.field

        if agg_field not in agg_df.columns:
            return False

        operator = condition.operator
        try:
            if operator == "sum":
                agg_value = agg_df[agg_field].sum()
            elif operator == "avg":
                agg_value = agg_df[agg_field].mean()
            elif operator == "count":
                agg_value = len(agg_df)
            elif operator == "min":
                agg_value = agg_df[agg_field].min()
            elif operator == "max":
                agg_value = agg_df[agg_field].max()
            else:
                logger.warning(f"Unknown aggregation operator: {operator}")
                return False

            # Compare aggregated value against threshold
            threshold = float(condition.value)
            return float(value) <= agg_value - threshold

        except (ValueError, TypeError) as e:
            logger.warning(f"Aggregation error: {e}")
            return False

    def _calculate_confidence(
        self,
        matched_rules: list[str],
        rule_details: dict[str, Any],
        outcome: DecisionOutcome,
    ) -> float:
        """Calculate confidence score based on evaluation results."""
        if not matched_rules:
            # No rules matched, low confidence
            return 40.0

        # Base confidence from number of matched rules
        base_confidence = min(60 + len(matched_rules) * 10, 85)

        # Adjust based on outcome clarity
        if outcome in (DecisionOutcome.ACCEPTED, DecisionOutcome.REJECTED):
            # Clear outcomes get higher confidence
            base_confidence += 10
        else:
            # Reconsider outcome indicates uncertainty
            base_confidence -= 10

        # Check for any errors in evaluation
        error_count = sum(1 for d in rule_details.values() if "error" in d)
        if error_count > 0:
            base_confidence -= error_count * 5

        # Ensure confidence is within bounds
        return max(0, min(100, base_confidence))

    def get_evaluation_summary(
        self, batch_result: BatchEvaluationResult
    ) -> dict[str, Any]:
        """Get a summary of batch evaluation results."""
        return {
            "total_rows": batch_result.total_rows,
            "accepted": {
                "count": batch_result.accepted_count,
                "percentage": (
                    batch_result.accepted_count / batch_result.total_rows * 100
                    if batch_result.total_rows > 0
                    else 0
                ),
            },
            "rejected": {
                "count": batch_result.rejected_count,
                "percentage": (
                    batch_result.rejected_count / batch_result.total_rows * 100
                    if batch_result.total_rows > 0
                    else 0
                ),
            },
            "reconsider": {
                "count": batch_result.reconsider_count,
                "percentage": (
                    batch_result.reconsider_count / batch_result.total_rows * 100
                    if batch_result.total_rows > 0
                    else 0
                ),
            },
            "processing_time_ms": batch_result.processing_time_ms,
            "avg_time_per_row_ms": (
                batch_result.processing_time_ms / batch_result.total_rows
                if batch_result.total_rows > 0
                else 0
            ),
            "error_count": len(batch_result.errors),
            "confidence_distribution": self._get_confidence_distribution(
                batch_result.results
            ),
        }

    def _get_confidence_distribution(
        self, results: list[EvaluationResult]
    ) -> dict[str, int]:
        """Get distribution of confidence scores by band."""
        distribution = {"high": 0, "medium": 0, "low": 0, "very_low": 0}

        for result in results:
            if result.score >= 85:
                distribution["high"] += 1
            elif result.score >= 60:
                distribution["medium"] += 1
            elif result.score >= 40:
                distribution["low"] += 1
            else:
                distribution["very_low"] += 1

        return distribution
