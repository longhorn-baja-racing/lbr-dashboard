# test_loader.py
import os
from data_loader import DataLoader

# Create and use a DataLoader instance
loader = DataLoader()
# Get the directory of this script and load the CSV file relative to it
script_dir = os.path.dirname(os.path.abspath(__file__))
loader.load_file(os.path.join(script_dir, "sample_baja_log.csv"))

print("File loaded successfully!")

# Show available columns
columns = loader.get_columns()
print("\nAvailable sensor columns:")
for c in columns:
    print(" -", c)

# Pick one column to test
column_name = "wheel_fl_rpm"

# Test pandas version
timestamps_pd, values_pd = loader.get_data_pandas(column_name)
print(f"\nPandas version ({column_name}):")
print(timestamps_pd.head())   # first 5 timestamps
print(values_pd.head())       # first 5 values

# Test list version
timestamps_list, values_list = loader.get_data_lists(column_name)
print(f"\nList version ({column_name}):")
print(timestamps_list[:5])    # first 5 timestamps
print(values_list[:5])        # first 5 values