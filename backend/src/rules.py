"""
Rules module for MWCS - handles rule building, serialization, and template management.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    """Types of rules supported by the logic engine."""

    NUMERIC = "numeric"
    TEXT = "text"
    DATE = "date"
    LOOKUP = "lookup"
    AGGREGATION = "aggregation"
    CONDITIONAL = "conditional"
    BUSINESS = "business"


class NumericOperator(str, Enum):
    """Operators for numeric comparisons."""

    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUAL = "="
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    BETWEEN = "between"


class TextOperator(str, Enum):
    """Operators for text comparisons."""

    CONTAINS = "contains"
    EXACT_MATCH = "exact_match"
    REGEX = "regex"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class DateOperator(str, Enum):
    """Operators for date comparisons."""

    BEFORE = "before"
    AFTER = "after"
    WITHIN_RANGE = "within_range"
    WITHIN_DAYS = "within_days"


class LookupOperator(str, Enum):
    """Operators for lookup operations."""

    MATCH = "match"
    JOIN = "join"


class AggregationOperator(str, Enum):
    """Operators for aggregation operations."""

    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    MIN = "min"
    MAX = "max"


class LogicalOperator(str, Enum):
    """Logical operators for combining conditions."""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class DecisionOutcome(str, Enum):
    """Possible outcomes of rule evaluation."""

    ACCEPTED = "ACCEPTED"
    RECONSIDER = "RECONSIDER"
    REJECTED = "REJECTED"


@dataclass
class RuleCondition:
    """A single condition within a rule."""

    field: str
    rule_type: RuleType
    operator: str
    value: Any
    value_end: Optional[Any] = None  # For range operations
    lookup_dataset: Optional[str] = None  # For lookup operations
    lookup_field: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "field": self.field,
            "rule_type": self.rule_type.value if isinstance(self.rule_type, RuleType) else self.rule_type,
            "operator": self.operator.value if isinstance(self.operator, Enum) else self.operator,
            "value": self.value,
            "value_end": self.value_end,
            "lookup_dataset": self.lookup_dataset,
            "lookup_field": self.lookup_field,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RuleCondition":
        """Create from dictionary."""
        return cls(
            field=data["field"],
            rule_type=RuleType(data["rule_type"]),
            operator=data["operator"],
            value=data["value"],
            value_end=data.get("value_end"),
            lookup_dataset=data.get("lookup_dataset"),
            lookup_field=data.get("lookup_field"),
        )


@dataclass
class Rule:
    """A rule with conditions and outcome."""

    name: str
    conditions: list[Union[RuleCondition, "RuleGroup"]]
    outcome: DecisionOutcome
    priority: int = 0
    description: str = ""
    enabled: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "conditions": [
                c.to_dict() if hasattr(c, "to_dict") else c for c in self.conditions
            ],
            "outcome": self.outcome.value if isinstance(self.outcome, DecisionOutcome) else self.outcome,
            "priority": self.priority,
            "description": self.description,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Rule":
        """Create from dictionary."""
        conditions = []
        for c in data.get("conditions", []):
            if "conditions" in c:  # It's a RuleGroup
                conditions.append(RuleGroup.from_dict(c))
            else:
                conditions.append(RuleCondition.from_dict(c))

        return cls(
            name=data["name"],
            conditions=conditions,
            outcome=DecisionOutcome(data["outcome"]),
            priority=data.get("priority", 0),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
        )


@dataclass
class RuleGroup:
    """A group of conditions combined with a logical operator."""

    conditions: list[Union[RuleCondition, "RuleGroup"]]
    operator: LogicalOperator = LogicalOperator.AND

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "conditions": [
                c.to_dict() if hasattr(c, "to_dict") else c for c in self.conditions
            ],
            "operator": self.operator.value if isinstance(self.operator, LogicalOperator) else self.operator,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RuleGroup":
        """Create from dictionary."""
        conditions = []
        for c in data.get("conditions", []):
            if "conditions" in c and "operator" in c and "name" not in c:
                conditions.append(RuleGroup.from_dict(c))
            elif "field" in c:
                conditions.append(RuleCondition.from_dict(c))

        return cls(
            conditions=conditions,
            operator=LogicalOperator(data.get("operator", "AND")),
        )


@dataclass
class ConditionalRule:
    """IF-THEN-ELSE rule structure."""

    name: str
    if_conditions: RuleGroup
    then_outcome: DecisionOutcome
    else_outcome: Optional[DecisionOutcome] = None
    else_rule: Optional["ConditionalRule"] = None  # For chained IF-THEN-ELSE
    priority: int = 0
    description: str = ""
    enabled: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "type": "conditional",
            "if_conditions": self.if_conditions.to_dict(),
            "then_outcome": self.then_outcome.value,
            "else_outcome": self.else_outcome.value if self.else_outcome else None,
            "else_rule": self.else_rule.to_dict() if self.else_rule else None,
            "priority": self.priority,
            "description": self.description,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConditionalRule":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            if_conditions=RuleGroup.from_dict(data["if_conditions"]),
            then_outcome=DecisionOutcome(data["then_outcome"]),
            else_outcome=DecisionOutcome(data["else_outcome"]) if data.get("else_outcome") else None,
            else_rule=ConditionalRule.from_dict(data["else_rule"]) if data.get("else_rule") else None,
            priority=data.get("priority", 0),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
        )


@dataclass
class RuleSet:
    """A complete set of rules for evaluation."""

    name: str
    rules: list[Union[Rule, ConditionalRule]] = field(default_factory=list)
    version: str = "1.0"
    description: str = ""
    default_outcome: DecisionOutcome = DecisionOutcome.RECONSIDER

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "rules": [r.to_dict() for r in self.rules],
            "version": self.version,
            "description": self.description,
            "default_outcome": self.default_outcome.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RuleSet":
        """Create from dictionary."""
        rules = []
        for r in data.get("rules", []):
            if r.get("type") == "conditional":
                rules.append(ConditionalRule.from_dict(r))
            else:
                rules.append(Rule.from_dict(r))

        return cls(
            name=data["name"],
            rules=rules,
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            default_outcome=DecisionOutcome(data.get("default_outcome", "RECONSIDER")),
        )


class RuleBuilder:
    """Builder class for creating and managing rules."""

    def __init__(self, templates_dir: str = "templates"):
        """Initialize the rule builder."""
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
        self._current_ruleset: Optional[RuleSet] = None

    @property
    def current_ruleset(self) -> Optional[RuleSet]:
        """Get the current ruleset."""
        return self._current_ruleset

    def new_ruleset(self, name: str, description: str = "") -> RuleSet:
        """Create a new empty ruleset."""
        self._current_ruleset = RuleSet(name=name, description=description)
        logger.info(f"Created new ruleset: {name}")
        return self._current_ruleset

    def add_rule(
        self,
        name: str,
        conditions: list[Union[RuleCondition, RuleGroup]],
        outcome: DecisionOutcome,
        priority: int = 0,
        description: str = "",
    ) -> Rule:
        """Add a simple rule to the current ruleset."""
        if self._current_ruleset is None:
            raise ValueError("No ruleset active. Call new_ruleset() first.")

        rule = Rule(
            name=name,
            conditions=conditions,
            outcome=outcome,
            priority=priority,
            description=description,
        )
        self._current_ruleset.rules.append(rule)
        logger.info(f"Added rule: {name}")
        return rule

    def add_conditional_rule(
        self,
        name: str,
        if_conditions: RuleGroup,
        then_outcome: DecisionOutcome,
        else_outcome: Optional[DecisionOutcome] = None,
        else_rule: Optional[ConditionalRule] = None,
        priority: int = 0,
        description: str = "",
    ) -> ConditionalRule:
        """Add a conditional rule to the current ruleset."""
        if self._current_ruleset is None:
            raise ValueError("No ruleset active. Call new_ruleset() first.")

        rule = ConditionalRule(
            name=name,
            if_conditions=if_conditions,
            then_outcome=then_outcome,
            else_outcome=else_outcome,
            else_rule=else_rule,
            priority=priority,
            description=description,
        )
        self._current_ruleset.rules.append(rule)
        logger.info(f"Added conditional rule: {name}")
        return rule

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name."""
        if self._current_ruleset is None:
            return False

        for i, rule in enumerate(self._current_ruleset.rules):
            if rule.name == name:
                del self._current_ruleset.rules[i]
                logger.info(f"Removed rule: {name}")
                return True
        return False

    def save_template(self, filename: str) -> str:
        """Save the current ruleset as a template."""
        if self._current_ruleset is None:
            raise ValueError("No ruleset to save.")

        filepath = self.templates_dir / f"{filename}.json"
        with open(filepath, "w") as f:
            json.dump(self._current_ruleset.to_dict(), f, indent=2)

        logger.info(f"Saved template: {filepath}")
        return str(filepath)

    def load_template(self, filename: str) -> RuleSet:
        """Load a ruleset from a template file."""
        filepath = self.templates_dir / f"{filename}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Template not found: {filepath}")

        with open(filepath, "r") as f:
            data = json.load(f)

        self._current_ruleset = RuleSet.from_dict(data)
        logger.info(f"Loaded template: {filepath}")
        return self._current_ruleset

    def list_templates(self) -> list[str]:
        """List all available template files."""
        return [f.stem for f in self.templates_dir.glob("*.json")]

    def delete_template(self, filename: str) -> bool:
        """Delete a template file."""
        filepath = self.templates_dir / f"{filename}.json"
        if filepath.exists():
            filepath.unlink()
            logger.info(f"Deleted template: {filepath}")
            return True
        return False

    def export_ruleset_json(self) -> str:
        """Export the current ruleset as a JSON string."""
        if self._current_ruleset is None:
            raise ValueError("No ruleset to export.")
        return json.dumps(self._current_ruleset.to_dict(), indent=2)

    def import_ruleset_json(self, json_str: str) -> RuleSet:
        """Import a ruleset from a JSON string."""
        data = json.loads(json_str)
        self._current_ruleset = RuleSet.from_dict(data)
        return self._current_ruleset

    @staticmethod
    def create_condition(
        field: str,
        rule_type: RuleType,
        operator: str,
        value: Any,
        value_end: Optional[Any] = None,
        lookup_dataset: Optional[str] = None,
        lookup_field: Optional[str] = None,
    ) -> RuleCondition:
        """Helper to create a rule condition."""
        return RuleCondition(
            field=field,
            rule_type=rule_type,
            operator=operator,
            value=value,
            value_end=value_end,
            lookup_dataset=lookup_dataset,
            lookup_field=lookup_field,
        )

    @staticmethod
    def create_group(
        conditions: list[Union[RuleCondition, RuleGroup]],
        operator: LogicalOperator = LogicalOperator.AND,
    ) -> RuleGroup:
        """Helper to create a rule group."""
        return RuleGroup(conditions=conditions, operator=operator)


def get_predefined_business_rules() -> dict[str, RuleSet]:
    """Get predefined business rule templates."""
    templates = {}

    # Critical Asset Priority Template
    critical_asset = RuleSet(
        name="Critical Asset Priority",
        description="Prioritize maintenance for critical assets",
        rules=[
            Rule(
                name="Critical High Priority",
                conditions=[
                    RuleCondition(
                        field="Priority",
                        rule_type=RuleType.TEXT,
                        operator=TextOperator.EXACT_MATCH.value,
                        value="High",
                    ),
                    RuleCondition(
                        field="Risk Level",
                        rule_type=RuleType.TEXT,
                        operator=TextOperator.EXACT_MATCH.value,
                        value="Critical",
                    ),
                ],
                outcome=DecisionOutcome.ACCEPTED,
                priority=100,
                description="Accept high priority work on critical assets",
            ),
            Rule(
                name="Low Priority Non-Critical",
                conditions=[
                    RuleCondition(
                        field="Priority",
                        rule_type=RuleType.TEXT,
                        operator=TextOperator.EXACT_MATCH.value,
                        value="Low",
                    ),
                    RuleCondition(
                        field="Risk Level",
                        rule_type=RuleType.TEXT,
                        operator=TextOperator.EXACT_MATCH.value,
                        value="Low",
                    ),
                ],
                outcome=DecisionOutcome.REJECTED,
                priority=50,
                description="Reject low priority work on non-critical assets",
            ),
        ],
    )
    templates["critical_asset_priority"] = critical_asset

    # Budget-Based Template
    budget_based = RuleSet(
        name="Budget-Based Categorization",
        description="Categorize based on cost estimates and budget",
        rules=[
            Rule(
                name="Within Budget",
                conditions=[
                    RuleCondition(
                        field="Cost Estimate",
                        rule_type=RuleType.NUMERIC,
                        operator=NumericOperator.LESS_EQUAL.value,
                        value=5000,
                    ),
                ],
                outcome=DecisionOutcome.ACCEPTED,
                priority=80,
                description="Accept work within budget threshold",
            ),
            Rule(
                name="Over Budget",
                conditions=[
                    RuleCondition(
                        field="Cost Estimate",
                        rule_type=RuleType.NUMERIC,
                        operator=NumericOperator.GREATER_THAN.value,
                        value=10000,
                    ),
                ],
                outcome=DecisionOutcome.REJECTED,
                priority=80,
                description="Reject work significantly over budget",
            ),
        ],
    )
    templates["budget_based"] = budget_based

    # Service Date Template
    service_date = RuleSet(
        name="Service Interval Based",
        description="Categorize based on last service date",
        rules=[
            ConditionalRule(
                name="Overdue Service Check",
                if_conditions=RuleGroup(
                    conditions=[
                        RuleCondition(
                            field="Last Service Date",
                            rule_type=RuleType.DATE,
                            operator=DateOperator.WITHIN_DAYS.value,
                            value=-365,  # More than 365 days ago
                        ),
                    ]
                ),
                then_outcome=DecisionOutcome.ACCEPTED,
                else_outcome=DecisionOutcome.RECONSIDER,
                priority=70,
                description="Accept overdue maintenance work",
            ),
        ],
    )
    templates["service_interval"] = service_date

    return templates
