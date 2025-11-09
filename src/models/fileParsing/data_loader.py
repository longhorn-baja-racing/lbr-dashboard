import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal


class DataLoader(QObject):
    """Handles loading and parsing of telemetry log files for the dashboard."""

    file_loaded = pyqtSignal(str)
    load_failed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.df = None
        self.file_path = None

    def load_file(self, file_path: str):
        """Load CSV or Parquet file into a pandas DataFrame."""
        try:
            if file_path.endswith(".csv"):
                self.df = pd.read_csv(file_path)
            elif file_path.endswith(".parquet"):
                self.df = pd.read_parquet(file_path)
            else:
                raise ValueError("Unsupported file format (use .csv or .parquet).")

            if "timestamp_ms" not in self.df.columns:
                raise ValueError("Missing 'timestamp_ms' column in log file.")

            # Convert numeric timestamps to timedelta for time-based plotting
            self.df["timestamp_ms"] = pd.to_timedelta(self.df["timestamp_ms"], unit="ms")

            self.file_path = file_path
            self.file_loaded.emit(file_path)

        except Exception as e:
            self.load_failed.emit(str(e))

    def get_columns(self):
        """Return a list of available sensor columns (excluding timestamp)."""
        if self.df is None:
            return []
        return [col for col in self.df.columns if col != "timestamp_ms"]

    # --- Version 1: pandas-style output ---
    def get_data_pandas(self, column_name: str):
        """
        Return timestamps and values as pandas Series (for pandas/pyqtgraph usage).
        Timestamp column will be a pandas Timedelta.
        """
        if self.df is None or column_name not in self.df.columns:
            return None, None

        timestamps = self.df["timestamp_ms"]       # pandas Timedelta Series
        values = self.df[column_name]              # pandas Series for the sensor
        return timestamps, values

    # --- Version 2: plain Python lists ---
    def get_data_lists(self, column_name: str):
        """
        Return timestamps and values as regular Python lists (for lightweight plotting).
        Timestamps are converted to milliseconds as floats.
        """
        if self.df is None or column_name not in self.df.columns:
            return None, None

        timestamps = self.df["timestamp_ms"].dt.total_seconds().mul(1000).tolist()
        values = self.df[column_name].tolist()
        return timestamps, values
