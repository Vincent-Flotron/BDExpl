from tkinter import messagebox
from typing  import Optional
import sqlite3
import psycopg2
import oracledb
import threading  # to timeout connection testing

# Conditionally import pyodbc only on Windows
import sys
if sys.platform == 'win32':
    import pyodbc
else:
    pyodbc = None

class ConnectionManager:
    """Manages database connections and related UI operations"""

    def __init__(self, root, db_connection, panel_database_tree, panel_status_bar, credential_manager):
        self.root = root
        self.db_connection = db_connection
        self.panel_database_tree = panel_database_tree
        self.panel_status_bar = panel_status_bar
        self.connection_name: Optional[str] = None
        self.credential_manager = credential_manager

    def connect_with_credman(self, connection_name: str):
        """Connect using Windows Credential Manager via CredentialManager.py"""
        # First, disconnect any existing connection
        self.disconnect()

        try:
            conn_type = self.credential_manager.get_connection_type_offline(connection_name)

            if conn_type == "Oracle":
                conn_str = self.credential_manager.get_conn_string(connection_name)
                if pyodbc:
                    self.db_connection.current_connection = pyodbc.connect(conn_str)
                else:
                    raise Exception("pyodbc module is not available")
                self.db_connection.current_connection_type = "Oracle"
                self.connection_name = connection_name
                self.panel_status_bar.set_status(f"Connected via: {connection_name}")
                self.panel_database_tree.load_database_objects()
            elif conn_type == "SQLite":
                db_path = self.credential_manager.get_sqlite_conn_string(connection_name)
                self.db_connection.current_connection = sqlite3.connect(db_path)
                self.db_connection.current_connection_type = "SQLite"
                self.connection_name = connection_name
                self.panel_status_bar.set_status(f"Connected via: {connection_name} (SQLite)")
                self.panel_database_tree.load_database_objects()
            elif conn_type == "OracleDB":
                params = self.credential_manager.get_oracledb_conn_params(connection_name)
                self.db_connection.current_connection = oracledb.connect(
                    user=params["user"],
                    password=params["password"],
                    host=params["host"],
                    port=int(params["port"]),
                    sid=params["sid"],
                )
                self.db_connection.current_connection_type = "OracleDB"
                self.connection_name = connection_name
                self.panel_status_bar.set_status(f"Connected via: {connection_name} (OracleDB)")
                self.panel_database_tree.load_database_objects()
            elif conn_type == "PostgreSQL":
                params = self.credential_manager.get_postgresql_conn_params(connection_name)
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
                self.panel_status_bar.set_status(f"Connected via: {connection_name} (PostgreSQL)")
                self.panel_database_tree.load_database_objects()
            elif conn_type == "MSSQL":
                params = self.credential_manager.get_mssql_conn_params(connection_name)
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
                self.panel_status_bar.set_status(f"Connected via: {connection_name} (SQL Server)")
                self.panel_database_tree.load_database_objects()
            else:
                messagebox.showerror("Connection Error", f"Unknown connection type: {conn_type}")

        except ImportError as e:
            messagebox.showerror("Error", f"CredentialManager module not found: {str(e)}")
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
            self.panel_status_bar.set_status("Not connected")
            self.panel_database_tree.clear_tree()

    def test_connection_from_params(self, db_type: str, params: dict, timeout: float = 3.0) -> tuple[bool, str]:
        """
        Open and immediately close a connection built from raw *params* with a strict timeout.
        Returns (success: bool, message: str).
        The active connection is never touched.

        Uses a daemon thread to enforce the timeout, as DB drivers often block
        the main thread indefinitely during DNS resolution or TCP handshakes.
        """
        result = {"success": False, "message": "Connection timed out"}
        exception_msg = None

        def _connect_target():
            nonlocal exception_msg
            conn = None
            try:
                if db_type == "Oracle":
                    if not pyodbc:
                        result["message"] = "pyodbc is not available on this platform"
                        result["success"] = False
                        return
                    ora_conn_str = self.credential_manager.format_to_oracle_driver_conn_str(
                        params["driver"], params["host"], params["user"], params["password"]
                    )
                    conn = pyodbc.connect(ora_conn_str) 

                elif db_type == "SQLite":
                    conn = sqlite3.connect(params["path"])

                elif db_type == "OracleDB":
                    conn = oracledb.connect(
                        user=params["user"], password=params["password"],
                        host=params["host"], port=int(params["port"]), sid=params["sid"]
                    )

                elif db_type == "PostgreSQL":
                    ssl_args = {"sslmode": params["sslmode"]}
                    if params.get("sslrootcert"):
                        ssl_args["sslrootcert"] = params["sslrootcert"]
                    conn = psycopg2.connect(
                        host=params["host"], port=int(params["port"]),
                        dbname=params["database"], user=params["user"],
                        password=params["password"], **ssl_args
                    )

                elif db_type == "MSSQL":
                    if not pyodbc:
                        result["message"] = "pyodbc is not available on this platform"
                        result["success"] = False
                        return
                    server = f"{params['host']},{params['port']}" if params.get("port") else params["host"]
                    if params.get("auth_type") == "Windows":
                        cs = (f"DRIVER={params['driver']};SERVER={server};"
                              f"DATABASE={params['database']};Trusted_Connection=yes;"
                              f"Encrypt={params['encrypt']};TrustServerCertificate={params['trust_server_cert']};")
                    else:
                        cs = (f"DRIVER={params['driver']};SERVER={server};"
                              f"DATABASE={params['database']};UID={params['user']};PWD={params['password']};"
                              f"Encrypt={params['encrypt']};TrustServerCertificate={params['trust_server_cert']};")
                    conn = pyodbc.connect(cs)

                else:
                    result["message"] = f"Unknown connection type: {db_type}"
                    result["success"] = False
                    return

                # If we reach here, connection succeeded
                result["success"] = True
                result["message"] = "Connection successful"

            except Exception as e:
                exception_msg = str(e)
                result["success"] = False
                result["message"] = str(e)
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

        # Run the connection attempt in a separate thread
        thread = threading.Thread(target=_connect_target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Thread is still running, meaning we timed out
            # Note: We cannot forcibly kill the thread in Python, but we ignore its result.
            # The daemon flag ensures it dies when the main program exits.
            return False, f"Connection timed out after {timeout} seconds"
        
        # Thread finished within time, return the captured result
        if exception_msg and not result["success"]:
            return False, result["message"]
            
        return result["success"], result["message"]


    def test_connection(self, connection_name: str) -> tuple[bool, str]:
        """
        Open and immediately close a stored connection by name.
        Resolves credentials via CredentialManager, then delegates to
        test_connection_from_params. Returns (success: bool, message: str).
        """
        try:
            conn_type = self.credential_manager.get_connection_type_offline(connection_name)

            if conn_type == "Oracle":
                params = {"conn_str": self.credential_manager.get_conn_string(connection_name)}
            elif conn_type == "SQLite":
                params = {"path": self.credential_manager.get_sqlite_conn_string(connection_name)}
            elif conn_type == "OracleDB":
                params = self.credential_manager.get_oracledb_conn_params(connection_name)
            elif conn_type == "PostgreSQL":
                params = self.credential_manager.get_postgresql_conn_params(connection_name)
            elif conn_type == "MSSQL":
                params = self.credential_manager.get_mssql_conn_params(connection_name)
            else:
                return False, f"Unknown connection type: {conn_type}"

            return self.test_connection_from_params(conn_type, params)

        except Exception as e:
            return False, str(e)

    def delete_connection(self, connection_name: str):
        """Delete a connection from Windows Credential Manager"""
        try:
            self.credential_manager.delete_connection_credentials(connection_name)

            # If the deleted connection is the currently active one, disconnect
            if self.connection_name == connection_name:
                self.disconnect()

            messagebox.showinfo("Success", f"Connection '{connection_name}' deleted successfully")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete connection: {str(e)}")
            return False