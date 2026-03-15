import requests
import json
import uuid
import datetime
import os

MARQUEZ_URL = os.environ.get("MARQUEZ_URL", "http://localhost:5000")
NAMESPACE = "pondhouse_default"
DATA_DIR = "backend/data"

def _ensure_namespace():
    """Ensure the namespace exists in Marquez (mocked for now if no connection)"""
    try:
        url = f"{MARQUEZ_URL}/api/v1/namespaces/{NAMESPACE}"
        res = requests.put(url, json={
            "ownerName": "PondHouse_System",
            "description": "Default namespace for PondHouse analytics"
        }, timeout=2)
        return True
    except Exception:
        # Fallback to local file mock
        return False

def list_datasets():
    """
    List datasets registered.
    If Marquez is down, fallback to reading the data directory.
    """
    try:
        url = f"{MARQUEZ_URL}/api/v1/namespaces/{NAMESPACE}/datasets"
        res = requests.get(url, timeout=2)
        if res.status_code == 200:
            return res.json().get('datasets', [])
    except Exception:
        pass

    # Local fallback logic
    datasets = []
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if f.endswith('.csv') or f.endswith('.parquet'):
                file_path = os.path.join(DATA_DIR, f)
                stat = os.stat(file_path)
                datasets.append({
                    "name": f.split('.')[0], # e.g. "sales_data"
                    "physicalName": f,
                    "createdAt": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat() + "Z",
                    "updatedAt": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z",
                    "namespace": NAMESPACE,
                    "sourceName": "local_fs",
                    "type": "FILE",
                    "description": "Local file fallback",
                    "fields": [],
                    "tags": [],
                    "path": file_path # custom field for our engine
                })
    return datasets

def register_dataset(file_name, file_path, schema=None):
    """Register a new dataset in Marquez (mocked with local storage)"""
    dataset_name = file_name.split('.')[0]

    payload = {
        "type": "DB_TABLE", # Treating files as tables
        "physicalName": file_name,
        "sourceName": "local_fs",
        "fields": schema or [],
        "description": f"Uploaded via PondHouse at {datetime.datetime.now().isoformat()}"
    }

    try:
        url = f"{MARQUEZ_URL}/api/v1/namespaces/{NAMESPACE}/datasets/{dataset_name}"
        requests.put(url, json=payload, timeout=2)
    except Exception as e:
        print(f"Warning: Failed to reach Marquez, falling back to local. Error: {e}")

    return dataset_name

def log_job_run(job_name, query, input_datasets, output_dataset=None):
    """
    Simulates sending an OpenLineage event to Marquez
    """
    run_id = str(uuid.uuid4())
    event_time = datetime.datetime.now().isoformat() + "Z"

    # Building the OpenLineage payload structure
    openlineage_event = {
        "eventType": "START",
        "eventTime": event_time,
        "run": {
            "runId": run_id
        },
        "job": {
            "namespace": NAMESPACE,
            "name": job_name,
            "facets": {
                "sql": {
                    "_producer": "pondhouse",
                    "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SQLJobFacet.json",
                    "query": query
                }
            }
        },
        "inputs": [
            {
                "namespace": NAMESPACE,
                "name": ds
            } for ds in input_datasets
        ],
        "outputs": []
    }

    if output_dataset:
         openlineage_event["outputs"].append({
             "namespace": NAMESPACE,
             "name": output_dataset
         })

    try:
        url = f"{MARQUEZ_URL}/api/v1/lineage"
        requests.post(url, json=openlineage_event, timeout=2)
        print(f"✅ Lineage logged to Marquez: Job={job_name}, RunID={run_id}")
    except Exception as e:
         # Log to console for MVP proof
         print(f"ℹ️ [MOCK] Lineage event generated (Marquez unreachable): \n{json.dumps(openlineage_event, indent=2)}")

    return run_id
