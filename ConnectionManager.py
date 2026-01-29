from tkinter import messagebox
from typing import Optional
import pyodbc

class ConnectionManager:
    """Manages database connections and related UI operations"""

    def __init__(self, root, db_connection, database_tree_panel, status_bar_panel):
        self.root = root
        self.db_connection = db_connection
        self.database_tree_panel = database_tree_panel
        self.status_bar_panel = status_bar_panel
        self.connection_name: Optional[str] = None
        
    def connect_with_credman(self, connection_name: str):
        """Connect using Windows Credential Manager via connstr_generator.py"""
        # First, disconnect any existing connection
        self.disconnect()

        try:
            from connstr_generator import get_conn_string
            conn_str = get_conn_string(connection_name)
            self.db_connection.current_connection = pyodbc.connect(conn_str)
            self.connection_name = connection_name
            self.status_bar_panel.set_status(f"Connected via: {connection_name}")
            self.database_tree_panel.load_database_objects()
        except ImportError:
            messagebox.showerror("Error", "connstr_generator module not found")
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
            self.connection_name = None
            self.status_bar_panel.set_status("Not connected")
            self.database_tree_panel.clear_tree()


    def delete_connection(self, connection_name: str):
        """Delete a connection from Windows Credential Manager"""
        try:
            from connstr_generator import delete_connection_credentials
            delete_connection_credentials(connection_name)

            # If the deleted connection is the currently active one, disconnect
            if self.connection_name == connection_name:
                self.disconnect()

            messagebox.showinfo("Success", f"Connection '{connection_name}' deleted successfully")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete connection: {str(e)}")
            return False