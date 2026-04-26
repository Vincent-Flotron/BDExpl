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

    def connect(self, name):
        conn_details = self.connections[name]
        if conn_details["db_type"] == "Oracle":
            conn_str = f"DRIVER={{Oracle}};SERVER={conn_details['host']};PORT={conn_details['port']};UID={conn_details['user']};PWD={conn_details['password']}"
            if pyodbc:
                return pyodbc.connect(conn_str)
            else:
                raise Exception("pyodbc module is not available")
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

    def connect_mssql(self, host, port, database, user, password,
                      auth_type="SQL", driver="{ODBC Driver 17 for SQL Server}",
                      encrypt="yes", trust_server_cert="yes"):
        """Connect to a Microsoft SQL Server database via pyodbc"""
        server = f"{host},{port}" if port else host
        if auth_type == "Windows":
            conn_str = (
                f"DRIVER={driver};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"Trusted_Connection=yes;"
                f"Encrypt={encrypt};"
                f"TrustServerCertificate={trust_server_cert};"
            )
        else:
            conn_str = (
                f"DRIVER={driver};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={user};"
                f"PWD={password};"
                f"Encrypt={encrypt};"
                f"TrustServerCertificate={trust_server_cert};"
            )
        if pyodbc:
            return pyodbc.connect(conn_str)
        else:
            raise Exception("pyodbc module is not available")

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

        # Fallback: isinstance checks (cannot distinguish Oracle ODBC from MSSQL)
        conn = self.current_connection
        if isinstance(conn, psycopg2.extensions.connection):
            return "PostgreSQL"
        elif isinstance(conn, sqlite3.Connection):
            return "SQLite"
        elif isinstance(conn, oracledb.Connection):
            return "OracleDB"
        elif pyodbc and isinstance(conn, pyodbc.Connection):
            return "Oracle"   # conservative fallback
        else:
            return "Unknown"