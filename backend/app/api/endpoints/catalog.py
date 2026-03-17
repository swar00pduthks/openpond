from fastapi import APIRouter
from ...services.marquez_client import list_datasets

router = APIRouter()

@router.get("/datasets")
def get_catalog_datasets():
    """
    Get all registered datasets from the catalog proxy (Marquez).
    """
    return list_datasets()
