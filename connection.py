import pyodbc
import sqlite3
import psycopg2
import oracledb
from QueryManager import QueriesSQLite, QueriesOracle, QueriesPostgreSQL

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
        elif conn_details["db_type"] == "OracleDB":
            return oracledb.connect(
                user=conn_details["user"],
                password=conn_details["password"],
                host=conn_details["host"],
                port=int(conn_details["port"]),
                sid=conn_details.get("sid", ""),
            )
        elif conn_details["db_type"] == "PostgreSQL":
            ssl_args = {"sslmode": conn_details.get("sslmode", "require")}
            if conn_details.get("sslrootcert"):
                ssl_args["sslrootcert"] = conn_details["sslrootcert"]
            return psycopg2.connect(
                host=conn_details["host"],
                port=conn_details["port"],
                dbname=conn_details.get("database", ""),
                user=conn_details["user"],
                password=conn_details["password"],
                **ssl_args,
            )
        else:
            raise ValueError(f"Unsupported database type: {conn_details['db_type']}")

    def connect_sqlite(self, db_path):
        """Connect to a SQLite database"""
        return sqlite3.connect(db_path)

    def connect_oracledb(self, host, port, sid, user, password):
        """Connect to an Oracle database using the oracledb driver (thin mode)"""
        return oracledb.connect(
            user=user,
            password=password,
            host=host,
            port=int(port),
            sid=sid,
        )

    def connect_postgresql(self, host, port, database, user, password,
                           sslmode="require", sslrootcert=""):
        """Connect to a PostgreSQL database"""
        ssl_args = {"sslmode": sslmode}
        if sslrootcert:
            ssl_args["sslrootcert"] = sslrootcert
        return psycopg2.connect(
            host=host,
            port=int(port),
            dbname=database,
            user=user,
            password=password,
            **ssl_args,
        )

    def get_queries_instance(self, connection):
        if type(connection) == sqlite3.Connection:
            return QueriesSQLite()
        elif isinstance(connection, psycopg2.extensions.connection):
            return QueriesPostgreSQL()
        elif type(connection) == pyodbc.Connection:
            return QueriesOracle()
        elif isinstance(connection, oracledb.Connection):
            return QueriesOracle()
        else:
            return QueriesOracle()
