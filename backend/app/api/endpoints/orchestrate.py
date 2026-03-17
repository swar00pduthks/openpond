from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
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

    # Initialize a default error reference
    current_task_id = "initialization"

    try:
        # Pre-register physical datasets needed by the DAG
        for task in agent_dag.get("tasks", []):
            for input_ds in task.get("inputs", []):
                if input_ds in catalog_map:
                    file_uri = catalog_map[input_ds]
                    if file_uri.endswith('.parquet'):
                        con.execute(f"CREATE OR REPLACE VIEW {input_ds} AS SELECT * FROM parquet_scan('{file_uri}')")
                    elif file_uri.endswith('.csv'):
                        con.execute(f"CREATE OR REPLACE VIEW {input_ds} AS SELECT * FROM read_csv_auto('{file_uri}')")

        # Execute the DAG sequentially
        for task in agent_dag.get("tasks", []):
            current_task_id = task.get("task_id", "unknown")
            job_name = f"AAF_{agent_dag['dag_id']}_{current_task_id}"

            outputs = task.get("outputs", [])
            output_name = outputs[0] if outputs else None

            run_id = log_job_run(job_name, task["query"], task.get("inputs", []), output_name)

            pd_result = con.execute(task["query"]).df()

            dag_results.append({
                "task_id": current_task_id,
                "run_id": run_id,
                "status": "success",
                "columns": [{"name": col, "type": str(dtype)} for col, dtype in pd_result.dtypes.items()] if not pd_result.empty else [],
                "data": pd_result.to_dict(orient="records") if not pd_result.empty else [],
                "row_count": len(pd_result)
            })

    except Exception as e:
        con.close()
        raise HTTPException(status_code=500, detail=f"AAF DAG Execution Failed at node '{current_task_id}': {str(e)}")

    con.close()

    return {
        "dag_id": agent_dag.get("dag_id", "unknown"),
        "results": dag_results
    }
