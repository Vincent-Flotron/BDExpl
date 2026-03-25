import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyodbc
import json
import os
import signal
from typing            import Optional
from connection        import DBConnection
from Panels            import DatabaseTreePanel, SQLQueryEditorPanel, QueryResultPanel, StatusBarPanel
from ConnectionManager import ConnectionManager
from connstr_generator import get_all_connection_names, save_odbc_user_credentials, save_oracledb_connection, save_postgresql_connection, save_sqlite_connection


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
        self.root.geometry("1600x1000")

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
        dialog.geometry("400x750")
        dialog.transient(self.root)
        dialog.grab_set()

        # Connection name
        tk.Label(dialog, text="Connection Name:").pack(pady=(10, 0))
        conn_name_var = tk.StringVar()
        conn_name_entry = tk.Entry(dialog, textvariable=conn_name_var)
        conn_name_entry.pack(fill=tk.X, padx=20, pady=5)

        # Database type selection
        tk.Label(dialog, text="Database Type:").pack(pady=(10, 0))
        db_type_var = tk.StringVar(value="Oracle")
        db_type_frame = tk.Frame(dialog)
        db_type_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Radiobutton(db_type_frame, text="Oracle",     variable=db_type_var, value="Oracle").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(db_type_frame, text="OracleDB",   variable=db_type_var, value="OracleDB").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(db_type_frame, text="PostgreSQL", variable=db_type_var, value="PostgreSQL").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(db_type_frame, text="SQLite",     variable=db_type_var, value="SQLite").pack(side=tk.LEFT, padx=10)

        # ── Oracle fields ──────────────────────────────────────────────
        oracle_frame = tk.Frame(dialog)

        tk.Label(oracle_frame, text="Host or Server name:").pack(pady=(10, 0))
        host_var = tk.StringVar()
        tk.Entry(oracle_frame, textvariable=host_var).pack(fill=tk.X, pady=5)

        tk.Label(oracle_frame, text="Username:").pack(pady=(10, 0))
        oracle_user_var = tk.StringVar()
        tk.Entry(oracle_frame, textvariable=oracle_user_var).pack(fill=tk.X, pady=5)

        tk.Label(oracle_frame, text="Password:").pack(pady=(10, 0))
        oracle_pwd_var = tk.StringVar()
        tk.Entry(oracle_frame, textvariable=oracle_pwd_var, show="*").pack(fill=tk.X, pady=5)

        # ── OracleDB fields (oracledb driver — host/port/sid) ──────────
        oracledb_frame = tk.Frame(dialog)

        tk.Label(oracledb_frame, text="Host:").pack(pady=(10, 0))
        odb_host_var = tk.StringVar(value="localhost")
        tk.Entry(oracledb_frame, textvariable=odb_host_var).pack(fill=tk.X, pady=5)

        tk.Label(oracledb_frame, text="Port:").pack(pady=(10, 0))
        odb_port_var = tk.StringVar(value="1521")
        tk.Entry(oracledb_frame, textvariable=odb_port_var).pack(fill=tk.X, pady=5)

        tk.Label(oracledb_frame, text="SID:").pack(pady=(10, 0))
        odb_sid_var = tk.StringVar()
        tk.Entry(oracledb_frame, textvariable=odb_sid_var).pack(fill=tk.X, pady=5)

        tk.Label(oracledb_frame, text="Username:").pack(pady=(10, 0))
        odb_user_var = tk.StringVar()
        tk.Entry(oracledb_frame, textvariable=odb_user_var).pack(fill=tk.X, pady=5)

        tk.Label(oracledb_frame, text="Password:").pack(pady=(10, 0))
        odb_pwd_var = tk.StringVar()
        tk.Entry(oracledb_frame, textvariable=odb_pwd_var, show="*").pack(fill=tk.X, pady=5)

        # ── PostgreSQL fields ──────────────────────────────────────────
        pg_frame = tk.Frame(dialog)

        tk.Label(pg_frame, text="Host:").pack(pady=(10, 0))
        pg_host_var = tk.StringVar(value="localhost")
        tk.Entry(pg_frame, textvariable=pg_host_var).pack(fill=tk.X, pady=5)

        tk.Label(pg_frame, text="Port:").pack(pady=(10, 0))
        pg_port_var = tk.StringVar(value="5432")
        tk.Entry(pg_frame, textvariable=pg_port_var).pack(fill=tk.X, pady=5)

        tk.Label(pg_frame, text="Database:").pack(pady=(10, 0))
        pg_db_var = tk.StringVar()
        tk.Entry(pg_frame, textvariable=pg_db_var).pack(fill=tk.X, pady=5)

        tk.Label(pg_frame, text="Username:").pack(pady=(10, 0))
        pg_user_var = tk.StringVar()
        tk.Entry(pg_frame, textvariable=pg_user_var).pack(fill=tk.X, pady=5)

        tk.Label(pg_frame, text="Password:").pack(pady=(10, 0))
        pg_pwd_var = tk.StringVar()
        tk.Entry(pg_frame, textvariable=pg_pwd_var, show="*").pack(fill=tk.X, pady=5)

        tk.Label(pg_frame, text="SSL Mode:").pack(pady=(10, 0))
        pg_sslmode_var = tk.StringVar(value="require")
        ttk.Combobox(
            pg_frame,
            textvariable=pg_sslmode_var,
            values=["require", "verify-ca", "verify-full", "prefer", "allow", "disable"],
            state="readonly",
            width=18,
        ).pack(anchor=tk.W, pady=5)

        # CA certificate — only relevant for verify-ca / verify-full
        pg_sslrootcert_label = tk.Label(pg_frame, text="CA Certificate (optional):")
        pg_sslrootcert_label.pack(pady=(5, 0))
        pg_sslrootcert_var = tk.StringVar()
        pg_sslrootcert_frame = tk.Frame(pg_frame)
        pg_sslrootcert_frame.pack(fill=tk.X, pady=5)
        tk.Entry(pg_sslrootcert_frame, textvariable=pg_sslrootcert_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        def browse_ca_cert():
            path = filedialog.askopenfilename(
                title="Select CA Certificate",
                filetypes=[("Certificate files", "*.pem *.crt *.cer"), ("All files", "*.*")]
            )
            if path:
                pg_sslrootcert_var.set(path)

        ttk.Button(pg_sslrootcert_frame, text="...", command=browse_ca_cert, width=3).pack(side=tk.LEFT, padx=(4, 0))

        # ── SQLite fields ──────────────────────────────────────────────
        sqlite_frame = tk.Frame(dialog)

        tk.Label(sqlite_frame, text="Database File Path:").pack(pady=(10, 0))
        db_path_var = tk.StringVar()
        tk.Entry(sqlite_frame, textvariable=db_path_var).pack(fill=tk.X, pady=5)

        def browse_db_file():
            file_path = filedialog.askopenfilename(
                title="Select SQLite Database File",
                filetypes=[("SQLite Database Files", "*.db *.sqlite *.sqlite3")]
            )
            if file_path:
                db_path_var.set(file_path)

        ttk.Button(sqlite_frame, text="Browse...", command=browse_db_file).pack(pady=5)

        # ── Toggle visibility ──────────────────────────────────────────
        all_frames = [oracle_frame, oracledb_frame, pg_frame, sqlite_frame]
        frame_map  = {"Oracle": oracle_frame, "OracleDB": oracledb_frame, "PostgreSQL": pg_frame, "SQLite": sqlite_frame}

        def toggle_db_fields(*args):
            active = frame_map[db_type_var.get()]
            for f in all_frames:
                f.pack_forget()
            active.pack(fill=tk.X, padx=20, pady=5)

        db_type_var.trace_add("write", toggle_db_fields)
        toggle_db_fields()  # show Oracle frame on open

        # ── Save / Connect ─────────────────────────────────────────────
        def save_connection():
            conn_name = conn_name_var.get().strip()
            db_type   = db_type_var.get()

            if not conn_name:
                messagebox.showerror("Error", "Connection name is required")
                return

            try:
                if db_type == "Oracle":
                    host     = host_var.get().strip()
                    user     = oracle_user_var.get().strip()
                    password = oracle_pwd_var.get().strip()
                    if not user:
                        messagebox.showerror("Error", "Username is required")
                        return
                    if not password:
                        messagebox.showerror("Error", "Password is required")
                        return
                    save_odbc_user_credentials(conn_name, host, user, password)

                elif db_type == "OracleDB":
                    odb_host = odb_host_var.get().strip()
                    odb_port = odb_port_var.get().strip()
                    odb_sid  = odb_sid_var.get().strip()
                    odb_user = odb_user_var.get().strip()
                    odb_pwd  = odb_pwd_var.get().strip()
                    if not odb_host:
                        messagebox.showerror("Error", "Host is required")
                        return
                    if not odb_sid:
                        messagebox.showerror("Error", "SID is required")
                        return
                    if not odb_user:
                        messagebox.showerror("Error", "Username is required")
                        return
                    if not odb_pwd:
                        messagebox.showerror("Error", "Password is required")
                        return
                    try:
                        port_int = int(odb_port)
                    except ValueError:
                        messagebox.showerror("Error", "Port must be a number")
                        return
                    save_oracledb_connection(conn_name, odb_host, port_int, odb_sid,
                                             odb_user, odb_pwd)

                elif db_type == "PostgreSQL":
                    pg_host = pg_host_var.get().strip()
                    pg_port = pg_port_var.get().strip()
                    pg_db   = pg_db_var.get().strip()
                    pg_user = pg_user_var.get().strip()
                    pg_pwd  = pg_pwd_var.get().strip()
                    pg_ssl  = pg_sslmode_var.get().strip()
                    pg_cert = pg_sslrootcert_var.get().strip()
                    if not pg_host:
                        messagebox.showerror("Error", "Host is required")
                        return
                    if not pg_db:
                        messagebox.showerror("Error", "Database name is required")
                        return
                    if not pg_user:
                        messagebox.showerror("Error", "Username is required")
                        return
                    if not pg_pwd:
                        messagebox.showerror("Error", "Password is required")
                        return
                    try:
                        port_int = int(pg_port)
                    except ValueError:
                        messagebox.showerror("Error", "Port must be a number")
                        return
                    save_postgresql_connection(conn_name, pg_host, port_int, pg_db,
                                               pg_user, pg_pwd, pg_ssl, pg_cert)

                else:  # SQLite
                    db_path = db_path_var.get().strip()
                    if not db_path:
                        messagebox.showerror("Error", "Database file path is required")
                        return
                    save_sqlite_connection(conn_name, db_path)

                messagebox.showinfo("Success", f"Connection '{conn_name}' saved successfully")
                self.populate_existing_connections_menu()
                self.connection_manager.connect_with_credman(conn_name)
                dialog.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to save connection: {str(e)}")

        ttk.Button(dialog, text="Save & Connect", command=save_connection).pack(pady=20)
        ttk.Button(dialog, text="Cancel",         command=dialog.destroy).pack(pady=5)


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