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
        
        if op == "=": return row_val == val
        if op == "!=": return row_val != val
        if op == "IN": return row_val in [v.strip() for v in val.split(",")]
        if op == "CONTAINS": return val.lower() in row_val.lower()
        if op == ">":
            try: return float(row_val) > float(val)
            except: return False
        if op == "<":
            try: return float(row_val) < float(val)
            except: return False
            
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
        df = pd.read_excel(original.file_path)
        
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
            supp_df = pd.read_excel(ds.file_path)
            
        supp_df = supp_df[[mapping.equipment_id_col, mapping.category_col]].copy()
        
        # Preserve the supplementary equipment ID before renaming the join key
        renamed_eq_col = f"{ds.name}.{mapping.equipment_id_col}"
        renamed_cat_col = f"{ds.name}.{mapping.category_col}"
        
        supp_df[renamed_eq_col] = supp_df[mapping.equipment_id_col]
        
        supp_df = supp_df.rename(columns={
            mapping.equipment_id_col: orig_eq_col,
            mapping.category_col: renamed_cat_col
        })
        
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
