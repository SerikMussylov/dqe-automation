import pytest
import pandas as pd
from pathlib import Path

# Fixture to read the CSV file
@pytest.fixture(scope="session")
def path_to_file():
    return Path(__file__).resolve().parent.parent / "src" / "data" / "data.csv"

# Fixture to read the CSV file and return its content
@pytest.fixture(scope="session")
def csv_data(path_to_file):
    return pd.read_csv(path_to_file)

# Fixture to validate the schema of the file
@pytest.fixture(scope="session")
def validate_schema():
    def _validate(actual_schema, expected_schema):
        return list(actual_schema) == list(expected_schema)
    return _validate


# Pytest hook to mark unmarked tests with a custom mark
def pytest_collection_modifyitems(items):
    for item in items:
        if not list(item.iter_markers()):
            item.add_marker(pytest.mark.unmarked)