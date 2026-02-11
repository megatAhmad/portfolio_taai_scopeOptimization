"""
Predefined Functions Module for MWCS.

Contains pre-coded Python functions that can be used as rule evaluators.
Each function takes a row (pd.Series) and optional parameters, returning
a tuple of (result: bool, details: dict).
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import pandas as pd
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


# Type alias for predefined function signature
PredefinedFunction = Callable[[pd.Series, dict[str, Any]], tuple[bool, dict[str, Any]]]


class FunctionRegistry:
    """Registry for predefined rule functions."""

    _functions: dict[str, dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        parameters: dict[str, dict[str, Any]],
        category: str = "General",
    ):
        """Decorator to register a function."""
        def decorator(func: PredefinedFunction) -> PredefinedFunction:
            cls._functions[name] = {
                "function": func,
                "name": name,
                "description": description,
                "parameters": parameters,
                "category": category,
            }
            return func
        return decorator

    @classmethod
    def get_function(cls, name: str) -> Optional[PredefinedFunction]:
        """Get a registered function by name."""
        entry = cls._functions.get(name)
        return entry["function"] if entry else None

    @classmethod
    def get_function_info(cls, name: str) -> Optional[dict[str, Any]]:
        """Get function metadata."""
        return cls._functions.get(name)

    @classmethod
    def list_functions(cls) -> dict[str, dict[str, Any]]:
        """List all registered functions as a dict keyed by function name."""
        return {
            name: {k: v for k, v in entry.items() if k != "function"}
            for name, entry in cls._functions.items()
        }

    @classmethod
    def list_by_category(cls) -> dict[str, list[dict[str, Any]]]:
        """List functions grouped by category."""
        categories: dict[str, list] = {}
        for entry in cls._functions.values():
            category = entry["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append({k: v for k, v in entry.items() if k != "function"})
        return categories

    @classmethod
    def execute(
        cls,
        name: str,
        row: pd.Series,
        params: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        """Execute a registered function."""
        func = cls.get_function(name)
        if func is None:
            return False, {"error": f"Function '{name}' not found"}

        try:
            return func(row, params)
        except Exception as e:
            logger.error(f"Error executing function '{name}': {e}")
            return False, {"error": str(e)}


# =============================================================================
# Cost-Based Functions
# =============================================================================

@FunctionRegistry.register(
    name="check_cost_threshold",
    description="Check if cost estimate is within a threshold",
    parameters={
        "max_cost": {"type": "float", "description": "Maximum allowed cost", "default": 5000.0},
        "cost_column": {"type": "string", "description": "Column name for cost", "default": "Cost Estimate"},
    },
    category="Cost Analysis",
)
def check_cost_threshold(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Check if cost is within threshold."""
    max_cost = params.get("max_cost", 5000.0)
    cost_col = params.get("cost_column", "Cost Estimate")

    cost = row.get(cost_col, 0)
    if pd.isna(cost):
        return False, {"reason": "Cost value is missing", "cost": None}

    cost = float(cost)
    result = cost <= max_cost

    return result, {
        "cost": cost,
        "threshold": max_cost,
        "within_budget": result,
        "difference": max_cost - cost,
    }


@FunctionRegistry.register(
    name="check_cost_per_hour",
    description="Check if cost per estimated hour is reasonable",
    parameters={
        "max_rate": {"type": "float", "description": "Maximum cost per hour", "default": 500.0},
        "cost_column": {"type": "string", "description": "Column name for cost", "default": "Cost Estimate"},
        "hours_column": {"type": "string", "description": "Column name for hours", "default": "Estimated Hours"},
    },
    category="Cost Analysis",
)
def check_cost_per_hour(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Check if cost per hour is within limits."""
    max_rate = params.get("max_rate", 500.0)
    cost_col = params.get("cost_column", "Cost Estimate")
    hours_col = params.get("hours_column", "Estimated Hours")

    cost = row.get(cost_col, 0)
    hours = row.get(hours_col, 0)

    if pd.isna(cost) or pd.isna(hours) or float(hours) == 0:
        return False, {"reason": "Cannot calculate cost per hour", "rate": None}

    rate = float(cost) / float(hours)
    result = rate <= max_rate

    return result, {
        "cost": float(cost),
        "hours": float(hours),
        "rate": round(rate, 2),
        "max_rate": max_rate,
        "acceptable": result,
    }


# =============================================================================
# Time-Based Functions
# =============================================================================

@FunctionRegistry.register(
    name="check_service_overdue",
    description="Check if equipment service is overdue based on last service date",
    parameters={
        "max_days": {"type": "int", "description": "Maximum days since last service", "default": 365},
        "date_column": {"type": "string", "description": "Column name for date", "default": "Last Service Date"},
    },
    category="Time Analysis",
)
def check_service_overdue(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Check if service is overdue."""
    max_days = params.get("max_days", 365)
    date_col = params.get("date_column", "Last Service Date")

    date_val = row.get(date_col)
    if pd.isna(date_val):
        return True, {"reason": "No service date found - considered overdue", "days_since": None}

    try:
        if isinstance(date_val, (datetime, pd.Timestamp)):
            last_service = date_val
        else:
            last_service = date_parser.parse(str(date_val))

        days_since = (datetime.now() - last_service).days
        is_overdue = days_since > max_days

        return is_overdue, {
            "last_service": last_service.strftime("%Y-%m-%d"),
            "days_since": days_since,
            "max_days": max_days,
            "is_overdue": is_overdue,
        }
    except (ValueError, TypeError) as e:
        return True, {"reason": f"Cannot parse date: {e}", "days_since": None}


@FunctionRegistry.register(
    name="check_hours_availability",
    description="Check if estimated hours fit within available capacity",
    parameters={
        "available_hours": {"type": "float", "description": "Available hours in period", "default": 40.0},
        "hours_column": {"type": "string", "description": "Column name for hours", "default": "Estimated Hours"},
    },
    category="Time Analysis",
)
def check_hours_availability(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Check if estimated hours fit within availability."""
    available = params.get("available_hours", 40.0)
    hours_col = params.get("hours_column", "Estimated Hours")

    hours = row.get(hours_col, 0)
    if pd.isna(hours):
        return False, {"reason": "Hours not specified", "fits": False}

    hours = float(hours)
    fits = hours <= available

    return fits, {
        "estimated_hours": hours,
        "available_hours": available,
        "fits_schedule": fits,
        "remaining": available - hours,
    }


# =============================================================================
# Priority-Based Functions
# =============================================================================

@FunctionRegistry.register(
    name="check_priority_level",
    description="Check if priority meets minimum level",
    parameters={
        "required_priorities": {"type": "list", "description": "List of acceptable priorities", "default": ["High", "Critical"]},
        "priority_column": {"type": "string", "description": "Column name for priority", "default": "Priority"},
    },
    category="Priority Analysis",
)
def check_priority_level(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Check if priority is in accepted list."""
    required = params.get("required_priorities", ["High", "Critical"])
    priority_col = params.get("priority_column", "Priority")

    priority = row.get(priority_col, "")
    if pd.isna(priority):
        return False, {"reason": "Priority not specified", "matches": False}

    priority = str(priority)
    matches = any(p.lower() == priority.lower() for p in required)

    return matches, {
        "priority": priority,
        "required": required,
        "matches": matches,
    }


@FunctionRegistry.register(
    name="calculate_composite_priority",
    description="Calculate composite priority score from multiple factors",
    parameters={
        "priority_weights": {"type": "dict", "description": "Priority level weights", "default": {"High": 100, "Medium": 50, "Low": 20}},
        "risk_weights": {"type": "dict", "description": "Risk level weights", "default": {"Critical": 100, "High": 75, "Medium": 50, "Low": 25}},
        "threshold": {"type": "float", "description": "Minimum composite score", "default": 100.0},
        "priority_column": {"type": "string", "description": "Priority column", "default": "Priority"},
        "risk_column": {"type": "string", "description": "Risk column", "default": "Risk Level"},
    },
    category="Priority Analysis",
)
def calculate_composite_priority(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Calculate composite priority from multiple factors."""
    priority_weights = params.get("priority_weights", {"High": 100, "Medium": 50, "Low": 20})
    risk_weights = params.get("risk_weights", {"Critical": 100, "High": 75, "Medium": 50, "Low": 25})
    threshold = params.get("threshold", 100.0)
    priority_col = params.get("priority_column", "Priority")
    risk_col = params.get("risk_column", "Risk Level")

    priority = str(row.get(priority_col, ""))
    risk = str(row.get(risk_col, ""))

    priority_score = priority_weights.get(priority, 0)
    risk_score = risk_weights.get(risk, 0)
    composite = (priority_score + risk_score) / 2

    meets_threshold = composite >= threshold

    return meets_threshold, {
        "priority": priority,
        "risk": risk,
        "priority_score": priority_score,
        "risk_score": risk_score,
        "composite_score": composite,
        "threshold": threshold,
        "meets_threshold": meets_threshold,
    }


# =============================================================================
# Category-Based Functions
# =============================================================================

@FunctionRegistry.register(
    name="check_category_allowed",
    description="Check if work category is in allowed list",
    parameters={
        "allowed_categories": {"type": "list", "description": "List of allowed categories", "default": ["Preventive Maintenance", "Corrective Maintenance"]},
        "category_column": {"type": "string", "description": "Column name for category", "default": "Category"},
    },
    category="Category Analysis",
)
def check_category_allowed(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Check if category is allowed."""
    allowed = params.get("allowed_categories", ["Preventive Maintenance", "Corrective Maintenance"])
    category_col = params.get("category_column", "Category")

    category = row.get(category_col, "")
    if pd.isna(category):
        return False, {"reason": "Category not specified", "allowed": False}

    category = str(category)
    is_allowed = any(c.lower() == category.lower() for c in allowed)

    return is_allowed, {
        "category": category,
        "allowed_list": allowed,
        "is_allowed": is_allowed,
    }


@FunctionRegistry.register(
    name="check_description_keywords",
    description="Check if description contains required keywords",
    parameters={
        "required_keywords": {"type": "list", "description": "Keywords that should be present (any)", "default": []},
        "forbidden_keywords": {"type": "list", "description": "Keywords that should not be present", "default": []},
        "description_column": {"type": "string", "description": "Column name for description", "default": "Description"},
    },
    category="Category Analysis",
)
def check_description_keywords(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Check description for required/forbidden keywords."""
    required = params.get("required_keywords", [])
    forbidden = params.get("forbidden_keywords", [])
    desc_col = params.get("description_column", "Description")

    description = str(row.get(desc_col, "")).lower()

    # Check required keywords (any match is OK)
    found_required = [kw for kw in required if kw.lower() in description]
    has_required = len(found_required) > 0 if required else True

    # Check forbidden keywords
    found_forbidden = [kw for kw in forbidden if kw.lower() in description]
    has_forbidden = len(found_forbidden) > 0

    result = has_required and not has_forbidden

    return result, {
        "description_length": len(description),
        "required_keywords": required,
        "found_required": found_required,
        "forbidden_keywords": forbidden,
        "found_forbidden": found_forbidden,
        "passes": result,
    }


# =============================================================================
# Asset-Based Functions
# =============================================================================

@FunctionRegistry.register(
    name="check_asset_exists",
    description="Check if asset ID exists in asset registry",
    parameters={
        "asset_column": {"type": "string", "description": "Column name for asset ID", "default": "Asset ID"},
    },
    category="Asset Analysis",
)
def check_asset_exists(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Check if asset ID is present."""
    asset_col = params.get("asset_column", "Asset ID")

    asset_id = row.get(asset_col)
    exists = not pd.isna(asset_id) and str(asset_id).strip() != ""

    return exists, {
        "asset_id": str(asset_id) if exists else None,
        "exists": exists,
    }


@FunctionRegistry.register(
    name="check_asset_pattern",
    description="Check if asset ID matches expected pattern",
    parameters={
        "pattern": {"type": "string", "description": "Regex pattern for asset ID", "default": r"^AST-\d{4,}$"},
        "asset_column": {"type": "string", "description": "Column name for asset ID", "default": "Asset ID"},
    },
    category="Asset Analysis",
)
def check_asset_pattern(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Check if asset ID matches pattern."""
    pattern = params.get("pattern", r"^AST-\d{4,}$")
    asset_col = params.get("asset_column", "Asset ID")

    asset_id = str(row.get(asset_col, ""))

    try:
        matches = bool(re.match(pattern, asset_id))
    except re.error as e:
        return False, {"error": f"Invalid regex pattern: {e}"}

    return matches, {
        "asset_id": asset_id,
        "pattern": pattern,
        "matches": matches,
    }


# =============================================================================
# Supporting Dataset Functions
# =============================================================================

@FunctionRegistry.register(
    name="check_equipment_criticality",
    description="Check if equipment meets criticality requirements based on classification master",
    parameters={
        "min_criticality_score": {"type": "float", "description": "Minimum criticality score", "default": 50.0},
        "required_classifications": {"type": "list", "description": "Required equipment classifications", "default": ["Critical", "Standard"]},
        "asset_column": {"type": "string", "description": "Column name for asset ID", "default": "Asset ID"},
    },
    category="Supporting Dataset Analysis",
)
def check_equipment_criticality(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Check equipment criticality from supporting dataset."""
    min_score = params.get("min_criticality_score", 50.0)
    required_classes = params.get("required_classifications", ["Critical", "Standard"])
    asset_col = params.get("asset_column", "Asset ID")

    asset_id = str(row.get(asset_col, ""))

    # Get classification from row if propagated
    classification = str(row.get("equipment_classification", "Unclassified"))
    criticality_score = float(row.get("criticality_score", 0))

    class_ok = classification in required_classes
    score_ok = criticality_score >= min_score

    return class_ok and score_ok, {
        "asset_id": asset_id,
        "classification": classification,
        "criticality_score": criticality_score,
        "min_score": min_score,
        "required_classifications": required_classes,
        "classification_ok": class_ok,
        "score_ok": score_ok,
    }


@FunctionRegistry.register(
    name="check_redundancy_requirements",
    description="Check if equipment meets redundancy requirements",
    parameters={
        "require_backup": {"type": "bool", "description": "Require backup asset", "default": False},
        "max_dependencies": {"type": "int", "description": "Maximum allowed dependencies", "default": 2},
        "allowed_redundancy_types": {"type": "list", "description": "Allowed redundancy types", "default": ["Dual Dependency", "No Dependency"]},
    },
    category="Supporting Dataset Analysis",
)
def check_redundancy_requirements(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Check equipment redundancy requirements."""
    require_backup = params.get("require_backup", False)
    max_deps = params.get("max_dependencies", 2)
    allowed_types = params.get("allowed_redundancy_types", ["Dual Dependency", "No Dependency"])

    # Get redundancy info from row if propagated
    redundancy_type = str(row.get("redundancy_type", "Uncertain"))
    dependency_count = int(row.get("dependency_count", 0))
    has_backup = bool(row.get("has_backup", False))

    type_ok = redundancy_type in allowed_types
    deps_ok = dependency_count <= max_deps
    backup_ok = has_backup if require_backup else True

    return type_ok and deps_ok and backup_ok, {
        "redundancy_type": redundancy_type,
        "dependency_count": dependency_count,
        "has_backup": has_backup,
        "allowed_types": allowed_types,
        "max_dependencies": max_deps,
        "require_backup": require_backup,
        "type_ok": type_ok,
        "deps_ok": deps_ok,
        "backup_ok": backup_ok,
    }


# =============================================================================
# Composite/Complex Functions
# =============================================================================

@FunctionRegistry.register(
    name="evaluate_work_order_completeness",
    description="Evaluate if work order has all required fields",
    parameters={
        "required_fields": {"type": "list", "description": "List of required field names", "default": ["Work ID", "Description", "Priority", "Category"]},
        "min_description_length": {"type": "int", "description": "Minimum description length", "default": 10},
    },
    category="Data Quality",
)
def evaluate_work_order_completeness(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Evaluate work order completeness."""
    required = params.get("required_fields", ["Work ID", "Description", "Priority", "Category"])
    min_desc_len = params.get("min_description_length", 10)

    missing_fields = []
    present_fields = []

    for field in required:
        value = row.get(field)
        if pd.isna(value) or str(value).strip() == "":
            missing_fields.append(field)
        else:
            present_fields.append(field)

    # Check description length
    description = str(row.get("Description", ""))
    desc_ok = len(description) >= min_desc_len

    is_complete = len(missing_fields) == 0 and desc_ok

    return is_complete, {
        "required_fields": required,
        "present_fields": present_fields,
        "missing_fields": missing_fields,
        "description_length": len(description),
        "min_description_length": min_desc_len,
        "description_ok": desc_ok,
        "is_complete": is_complete,
    }


@FunctionRegistry.register(
    name="calculate_acceptance_score",
    description="Calculate overall acceptance score based on multiple factors",
    parameters={
        "cost_weight": {"type": "float", "description": "Weight for cost factor", "default": 0.3},
        "priority_weight": {"type": "float", "description": "Weight for priority factor", "default": 0.4},
        "criticality_weight": {"type": "float", "description": "Weight for criticality factor", "default": 0.3},
        "acceptance_threshold": {"type": "float", "description": "Minimum score for acceptance", "default": 60.0},
    },
    category="Composite Analysis",
)
def calculate_acceptance_score(row: pd.Series, params: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Calculate composite acceptance score."""
    cost_weight = params.get("cost_weight", 0.3)
    priority_weight = params.get("priority_weight", 0.4)
    criticality_weight = params.get("criticality_weight", 0.3)
    threshold = params.get("acceptance_threshold", 60.0)

    # Normalize cost score (lower cost = higher score)
    cost = float(row.get("Cost Estimate", 5000))
    cost_score = max(0, min(100, 100 - (cost / 100)))

    # Priority score
    priority_scores = {"High": 100, "Critical": 100, "Medium": 60, "Low": 30}
    priority = str(row.get("Priority", "Medium"))
    priority_score = priority_scores.get(priority, 50)

    # Criticality score from supporting data
    criticality_score = float(row.get("criticality_score", 50))

    # Calculate weighted score
    total_score = (
        cost_score * cost_weight +
        priority_score * priority_weight +
        criticality_score * criticality_weight
    )

    accepted = total_score >= threshold

    return accepted, {
        "cost_score": round(cost_score, 2),
        "priority_score": priority_score,
        "criticality_score": criticality_score,
        "weights": {
            "cost": cost_weight,
            "priority": priority_weight,
            "criticality": criticality_weight,
        },
        "total_score": round(total_score, 2),
        "threshold": threshold,
        "accepted": accepted,
    }


def get_all_functions() -> list[dict[str, Any]]:
    """Get all registered functions with their metadata."""
    return FunctionRegistry.list_functions()


def get_functions_by_category() -> dict[str, list[dict[str, Any]]]:
    """Get functions organized by category."""
    return FunctionRegistry.list_by_category()


def execute_function(
    name: str,
    row: pd.Series,
    params: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    """Execute a predefined function."""
    return FunctionRegistry.execute(name, row, params)


# Module-level instance for convenient access
function_registry = FunctionRegistry()
