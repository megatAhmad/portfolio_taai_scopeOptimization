from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
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
    sheet_name: Optional[str] = Form(None),
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
        schema_json = ingest_dataset_profile(file_path, sheet_name)
        schema_json["filename"] = file.filename
    except Exception as e:
        schema_json = {"filename": file.filename, "error": str(e)}
        
    db_dataset = models.DatasetUpload(
        project_id=project_id,
        name=name,
        is_original=is_original,
        file_path=file_path,
        sheet_name=sheet_name,
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
        
    existing_mapping = db.query(models.ColumnMapping).filter(models.ColumnMapping.dataset_id == dataset_id).first()
    if existing_mapping:
        existing_mapping.equipment_id_col = mapping.equipment_id_col
        existing_mapping.mapping_rules = mapping.mapping_rules
        existing_mapping.derived_column_name = mapping.derived_column_name
        existing_mapping.data_type = mapping.data_type
        existing_mapping.default_output = mapping.default_output
        existing_mapping.empty_output = mapping.empty_output
        new_mapping = existing_mapping
    else:
        new_mapping = models.ColumnMapping(
            dataset_id=dataset_id,
            equipment_id_col=mapping.equipment_id_col,
            category_col=mapping.category_col,
            mapping_rules=mapping.mapping_rules,
            derived_column_name=mapping.derived_column_name,
            data_type=mapping.data_type,
            default_output=mapping.default_output,
            empty_output=mapping.empty_output
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

@router.delete("/{dataset_id}")
def delete_dataset(project_id: int, dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(models.DatasetUpload).filter(models.DatasetUpload.dataset_id == dataset_id, models.DatasetUpload.project_id == project_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    if os.path.exists(dataset.file_path):
        try:
            os.remove(dataset.file_path)
        except:
            pass
            
    db.query(models.ColumnMapping).filter(models.ColumnMapping.dataset_id == dataset_id).delete()
    db.delete(dataset)
    db.commit()
    return {"message": "Dataset deleted successfully"}
