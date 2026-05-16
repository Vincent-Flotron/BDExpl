"""
ConnectionDialogs.py - Separated connection dialog classes for DBExplorer

This module contains dialog classes for managing database connections:
- DeleteConnectionDialog: Dialog for deleting existing connections
- NewConnectionDialog: Dialog for creating new connections
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional


class DeleteConnectionDialog:
    """Dialog for deleting a connection"""
    
    def __init__(self, parent):
        self.root = parent.root
        self.parent = parent
        self.conn_str_generator = parent.conn_str_generator
        self.connection_manager = parent.connection_manager
        self.result = None
    
    def show(self):
        """Show dialog for deleting a connection"""
        try:
            connections = self.conn_str_generator.get_all_connection_names()

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
                        self.parent.populate_existing_connections_menu()
                        dialog.destroy()

            delete_btn = ttk.Button(dialog, text="Delete", command=delete_connection)
            delete_btn.pack(pady=10)

            # Cancel button
            cancel_btn = ttk.Button(dialog, text="Cancel", command=dialog.destroy)
            cancel_btn.pack(pady=5)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to show delete dialog: {str(e)}")



class NewConnectionDialog:
    """Dialog for creating a new connection"""
    
    def __init__(self, parent):
        self.root = parent.root
        self.parent = parent
        self.conn_str_generator = parent.conn_str_generator
        self.connection_manager = parent.connection_manager
        self.result = False
    

    def show(self):
        """Show dialog for creating a new connection"""
        dialog = tk.Toplevel(self.root)
        dialog.title("New Connection")
        dialog.geometry("530x830")
        dialog.transient(self.root)
        dialog.grab_set()

        # Add storage method indicator at the top
        storage_label = tk.Label(
            dialog,
            text=f"Storage: {'Environment Variables' if self.conn_str_generator.use_env_vars else 'Windows Credential Manager'}",
            fg="blue"
        )
        storage_label.pack(pady=(5, 0))

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
        ttk.Radiobutton(db_type_frame, text="SQL Server", variable=db_type_var, value="MSSQL").pack(side=tk.LEFT, padx=10)
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

        # ── SQL Server fields ──────────────────────────────────────────
        mssql_frame = tk.Frame(dialog)

        tk.Label(mssql_frame, text="Host / Server name:").pack(pady=(10, 0))
        mssql_host_var = tk.StringVar(value="localhost")
        tk.Entry(mssql_frame, textvariable=mssql_host_var).pack(fill=tk.X, pady=5)

        tk.Label(mssql_frame, text="Port:").pack(pady=(10, 0))
        mssql_port_var = tk.StringVar(value="1433")
        tk.Entry(mssql_frame, textvariable=mssql_port_var).pack(fill=tk.X, pady=5)

        tk.Label(mssql_frame, text="Database:").pack(pady=(10, 0))
        mssql_db_var = tk.StringVar()
        tk.Entry(mssql_frame, textvariable=mssql_db_var).pack(fill=tk.X, pady=5)

        tk.Label(mssql_frame, text="Authentication:").pack(pady=(10, 0))
        mssql_auth_var = tk.StringVar(value="SQL")
        mssql_auth_frame = tk.Frame(mssql_frame)
        mssql_auth_frame.pack(anchor=tk.W, pady=5)
        ttk.Radiobutton(mssql_auth_frame, text="SQL Server Auth", variable=mssql_auth_var, value="SQL").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mssql_auth_frame, text="Windows Auth",    variable=mssql_auth_var, value="Windows").pack(side=tk.LEFT, padx=5)

        mssql_user_label = tk.Label(mssql_frame, text="Username:")
        mssql_user_label.pack(pady=(10, 0))
        mssql_user_var = tk.StringVar()
        mssql_user_entry = tk.Entry(mssql_frame, textvariable=mssql_user_var)
        mssql_user_entry.pack(fill=tk.X, pady=5)

        mssql_pwd_label = tk.Label(mssql_frame, text="Password:")
        mssql_pwd_label.pack(pady=(10, 0))
        mssql_pwd_var = tk.StringVar()
        mssql_pwd_entry = tk.Entry(mssql_frame, textvariable=mssql_pwd_var, show="*")
        mssql_pwd_entry.pack(fill=tk.X, pady=5)

        tk.Label(mssql_frame, text="ODBC Driver:").pack(pady=(10, 0))
        mssql_driver_var = tk.StringVar(value="{ODBC Driver 17 for SQL Server}")
        ttk.Combobox(
            mssql_frame, textvariable=mssql_driver_var,
            values=[
                "{ODBC Driver 18 for SQL Server}",
                "{ODBC Driver 17 for SQL Server}",
                "{SQL Server}",
            ],
            width=35,
        ).pack(anchor=tk.W, pady=5)

        tk.Label(mssql_frame, text="Encrypt:").pack(pady=(5, 0))
        mssql_encrypt_var = tk.StringVar(value="yes")
        ttk.Combobox(
            mssql_frame, textvariable=mssql_encrypt_var,
            values=["yes", "no", "strict"],
            state="readonly", width=10,
        ).pack(anchor=tk.W, pady=5)

        tk.Label(mssql_frame, text="Trust Server Certificate:").pack(pady=(5, 0))
        mssql_trust_var = tk.StringVar(value="yes")
        ttk.Combobox(
            mssql_frame, textvariable=mssql_trust_var,
            values=["yes", "no"],
            state="readonly", width=10,
        ).pack(anchor=tk.W, pady=5)

        def toggle_mssql_auth(*args):
            if mssql_auth_var.get() == "Windows":
                mssql_user_label.pack_forget()
                mssql_user_entry.pack_forget()
                mssql_pwd_label.pack_forget()
                mssql_pwd_entry.pack_forget()
            else:
                # Re-show in order
                mssql_user_label.pack(pady=(10, 0))
                mssql_user_entry.pack(fill=tk.X, pady=5)
                mssql_pwd_label.pack(pady=(10, 0))
                mssql_pwd_entry.pack(fill=tk.X, pady=5)

        mssql_auth_var.trace_add("write", toggle_mssql_auth)

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
        all_frames = [oracle_frame, oracledb_frame, pg_frame, mssql_frame, sqlite_frame]
        frame_map  = {"Oracle": oracle_frame, "OracleDB": oracledb_frame, "PostgreSQL": pg_frame, "MSSQL": mssql_frame, "SQLite": sqlite_frame}

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
                    self.conn_str_generator.save_oracle_odbc_user_credentials(conn_name, host, user, password)

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
                    self.conn_str_generator.save_oracledb_credentials(conn_name, odb_host, port_int, odb_sid,
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
                    self.conn_str_generator.save_postgresql_credentials(conn_name, pg_host, port_int, pg_db,
                                               pg_user, pg_pwd, pg_ssl, pg_cert)

                elif db_type == "MSSQL":
                    ms_host   = mssql_host_var.get().strip()
                    ms_port   = mssql_port_var.get().strip()
                    ms_db     = mssql_db_var.get().strip()
                    ms_auth   = mssql_auth_var.get().strip()
                    ms_user   = mssql_user_var.get().strip()
                    ms_pwd    = mssql_pwd_var.get().strip()
                    ms_driver = mssql_driver_var.get().strip()
                    ms_enc    = mssql_encrypt_var.get().strip()
                    ms_trust  = mssql_trust_var.get().strip()
                    if not ms_host:
                        messagebox.showerror("Error", "Host is required")
                        return
                    if not ms_db:
                        messagebox.showerror("Error", "Database name is required")
                        return
                    if ms_auth == "SQL":
                        if not ms_user:
                            messagebox.showerror("Error", "Username is required for SQL Server Authentication")
                            return
                        if not ms_pwd:
                            messagebox.showerror("Error", "Password is required for SQL Server Authentication")
                            return
                    try:
                        port_int = int(ms_port)
                    except ValueError:
                        messagebox.showerror("Error", "Port must be a number")
                        return
                    self.conn_str_generator.save_mssql_credentials(
                        conn_name, ms_host, port_int, ms_db,
                        ms_user, ms_pwd, ms_auth, ms_driver, ms_enc, ms_trust
                    )

                else:  # SQLite
                    db_path = db_path_var.get().strip()
                    if not db_path:
                        messagebox.showerror("Error", "Database file path is required")
                        return
                    self.conn_str_generator.save_sqlite_credentials(conn_name, db_path)

                messagebox.showinfo("Success", f"Connection '{conn_name}' saved successfully")
                self.parent.populate_existing_connections_menu()
                self.connection_manager.connect_with_credman(conn_name)
                dialog.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to save connection: {str(e)}")

        ttk.Button(dialog, text="Save & Connect", command=save_connection).pack(pady=20)
        ttk.Button(dialog, text="Cancel",         command=dialog.destroy).pack(pady=5)
