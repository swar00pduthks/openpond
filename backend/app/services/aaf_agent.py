import json
import uuid

# This service acts as the bridge to the user's AAF (Agent Application Framework).
# In production, this would initialize an AAF Agent (e.g., DataEngineerAgent),
# provide it tools to read the Marquez Catalog, and prompt it to generate a DAG of SQL tasks.

def parse_natural_language_to_dag(prompt: str, available_datasets: list) -> dict:
    """
    Simulates the AAF LLM response.
    Given a natural language prompt, the AAF Agent returns a JSON DAG of DuckDB SQL executions.
    """

    # In a real scenario, we pass `prompt` and `available_datasets` schemas to the AAF LLM.
    # For this MVP proof-of-concept, if the prompt asks to join sales and users, we return a mock DAG.

    prompt_lower = prompt.lower()

    if "join" in prompt_lower and "sales" in prompt_lower and "user" in prompt_lower:
        # The AAF Agent generates a two-step DAG:
        # Step 1: Filter active users (ETL)
        # Step 2: Join with sales (Analytics)
        dag_id = f"aaf_pipeline_{uuid.uuid4().hex[:8]}"

        return {
            "dag_id": dag_id,
            "agent_reasoning": "I found 'sample_sales' and 'users' in the catalog. I will first filter active users, then join their scores with the sales data aggregated by category.",
            "tasks": [
                {
                    "task_id": "filter_active_users",
                    "depends_on": [],
                    "query": "CREATE OR REPLACE VIEW active_users AS SELECT user_id, age, score FROM users WHERE active = true",
                    "inputs": ["users"],
                    "outputs": ["active_users"]
                },
                {
                    "task_id": "analyze_sales_by_active_users",
                    "depends_on": ["filter_active_users"],
                    # Note: Joining on a mock condition since the sample data doesn't share a clean key,
                    # but this proves the SQL DAG generation capability.
                    "query": "SELECT s.category, SUM(s.sales) as total_sales, AVG(u.score) as avg_user_score FROM sample_sales s CROSS JOIN active_users u GROUP BY s.category",
                    "inputs": ["sample_sales", "active_users"],
                    "outputs": ["final_analysis_result"]
                }
            ]
        }

    # Fallback default single-step DAG if the prompt is unrecognized
    return {
        "dag_id": f"aaf_pipeline_{uuid.uuid4().hex[:8]}",
        "agent_reasoning": "I did not recognize specific tables to join, so I am running a basic summary on the sales data.",
        "tasks": [
            {
                "task_id": "default_summary",
                "depends_on": [],
                "query": "SELECT category, SUM(sales) as total_sales FROM sample_sales GROUP BY category",
                "inputs": ["sample_sales"],
                "outputs": ["summary_result"]
            }
        ]
    }
