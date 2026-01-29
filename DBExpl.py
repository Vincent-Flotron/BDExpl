import tkinter as tk
from tkinter import ttk, messagebox
import pyodbc
import json
import os
from typing import Optional
from connection import DBConnection
import signal
from Panels import DatabaseTreePanel, SQLQueryEditorPanel, QueryResultPanel, StatusBarPanel
from ConnectionManager import ConnectionManager


class Theme:
    def __init__(self, root):
        self.root = root

    def setup(self):
        """Configure a professional light theme with improved styling"""
        # Color palette
        bg_color = '#f5f7fa'  # Lighter background
        primary_color = '#4a90e2'  # Softer blue
        secondary_color = '#d0d9e3'  # Light gray-blue
        text_color = '#333333'  # Darker text for better readability
        accent_color = '#357abd'  # Slightly darker blue for accents
        border_color = '#d1d5db'  # Subtle border color
        highlight_color = '#e5e7eb'  # For highlighted elements
        success_color = '#2ecc71'  # Green for success messages
        error_color = '#e74c3c'  # Red for errors

        self.style = ttk.Style()
        self.style.theme_use('clam')  # Best theme for custom styling

        # Configure root window
        self.root.configure(bg=bg_color)

        # Style for frames
        self.style.configure('TFrame', background=bg_color, bordercolor=border_color)

        # Style for labels
        self.style.configure('TLabel',
                            background=bg_color,
                            foreground=text_color,
                            font=('Helvetica', 10))
        self.style.configure('Bold.TLabel',
                            font=('Helvetica', 10, 'bold'),
                            foreground=text_color)
        self.style.configure('Status.TLabel',
                            background=secondary_color,
                            foreground=text_color,
                            anchor='w',
                            relief='flat',
                            font=('Helvetica', 9))

        # Style for buttons
        self.style.configure('TButton',
                            font=('Helvetica', 9),
                            borderwidth=1,
                            padding=8,
                            background=primary_color,
                            foreground='white')
        self.style.map('TButton',
                      background=[('active', accent_color), ('!active', primary_color)],
                      relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

        # Style for notebook (tabs)
        self.style.configure('TNotebook',
                            background=bg_color,
                            borderwidth=0)
        self.style.configure('TNotebook.Tab',
                            font=('Helvetica', 9),
                            padding=[12, 6],
                            background=highlight_color,
                            foreground=text_color)
        self.style.map('TNotebook.Tab',
                      background=[('selected', bg_color), ('!selected', highlight_color)],
                      expand=[('selected', [1, 1, 1, 0])])

        # Style for treeview
        self.style.configure('Treeview',
                            font=('Helvetica', 9),
                            rowheight=28,
                            background=bg_color,
                            fieldbackground=bg_color,
                            foreground=text_color,
                            bordercolor=border_color,
                            highlightthickness=0)
        self.style.map('Treeview',
                      background=[('selected', primary_color)],
                      foreground=[('selected', 'white')])
        self.style.configure('Treeview.Heading',
                            font=('Helvetica', 10, 'bold'),
                            foreground=text_color,
                            padding=[5, 5])

        # Style for entry and combobox
        self.style.configure('TEntry',
                            fieldbackground='#ffffff',
                            foreground=text_color,
                            insertcolor=text_color,
                            bordercolor=border_color)
        self.style.configure('TCombobox',
                            fieldbackground='#ffffff',
                            foreground=text_color,
                            bordercolor=border_color)

        # Style for scrollbar
        self.style.configure('TScrollbar',
                            background=secondary_color,
                            troughcolor=bg_color,
                            bordercolor=border_color,
                            arrowcolor=text_color,
                            width=12)

        # Style for separators
        self.style.configure('TSeparator',
                            background=border_color)

        # Style for radio buttons
        self.style.configure('TRadiobutton',
                            background=bg_color,
                            foreground=text_color,
                            font=('Helvetica', 9))
        
        # Style tab close button 
        self.style.configure('Close.TButton',
                    font=('Helvetica', 9, 'bold'),
                    borderwidth=1,
                    padding=2,
                    background=error_color,
                    foreground='white')


        # Configure custom style for SQL editor text
        self.sql_editor_style = {
            'bg': '#ffffff',
            'fg': text_color,
            'insertbackground': text_color,
            'selectbackground': primary_color,
            'selectforeground': 'white',
            'padx': 8,
            'pady': 8,
            'borderwidth': 0,
            'highlightthickness': 1,
            'highlightcolor': border_color,
            'highlightbackground': border_color,
            'font': ('Consolas', 10)
        }




class DBExp:
    """Database Explorer - Scalable multi-database GUI tool"""

    CONFIG_FILE = "dbexp_config.json"

    def __init__(self, root):
        self.root = root
        self.root.title("DBExp - Database Explorer")
        self.root.geometry("1400x800")

        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        # Database connection
        self.db_connection = DBConnection()
        self.db_connection.current_connection: Optional[pyodbc.Connection] = None

        # Configuration
        self.config = self.load_config()

        # Setup theme and UI
        self.theme = Theme(self.root)
        self.theme.setup()
        self.setup_ui()

        # Initialize existing_connections_menu before setup_menu
        self.existing_connections_menu = tk.Menu(self.root, tearoff=0)

        self.setup_menu()


    def setup_ui(self):
        """Create the three-panel interface"""
        # Main container with PanedWindow for resizable panels
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.query_result_panel = QueryResultPanel(self.root, self.db_connection)
        self.sql_query_editor_panel = SQLQueryEditorPanel(self.query_result_panel, self.db_connection)

        # Left Panel: DB Treeview
        self.database_tree_panel = DatabaseTreePanel(main_paned, self.db_connection, self.sql_query_editor_panel)
        self.database_tree_panel.setup()

        # Right container for SQL Query and Query Result
        right_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned, weight=3)

        # Middle Panel: SQL Query Editor
        self.sql_query_editor_panel.setup(right_paned, self.root, self.theme)

        # Bottom Panel: Query Result
        self.query_result_panel.setup(right_paned, self.config)

        # Status bar
        self.status_bar_panel = StatusBarPanel(self.root, text="Not connected", style='Status.TLabel')

        # Connection manager
        self.connection_manager = ConnectionManager(
            self.root, 
            self.db_connection, 
            self.database_tree_panel, 
            self.status_bar_panel
        )


    

    def load_config(self) -> dict:
        """Load persistent configuration"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self):
        """Save persistent configuration"""
        self.config["show_labels"] = self.query_result_panel.show_labels
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

    def setup_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Connection menu
        conn_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Connection", menu=conn_menu)

        # Add submenu for existing connections
        self.existing_connections_menu = tk.Menu(conn_menu, tearoff=0)
        conn_menu.add_cascade(label="Connect with Existing", menu=self.existing_connections_menu)

        # Add submenu for new connection
        conn_menu.add_command(label="Connect with New Credentials", command=self.show_new_connection_dialog)

        # Add delete connection command
        conn_menu.add_command(label="Delete Connection", command=self.show_delete_connection_dialog)

        conn_menu.add_separator()
        conn_menu.add_command(label="Disconnect", command=self.connection_manager.disconnect)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New SQL", command=self.sql_query_editor_panel.new_sql_tab)
        file_menu.add_command(label="Open SQL...", command=self.sql_query_editor_panel.open_sql_file)
        file_menu.add_command(label="Save", command=self.sql_query_editor_panel.save_current_sql)
        file_menu.add_command(label="Save As...", command=self.sql_query_editor_panel.save_sql_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Query menu
        query_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Query", menu=query_menu)
        query_menu.add_command(label="Execute (F5)", command=self.sql_query_editor_panel.execute_query)
        query_menu.add_command(label="Execute Selection", command=self.sql_query_editor_panel.execute_selection)

        # Populate existing connections menu
        self.populate_existing_connections_menu()

    def show_delete_connection_dialog(self):
        """Show dialog for deleting a connection"""
        try:
            from connstr_generator import get_all_connection_names
            connections = get_all_connection_names()

            if not connections:
                messagebox.showinfo("Info", "No connections available to delete")
                return

            dialog = tk.Toplevel(self.root)
            dialog.title("Delete Connection")
            dialog.geometry("400x280")
            dialog.transient(self.root)
            dialog.grab_set()

            # Connection selection
            tk.Label(dialog, text="Select Connection to Delete:").pack(pady=(10, 0))
            conn_var = tk.StringVar()
            conn_combobox = ttk.Combobox(dialog, textvariable=conn_var, values=connections, state="readonly")
            conn_combobox.pack(fill=tk.X, padx=20, pady=5)
            conn_combobox.current(0)

            # Warning label
            warning_label = tk.Label(
                dialog,
                text="WARNING: This will permanently delete the connection credentials from Windows Credential Manager.",
                fg="red",
                wraplength=350
            )
            warning_label.pack(pady=10)

            # Delete button
            def delete_connection():
                conn_name = conn_var.get()
                if not conn_name:
                    messagebox.showerror("Error", "Please select a connection to delete")
                    return

                # Confirm deletion
                if messagebox.askyesno(
                    "Confirm Deletion",
                    f"Are you sure you want to delete the connection '{conn_name}'?\n\nThis action cannot be undone."
                ):
                    if self.connection_manager.delete_connection(conn_name):
                        # Refresh the connections menu
                        self.populate_existing_connections_menu()
                        dialog.destroy()

            delete_btn = ttk.Button(dialog, text="Delete", command=delete_connection)
            delete_btn.pack(pady=10)

            # Cancel button
            cancel_btn = ttk.Button(dialog, text="Cancel", command=dialog.destroy)
            cancel_btn.pack(pady=5)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to show delete dialog: {str(e)}")
            
    def populate_existing_connections_menu(self):
        """Populate the existing connections menu with available connections"""
        try:
            from connstr_generator import get_all_connection_names
            connections = get_all_connection_names()

            # Clear existing items
            self.existing_connections_menu.delete(0, tk.END)

            # Add connections to menu
            for conn_name in connections:
                self.existing_connections_menu.add_command(
                    label=conn_name,
                    command=lambda name=conn_name: self.connection_manager.connect_with_credman(name)
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load existing connections: {str(e)}")

    def show_new_connection_dialog(self):
        """Show dialog for creating a new connection"""
        dialog = tk.Toplevel(self.root)
        dialog.title("New Connection")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Connection name
        tk.Label(dialog, text="Connection Name:").pack(pady=(10, 0))
        conn_name_var = tk.StringVar()
        conn_name_entry = tk.Entry(dialog, textvariable=conn_name_var)
        conn_name_entry.pack(fill=tk.X, padx=20, pady=5)

        # Host
        tk.Label(dialog, text="Host or Server name:").pack(pady=(10, 0))
        host_var = tk.StringVar()
        host_entry = tk.Entry(dialog, textvariable=host_var)
        host_entry.pack(fill=tk.X, padx=20, pady=5)

        # Username
        tk.Label(dialog, text="Username:").pack(pady=(10, 0))
        user_var = tk.StringVar()
        user_entry = tk.Entry(dialog, textvariable=user_var)
        user_entry.pack(fill=tk.X, padx=20, pady=5)

        # Password
        tk.Label(dialog, text="Password:").pack(pady=(10, 0))
        pwd_var = tk.StringVar()
        pwd_entry = tk.Entry(dialog, textvariable=pwd_var, show="*")
        pwd_entry.pack(fill=tk.X, padx=20, pady=5)

        # Save button
        def save_connection():
            conn_name = conn_name_var.get().strip()
            host = host_var.get().strip()
            user = user_var.get().strip()
            password = pwd_var.get().strip()

            if not conn_name:
                messagebox.showerror("Error", "Connection name is required")
                return
            if not user:
                messagebox.showerror("Error", "Username is required")
                return
            if not password:
                messagebox.showerror("Error", "Password is required")
                return

            try:
                from connstr_generator import save_odbc_user_credentials
                save_odbc_user_credentials(conn_name, host, user, password)
                messagebox.showinfo("Success", f"Connection '{conn_name}' saved successfully")

                # Refresh the connections menu
                self.populate_existing_connections_menu()

                # Connect with the new credentials
                self.connection_manager.connect_with_credman(conn_name)

                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save connection: {str(e)}")

        save_btn = ttk.Button(dialog, text="Save & Connect", command=save_connection)
        save_btn.pack(pady=20)

        # Cancel button
        cancel_btn = ttk.Button(dialog, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(pady=5)

    def close_keys_tab(self, frame):
        print("close_keys_tab")
        self.sql_query_editor_panel.close_keys_tab(frame)


    def shutdown(self, *args):
        """Gracefully shutdown application and close DB connections"""
        self.connection_manager.disconnect()
        self.root.quit()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = DBExp(root)

    # Graceful shutdown on signals
    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown())
    signal.signal(signal.SIGTERM, lambda sig, frame: app.shutdown())

    root.mainloop()

if __name__ == "__main__":
    main()