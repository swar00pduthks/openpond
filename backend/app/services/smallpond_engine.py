import smallpond
import pandas as pd
import duckdb
import os
import uuid

# Global session instance
_sp_session = None
RAY_ADDRESS = os.environ.get("RAY_ADDRESS") # e.g., "ray://ray-cluster-head-svc:10001" for K8s

def get_session():
    global _sp_session
    if _sp_session is None:
        if RAY_ADDRESS:
            # Connect to scalable K8s Ray cluster (Azure/AWS/GCP)
            _sp_session = smallpond.init(ray_address=RAY_ADDRESS)
        else:
            # Fallback for local / Sandbox MVP
            # DuckDB direct fallback was used previously to bypass Replit Sandbox memory crashes
            _sp_session = None
    return _sp_session

def execute_query(query: str, datasets: dict) -> dict:
    """
    Executes a duckdb SQL query either distributed on K8s (SmallPond) or local fallback (DuckDB).
    `datasets` is a dict of { table_name: file_path/URI }
    """
    sp = get_session()

    # --- DISTRIBUTED CLOUD EXECUTION (SmallPond on Ray K8s Cluster) ---
    if sp is not None:
        sp_dfs = {}
        for table_name, file_uri in datasets.items():
            if file_uri.endswith('.parquet'):
                sp_dfs[table_name] = sp.read_parquet(file_uri)
            elif file_uri.endswith('.csv'):
                # Handle CSV directly or via duckdb integration
                sp_dfs[table_name] = sp.read_csv(file_uri)

        ordered_dfs = []
        formatted_query = query
        for idx, (table_name, sp_df) in enumerate(sp_dfs.items()):
            formatted_query = formatted_query.replace(table_name, f"{{{idx}}}")
            ordered_dfs.append(sp_df)

        try:
            result_df = sp.partial_sql(formatted_query, *ordered_dfs)
            pd_result = result_df.to_pandas()
            return {
                "columns": [{"name": col, "type": str(dtype)} for col, dtype in pd_result.dtypes.items()],
                "data": pd_result.to_dict(orient="records"),
                "row_count": len(pd_result),
                "status": "success"
            }
        except Exception as e:
            return {"status": "error", "message": f"SmallPond (Ray Cluster) Error: {str(e)}"}

    # --- LOCAL SANDBOX EXECUTION (Pure DuckDB Fallback) ---
    else:
        con = duckdb.connect(database=':memory:')
        try:
            for table_name, file_uri in datasets.items():
                if file_uri.endswith('.parquet'):
                    con.execute(f"CREATE VIEW {table_name} AS SELECT * FROM parquet_scan('{file_uri}')")
                elif file_uri.endswith('.csv'):
                    con.execute(f"CREATE VIEW {table_name} AS SELECT * FROM read_csv_auto('{file_uri}')")
            pd_result = con.execute(query).df()
            return {
                "columns": [{"name": col, "type": str(dtype)} for col, dtype in pd_result.dtypes.items()],
                "data": pd_result.to_dict(orient="records"),
                "row_count": len(pd_result),
                "status": "success"
            }
        except Exception as e:
            return {"status": "error", "message": f"Local DuckDB Error: {str(e)}"}
        finally:
            con.close()
