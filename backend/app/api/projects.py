from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, models
from app.database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("/", response_model=list[schemas.Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Project).offset(skip).limit(limit).all()

@router.get("/{project_id}", response_model=schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

import os
@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Delete uploaded files on disk
    datasets = db.query(models.DatasetUpload).filter(models.DatasetUpload.project_id == project_id).all()
    for ds in datasets:
        if os.path.exists(ds.file_path):
            try:
                os.remove(ds.file_path)
            except:
                pass
                
    # Manually delete related records to prevent FK constraints issues if sqlite CASCADE is off
    db.query(models.RuleSet).filter(models.RuleSet.project_id == project_id).delete()
    db.query(models.ClassificationRun).filter(models.ClassificationRun.project_id == project_id).delete()
    for ds in datasets:
        db.query(models.ColumnMapping).filter(models.ColumnMapping.dataset_id == ds.dataset_id).delete()
    db.query(models.DatasetUpload).filter(models.DatasetUpload.project_id == project_id).delete()
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}
