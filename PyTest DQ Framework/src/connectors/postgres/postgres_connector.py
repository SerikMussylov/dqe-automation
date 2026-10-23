
import pandas as pd

class PostgresConnectorContextManager:
    def __init__(self, db_host: str, db_name: str, db_port: int, db_user: str, db_password: str):
        self._params = dict(host=db_host, dbname=db_name, port=db_port,
                            user=db_user, password=db_password)
        self.connection = None

    def __enter__(self):
        import psycopg2

        self.connection = psycopg2.connect(**self._params)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        return False

    def get_data_sql(self, sql):
        if self.connection is None:
            raise RuntimeError("The PostgreSQL connector must be used inside a context manager")

        with self.connection.cursor() as cursor:
            cursor.execute(sql)
            if cursor.description is None:
                return pd.DataFrame()
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=columns)


