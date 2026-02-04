"""
Unit tests for the Logic Engine module.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from src.logic_engine import LogicEngine, EvaluationResult, BatchEvaluationResult
from src.rules import (
    DecisionOutcome,
    LogicalOperator,
    NumericOperator,
    Rule,
    RuleCondition,
    RuleGroup,
    RuleSet,
    RuleType,
    TextOperator,
    ConditionalRule,
)


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
            "Last Service Date": (datetime.now() - timedelta(days=400)).strftime(
                "%Y-%m-%d"
            ),
            "Asset ID": "AST-1234",
            "Location": "Building A - Floor 1",
            "Cost Estimate": 3500.00,
            "Risk Level": "Medium",
        }
    )


@pytest.fixture
def sample_dataframe(sample_row):
    """Create a sample DataFrame for testing."""
    rows = []
    for i in range(5):
        row = sample_row.copy()
        row["Work ID"] = f"WO-{i+1:05d}"
        row["Priority"] = ["High", "Medium", "Low", "High", "Medium"][i]
        row["Cost Estimate"] = [3500, 1500, 8000, 2000, 12000][i]
        rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture
def simple_ruleset():
    """Create a simple ruleset for testing."""
    return RuleSet(
        name="Test Ruleset",
        rules=[
            Rule(
                name="High Priority Accept",
                conditions=[
                    RuleCondition(
                        field="Priority",
                        rule_type=RuleType.TEXT,
                        operator="exact_match",
                        value="High",
                    )
                ],
                outcome=DecisionOutcome.ACCEPTED,
                priority=100,
            ),
            Rule(
                name="Low Priority Reject",
                conditions=[
                    RuleCondition(
                        field="Priority",
                        rule_type=RuleType.TEXT,
                        operator="exact_match",
                        value="Low",
                    )
                ],
                outcome=DecisionOutcome.REJECTED,
                priority=50,
            ),
        ],
        default_outcome=DecisionOutcome.RECONSIDER,
    )


@pytest.fixture
def numeric_ruleset():
    """Create a ruleset with numeric conditions."""
    return RuleSet(
        name="Numeric Test Ruleset",
        rules=[
            Rule(
                name="Cost Over 5000 Reject",
                conditions=[
                    RuleCondition(
                        field="Cost Estimate",
                        rule_type=RuleType.NUMERIC,
                        operator=">",
                        value=5000,
                    )
                ],
                outcome=DecisionOutcome.REJECTED,
                priority=80,
            ),
            Rule(
                name="Cost Under 2000 Accept",
                conditions=[
                    RuleCondition(
                        field="Cost Estimate",
                        rule_type=RuleType.NUMERIC,
                        operator="<",
                        value=2000,
                    )
                ],
                outcome=DecisionOutcome.ACCEPTED,
                priority=70,
            ),
        ],
        default_outcome=DecisionOutcome.RECONSIDER,
    )


class TestLogicEngine:
    """Tests for LogicEngine class."""

    def test_init_without_ruleset(self):
        """Test initialization without a ruleset."""
        engine = LogicEngine()
        assert engine.ruleset is None

    def test_init_with_ruleset(self, simple_ruleset):
        """Test initialization with a ruleset."""
        engine = LogicEngine(simple_ruleset)
        assert engine.ruleset == simple_ruleset

    def test_set_ruleset(self, simple_ruleset):
        """Test setting a ruleset."""
        engine = LogicEngine()
        engine.ruleset = simple_ruleset
        assert engine.ruleset == simple_ruleset

    def test_evaluate_without_ruleset(self, sample_row):
        """Test evaluation without a ruleset raises error."""
        engine = LogicEngine()
        with pytest.raises(ValueError, match="No ruleset configured"):
            engine.evaluate_row(sample_row)

    def test_evaluate_high_priority_row(self, simple_ruleset, sample_row):
        """Test evaluation of a high priority row."""
        engine = LogicEngine(simple_ruleset)
        result = engine.evaluate_row(sample_row)

        assert isinstance(result, EvaluationResult)
        assert result.outcome == DecisionOutcome.ACCEPTED
        assert "High Priority Accept" in result.matched_rules

    def test_evaluate_low_priority_row(self, simple_ruleset):
        """Test evaluation of a low priority row."""
        engine = LogicEngine(simple_ruleset)
        row = pd.Series(
            {
                "Work ID": "WO-00002",
                "Priority": "Low",
                "Category": "Inspection",
                "Estimated Hours": 2,
            }
        )
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.REJECTED
        assert "Low Priority Reject" in result.matched_rules

    def test_evaluate_medium_priority_row(self, simple_ruleset):
        """Test evaluation falls back to default for medium priority."""
        engine = LogicEngine(simple_ruleset)
        row = pd.Series(
            {
                "Work ID": "WO-00003",
                "Priority": "Medium",
                "Category": "Maintenance",
                "Estimated Hours": 5,
            }
        )
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.RECONSIDER
        assert len(result.matched_rules) == 0

    def test_numeric_comparison_greater_than(self, numeric_ruleset):
        """Test numeric greater than comparison."""
        engine = LogicEngine(numeric_ruleset)
        row = pd.Series(
            {
                "Work ID": "WO-00004",
                "Priority": "High",
                "Cost Estimate": 6000,
            }
        )
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.REJECTED
        assert "Cost Over 5000 Reject" in result.matched_rules

    def test_numeric_comparison_less_than(self, numeric_ruleset):
        """Test numeric less than comparison."""
        engine = LogicEngine(numeric_ruleset)
        row = pd.Series(
            {
                "Work ID": "WO-00005",
                "Priority": "Low",
                "Cost Estimate": 1500,
            }
        )
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.ACCEPTED
        assert "Cost Under 2000 Accept" in result.matched_rules

    def test_batch_evaluation(self, simple_ruleset, sample_dataframe):
        """Test batch evaluation of multiple rows."""
        engine = LogicEngine(simple_ruleset)
        result = engine.evaluate_batch(sample_dataframe)

        assert isinstance(result, BatchEvaluationResult)
        assert result.total_rows == 5
        assert len(result.results) == 5
        assert result.accepted_count + result.rejected_count + result.reconsider_count == 5

    def test_confidence_score_range(self, simple_ruleset, sample_row):
        """Test that confidence scores are within valid range."""
        engine = LogicEngine(simple_ruleset)
        result = engine.evaluate_row(sample_row)

        assert 0 <= result.score <= 100

    def test_case_insensitive_field_matching(self, simple_ruleset):
        """Test that field matching is case-insensitive."""
        engine = LogicEngine(simple_ruleset)
        row = pd.Series(
            {
                "work id": "WO-00006",  # lowercase
                "PRIORITY": "High",  # uppercase
                "category": "Test",
            }
        )
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.ACCEPTED

    def test_null_value_handling(self, simple_ruleset):
        """Test handling of null/missing values."""
        engine = LogicEngine(simple_ruleset)
        row = pd.Series(
            {
                "Work ID": "WO-00007",
                "Priority": None,  # null value
                "Category": "Test",
            }
        )
        result = engine.evaluate_row(row)

        # Should fall back to default since Priority is null
        assert result.outcome == DecisionOutcome.RECONSIDER

    def test_evaluation_summary(self, simple_ruleset, sample_dataframe):
        """Test evaluation summary generation."""
        engine = LogicEngine(simple_ruleset)
        batch_result = engine.evaluate_batch(sample_dataframe)
        summary = engine.get_evaluation_summary(batch_result)

        assert "total_rows" in summary
        assert "accepted" in summary
        assert "rejected" in summary
        assert "reconsider" in summary
        assert "processing_time_ms" in summary
        assert "confidence_distribution" in summary


class TestRuleGroups:
    """Tests for rule groups with logical operators."""

    def test_and_group_all_match(self):
        """Test AND group where all conditions match."""
        ruleset = RuleSet(
            name="AND Test",
            rules=[
                Rule(
                    name="AND Rule",
                    conditions=[
                        RuleGroup(
                            conditions=[
                                RuleCondition(
                                    field="Priority",
                                    rule_type=RuleType.TEXT,
                                    operator="exact_match",
                                    value="High",
                                ),
                                RuleCondition(
                                    field="Cost Estimate",
                                    rule_type=RuleType.NUMERIC,
                                    operator="<",
                                    value=5000,
                                ),
                            ],
                            operator=LogicalOperator.AND,
                        )
                    ],
                    outcome=DecisionOutcome.ACCEPTED,
                    priority=100,
                )
            ],
        )

        engine = LogicEngine(ruleset)
        row = pd.Series({"Priority": "High", "Cost Estimate": 3000})
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.ACCEPTED

    def test_and_group_partial_match(self):
        """Test AND group where not all conditions match."""
        ruleset = RuleSet(
            name="AND Test",
            rules=[
                Rule(
                    name="AND Rule",
                    conditions=[
                        RuleGroup(
                            conditions=[
                                RuleCondition(
                                    field="Priority",
                                    rule_type=RuleType.TEXT,
                                    operator="exact_match",
                                    value="High",
                                ),
                                RuleCondition(
                                    field="Cost Estimate",
                                    rule_type=RuleType.NUMERIC,
                                    operator="<",
                                    value=5000,
                                ),
                            ],
                            operator=LogicalOperator.AND,
                        )
                    ],
                    outcome=DecisionOutcome.ACCEPTED,
                    priority=100,
                )
            ],
            default_outcome=DecisionOutcome.REJECTED,
        )

        engine = LogicEngine(ruleset)
        row = pd.Series({"Priority": "High", "Cost Estimate": 6000})  # Cost too high
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.REJECTED

    def test_or_group_one_match(self):
        """Test OR group where one condition matches."""
        ruleset = RuleSet(
            name="OR Test",
            rules=[
                Rule(
                    name="OR Rule",
                    conditions=[
                        RuleGroup(
                            conditions=[
                                RuleCondition(
                                    field="Priority",
                                    rule_type=RuleType.TEXT,
                                    operator="exact_match",
                                    value="High",
                                ),
                                RuleCondition(
                                    field="Priority",
                                    rule_type=RuleType.TEXT,
                                    operator="exact_match",
                                    value="Critical",
                                ),
                            ],
                            operator=LogicalOperator.OR,
                        )
                    ],
                    outcome=DecisionOutcome.ACCEPTED,
                    priority=100,
                )
            ],
        )

        engine = LogicEngine(ruleset)
        row = pd.Series({"Priority": "High", "Cost Estimate": 3000})
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.ACCEPTED


class TestConditionalRules:
    """Tests for conditional IF-THEN-ELSE rules."""

    def test_conditional_if_matches(self):
        """Test conditional rule where IF condition matches."""
        ruleset = RuleSet(
            name="Conditional Test",
            rules=[
                ConditionalRule(
                    name="Priority Check",
                    if_conditions=RuleGroup(
                        conditions=[
                            RuleCondition(
                                field="Priority",
                                rule_type=RuleType.TEXT,
                                operator="exact_match",
                                value="High",
                            )
                        ]
                    ),
                    then_outcome=DecisionOutcome.ACCEPTED,
                    else_outcome=DecisionOutcome.REJECTED,
                    priority=100,
                )
            ],
        )

        engine = LogicEngine(ruleset)
        row = pd.Series({"Priority": "High", "Cost Estimate": 3000})
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.ACCEPTED

    def test_conditional_else_branch(self):
        """Test conditional rule where ELSE branch is taken."""
        ruleset = RuleSet(
            name="Conditional Test",
            rules=[
                ConditionalRule(
                    name="Priority Check",
                    if_conditions=RuleGroup(
                        conditions=[
                            RuleCondition(
                                field="Priority",
                                rule_type=RuleType.TEXT,
                                operator="exact_match",
                                value="High",
                            )
                        ]
                    ),
                    then_outcome=DecisionOutcome.ACCEPTED,
                    else_outcome=DecisionOutcome.REJECTED,
                    priority=100,
                )
            ],
        )

        engine = LogicEngine(ruleset)
        row = pd.Series({"Priority": "Low", "Cost Estimate": 3000})
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.REJECTED


class TestTextOperators:
    """Tests for text operators."""

    def test_contains_operator(self):
        """Test contains operator."""
        ruleset = RuleSet(
            name="Text Test",
            rules=[
                Rule(
                    name="Contains Test",
                    conditions=[
                        RuleCondition(
                            field="Description",
                            rule_type=RuleType.TEXT,
                            operator="contains",
                            value="emergency",
                        )
                    ],
                    outcome=DecisionOutcome.ACCEPTED,
                    priority=100,
                )
            ],
        )

        engine = LogicEngine(ruleset)
        row = pd.Series({"Description": "Emergency repair needed"})
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.ACCEPTED

    def test_starts_with_operator(self):
        """Test starts_with operator."""
        ruleset = RuleSet(
            name="Text Test",
            rules=[
                Rule(
                    name="Starts With Test",
                    conditions=[
                        RuleCondition(
                            field="Work ID",
                            rule_type=RuleType.TEXT,
                            operator="starts_with",
                            value="WO-",
                        )
                    ],
                    outcome=DecisionOutcome.ACCEPTED,
                    priority=100,
                )
            ],
        )

        engine = LogicEngine(ruleset)
        row = pd.Series({"Work ID": "WO-00001"})
        result = engine.evaluate_row(row)

        assert result.outcome == DecisionOutcome.ACCEPTED
