import pytest
import re

EXPECTED_SCHEMA = ["id", "name", "age", "email", "is_active"]
EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")

def test_file_not_empty(csv_data):
    assert not csv_data.empty, "CSV file is empty: expected at least one data row"


@pytest.mark.validate_csv
@pytest.mark.xfail(reason="Known data issue: data.csv contains a duplicated row id=4")
def test_duplicates(csv_data):
    duplicates = csv_data[csv_data.duplicated(keep=False)]
    assert duplicates.empty, (
        f"Found {csv_data.duplicated().sum()} duplicate row(s):\n{duplicates.to_string(index=False)}"
    )

@pytest.mark.validate_csv
def test_validate_schema(csv_data, validate_schema):
    actual = list(csv_data.columns)
    assert validate_schema(actual, EXPECTED_SCHEMA), (
        f"Schema mismatch. Expected: {EXPECTED_SCHEMA}, actual: {actual}"
    )

@pytest.mark.validate_csv
@pytest.mark.skip(reason="Age validation is skipped for now")
def test_age_column_valid(csv_data):
    ages = csv_data["age"]
    invalid = csv_data[~ages.between(0, 100)]
    assert invalid.empty, (
        f"Age must be between 0 and 100. Invalid rows:\n{invalid[['id', 'age']].to_string(index=False)}"
    )

@pytest.mark.validate_csv
def test_email_column_valid(csv_data):
    is_valid = csv_data["email"].astype(str).apply(lambda e: bool(EMAIL_PATTERN.match(e)))
    invalid = csv_data[~is_valid]
    assert invalid.empty, (
        f"Invalid email format in {len(invalid)} row(s):\n{invalid[['id', 'email']].to_string(index=False)}"
    )

@pytest.mark.parametrize("id, is_active", [(1, False), (2, True)])
def test_active_players(csv_data, id, is_active):
    row = csv_data.loc[csv_data["id"] == id]
    assert not row.empty, f"No row with id={id} found in CSV"
    actual = bool(row["is_active"].iloc[0])
    assert actual == is_active, f"id={id}: expected is_active={is_active}, actual is_active={actual}"


def test_active_player(csv_data):
    row = csv_data.loc[csv_data["id"] == 2]
    assert not row.empty, "No row with id=2 found in CSV"
    actual = bool(row["is_active"].iloc[0])
    assert actual is True, f"id=2: expected is_active=True, actual is_active={actual}"
