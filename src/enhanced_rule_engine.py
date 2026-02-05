"""
Enhanced Rule Engine for MWCS.

Supports three rule types:
1. Condition-based rules - Traditional operators and thresholds
2. Function-based rules - Pre-coded Python functions with parameters
3. AI-powered rules - Dynamically generated and executed Python code

Rules are evaluated sequentially based on their connections and priority.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Union

import pandas as pd

from .predefined_functions import FunctionRegistry, execute_function
from .supporting_datasets import (
    DecisionCategory,
    EquipmentClassification,
    EquipmentRedundancy,
    SupportingDatasetManager,
    WorkTypeCategory,
)

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    """Types of rules supported by the enhanced engine."""
    CONDITION = "condition"
    FUNCTION = "function"
    AI_GENERATED = "ai_generated"


class ConditionOperator(str, Enum):
    """Operators for condition-based rules."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"


class LogicalOperator(str, Enum):
    """Logical operators for combining conditions."""
    AND = "and"
    OR = "or"
    NOT = "not"


class RuleOutcome(str, Enum):
    """Possible outcomes of rule evaluation."""
    ACCEPT = "ACCEPTED"
    REJECT = "REJECTED"
    RECONSIDER = "RECONSIDER"
    CONTINUE = "CONTINUE"  # Continue to next rule


@dataclass
class Condition:
    """A single condition in a condition-based rule."""
    field: str
    operator: ConditionOperator
    value: Any
    value_end: Optional[Any] = None  # For BETWEEN operator

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
            "value_end": self.value_end,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Condition":
        return cls(
            field=data["field"],
            operator=ConditionOperator(data["operator"]),
            value=data["value"],
            value_end=data.get("value_end"),
        )


@dataclass
class ConditionGroup:
    """Group of conditions combined with logical operators."""
    conditions: list[Union[Condition, "ConditionGroup"]]
    operator: LogicalOperator = LogicalOperator.AND

    def to_dict(self) -> dict:
        return {
            "conditions": [
                c.to_dict() for c in self.conditions
            ],
            "operator": self.operator.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConditionGroup":
        conditions = []
        for c in data.get("conditions", []):
            if "conditions" in c:
                conditions.append(cls.from_dict(c))
            else:
                conditions.append(Condition.from_dict(c))
        return cls(
            conditions=conditions,
            operator=LogicalOperator(data.get("operator", "and")),
        )


@dataclass
class ConditionRule:
    """Traditional condition-based rule."""
    id: str
    name: str
    conditions: ConditionGroup
    outcome_on_match: RuleOutcome
    outcome_on_no_match: RuleOutcome = RuleOutcome.CONTINUE
    priority: int = 0
    enabled: bool = True
    description: str = ""

    @property
    def rule_id(self) -> str:
        """Alias for id."""
        return self.id

    @property
    def rule_type(self) -> "RuleType":
        """Return the rule type."""
        return RuleType.CONDITION

    @property
    def outcome(self) -> str:
        """Alias for outcome_on_match value."""
        return self.outcome_on_match.value

    @property
    def column(self) -> str:
        """Get the column from the first condition."""
        if self.conditions and self.conditions.conditions:
            first = self.conditions.conditions[0]
            if isinstance(first, Condition):
                return first.field
        return ""

    @property
    def operator(self) -> ConditionOperator:
        """Get the operator from the first condition."""
        if self.conditions and self.conditions.conditions:
            first = self.conditions.conditions[0]
            if isinstance(first, Condition):
                return first.operator
        return ConditionOperator.EQUALS

    @property
    def value(self) -> Any:
        """Get the value from the first condition."""
        if self.conditions and self.conditions.conditions:
            first = self.conditions.conditions[0]
            if isinstance(first, Condition):
                return first.value
        return None

    @classmethod
    def create_simple(
        cls,
        rule_id: str,
        name: str,
        column: str,
        operator: ConditionOperator,
        value: Any,
        outcome: str = "RECONSIDER",
        description: str = "",
        priority: int = 0,
        enabled: bool = True,
    ) -> "ConditionRule":
        """Create a simple condition rule with a single condition."""
        condition = Condition(field=column, operator=operator, value=value)
        condition_group = ConditionGroup(conditions=[condition])
        return cls(
            id=rule_id,
            name=name,
            conditions=condition_group,
            outcome_on_match=RuleOutcome(outcome),
            priority=priority,
            enabled=enabled,
            description=description,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": RuleType.CONDITION.value,
            "conditions": self.conditions.to_dict(),
            "outcome_on_match": self.outcome_on_match.value,
            "outcome_on_no_match": self.outcome_on_no_match.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConditionRule":
        return cls(
            id=data["id"],
            name=data["name"],
            conditions=ConditionGroup.from_dict(data["conditions"]),
            outcome_on_match=RuleOutcome(data["outcome_on_match"]),
            outcome_on_no_match=RuleOutcome(data.get("outcome_on_no_match", "CONTINUE")),
            priority=data.get("priority", 0),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
        )


@dataclass
class FunctionRule:
    """Python function-based rule."""
    id: str
    name: str
    function_name: str
    parameters: dict[str, Any]
    outcome_on_match: RuleOutcome
    outcome_on_no_match: RuleOutcome = RuleOutcome.CONTINUE
    priority: int = 0
    enabled: bool = True
    description: str = ""

    @property
    def rule_id(self) -> str:
        """Alias for id."""
        return self.id

    @property
    def rule_type(self) -> "RuleType":
        """Return the rule type."""
        return RuleType.FUNCTION

    @property
    def outcome(self) -> str:
        """Alias for outcome_on_match value."""
        return self.outcome_on_match.value

    @classmethod
    def create_simple(
        cls,
        rule_id: str,
        name: str,
        function_name: str,
        parameters: dict[str, Any],
        outcome: str = "RECONSIDER",
        description: str = "",
        priority: int = 0,
        enabled: bool = True,
    ) -> "FunctionRule":
        """Create a function rule with simplified parameters."""
        return cls(
            id=rule_id,
            name=name,
            function_name=function_name,
            parameters=parameters,
            outcome_on_match=RuleOutcome(outcome),
            priority=priority,
            enabled=enabled,
            description=description,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": RuleType.FUNCTION.value,
            "function_name": self.function_name,
            "parameters": self.parameters,
            "outcome_on_match": self.outcome_on_match.value,
            "outcome_on_no_match": self.outcome_on_no_match.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FunctionRule":
        return cls(
            id=data["id"],
            name=data["name"],
            function_name=data["function_name"],
            parameters=data.get("parameters", {}),
            outcome_on_match=RuleOutcome(data["outcome_on_match"]),
            outcome_on_no_match=RuleOutcome(data.get("outcome_on_no_match", "CONTINUE")),
            priority=data.get("priority", 0),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
        )


@dataclass
class AIGeneratedRule:
    """AI-powered rule with dynamically generated code."""
    id: str
    name: str
    prompt: str
    generated_code: str = ""
    outcome_on_match: RuleOutcome = RuleOutcome.ACCEPT
    outcome_on_no_match: RuleOutcome = RuleOutcome.CONTINUE
    priority: int = 0
    enabled: bool = True
    description: str = ""
    last_generated: Optional[str] = None
    generation_model: str = ""

    @property
    def rule_id(self) -> str:
        """Alias for id."""
        return self.id

    @property
    def rule_type(self) -> "RuleType":
        """Return the rule type."""
        return RuleType.AI_GENERATED

    @property
    def outcome(self) -> str:
        """Alias for outcome_on_match value."""
        return self.outcome_on_match.value

    @property
    def model(self) -> str:
        """Alias for generation_model."""
        return self.generation_model

    @classmethod
    def create_simple(
        cls,
        rule_id: str,
        name: str,
        prompt: str,
        outcome: str = "RECONSIDER",
        description: str = "",
        priority: int = 0,
        enabled: bool = True,
        model: str = "gpt-4",
    ) -> "AIGeneratedRule":
        """Create an AI rule with simplified parameters."""
        return cls(
            id=rule_id,
            name=name,
            prompt=prompt,
            outcome_on_match=RuleOutcome(outcome),
            priority=priority,
            enabled=enabled,
            description=description,
            generation_model=model,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": RuleType.AI_GENERATED.value,
            "prompt": self.prompt,
            "generated_code": self.generated_code,
            "outcome_on_match": self.outcome_on_match.value,
            "outcome_on_no_match": self.outcome_on_no_match.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "description": self.description,
            "last_generated": self.last_generated,
            "generation_model": self.generation_model,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AIGeneratedRule":
        return cls(
            id=data["id"],
            name=data["name"],
            prompt=data["prompt"],
            generated_code=data.get("generated_code", ""),
            outcome_on_match=RuleOutcome(data.get("outcome_on_match", "ACCEPTED")),
            outcome_on_no_match=RuleOutcome(data.get("outcome_on_no_match", "CONTINUE")),
            priority=data.get("priority", 0),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
            last_generated=data.get("last_generated"),
            generation_model=data.get("generation_model", ""),
        )


# Union type for all rules
Rule = Union[ConditionRule, FunctionRule, AIGeneratedRule]


@dataclass
class RuleConnection:
    """Connection between rules for sequential evaluation."""
    id: str
    from_rule_id: Optional[str]  # None for entry point
    to_rule_id: str
    condition: str = "always"  # "on_match", "on_no_match", "always"
    priority: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_rule_id": self.from_rule_id,
            "to_rule_id": self.to_rule_id,
            "condition": self.condition,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RuleConnection":
        return cls(
            id=data["id"],
            from_rule_id=data.get("from_rule_id"),
            to_rule_id=data["to_rule_id"],
            condition=data.get("condition", "always"),
            priority=data.get("priority", 0),
        )


@dataclass
class RuleEvaluationResult:
    """Result of evaluating a single rule."""
    rule_id: str
    rule_name: str
    rule_type: RuleType
    matched: bool
    outcome: RuleOutcome
    details: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class RowEvaluationResult:
    """Complete evaluation result for a row."""
    row_index: int
    work_id: str
    final_outcome: RuleOutcome
    rule_results: list[RuleEvaluationResult]
    supporting_data_classification: dict[str, Any]
    total_execution_time_ms: float
    timestamp: str


@dataclass
class AuditLogEntry:
    """Audit log entry for rule decisions."""
    timestamp: str
    row_index: int
    work_id: str
    rule_id: str
    rule_name: str
    rule_type: str
    matched: bool
    outcome: str
    details: dict[str, Any]
    execution_time_ms: float
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class EnhancedRuleEngine:
    """Enhanced rule engine supporting multiple rule types."""

    def __init__(self):
        self.rules: dict[str, Rule] = {}
        self.connections: dict[str, RuleConnection] = {}
        self.supporting_data_manager = SupportingDatasetManager()
        self.audit_log: list[AuditLogEntry] = []
        self._ai_service = None

    def set_ai_service(self, ai_service) -> None:
        """Set the AI service for AI-generated rules."""
        self._ai_service = ai_service

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine."""
        self.rules[rule.id] = rule
        logger.info(f"Added rule: {rule.name} ({rule.id})")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the engine."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            # Remove associated connections
            self.connections = {
                k: v for k, v in self.connections.items()
                if v.from_rule_id != rule_id and v.to_rule_id != rule_id
            }
            logger.info(f"Removed rule: {rule_id}")
            return True
        return False

    def add_connection(self, connection: RuleConnection) -> None:
        """Add a connection between rules."""
        self.connections[connection.id] = connection
        logger.info(f"Added connection: {connection.from_rule_id} -> {connection.to_rule_id}")

    def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            return True
        return False

    def get_entry_rules(self) -> list[Rule]:
        """Get rules that are entry points (no incoming connections)."""
        rules_with_incoming = {
            c.to_rule_id for c in self.connections.values()
            if c.from_rule_id is not None
        }

        entry_rules = []
        for rule_id, rule in self.rules.items():
            if rule.enabled and rule_id not in rules_with_incoming:
                entry_rules.append(rule)

        # Also include rules connected from None (explicit entry points)
        explicit_entries = {
            c.to_rule_id for c in self.connections.values()
            if c.from_rule_id is None
        }
        for rule_id in explicit_entries:
            if rule_id in self.rules and self.rules[rule_id] not in entry_rules:
                if self.rules[rule_id].enabled:
                    entry_rules.append(self.rules[rule_id])

        return sorted(entry_rules, key=lambda r: r.priority, reverse=True)

    def get_next_rules(self, rule_id: str, matched: bool) -> list[Rule]:
        """Get next rules based on current rule and match result."""
        next_rules = []

        for conn in self.connections.values():
            if conn.from_rule_id != rule_id:
                continue

            # Check connection condition
            if conn.condition == "always":
                pass
            elif conn.condition == "on_match" and not matched:
                continue
            elif conn.condition == "on_no_match" and matched:
                continue

            if conn.to_rule_id in self.rules:
                rule = self.rules[conn.to_rule_id]
                if rule.enabled:
                    next_rules.append((conn.priority, rule))

        # Sort by connection priority
        next_rules.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in next_rules]

    def evaluate_row(
        self,
        row: pd.Series,
        row_index: int,
    ) -> RowEvaluationResult:
        """Evaluate all rules for a single row."""
        start_time = time.time()

        # Get work ID
        work_id = str(row.get("Work ID", f"Row-{row_index}"))

        # Classify using supporting datasets
        asset_id = str(row.get("Asset ID", ""))
        work_type = str(row.get("Category", ""))
        description = str(row.get("Description", ""))

        supporting_classification = self.supporting_data_manager.classify_work_item(
            asset_id, work_type, description
        )

        # Propagate supporting data to row for rule evaluation
        enriched_row = row.copy()
        for key, value in supporting_classification.items():
            enriched_row[key] = value

        # Evaluate rules
        rule_results = []
        final_outcome = RuleOutcome.RECONSIDER
        evaluated_rules = set()

        # Start with entry rules
        rules_to_evaluate = self.get_entry_rules()

        while rules_to_evaluate:
            rule = rules_to_evaluate.pop(0)

            if rule.id in evaluated_rules:
                continue
            evaluated_rules.add(rule.id)

            # Evaluate the rule
            result = self._evaluate_rule(rule, enriched_row, row_index, work_id)
            rule_results.append(result)

            # Check if we have a final outcome
            if result.outcome in (RuleOutcome.ACCEPT, RuleOutcome.REJECT, RuleOutcome.RECONSIDER):
                if result.outcome != RuleOutcome.CONTINUE:
                    final_outcome = result.outcome
                    # Continue evaluating unless this is a terminal outcome
                    if result.matched and result.outcome != RuleOutcome.CONTINUE:
                        break

            # Get next rules
            next_rules = self.get_next_rules(rule.id, result.matched)
            for next_rule in next_rules:
                if next_rule.id not in evaluated_rules:
                    rules_to_evaluate.insert(0, next_rule)

        # If no definitive outcome, use default based on supporting data
        if final_outcome == RuleOutcome.RECONSIDER:
            recommended = supporting_classification.get("recommended_decision", "RECONSIDER")
            try:
                final_outcome = RuleOutcome(recommended)
            except ValueError:
                final_outcome = RuleOutcome.RECONSIDER

        total_time = (time.time() - start_time) * 1000

        return RowEvaluationResult(
            row_index=row_index,
            work_id=work_id,
            final_outcome=final_outcome,
            rule_results=rule_results,
            supporting_data_classification=supporting_classification,
            total_execution_time_ms=total_time,
            timestamp=datetime.now().isoformat(),
        )

    def _evaluate_rule(
        self,
        rule: Rule,
        row: pd.Series,
        row_index: int,
        work_id: str,
    ) -> RuleEvaluationResult:
        """Evaluate a single rule against a row."""
        start_time = time.time()

        try:
            if isinstance(rule, ConditionRule):
                matched, details = self._evaluate_condition_rule(rule, row)
                rule_type = RuleType.CONDITION
            elif isinstance(rule, FunctionRule):
                matched, details = self._evaluate_function_rule(rule, row)
                rule_type = RuleType.FUNCTION
            elif isinstance(rule, AIGeneratedRule):
                matched, details = self._evaluate_ai_rule(rule, row)
                rule_type = RuleType.AI_GENERATED
            else:
                matched = False
                details = {"error": "Unknown rule type"}
                rule_type = RuleType.CONDITION

            outcome = rule.outcome_on_match if matched else rule.outcome_on_no_match
            error = None

        except Exception as e:
            matched = False
            details = {"error": str(e)}
            outcome = rule.outcome_on_no_match
            error = str(e)
            rule_type = RuleType.CONDITION
            logger.error(f"Error evaluating rule {rule.name}: {e}")

        execution_time = (time.time() - start_time) * 1000

        # Create audit log entry
        audit_entry = AuditLogEntry(
            timestamp=datetime.now().isoformat(),
            row_index=row_index,
            work_id=work_id,
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule_type.value,
            matched=matched,
            outcome=outcome.value,
            details=details,
            execution_time_ms=execution_time,
            error=error,
        )
        self.audit_log.append(audit_entry)

        return RuleEvaluationResult(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule_type,
            matched=matched,
            outcome=outcome,
            details=details,
            execution_time_ms=execution_time,
            error=error,
        )

    def _evaluate_condition_rule(
        self,
        rule: ConditionRule,
        row: pd.Series,
    ) -> tuple[bool, dict[str, Any]]:
        """Evaluate a condition-based rule."""
        matched, details = self._evaluate_condition_group(rule.conditions, row)
        return matched, details

    def _evaluate_condition_group(
        self,
        group: ConditionGroup,
        row: pd.Series,
    ) -> tuple[bool, dict[str, Any]]:
        """Evaluate a group of conditions."""
        results = []
        details = {"conditions": []}

        for condition in group.conditions:
            if isinstance(condition, ConditionGroup):
                result, sub_details = self._evaluate_condition_group(condition, row)
            else:
                result, sub_details = self._evaluate_condition(condition, row)

            results.append(result)
            details["conditions"].append(sub_details)

        if group.operator == LogicalOperator.AND:
            final_result = all(results)
        elif group.operator == LogicalOperator.OR:
            final_result = any(results)
        elif group.operator == LogicalOperator.NOT:
            final_result = not any(results)
        else:
            final_result = all(results)

        details["operator"] = group.operator.value
        details["result"] = final_result
        return final_result, details

    def _evaluate_condition(
        self,
        condition: Condition,
        row: pd.Series,
    ) -> tuple[bool, dict[str, Any]]:
        """Evaluate a single condition."""
        field_value = row.get(condition.field)
        compare_value = condition.value
        operator = condition.operator

        details = {
            "field": condition.field,
            "field_value": str(field_value) if field_value is not None else None,
            "operator": operator.value,
            "compare_value": str(compare_value),
        }

        # Handle null checks first
        if operator == ConditionOperator.IS_NULL:
            result = pd.isna(field_value)
            details["result"] = result
            return result, details

        if operator == ConditionOperator.IS_NOT_NULL:
            result = not pd.isna(field_value)
            details["result"] = result
            return result, details

        # If field is null for other operators, condition fails
        if pd.isna(field_value):
            details["result"] = False
            details["reason"] = "Field value is null"
            return False, details

        try:
            if operator == ConditionOperator.EQUALS:
                result = str(field_value).lower() == str(compare_value).lower()

            elif operator == ConditionOperator.NOT_EQUALS:
                result = str(field_value).lower() != str(compare_value).lower()

            elif operator == ConditionOperator.GREATER_THAN:
                result = float(field_value) > float(compare_value)

            elif operator == ConditionOperator.LESS_THAN:
                result = float(field_value) < float(compare_value)

            elif operator == ConditionOperator.GREATER_EQUAL:
                result = float(field_value) >= float(compare_value)

            elif operator == ConditionOperator.LESS_EQUAL:
                result = float(field_value) <= float(compare_value)

            elif operator == ConditionOperator.CONTAINS:
                result = str(compare_value).lower() in str(field_value).lower()

            elif operator == ConditionOperator.NOT_CONTAINS:
                result = str(compare_value).lower() not in str(field_value).lower()

            elif operator == ConditionOperator.STARTS_WITH:
                result = str(field_value).lower().startswith(str(compare_value).lower())

            elif operator == ConditionOperator.ENDS_WITH:
                result = str(field_value).lower().endswith(str(compare_value).lower())

            elif operator == ConditionOperator.REGEX:
                import re
                result = bool(re.search(str(compare_value), str(field_value)))

            elif operator == ConditionOperator.IN_LIST:
                values = [v.strip().lower() for v in str(compare_value).split(",")]
                result = str(field_value).lower() in values

            elif operator == ConditionOperator.NOT_IN_LIST:
                values = [v.strip().lower() for v in str(compare_value).split(",")]
                result = str(field_value).lower() not in values

            elif operator == ConditionOperator.BETWEEN:
                value = float(field_value)
                low = float(compare_value)
                high = float(condition.value_end) if condition.value_end else low
                result = low <= value <= high
                details["value_end"] = str(high)

            else:
                result = False
                details["reason"] = f"Unknown operator: {operator}"

        except (ValueError, TypeError) as e:
            result = False
            details["error"] = str(e)

        details["result"] = result
        return result, details

    def _evaluate_function_rule(
        self,
        rule: FunctionRule,
        row: pd.Series,
    ) -> tuple[bool, dict[str, Any]]:
        """Evaluate a function-based rule."""
        matched, details = execute_function(
            rule.function_name,
            row,
            rule.parameters,
        )
        return matched, details

    def _evaluate_ai_rule(
        self,
        rule: AIGeneratedRule,
        row: pd.Series,
    ) -> tuple[bool, dict[str, Any]]:
        """Evaluate an AI-generated rule."""
        if not rule.generated_code:
            return False, {"error": "No generated code available"}

        # Create a safe execution environment
        safe_globals = {
            "__builtins__": {
                "True": True,
                "False": False,
                "None": None,
                "abs": abs,
                "all": all,
                "any": any,
                "bool": bool,
                "float": float,
                "int": int,
                "len": len,
                "max": max,
                "min": min,
                "round": round,
                "str": str,
                "sum": sum,
            },
            "pd": pd,
            "datetime": datetime,
        }

        safe_locals = {
            "row": row,
            "result": False,
            "details": {},
        }

        try:
            exec(rule.generated_code, safe_globals, safe_locals)
            result = bool(safe_locals.get("result", False))
            details = safe_locals.get("details", {})
            details["code_executed"] = True
            return result, details
        except Exception as e:
            logger.error(f"Error executing AI-generated code: {e}")
            return False, {"error": str(e), "code_executed": False}

    def evaluate_dataframe(
        self,
        df: pd.DataFrame,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[RowEvaluationResult]:
        """Evaluate all rows in a DataFrame."""
        results = []
        total = len(df)

        for idx, (row_idx, row) in enumerate(df.iterrows()):
            result = self.evaluate_row(row, idx)
            results.append(result)

            if progress_callback and idx % 10 == 0:
                progress_callback(idx + 1, total)

        return results

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Get the audit log as a list of dictionaries."""
        return [entry.to_dict() for entry in self.audit_log]

    def clear_audit_log(self) -> None:
        """Clear the audit log."""
        self.audit_log = []

    def export_audit_log_df(self) -> pd.DataFrame:
        """Export audit log as DataFrame."""
        if not self.audit_log:
            return pd.DataFrame()
        return pd.DataFrame([e.to_dict() for e in self.audit_log])

    def get_rules_summary(self) -> dict[str, Any]:
        """Get summary of configured rules."""
        rule_types = {"condition": 0, "function": 0, "ai_generated": 0}

        for rule in self.rules.values():
            if isinstance(rule, ConditionRule):
                rule_types["condition"] += 1
            elif isinstance(rule, FunctionRule):
                rule_types["function"] += 1
            elif isinstance(rule, AIGeneratedRule):
                rule_types["ai_generated"] += 1

        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
            "rule_types": rule_types,
            "total_connections": len(self.connections),
            "supporting_datasets": self.supporting_data_manager.get_classification_summary(),
        }

    def to_dict(self) -> dict[str, Any]:
        """Export engine configuration to dictionary."""
        return {
            "rules": {k: v.to_dict() for k, v in self.rules.items()},
            "connections": {k: v.to_dict() for k, v in self.connections.items()},
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        """Load engine configuration from dictionary."""
        # Load rules
        self.rules = {}
        for rule_id, rule_data in data.get("rules", {}).items():
            rule_type = rule_data.get("type", "condition")
            if rule_type == "condition":
                self.rules[rule_id] = ConditionRule.from_dict(rule_data)
            elif rule_type == "function":
                self.rules[rule_id] = FunctionRule.from_dict(rule_data)
            elif rule_type == "ai_generated":
                self.rules[rule_id] = AIGeneratedRule.from_dict(rule_data)

        # Load connections
        self.connections = {}
        for conn_id, conn_data in data.get("connections", {}).items():
            self.connections[conn_id] = RuleConnection.from_dict(conn_data)

        logger.info(f"Loaded {len(self.rules)} rules and {len(self.connections)} connections")


def create_rule_id() -> str:
    """Generate a unique rule ID."""
    return f"rule_{uuid.uuid4().hex[:8]}"


def create_connection_id() -> str:
    """Generate a unique connection ID."""
    return f"conn_{uuid.uuid4().hex[:8]}"
