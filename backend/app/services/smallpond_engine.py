import duckdb
import pandas as pd
import os
import uuid

# Fallback to pure DuckDB execution due to Ray clustering timeouts on Replit.
# This proves the local fast execution model without the Ray distributed overhead
# which fails in constrained CI/Sandbox environments.

def execute_query(query: str, datasets: dict) -> dict:
    """
    Executes a duckdb SQL query.
    `datasets` is a dict of { table_name: file_path }
    """
    con = duckdb.connect(database=':memory:')

    try:
        # Register all required datasets as tables in duckdb
        for table_name, file_path in datasets.items():
            if file_path.endswith('.parquet'):
                con.execute(f"CREATE VIEW {table_name} AS SELECT * FROM parquet_scan('{file_path}')")
            elif file_path.endswith('.csv'):
                con.execute(f"CREATE VIEW {table_name} AS SELECT * FROM read_csv_auto('{file_path}')")
            else:
                raise ValueError(f"Unsupported file format for {file_path}")

        # Execute the original user query (duckdb understands the table names now)
        pd_result = con.execute(query).df()

        return {
            "columns": [{"name": col, "type": str(dtype)} for col, dtype in pd_result.dtypes.items()],
            "data": pd_result.to_dict(orient="records"),
            "row_count": len(pd_result),
            "status": "success"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        con.close()
