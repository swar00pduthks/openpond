import os
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException
from ...services.marquez_client import register_dataset

router = APIRouter()

DATA_DIR = "backend/data"

@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    """
    Ingest data into the platform (local storage for MVP).
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Security fix: Prevent Path Traversal by extracting just the base filename
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(DATA_DIR, safe_filename)

    if not (safe_filename.endswith(".csv") or safe_filename.endswith(".parquet")):
        raise HTTPException(status_code=400, detail="Only CSV and Parquet files are supported")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Register the dataset in our catalog (Marquez proxy)
        dataset_name = register_dataset(safe_filename, file_path)

        return {"status": "success", "message": f"File {safe_filename} uploaded and registered as dataset '{dataset_name}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
