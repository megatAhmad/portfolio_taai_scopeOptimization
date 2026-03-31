import pandas as pd

def evaluate_condition(row: dict, condition: dict) -> bool:
    field = condition.get("field")
    op = condition.get("operator")
    val = condition.get("value")
    
    row_val = row.get(field)
    
    if op == "==":
        return row_val == val
    elif op == "!=":
        return row_val != val
    elif op == "IN":
        return row_val in val if isinstance(val, list) else False
    elif op == "NOT_IN":
        return row_val not in val if isinstance(val, list) else True
    elif op == ">=":
        return row_val >= val if row_val is not None else False
    elif op == "<=":
        return row_val <= val if row_val is not None else False
    elif op == "CONTAINS":
        return val in str(row_val) if row_val is not None else False
    elif op == "IS_NULL":
        return row_val is None or pd.isna(row_val)
    elif op == "IS_NOT_NULL":
        return row_val is not None and not pd.isna(row_val)
    return False

def evaluate_node(row: dict, node: dict) -> bool:
    if "operator" in node and node["operator"] in ["AND", "OR", "NOT"]:
        op = node["operator"]
        conditions = node.get("conditions", [])
        if op == "AND":
            return all(evaluate_node(row, cond) for cond in conditions)
        elif op == "OR":
            return any(evaluate_node(row, cond) for cond in conditions)
        elif op == "NOT":
            return not evaluate_node(row, conditions[0]) if conditions else True
    else:
        return evaluate_condition(row, node)

def classify_row(row: dict, must_have_ast: dict, good_to_have_ast: dict) -> tuple[str, str]:
    """
    Evaluates the AST against the row to determine classification.
    Returns (Classification, RulePathFired)
    """
    if must_have_ast and evaluate_node(row, must_have_ast):
        return "Must Have", "Evaluated True on MustHave AST"
    if good_to_have_ast and evaluate_node(row, good_to_have_ast):
        return "Good to Have", "Evaluated True on GoodToHave AST"
    return "Not Needed", "Fell through to Default Not Needed"
