import shutil
import uuid
from pathlib import Path
from fastapi import UploadFile
from .config import BASE_DIR, UPLOAD_DIR

def storage_root() -> Path:
    root = UPLOAD_DIR if UPLOAD_DIR.is_absolute() else BASE_DIR / UPLOAD_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root

def save_upload(file: UploadFile, *parts: str) -> Path:
    folder = storage_root().joinpath(*parts)
    folder.mkdir(parents=True, exist_ok=True)
    filename = Path(file.filename or "upload").name
    target = folder / f"{uuid.uuid4().hex[:12]}_{filename}"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return target
