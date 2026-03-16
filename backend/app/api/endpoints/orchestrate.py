from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import duckdb

from ...services.marquez_client import list_datasets, log_job_run
from ...services.aaf_agent import parse_natural_language_to_dag

router = APIRouter()

class PlanRequest(BaseModel):
    prompt: str

class ExecuteRequest(BaseModel):
    dag: Dict[str, Any]

@router.post("/plan")
def generate_aaf_dag(request: PlanRequest):
    """
    Step 1: AAF Agent generates the DAG plan without executing it.
    """
    catalog = list_datasets()
    catalog_map = {ds['name']: ds['path'] for ds in catalog if 'name' in ds and 'path' in ds}

    agent_dag = parse_natural_language_to_dag(request.prompt, catalog_map.keys())
    return agent_dag

@router.post("/execute")
def execute_aaf_dag(request: ExecuteRequest):
    """
    Step 2: User confirmed the DAG. Execute it via Engine -> Log to Marquez.
    """
    catalog = list_datasets()
    catalog_map = {ds['name']: ds['path'] for ds in catalog if 'name' in ds and 'path' in ds}

    agent_dag = request.dag
    dag_results = []

    con = duckdb.connect(database=':memory:')
    try:
        # Pre-register physical datasets needed by the DAG
        for task in agent_dag["tasks"]:
            for input_ds in task["inputs"]:
                if input_ds in catalog_map:
                    file_uri = catalog_map[input_ds]
                    if file_uri.endswith('.parquet'):
                        con.execute(f"CREATE OR REPLACE VIEW {input_ds} AS SELECT * FROM parquet_scan('{file_uri}')")
                    elif file_uri.endswith('.csv'):
                        con.execute(f"CREATE OR REPLACE VIEW {input_ds} AS SELECT * FROM read_csv_auto('{file_uri}')")

        # Execute the DAG sequentially
        for task in agent_dag["tasks"]:
            job_name = f"AAF_{agent_dag['dag_id']}_{task['task_id']}"
            run_id = log_job_run(job_name, task["query"], task["inputs"], task["outputs"][0] if task["outputs"] else None)

            pd_result = con.execute(task["query"]).df()

            dag_results.append({
                "task_id": task["task_id"],
                "run_id": run_id,
                "status": "success",
                "columns": [{"name": col, "type": str(dtype)} for col, dtype in pd_result.dtypes.items()] if not pd_result.empty else [],
                "data": pd_result.to_dict(orient="records") if not pd_result.empty else [],
                "row_count": len(pd_result)
            })

    except Exception as e:
        con.close()
        raise HTTPException(status_code=500, detail=f"AAF DAG Execution Failed at node '{task['task_id']}': {str(e)}")

    con.close()

    return {
        "dag_id": agent_dag["dag_id"],
        "results": dag_results
    }
