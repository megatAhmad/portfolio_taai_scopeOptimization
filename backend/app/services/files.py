from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import UPLOAD_DIR


def persist_upload(project_id: int, upload: UploadFile) -> Path:
    project_dir = UPLOAD_DIR / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    target = project_dir / f'{uuid4().hex}_{upload.filename}'
    with target.open('wb') as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return target


def purge_path(path: str) -> None:
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()
    parent = file_path.parent
    if parent.exists() and not any(parent.iterdir()):
        parent.rmdir()


def purge_tree(path: str) -> None:
    tree_path = Path(path)
    if tree_path.exists():
        shutil.rmtree(tree_path)
