from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ClassificationRun, ClassificationRunArtifact, Dataset, Project, RuleSet
from app.schemas import (
    ClassificationResult,
    ClassificationRowsPage,
    ClassificationRunRead,
    DatasetInspectionResponse,
    DatasetRead,
    EquipmentIdCleaningConfig,
    MappingEntry,
    MatchingConfig,
    ProjectCreate,
    ProjectRead,
    RuleSetPayload,
    RuleSetRead,
)
from app.services.classification_storage import artifact_file_path, export_run_file, load_run_page, persist_run_artifacts
from app.services.dataframe_engine import (
    apply_derived_columns,
    apply_mapping,
    build_master_dataframe,
    classify_dataframe,
    inspect_upload,
    preview_dataframe,
    profile_dataframe,
    read_dataset,
    resolve_derived_columns,
    resolve_mapping_target,
    suggest_mappings,
    validate_upload_configuration,
)
from app.services.equipment_id_cleaning import apply_equipment_id_cleaning
from app.services.files import persist_upload, purge_path, purge_tree

router = APIRouter()
DEFAULT_PAGE_LIMIT = 100


def _serialize_run(run: ClassificationRun) -> ClassificationRunRead:
    return ClassificationRunRead(
        id=run.id,
        project_id=run.project_id,
        ruleset_id=run.ruleset_id,
        ruleset_version=run.ruleset_version,
        status=run.status,
        summary={key: int(value) for key, value in (run.summary or {}).items()},
        columns=[str(column) for column in (run.columns or [])],
        total_rows=int(run.total_rows or 0),
        created_at=run.created_at,
    )


def _load_rows_page(run: ClassificationRun, offset: int = 0, limit: int = DEFAULT_PAGE_LIMIT) -> ClassificationRowsPage:
    rows, explanations = load_run_page(run, offset=offset, limit=limit)
    return ClassificationRowsPage(
        run_id=run.id,
        rows=rows,
        explanations=explanations,
        columns=[str(column) for column in run.columns],
        total_rows=int(run.total_rows or 0),
        offset=offset,
        limit=limit,
    )


@router.get('/health')
def healthcheck():
    return {'status': 'ok'}


@router.post('/datasets/inspect-file', response_model=DatasetInspectionResponse)
def inspect_dataset_file(
    file: UploadFile = File(...),
    project_id: int | None = Form(None),
    role: str = Form('canonical'),
    sheet_name: str | None = Form(None),
    equipment_id_column: str | None = Form(None),
    equipment_id_cleaning_config: str = Form('{}'),
    db: Session = Depends(get_db),
):
    try:
        file_type, sheet_names, df = inspect_upload(file, sheet_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    canonical_columns: list[str] = []
    if project_id and role == 'supplementary':
        canonical = db.scalar(select(Dataset).where(Dataset.project_id == project_id, Dataset.role == 'canonical'))
        if canonical:
            canonical_columns = [entry['target'] for entry in canonical.mapping_rules if entry.get('include', True)]
            if not canonical_columns:
                canonical_columns = [profile['source'] for profile in canonical.schema_profile]

    if df is None:
        return DatasetInspectionResponse(
            file_name=file.filename,
            file_type=file_type,
            sheet_names=sheet_names,
            selected_sheet=None,
        )

    columns, preview_rows = preview_dataframe(df)
    profile = profile_dataframe(df)
    suggestions = suggest_mappings(columns, canonical_columns or columns)
    transformed_columns: list[str] = []
    transformed_preview_rows: list[dict[str, object]] = []
    audit_records = []
    transformed_row_count = 0
    changed_row_count = 0

    if equipment_id_column:
        if equipment_id_column not in columns:
            raise HTTPException(status_code=400, detail='Selected equipment ID column not found in inspected file')
        try:
            cleaning_config = EquipmentIdCleaningConfig.model_validate(json.loads(equipment_id_cleaning_config))
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f'Invalid equipment ID cleaning configuration: {exc}') from exc
        transformed_df, audits = apply_equipment_id_cleaning(df.copy(), equipment_id_column, cleaning_config)
        transformed_columns, transformed_preview_rows = preview_dataframe(transformed_df)
        audit_records = [item.model_dump() for item in audits]
        transformed_row_count = len(transformed_df)
        changed_row_count = sum(1 for item in audits if item.parse_status != 'unchanged')

    return DatasetInspectionResponse(
        file_name=file.filename,
        file_type=file_type,
        sheet_names=sheet_names,
        selected_sheet=sheet_name,
        columns=columns,
        preview_rows=preview_rows,
        schema_profile=profile,
        mapping_suggestions=suggestions,
        transformed_columns=transformed_columns,
        transformed_preview_rows=transformed_preview_rows,
        equipment_id_audit=audit_records,
        transformed_row_count=transformed_row_count,
        changed_row_count=changed_row_count,
    )


@router.get('/projects', response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(select(Project).order_by(Project.created_at.desc())).all()


@router.post('/projects', response_model=ProjectRead)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Project).where(Project.name == payload.name))
    if existing:
        raise HTTPException(status_code=400, detail='Project name already exists')
    project = Project(name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get('/projects/{project_id}')
def get_project_detail(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    ruleset = db.scalar(select(RuleSet).where(RuleSet.project_id == project_id).order_by(RuleSet.version_no.desc()))
    latest_run = db.scalar(select(ClassificationRun).where(ClassificationRun.project_id == project_id).order_by(ClassificationRun.created_at.desc()))
    return {
        'project': ProjectRead.model_validate(project),
        'datasets': [DatasetRead.model_validate(item) for item in sorted(project.datasets, key=lambda dataset: dataset.created_at)],
        'latest_ruleset': RuleSetRead.model_validate(ruleset) if ruleset else None,
        'latest_run': _serialize_run(latest_run) if latest_run else None,
    }


@router.delete('/projects/{project_id}')
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    for dataset in project.datasets:
        purge_path(dataset.file_path)
    for run in project.classification_runs:
        artifact_path = artifact_file_path(run, 'rows') or artifact_file_path(run, 'export') or artifact_file_path(run, 'explanations')
        if artifact_path:
            purge_tree(str(Path(artifact_path).parent))
    db.delete(project)
    db.commit()
    return {'message': 'Project deleted'}


@router.post('/projects/{project_id}/datasets', response_model=DatasetRead)
def upload_dataset(
    project_id: int,
    file: UploadFile = File(...),
    name: str = Form(...),
    role: str = Form(...),
    equipment_id_column: str = Form(...),
    canonical_join_column: str | None = Form(None),
    sheet_name: str | None = Form(None),
    mapping_rules: str = Form('[]'),
    derived_columns: str = Form('[]'),
    matching_config: str = Form('{"strategy":"normalized","fuzzy_threshold":0.82}'),
    equipment_id_cleaning_config: str = Form('{}'),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')

    if role == 'canonical':
        existing_canonical = db.scalar(select(Dataset).where(Dataset.project_id == project_id, Dataset.role == 'canonical'))
        if existing_canonical:
            raise HTTPException(status_code=400, detail='Canonical dataset already exists for this project')

    canonical_dataset = db.scalar(select(Dataset).where(Dataset.project_id == project_id, Dataset.role == 'canonical'))

    try:
        parsed_mapping_rules = [MappingEntry.model_validate(item).model_dump() for item in json.loads(mapping_rules)]
        parsed_derived = json.loads(derived_columns)
        parsed_matching = MatchingConfig.model_validate(json.loads(matching_config)).model_dump()
        parsed_cleaning = EquipmentIdCleaningConfig.model_validate(json.loads(equipment_id_cleaning_config)).model_dump()
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f'Invalid dataset configuration: {exc}') from exc

    if Path(file.filename).suffix.lower() in {'.xlsx', '.xls'} and not sheet_name:
        raise HTTPException(status_code=400, detail='Excel uploads require a selected sheet name')

    path = persist_upload(project_id, file)
    try:
        raw_df = read_dataset(str(path), file.filename, sheet_name)
        mapped_df = apply_mapping(raw_df, parsed_mapping_rules)
        validate_upload_configuration(
            raw_df=raw_df,
            mapped_df=mapped_df,
            mapping_rules=parsed_mapping_rules,
            equipment_id_column=equipment_id_column,
            role=role,
            canonical_join_column=canonical_join_column,
            canonical_dataset=canonical_dataset,
        )
        resolved_derived = resolve_derived_columns(parsed_derived, parsed_mapping_rules, [str(column) for column in mapped_df.columns])
        mapped_df = apply_derived_columns(mapped_df, resolved_derived)
        mapped_df, _ = apply_equipment_id_cleaning(mapped_df, resolve_mapping_target(parsed_mapping_rules, equipment_id_column), parsed_cleaning)
        _, preview_rows = preview_dataframe(mapped_df)
        schema_profile = [profile.model_dump() for profile in profile_dataframe(mapped_df)]
    except Exception as exc:
        purge_path(str(path))
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rename_map = {
        rule['source']: rule['target']
        for rule in parsed_mapping_rules
        if rule.get('include', True) and rule['target'] != rule['source']
    }

    dataset = Dataset(
        project_id=project_id,
        name=name,
        role=role,
        file_name=file.filename,
        file_path=str(path),
        sheet_name=sheet_name,
        equipment_id_column=equipment_id_column,
        canonical_join_column=canonical_join_column,
        column_mapping=rename_map,
        mapping_rules=parsed_mapping_rules,
        derived_columns=parsed_derived,
        preview_rows=preview_rows,
        schema_profile=schema_profile,
        matching_config=parsed_matching,
        equipment_id_cleaning_config=parsed_cleaning,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.delete('/datasets/{dataset_id}')
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail='Dataset not found')
    purge_path(dataset.file_path)
    db.delete(dataset)
    db.commit()
    return {'message': 'Dataset deleted'}


@router.post('/projects/{project_id}/rulesets', response_model=RuleSetRead)
def create_ruleset(project_id: int, payload: RuleSetPayload, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    latest_version = db.scalar(select(func.max(RuleSet.version_no)).where(RuleSet.project_id == project_id)) or 0
    ruleset = RuleSet(project_id=project_id, version_no=latest_version + 1, name=payload.name, ast_json=payload.ast_json.model_dump())
    db.add(ruleset)
    db.commit()
    db.refresh(ruleset)
    return ruleset


@router.get('/projects/{project_id}/rulesets/latest', response_model=RuleSetRead | None)
def get_latest_ruleset(project_id: int, db: Session = Depends(get_db)):
    return db.scalar(select(RuleSet).where(RuleSet.project_id == project_id).order_by(RuleSet.version_no.desc()))


@router.post('/projects/{project_id}/classify', response_model=ClassificationResult)
def classify_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')

    canonical = db.scalar(select(Dataset).where(Dataset.project_id == project_id, Dataset.role == 'canonical'))
    if not canonical:
        raise HTTPException(status_code=400, detail='Upload a canonical dataset first')

    supplementary = db.scalars(select(Dataset).where(Dataset.project_id == project_id, Dataset.role != 'canonical').order_by(Dataset.created_at)).all()
    ruleset = db.scalar(select(RuleSet).where(RuleSet.project_id == project_id).order_by(RuleSet.version_no.desc()))
    if not ruleset:
        raise HTTPException(status_code=400, detail='Create a rule set first')

    master = build_master_dataframe(canonical, supplementary)
    equipment_column = resolve_mapping_target(canonical.mapping_rules or [], canonical.equipment_id_column)
    classified, explanations = classify_dataframe(master, ruleset.ast_json, equipment_column)
    counts = {key: int(value) for key, value in classified['classification'].value_counts().to_dict().items()}
    rows = classified.where(classified.notna(), None).to_dict(orient='records')
    columns = [str(col) for col in classified.columns]

    run = ClassificationRun(
        project_id=project_id,
        ruleset_id=ruleset.id,
        ruleset_version=ruleset.version_no,
        status='completed',
        summary=counts,
        columns=columns,
        total_rows=len(rows),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    artifacts = persist_run_artifacts(run.id, rows, explanations, columns)
    for artifact in artifacts:
        db.add(
            ClassificationRunArtifact(
                run_id=run.id,
                artifact_type=artifact['artifact_type'],
                file_path=artifact['file_path'],
                format=artifact['format'],
            )
        )
    db.commit()
    db.refresh(run)

    page = _load_rows_page(run, offset=0, limit=DEFAULT_PAGE_LIMIT)
    return ClassificationResult(
        run_id=run.id,
        summary=run.summary,
        rows=page.rows,
        columns=page.columns,
        ruleset_version=run.ruleset_version,
        explanations=page.explanations,
        total_rows=run.total_rows,
        offset=page.offset,
        limit=page.limit,
    )


@router.get('/projects/{project_id}/classification-runs', response_model=list[ClassificationRunRead])
def list_classification_runs(project_id: int, db: Session = Depends(get_db)):
    runs = db.scalars(select(ClassificationRun).where(ClassificationRun.project_id == project_id).order_by(ClassificationRun.created_at.desc())).all()
    return [_serialize_run(run) for run in runs]


@router.get('/classification-runs/{run_id}', response_model=ClassificationRunRead)
def get_classification_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(ClassificationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='Classification run not found')
    return _serialize_run(run)


@router.get('/classification-runs/{run_id}/rows', response_model=ClassificationRowsPage)
def get_classification_run_rows(
    run_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=500),
    db: Session = Depends(get_db),
):
    run = db.get(ClassificationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='Classification run not found')
    return _load_rows_page(run, offset=offset, limit=limit)


@router.get('/classification-runs/{run_id}/export')
def export_classification_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(ClassificationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='Classification run not found')
    try:
        return export_run_file(run)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
