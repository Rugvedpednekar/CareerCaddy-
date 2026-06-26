import shutil
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
    target = folder / file.filename
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return target
