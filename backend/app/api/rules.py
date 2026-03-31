from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, models
from app.database import get_db

router = APIRouter(prefix="/projects/{project_id}/rules", tags=["rules"])

@router.post("/", response_model=schemas.RuleSet)
def create_rule_set(
    project_id: int,
    rule_set: schemas.RuleSetCreate,
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Find latest version_no
    latest = db.query(models.RuleSet).filter(models.RuleSet.project_id == project_id).order_by(models.RuleSet.version_no.desc()).first()
    version_no = latest.version_no + 1 if latest else 1

    db_rule_set = models.RuleSet(
        project_id=project_id,
        version_no=version_no,
        **rule_set.model_dump()
    )
    db.add(db_rule_set)
    db.commit()
    db.refresh(db_rule_set)
    return db_rule_set

@router.get("/", response_model=list[schemas.RuleSet])
def list_rule_sets(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.RuleSet).filter(models.RuleSet.project_id == project_id).all()
