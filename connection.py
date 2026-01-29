import pyodbc
import sqlite3
from QueryManager import QueriesSQLite, QueriesOracle

class DBConnection:
    def __init__(self):
        self.connections = {}
        self.current_connection = None

    def add_connection(self, name, host, port, user, password, db_type="Oracle", ssh_tunnel=None):
        self.connections[name] = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "db_type": db_type,
            "ssh_tunnel": ssh_tunnel,
        }

    def connect(self, name):
        conn_details = self.connections[name]
        if conn_details["db_type"] == "Oracle":
            conn_str = f"DRIVER={{Oracle}};SERVER={conn_details['host']};PORT={conn_details['port']};UID={conn_details['user']};PWD={conn_details['password']}"
            return pyodbc.connect(conn_str)
        elif conn_details["db_type"] == "SQLite":
            return sqlite3.connect(conn_details["host"])  # Assuming host is the path for SQLite
        else:
            raise ValueError(f"Unsupported database type: {conn_details['db_type']}")

    def connect_sqlite(self, db_path):
        """Connect to a SQLite database"""
        return sqlite3.connect(db_path)

    def get_queries_instance(self, connection):
        if type(connection) == sqlite3.Connection:
            return QueriesSQLite()
        elif type(connection) == pyodbc.Connection:
            return QueriesOracle()
        else:
            return QueriesOracle()
