import pytest

from src.connectors.file_system.parquet_reader import ParquetReader
from src.connectors.postgres.postgres_connector import PostgresConnectorContextManager
from src.data_quality.data_quality_validation_library import DataQualityLibrary

def pytest_addoption(parser):
    parser.addoption("--db_host", action="store", default="localhost", help="Database host")
    parser.addoption("--db_port", action="store", type=int, default=5434, help="Database port")
    parser.addoption("--db_name", action="store", default="mydatabase", help="Database name")
    parser.addoption("--db_user", action="store", default=None, help="Database username")
    parser.addoption("--db_password", action="store", default=None, help="Database password")

def pytest_configure(config):
    if "parquet_data" not in config.getoption("markexpr", ""):
        return

    missing_options = [
        option
        for option in ("--db_user", "--db_password")
        if not config.getoption(option[2:].replace("-", "_"))
    ]
    if missing_options:
        raise pytest.UsageError(
            "Missing required options for parquet_data tests: "
            + ", ".join(missing_options)
        )

@pytest.fixture(scope='session')
def db_connection(request):
    connector = PostgresConnectorContextManager(
        db_host=request.config.getoption("db_host"),
        db_name=request.config.getoption("db_name"),
        db_port=request.config.getoption("db_port"),
        db_user=request.config.getoption("db_user"),
        db_password=request.config.getoption("db_password"),
    )
    try:
        with connector as db_connector:
            yield db_connector
    except Exception as error:
        pytest.fail(f"Failed to initialize PostgreSQL connection: {error}")

@pytest.fixture(scope='session')
def parquet_reader():
    return ParquetReader()

@pytest.fixture(scope='session')
def data_quality_library():
    return DataQualityLibrary()