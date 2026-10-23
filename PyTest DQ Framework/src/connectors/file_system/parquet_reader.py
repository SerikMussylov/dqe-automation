from glob import glob
from os import fspath, path
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

class ParquetReader:
    """Reads all data files of a parquet dataset folder into one DataFrame.

    Files are read one by one so that hive partition folder names
    (e.g. partition_date=2000-01) are not added as extra columns.
    """

    def process(self, parquet_path, include_subfolders=False):
        root = Path(parquet_path)
        if not root.exists():
            raise FileNotFoundError(f"Parquet path does not exist: {parquet_path}")
        if root.is_file():
            files = [root]
        else:
            candidates = root.rglob("*") if include_subfolders else root.glob("*")
            files = sorted(p for p in candidates
                           if p.is_file() and not p.name.startswith((".", "_")))
        if not files:
            raise FileNotFoundError(f"No parquet files found under: {parquet_path}")
        frames = [pq.ParquetFile(f).read().to_pandas() for f in files]
        return pd.concat(frames, ignore_index=True)