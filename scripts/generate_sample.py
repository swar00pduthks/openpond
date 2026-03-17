import pandas as pd
import os

# Create data directory if it doesn't exist
os.makedirs("backend/data", exist_ok=True)

# Generate a sample CSV
df_csv = pd.DataFrame({
    "id": range(1, 101),
    "category": ["A", "B", "C", "D"] * 25,
    "sales": [x * 10 for x in range(1, 101)],
    "region": ["North", "South", "East", "West"] * 25
})
df_csv.to_csv("backend/data/sample_sales.csv", index=False)
print("Created backend/data/sample_sales.csv")

# Generate a sample Parquet
df_pq = pd.DataFrame({
    "user_id": range(1, 51),
    "age": [20 + (x % 40) for x in range(50)],
    "active": [True, False] * 25,
    "score": [x * 1.5 for x in range(1, 51)]
})
df_pq.to_parquet("backend/data/users.parquet")
print("Created backend/data/users.parquet")
