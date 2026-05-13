import sqlite3
import psycopg2
import oracledb
from QueryManager import QueriesSQLite, QueriesOracle, QueriesPostgreSQL, QueriesMSSQL

# Conditionally import pyodbc only on Windows
import sys
if sys.platform == 'win32':
    import pyodbc
else:
    pyodbc = None

class DBConnection:
    def __init__(self):
        self.connections = {}
        self.current_connection = None
        self.current_connection_type = None  # Explicit type tracking ("Oracle", "OracleDB", "PostgreSQL", "SQLite", "MSSQL")

    def add_connection(self, name, host, port, user, password, db_type="Oracle", ssh_tunnel=None):
        self.connections[name] = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "db_type": db_type,
            "ssh_tunnel": ssh_tunnel,
        }

    def get_queries_instance(self, connection):
        # Prefer the explicit type tracker when available
        if self.current_connection_type == "MSSQL":
            return QueriesMSSQL()
        if self.current_connection_type == "PostgreSQL":
            return QueriesPostgreSQL()
        if self.current_connection_type in ("Oracle", "OracleDB"):
            return QueriesOracle()
        if self.current_connection_type == "SQLite":
            return QueriesSQLite()
        # Fallback: isinstance checks (cannot distinguish Oracle ODBC from MSSQL)
        if type(connection) == sqlite3.Connection:
            return QueriesSQLite()
        elif isinstance(connection, psycopg2.extensions.connection):
            return QueriesPostgreSQL()
        elif isinstance(connection, oracledb.Connection):
            return QueriesOracle()
        elif pyodbc and type(connection) == pyodbc.Connection:
            return QueriesOracle()  # conservative fallback for pyodbc
        else:
            return QueriesOracle()

    def get_connection_type(self):
        """Get the type of the current database connection"""
        if not self.current_connection:
            return None

        # Prefer the explicit tracker set by ConnectionManager
        if self.current_connection_type:
            return self.current_connection_type
