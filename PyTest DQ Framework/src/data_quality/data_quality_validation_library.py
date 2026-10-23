from collections import Counter
import math
from datetime import date, datetime
from decimal import Decimal
import numpy as np
import pandas as pd


class DataQualityLibrary:
    """
    A library of static methods for performing data quality checks on pandas DataFrames.

    This class is intended to be used in a PyTest-based testing framework to validate
    the quality of data in DataFrames. Each method performs a specific data quality
    check and uses assertions to ensure that the data meets the expected conditions.
    """

    @staticmethod
    def check_duplicates(df, column_names=None):
        if column_names is not None:
            missing_columns = [name for name in column_names if name not in df.columns]
            assert not missing_columns, f"Columns not found for uniqueness check: {missing_columns}"

        duplicate_mask = df.duplicated(subset=column_names, keep=False)
        duplicates = df.loc[duplicate_mask]
        assert duplicates.empty, (
            f"Found {len(duplicates)} duplicate rows; sample: "
            f"{duplicates.head(5).to_dict(orient='records')}"
        )

    @staticmethod
    def check_count(df_expected, df_actual):
        assert len(df_expected) == len(df_actual), (
            f"Row count mismatch: expected {len(df_expected)}, got {len(df_actual)}"
        )

    @staticmethod
    def check_data_completeness(df_expected, df_actual):
        expected_columns = list(df_expected.columns)
        actual_columns = list(df_actual.columns)
        assert set(expected_columns) == set(actual_columns), (
            f"Column mismatch: expected {expected_columns}, got {actual_columns}"
        )

        actual_data = df_actual[expected_columns]
        expected_rows = Counter(
            tuple(DataQualityLibrary._normalize_value(value) for value in row)
            for row in df_expected.itertuples(index=False, name=None)
        )
        actual_rows = Counter(
            tuple(DataQualityLibrary._normalize_value(value) for value in row)
            for row in actual_data.itertuples(index=False, name=None)
        )
        missing_rows = expected_rows - actual_rows
        unexpected_rows = actual_rows - expected_rows
        assert not missing_rows and not unexpected_rows, (
            "Data mismatch; "
            f"missing from actual: {DataQualityLibrary._format_row_counts(missing_rows, expected_columns)}; "
            f"unexpected in actual: {DataQualityLibrary._format_row_counts(unexpected_rows, expected_columns)}"
        )

    @staticmethod
    def _normalize_value(value):
        if value is None or value is pd.NaT:
            return None
        if isinstance(value, (bool, np.bool_)):
            return bool(value)
        if isinstance(value, (Decimal, float, np.floating)):
            number = float(value)
            return None if math.isnan(number) else round(number, 6)  # absorbs float noise only
        if isinstance(value, (int, np.integer)):
            return float(value)
        if isinstance(value, (pd.Timestamp, datetime)):
            return value.strftime('%Y-%m-%d') if value.time() == datetime.min.time() else value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return value

    @staticmethod
    def _format_row_counts(row_counts, columns):
        return [
            {"row": dict(zip(columns, row)), "count": count}
            for row, count in row_counts.most_common(5)
        ]

    @staticmethod
    def check_dataset_is_not_empty(df):
        assert not df.empty, "Dataset is empty"

    @staticmethod
    def check_not_null_values(df, column_names=None):
        if column_names is None:
            column_names = list(df.columns)

        missing_columns = [name for name in column_names if name not in df.columns]
        assert not missing_columns, f"Columns not found for not-null check: {missing_columns}"

        null_counts = df[column_names].isna().sum()
        null_counts = null_counts[null_counts > 0].to_dict()
        assert not null_counts, f"Null values found by column: {null_counts}"
