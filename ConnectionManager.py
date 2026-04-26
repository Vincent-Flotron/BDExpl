from tkinter import messagebox
from typing  import Optional
import sqlite3
import psycopg2
import oracledb
from connstr_generator import ConnectionStringGenerator

# Conditionally import pyodbc only on Windows
import sys
if sys.platform == 'win32':
    import pyodbc
else:
    pyodbc = None

class ConnectionManager:
    """Manages database connections and related UI operations"""

    def __init__(self, root, db_connection, database_tree_panel, status_bar_panel):
        self.root = root
        self.db_connection = db_connection
        self.database_tree_panel = database_tree_panel
        self.status_bar_panel = status_bar_panel
        self.connection_name: Optional[str] = None
        self.conn_str_generator = ConnectionStringGenerator()

    def connect_with_credman(self, connection_name: str):
        """Connect using Windows Credential Manager via connstr_generator.py"""
        # First, disconnect any existing connection
        self.disconnect()

        try:
            conn_type = self.conn_str_generator.get_connection_type(connection_name)

            if conn_type == "Oracle":
                conn_str = self.conn_str_generator.get_conn_string(connection_name)
                if pyodbc:
                    self.db_connection.current_connection = pyodbc.connect(conn_str)
                else:
                    raise Exception("pyodbc module is not available")
                self.db_connection.current_connection_type = "Oracle"
                self.connection_name = connection_name
                self.status_bar_panel.set_status(f"Connected via: {connection_name}")
                self.database_tree_panel.load_database_objects()
            elif conn_type == "SQLite":
                db_path = self.conn_str_generator.get_sqlite_conn_string(connection_name)
                self.db_connection.current_connection = sqlite3.connect(db_path)
                self.db_connection.current_connection_type = "SQLite"
                self.connection_name = connection_name
                self.status_bar_panel.set_status(f"Connected via: {connection_name} (SQLite)")
                self.database_tree_panel.load_database_objects()
            elif conn_type == "OracleDB":
                params = self.conn_str_generator.get_oracledb_conn_params(connection_name)
                self.db_connection.current_connection = oracledb.connect(
                    user=params["user"],
                    password=params["password"],
                    host=params["host"],
                    port=int(params["port"]),
                    sid=params["sid"],
                )
                self.db_connection.current_connection_type = "OracleDB"
                self.connection_name = connection_name
                self.status_bar_panel.set_status(f"Connected via: {connection_name} (OracleDB)")
                self.database_tree_panel.load_database_objects()
            elif conn_type == "PostgreSQL":
                params = self.conn_str_generator.get_postgresql_conn_params(connection_name)
                ssl_args = {"sslmode": params["sslmode"]}
                if params.get("sslrootcert"):
                    ssl_args["sslrootcert"] = params["sslrootcert"]
                self.db_connection.current_connection = psycopg2.connect(
                    host=params["host"],
                    port=int(params["port"]),
                    dbname=params["database"],
                    user=params["user"],
                    password=params["password"],
                    **ssl_args,
                )
                self.db_connection.current_connection_type = "PostgreSQL"
                self.connection_name = connection_name
                self.status_bar_panel.set_status(f"Connected via: {connection_name} (PostgreSQL)")
                self.database_tree_panel.load_database_objects()
            elif conn_type == "MSSQL":
                params = self.conn_str_generator.get_mssql_conn_params(connection_name)
                server = f"{params['host']},{params['port']}" if params.get("port") else params["host"]
                if params.get("auth_type") == "Windows":
                    conn_str = (
                        f"DRIVER={params['driver']};"
                        f"SERVER={server};"
                        f"DATABASE={params['database']};"
                        f"Trusted_Connection=yes;"
                        f"Encrypt={params['encrypt']};"
                        f"TrustServerCertificate={params['trust_server_cert']};"
                    )
                else:
                    conn_str = (
                        f"DRIVER={params['driver']};"
                        f"SERVER={server};"
                        f"DATABASE={params['database']};"
                        f"UID={params['user']};"
                        f"PWD={params['password']};"
                        f"Encrypt={params['encrypt']};"
                        f"TrustServerCertificate={params['trust_server_cert']};"
                    )
                if pyodbc:
                    self.db_connection.current_connection = pyodbc.connect(conn_str)
                else:
                    raise Exception("pyodbc module is not available")
                self.db_connection.current_connection_type = "MSSQL"
                self.connection_name = connection_name
                self.status_bar_panel.set_status(f"Connected via: {connection_name} (SQL Server)")
                self.database_tree_panel.load_database_objects()
            else:
                messagebox.showerror("Connection Error", f"Unknown connection type: {conn_type}")

        except ImportError as e:
            messagebox.showerror("Error", f"connstr_generator module not found: {str(e)}")
        except sqlite3.Error as e:
            messagebox.showerror("Connection Error", f"SQLite connection failed: {str(e)}")
        except psycopg2.Error as e:
            messagebox.showerror("Connection Error", f"PostgreSQL connection failed: {str(e)}")
        except oracledb.Error as e:
            messagebox.showerror("Connection Error", f"OracleDB connection failed: {str(e)}")
        except pyodbc and pyodbc.Error as e:
            messagebox.showerror("Connection Error", f"ODBC connection failed: {str(e)}")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")

    def disconnect(self):
        """Disconnect from database"""
        if self.db_connection.current_connection:
            try:
                self.db_connection.current_connection.close()
            except:
                pass
            self.db_connection.current_connection = None
            self.db_connection.current_connection_type = None
            self.connection_name = None
            self.status_bar_panel.set_status("Not connected")
            self.database_tree_panel.clear_tree()

    def delete_connection(self, connection_name: str):
        """Delete a connection from Windows Credential Manager"""
        try:
            self.conn_str_generator.delete_connection_credentials(connection_name)

            # If the deleted connection is the currently active one, disconnect
            if self.connection_name == connection_name:
                self.disconnect()

            messagebox.showinfo("Success", f"Connection '{connection_name}' deleted successfully")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete connection: {str(e)}")
            return False