from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app import schemas, models
from app.database import get_db
import shutil
import os
import uuid
from app.services.data_ingestion import ingest_dataset_profile

router = APIRouter(prefix="/projects/{project_id}/datasets", tags=["datasets"])

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=schemas.DatasetUpload)
def upload_dataset(
    project_id: int,
    name: str = Form(...),
    is_original: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Generate profile
    try:
        schema_json = ingest_dataset_profile(file_path)
        schema_json["filename"] = file.filename
    except Exception as e:
        schema_json = {"filename": file.filename, "error": str(e)}
        
    db_dataset = models.DatasetUpload(
        project_id=project_id,
        name=name,
        is_original=is_original,
        file_path=file_path,
        dataset_schema=schema_json
    )
    db.add(db_dataset)
    db.commit()
    db.refresh(db_dataset)
    return db_dataset

@router.get("/", response_model=list[schemas.DatasetUpload])
def list_datasets(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.DatasetUpload).filter(models.DatasetUpload.project_id == project_id).all()

@router.post("/{dataset_id}/mapping", response_model=schemas.ColumnMapping)
def create_or_update_mapping(
    project_id: int,
    dataset_id: int,
    mapping: schemas.ColumnMappingCreate,
    db: Session = Depends(get_db)
):
    dataset = db.query(models.DatasetUpload).filter(models.DatasetUpload.dataset_id == dataset_id, models.DatasetUpload.project_id == project_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    existing = db.query(models.ColumnMapping).filter(models.ColumnMapping.dataset_id == dataset_id).first()
    if existing:
        existing.equipment_id_col = mapping.equipment_id_col
        existing.category_col = mapping.category_col
        db.commit()
        db.refresh(existing)
        return existing
        
    new_mapping = models.ColumnMapping(
        dataset_id=dataset_id,
        equipment_id_col=mapping.equipment_id_col,
        category_col=mapping.category_col
    )
    db.add(new_mapping)
    db.commit()
    db.refresh(new_mapping)
    return new_mapping

@router.get("/{dataset_id}/mapping", response_model=schemas.ColumnMapping)
def get_mapping(project_id: int, dataset_id: int, db: Session = Depends(get_db)):
    mapping = db.query(models.ColumnMapping).filter(models.ColumnMapping.dataset_id == dataset_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping
