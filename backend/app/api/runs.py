from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, models
from app.database import get_db
import pandas as pd
import json

router = APIRouter(prefix="/projects/{project_id}/classify", tags=["runs"])

def evaluate_node(row, node):
    if not node: return False
    
    if node.get("type") == "group":
        cond = node.get("condition", "AND")
        rules = node.get("rules", [])
        if not rules: return False
        
        results = [evaluate_node(row, r) for r in rules]
        if cond == "AND": return all(results)
        if cond == "OR": return any(results)
        if cond == "NOT": return not all(results) # Simplified NOT
        return False
        
    elif node.get("type") == "rule":
        field = node.get("field", "")
        op = node.get("operator", "=")
        val = str(node.get("value", ""))
        
        row_val = str(row.get(field, ""))
        
        def is_numeric():
            try:
                float(row_val)
                float(val)
                return True
            except: return False
        
        if op == "=": return row_val == val
        if op == "!=": return row_val != val
        if op == "IN": return row_val in [v.strip() for v in val.split(",")]
        if op == "CONTAINS": return str(val).lower() in str(row_val).lower()
        if op == ">": return float(row_val) > float(val) if is_numeric() else str(row_val) > str(val)
        if op == "<": return float(row_val) < float(val) if is_numeric() else str(row_val) < str(val)
        if op == ">=": return float(row_val) >= float(val) if is_numeric() else str(row_val) >= str(val)
        if op == "<=": return float(row_val) <= float(val) if is_numeric() else str(row_val) <= str(val)
        
        return False

def evaluate_row(row, ast):
    if not ast: return "Not Needed"
    
    if evaluate_node(row, ast.get("mustHave")):
        return "Must Have"
    if evaluate_node(row, ast.get("goodToHave")):
        return "Good to Have"
        
    return "Not Needed"

@router.post("/")
def run_classification(project_id: int, db: Session = Depends(get_db)):
    datasets = db.query(models.DatasetUpload).filter(models.DatasetUpload.project_id == project_id).all()
    if not datasets:
        raise HTTPException(status_code=400, detail="No datasets uploaded for this project")
        
    original = next((d for d in datasets if d.is_original), None)
    if not original:
        original = datasets[0]
        
    # Read original
    df = None
    if original.file_path.endswith(".csv"):
        df = pd.read_csv(original.file_path)
    else:
        df = pd.read_excel(original.file_path, sheet_name=original.sheet_name)
        
    orig_mapping = db.query(models.ColumnMapping).filter(models.ColumnMapping.dataset_id == original.dataset_id).first()
    if not orig_mapping or not orig_mapping.equipment_id_col:
        # Fallback to first column
        orig_eq_col = df.columns[0]
    else:
        orig_eq_col = orig_mapping.equipment_id_col
        
    # Join supplementary
    for ds in datasets:
        if ds.dataset_id == original.dataset_id: continue
        
        mapping = db.query(models.ColumnMapping).filter(models.ColumnMapping.dataset_id == ds.dataset_id).first()
        if not mapping or not mapping.equipment_id_col or not mapping.category_col:
            continue
            
        supp_df = None
        if ds.file_path.endswith(".csv"):
            supp_df = pd.read_csv(ds.file_path)
        else:
            supp_df = pd.read_excel(ds.file_path, sheet_name=ds.sheet_name)
            
        supp_df = supp_df[[mapping.equipment_id_col, mapping.category_col]].copy()
        
        # Preserve the supplementary equipment ID before renaming the join key
        renamed_eq_col = f"{ds.name}.{mapping.equipment_id_col}"
        renamed_cat_col = f"{ds.name}.{mapping.category_col}"
        
        supp_df[renamed_eq_col] = supp_df[mapping.equipment_id_col]
        
        derived_name = getattr(mapping, "derived_column_name", None)
        final_cat_col = derived_name if derived_name else renamed_cat_col
        data_type = getattr(mapping, "data_type", "text")
        
        supp_df = supp_df.rename(columns={
            mapping.equipment_id_col: orig_eq_col,
            mapping.category_col: final_cat_col
        })
        
        # Apply mapping rules to derive logic
        if getattr(mapping, "mapping_rules", None) and isinstance(mapping.mapping_rules, list) and len(mapping.mapping_rules) > 0:
            def apply_mapping_rules(row_val):
                empty_opt = getattr(mapping, "empty_output", "N/A")
                if pd.isna(row_val) or str(row_val).strip() == "": return empty_opt
                rv = row_val
                
                # Type handling for the source row value
                if data_type == "numeric":
                    try: rv = float(rv)
                    except: return row_val # fail safe
                elif data_type == "date":
                    try: rv = pd.to_datetime(rv)
                    except: return row_val
                else:
                    rv = str(rv)

                for rule in mapping.mapping_rules:
                    op = rule.get("operator", "=")
                    val = rule.get("value", "")
                    end_val = rule.get("value_end", "")
                    out = rule.get("output", "")
                    
                    tgt = val
                    tgt_end = end_val
                    
                    # Type handling for targets
                    if data_type == "numeric":
                        try: tgt = float(val); tgt_end = float(end_val) if end_val else 0
                        except: pass
                    elif data_type == "date":
                        try: tgt = pd.to_datetime(val); tgt_end = pd.to_datetime(end_val) if end_val else None
                        except: pass
                    else:
                        tgt = str(val); tgt_end = str(end_val)
                    
                    try:
                        if op == "=" and rv == tgt: return out
                        if op == "!=" and rv != tgt: return out
                        if op == ">" and rv > tgt: return out
                        if op == "<" and rv < tgt: return out
                        if op == ">=" and rv >= tgt: return out
                        if op == "<=" and rv <= tgt: return out
                        if op == "BETWEEN":
                            if tgt_end is not None and tgt <= rv <= tgt_end: return out
                    except: pass
                    
                return getattr(mapping, "default_output", "N/A")
                
            supp_df[final_cat_col] = supp_df[final_cat_col].apply(apply_mapping_rules)
            
        # Merge
        df = pd.merge(df, supp_df, on=orig_eq_col, how="left")
        
    # Load rules
    latest_rule = db.query(models.RuleSet).filter(models.RuleSet.project_id == project_id).order_by(models.RuleSet.version_no.desc()).first()
    ast = latest_rule.ast_json if latest_rule else None
    
    # Classify
    df["Classification"] = df.apply(lambda row: evaluate_row(row.to_dict(), ast), axis=1)
    
    # Generate summary
    summary = df["Classification"].value_counts().to_dict()
    # Format response
    records = df.fillna("").to_dict(orient="records")
    
    return {
        "summary": summary,
        "rows": records[:1000] # Return up to 1000 rows for the preview
    }
