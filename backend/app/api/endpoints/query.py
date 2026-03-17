from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from ...services.smallpond_engine import execute_query
from ...services.marquez_client import list_datasets, log_job_run

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    datasets_used: List[str] # List of table names referenced in query

@router.post("/execute")
def execute_sql_query(request: QueryRequest):
    """
    Execute a DuckDB SQL query via SmallPond and log the lineage.
    """
    # 1. Look up the physical paths from the catalog
    catalog = list_datasets()
    catalog_map = {ds['name']: ds['path'] for ds in catalog if 'name' in ds and 'path' in ds}

    # Check if all required datasets exist
    physical_datasets = {}
    for ds_name in request.datasets_used:
        if ds_name not in catalog_map:
            raise HTTPException(status_code=404, detail=f"Dataset '{ds_name}' not found in catalog.")
        physical_datasets[ds_name] = catalog_map[ds_name]

    # 2. Log START lineage event to Marquez
    job_name = f"UserQuery_{abs(hash(request.query)) % 10000}"
    run_id = log_job_run(job_name, request.query, request.datasets_used)

    # 3. Execute via SmallPond
    try:
        # Pass the map of table name -> file path
        # Example query: "SELECT * FROM sales_data"
        result = execute_query(request.query, physical_datasets)

        if result.get("status") == "error":
             raise HTTPException(status_code=500, detail=result.get("message"))

        # Log COMPLETE event (skipped for brevity, but would be here in prod)
        return {"run_id": run_id, "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
