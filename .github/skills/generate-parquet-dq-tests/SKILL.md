---
name: generate-parquet-dq-tests
description: >-
  Generates one mapping-based PyTest DQ module per Parquet dataset. Invoke explicitly
  after the framework exists; it must refuse framework, Jenkins, or conftest changes.
disable-model-invocation: true
---

## When this skill applies

Use this skill only for Step 3 of the PyTest DQ assignment, after the framework and this skill are reviewed. The framework must already provide the connectors, fixtures, pytest markers, and `DataQualityLibrary` methods specified below.

Generate only `PyTest DQ Framework/tests/dq checks/parquet_files/test_<dataset_name>.py`, one dataset per module. Do not modify framework source, fixtures, Jenkins configuration, or other tests. If asked to modify those files, or if required framework methods/fixtures are missing, stop and report the blocker instead of expanding scope.

## Inputs you must have

Have the dataset folder name, the dataset's definition in `docs/parquet-aggregated-data-mapping.md`, and the requirement id and author name for the module header. The mapping is authoritative for output columns, grain, measures, filters, and partitioning. If it is absent or does not define enough information to derive a source query, stop and ask for clarification.

Use `docs/project-environment.md` only to establish documented source-table relationships and foreign keys. Do not inspect or use `data_dev/`, pipeline SQL, parquet-loader SQL, previews, or existing output data to derive expected results.

## Hard rules

1. Create only `PyTest DQ Framework/tests/dq checks/parquet_files/test_<dataset_name>.py`. Do not create, edit, or repair framework files.
2. PostgreSQL is `source_data` (expected); Parquet is `target_data` (actual). Never swap their fixtures or compare a dataset with itself.
3. Derive the PostgreSQL query from the data mapping only, using documented source relationships as needed. Do not read `data_dev/` or copy SQL from pipeline code.
4. Add only joins, aggregations, rounding, filters, and expressions supported by the mapping or documented relationships. Do not invent `UNION`, extra `WHERE`, `CASE`, sign changes, or other pipeline behavior.
5. Alias every selected expression to its mapped output column name, and group by exactly the mapped dimensions/grain.
6. Keep this skill dataset-agnostic: never include concrete expected SQL for any named dataset.
7. Read `/parquet_data/<dataset_name>` through `parquet_reader.process(target_path, include_subfolders=True)`.
8. Include all five checks: non-empty smoke, data completeness, count, uniqueness, and not-null. Call the corresponding `DataQualityLibrary` methods; do not reimplement their logic in tests.
9. Every test has `parquet_data` and the dataset-specific marker. Add `smoke` only to the non-empty test.
10. The not-null check lists every mapped output column. Uniqueness checks the mapped grain columns so duplicate keys with differing measures are detected.
11. Do not weaken or rewrite mapping-derived SQL to make a test pass. A mismatch is evidence to report, not a reason to alter expected results.

## Workflow

1. Read the selected dataset's complete mapping entry. Record its output names, source tables/columns, grain, measures, filters, and partition details.
2. Derive an independent PostgreSQL SELECT: join only the documented tables needed for mapped columns; compute each mapped measure; apply only mapping-stated transformations; alias to the output names; group by the mapped grain.
3. Create one module at the required path using the template below. Fill the source query and output-column list from the mapping, and set the author and requirement header fields supplied by the user.
4. Keep `source_data` backed by `db_connection.get_data_sql(...)` and `target_data` backed by the dataset's Parquet folder with subfolders enabled.
5. Add all five library-backed checks and the required markers. Ensure only the not-empty test has the `smoke` marker.
6. Review the module against the Hard rules and the self-review checklist. Do not run pytest unless the user asks for execution; do not change expected SQL based on test results.


```python
"""
Description: Data Quality checks for <dataset_name> dataset.
Requirement(s): <requirement_id>
Author(s): <name>
"""

import pytest


@pytest.fixture(scope='module')
def source_data(db_connection):
    source_query = """
    -- expected query derived from mapping (grain + measures + joins)
    """
    return db_connection.get_data_sql(source_query)


@pytest.fixture(scope='module')
def target_data(parquet_reader):
    target_path = '/parquet_data/<dataset_name>'
    return parquet_reader.process(target_path, include_subfolders=True)


@pytest.mark.parquet_data
@pytest.mark.smoke
@pytest.mark.<dataset_name>
def test_check_dataset_is_not_empty(target_data, data_quality_library):
    data_quality_library.check_dataset_is_not_empty(target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_data_completeness(source_data, target_data, data_quality_library):
    data_quality_library.check_data_completeness(source_data, target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_count(source_data, target_data, data_quality_library):
    data_quality_library.check_count(source_data, target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_uniqueness(target_data, data_quality_library):
    data_quality_library.check_duplicates(target_data, ['<grain_col_1>', '<grain_col_2>'])


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_not_null_values(target_data, data_quality_library):
    data_quality_library.check_not_null_values(
        target_data, ['<col_1>', '<col_2>', '<col_3>']
    )
```

## SQL derivation (generic)

Use only the mapping's source tables and columns. Join tables on documented foreign keys when a mapped output requires fields from more than one table. Convert a mapped timestamp to the stated date grain where required. Build mapped name expressions using the mapping's stated order and separator. Use the exact aggregate and rounding described for each measure. Select dimensions and group by those same dimensions so the source result has the mapped grain. Alias all outputs exactly as the mapping names them. Include a filter only when the mapping explicitly provides one. Do not add a dataset-specific SQL example to this skill.

## After generation

Do not run pytest unless the user explicitly asks. If execution is requested, run the production selection (`-m "parquet_data"`) with the documented database options and report the HTML report location. Interpret failures as mapping-versus-Parquet discrepancies to investigate in the transformation; never rewrite expected SQL merely to obtain a green run.

---

## Skill review (self-check before Step 3)

Reject your own skill if any of these are true:

- [ ] Contains concrete expected SQL for `facility_name_min_time_spent_per_visit_date`, `facility_type_avg_time_spent_per_visit_date`, or `patient_sum_treatment_cost_per_facility_type`
- [ ] Tells the agent to use `data_dev/` or parquet loader SQL
- [ ] Omits completeness, count, uniqueness, or not-null
- [ ] Swaps Postgres vs Parquet fixtures or generates trivial always-pass checks
- [ ] Any section still contains an unfinished placeholder
