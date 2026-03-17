import smallpond
import pandas as pd

sp = smallpond.init()

# Create dummy data
df = pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"]})
df.to_parquet("test.parquet")

# Read with smallpond
sp_df = sp.read_parquet("test.parquet")
print(sp_df)

result = sp.partial_sql("SELECT * FROM {0} WHERE id > 1", sp_df)
print(result.to_pandas())
