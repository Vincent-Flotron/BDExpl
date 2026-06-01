"""
ConnectionDialogs.py - Separated connection dialog classes for DBExplorer

This module contains dialog classes for managing database connections:
- ManageConnectionsDialog: Full connection manager (new, edit, rename, clone, delete, test)
- NewConnectionDialog: Dialog for creating new connections (kept for backward compatibility)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional


# ── Shared helper: build a scrollable form frame ──────────────────────────────

def _make_scrollable(parent):
    """Return (outer_frame, inner_canvas, scrollable_frame) for a scrollable form area."""
    outer = tk.Frame(parent)
    canvas = tk.Canvas(outer, highlightthickness=0)
    vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    inner = tk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(win_id, width=canvas.winfo_width())

    inner.bind("<Configure>", _on_configure)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    return outer, canvas, inner


# ── Connection form mixin ─────────────────────────────────────────────────────

class _ConnectionFormMixin:
    """
    Builds and manages the per-DB-type form widgets.
    Must be mixed into a class that sets self.credential_manager and provides
    a container frame via self._form_container.
    """

    # ── public API ────────────────────────────────────────────────────────────

    def _build_form(self, container):
        """Build all DB-type fields inside *container*. Call once."""
        pad = dict(fill=tk.X, pady=4)

        # ── Oracle (ODBC) ──────────────────────────────────────────────
        self._oracle_frame = tk.Frame(container)

        tk.Label(self._oracle_frame, text="Driver:").pack(anchor=tk.W)
        self._odr_driver_var = tk.StringVar()
        tk.Entry(self._oracle_frame, textvariable=self._odr_driver_var).pack(**pad)

        tk.Label(self._oracle_frame, text="Host or Server name:").pack(anchor=tk.W)
        self._odr_host_var = tk.StringVar()
        tk.Entry(self._oracle_frame, textvariable=self._odr_host_var).pack(**pad)

        tk.Label(self._oracle_frame, text="Username:").pack(anchor=tk.W)
        self._odr_user_var = tk.StringVar()
        tk.Entry(self._oracle_frame, textvariable=self._odr_user_var).pack(**pad)

        tk.Label(self._oracle_frame, text="Password:").pack(anchor=tk.W)
        self._odr_pwd_var = tk.StringVar()
        tk.Entry(self._oracle_frame, textvariable=self._odr_pwd_var).pack(**pad)

        # ── OracleDB (python-oracledb) ─────────────────────────────────
        self._oracledb_frame = tk.Frame(container)
        tk.Label(self._oracledb_frame, text="Host:").pack(anchor=tk.W)
        self._odb_host_var = tk.StringVar(value="localhost")
        tk.Entry(self._oracledb_frame, textvariable=self._odb_host_var).pack(**pad)
        tk.Label(self._oracledb_frame, text="Port:").pack(anchor=tk.W)
        self._odb_port_var = tk.StringVar(value="1521")
        tk.Entry(self._oracledb_frame, textvariable=self._odb_port_var).pack(**pad)
        tk.Label(self._oracledb_frame, text="SID:").pack(anchor=tk.W)
        self._odb_sid_var = tk.StringVar()
        tk.Entry(self._oracledb_frame, textvariable=self._odb_sid_var).pack(**pad)
        tk.Label(self._oracledb_frame, text="Username:").pack(anchor=tk.W)
        self._odb_user_var = tk.StringVar()
        tk.Entry(self._oracledb_frame, textvariable=self._odb_user_var).pack(**pad)
        tk.Label(self._oracledb_frame, text="Password:").pack(anchor=tk.W)
        self._odb_pwd_var = tk.StringVar()
        tk.Entry(self._oracledb_frame, textvariable=self._odb_pwd_var).pack(**pad)

        # ── PostgreSQL ─────────────────────────────────────────────────
        self._pg_frame = tk.Frame(container)
        tk.Label(self._pg_frame, text="Host:").pack(anchor=tk.W)
        self._pg_host_var = tk.StringVar(value="localhost")
        tk.Entry(self._pg_frame, textvariable=self._pg_host_var).pack(**pad)
        tk.Label(self._pg_frame, text="Port:").pack(anchor=tk.W)
        self._pg_port_var = tk.StringVar(value="5432")
        tk.Entry(self._pg_frame, textvariable=self._pg_port_var).pack(**pad)
        tk.Label(self._pg_frame, text="Database:").pack(anchor=tk.W)
        self._pg_db_var = tk.StringVar()
        tk.Entry(self._pg_frame, textvariable=self._pg_db_var).pack(**pad)
        tk.Label(self._pg_frame, text="Username:").pack(anchor=tk.W)
        self._pg_user_var = tk.StringVar()
        tk.Entry(self._pg_frame, textvariable=self._pg_user_var).pack(**pad)
        tk.Label(self._pg_frame, text="Password:").pack(anchor=tk.W)
        self._pg_pwd_var = tk.StringVar()
        tk.Entry(self._pg_frame, textvariable=self._pg_pwd_var).pack(**pad)
        tk.Label(self._pg_frame, text="SSL Mode:").pack(anchor=tk.W)
        self._pg_sslmode_var = tk.StringVar(value="require")
        ttk.Combobox(
            self._pg_frame, textvariable=self._pg_sslmode_var,
            values=["require", "verify-ca", "verify-full", "prefer", "allow", "disable"],
            state="readonly", width=18,
        ).pack(anchor=tk.W, pady=4)
        tk.Label(self._pg_frame, text="CA Certificate (optional):").pack(anchor=tk.W)
        self._pg_sslrootcert_var = tk.StringVar()
        _cert_row = tk.Frame(self._pg_frame)
        _cert_row.pack(**pad)
        tk.Entry(_cert_row, textvariable=self._pg_sslrootcert_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(_cert_row, text="...", width=3,
                   command=lambda: self._pg_sslrootcert_var.set(
                       filedialog.askopenfilename(
                           title="Select CA Certificate",
                           filetypes=[("Certificate files", "*.pem *.crt *.cer"), ("All files", "*.*")]
                       ) or self._pg_sslrootcert_var.get()
                   )).pack(side=tk.LEFT, padx=(4, 0))

        # ── SQL Server ─────────────────────────────────────────────────
        self._mssql_frame = tk.Frame(container)
        tk.Label(self._mssql_frame, text="Host / Server name:").pack(anchor=tk.W)
        self._mssql_host_var = tk.StringVar(value="localhost")
        tk.Entry(self._mssql_frame, textvariable=self._mssql_host_var).pack(**pad)
        tk.Label(self._mssql_frame, text="Port:").pack(anchor=tk.W)
        self._mssql_port_var = tk.StringVar(value="1433")
        tk.Entry(self._mssql_frame, textvariable=self._mssql_port_var).pack(**pad)
        tk.Label(self._mssql_frame, text="Database:").pack(anchor=tk.W)
        self._mssql_db_var = tk.StringVar()
        tk.Entry(self._mssql_frame, textvariable=self._mssql_db_var).pack(**pad)
        tk.Label(self._mssql_frame, text="Authentication:").pack(anchor=tk.W)
        self._mssql_auth_var = tk.StringVar(value="SQL")
        _auth_row = tk.Frame(self._mssql_frame)
        _auth_row.pack(anchor=tk.W, pady=4)
        ttk.Radiobutton(_auth_row, text="SQL Server Auth", variable=self._mssql_auth_var, value="SQL").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(_auth_row, text="Windows Auth",    variable=self._mssql_auth_var, value="Windows").pack(side=tk.LEFT, padx=5)
        self._mssql_user_label = tk.Label(self._mssql_frame, text="Username:")
        self._mssql_user_label.pack(anchor=tk.W)
        self._mssql_user_var = tk.StringVar()
        self._mssql_user_entry = tk.Entry(self._mssql_frame, textvariable=self._mssql_user_var)
        self._mssql_user_entry.pack(**pad)
        self._mssql_pwd_label = tk.Label(self._mssql_frame, text="Password:")
        self._mssql_pwd_label.pack(anchor=tk.W)
        self._mssql_pwd_var = tk.StringVar()
        self._mssql_pwd_entry = tk.Entry(self._mssql_frame, textvariable=self._mssql_pwd_var)
        self._mssql_pwd_entry.pack(**pad)
        tk.Label(self._mssql_frame, text="ODBC Driver:").pack(anchor=tk.W)
        self._mssql_driver_var = tk.StringVar(value="{ODBC Driver 17 for SQL Server}")
        ttk.Combobox(
            self._mssql_frame, textvariable=self._mssql_driver_var,
            values=["{ODBC Driver 18 for SQL Server}", "{ODBC Driver 17 for SQL Server}", "{SQL Server}"],
            width=35,
        ).pack(anchor=tk.W, pady=4)
        tk.Label(self._mssql_frame, text="Encrypt:").pack(anchor=tk.W)
        self._mssql_encrypt_var = tk.StringVar(value="yes")
        ttk.Combobox(
            self._mssql_frame, textvariable=self._mssql_encrypt_var,
            values=["yes", "no", "strict"], state="readonly", width=10,
        ).pack(anchor=tk.W, pady=4)
        tk.Label(self._mssql_frame, text="Trust Server Certificate:").pack(anchor=tk.W)
        self._mssql_trust_var = tk.StringVar(value="yes")
        ttk.Combobox(
            self._mssql_frame, textvariable=self._mssql_trust_var,
            values=["yes", "no"], state="readonly", width=10,
        ).pack(anchor=tk.W, pady=4)
        self._mssql_auth_var.trace_add("write", self._toggle_mssql_auth)

        # ── SQLite ─────────────────────────────────────────────────────
        self._sqlite_frame = tk.Frame(container)
        tk.Label(self._sqlite_frame, text="Database File Path:").pack(anchor=tk.W)
        self._db_path_var = tk.StringVar()
        tk.Entry(self._sqlite_frame, textvariable=self._db_path_var).pack(**pad)
        ttk.Button(self._sqlite_frame, text="Browse…",
                   command=self._browse_sqlite).pack(anchor=tk.W, pady=4)

        self._all_db_frames = {
            "Oracle":     self._oracle_frame,
            "OracleDB":   self._oracledb_frame,
            "PostgreSQL": self._pg_frame,
            "MSSQL":      self._mssql_frame,
            "SQLite":     self._sqlite_frame,
        }

    def _toggle_db_fields(self, *_):
        active = self._all_db_frames[self._db_type_var.get()]
        for f in self._all_db_frames.values():
            f.pack_forget()
        active.pack(fill=tk.X, padx=0, pady=4)

    def _toggle_mssql_auth(self, *_):
        if self._mssql_auth_var.get() == "Windows":
            self._mssql_user_label.pack_forget()
            self._mssql_user_entry.pack_forget()
            self._mssql_pwd_label.pack_forget()
            self._mssql_pwd_entry.pack_forget()
        else:
            self._mssql_user_label.pack(anchor=tk.W)
            self._mssql_user_entry.pack(fill=tk.X, pady=4)
            self._mssql_pwd_label.pack(anchor=tk.W)
            self._mssql_pwd_entry.pack(fill=tk.X, pady=4)

    def _browse_sqlite(self):
        path = filedialog.askopenfilename(
            title="Select SQLite Database File",
            filetypes=[("SQLite Database Files", "*.db *.sqlite *.sqlite3")]
        )
        if path:
            self._db_path_var.set(path)

    # ── populate form from credential manager ────────────────────────────────

    def _load_connection_into_form(self, conn_name):
        """Fill all form vars from stored credentials for *conn_name*."""
        try:
            conn_type = self.credential_manager.get_connection_type_offline(conn_name)
            self._db_type_var.set(conn_type)
            self._toggle_db_fields()

            if conn_type == "Oracle":
                params = self.credential_manager.get_conn_string(conn_name)  # returns raw conn string
                # Best effort: the oracle ODBC path just returns a connection string
                params_splitted = params.split(";")

                driver   = params_splitted[0].split("=")[1]
                host     = params_splitted[1].split("=")[1]
                user_id  = params_splitted[4].split("=")[1]
                password = params_splitted[5].split("=")[1]

                self._odr_driver_var  .set( driver   )
                self._odr_host_var    .set( host     )
                self._odr_user_var.set( user_id  )
                self._odr_pwd_var     .set( password )

            elif conn_type == "OracleDB":
                p = self.credential_manager.get_oracledb_conn_params(conn_name)
                self._odb_host_var.set(p.get("host", ""))
                self._odb_port_var.set(str(p.get("port", "1521")))
                self._odb_sid_var.set(p.get("sid", ""))
                self._odb_user_var.set(p.get("user", ""))
                self._odb_pwd_var.set(p.get("password", ""))

            elif conn_type == "PostgreSQL":
                p = self.credential_manager.get_postgresql_conn_params(conn_name)
                self._pg_host_var.set(p.get("host", ""))
                self._pg_port_var.set(str(p.get("port", "5432")))
                self._pg_db_var.set(p.get("database", ""))
                self._pg_user_var.set(p.get("user", ""))
                self._pg_pwd_var.set(p.get("password", ""))
                self._pg_sslmode_var.set(p.get("sslmode", "require"))
                self._pg_sslrootcert_var.set(p.get("sslrootcert", ""))

            elif conn_type == "MSSQL":
                p = self.credential_manager.get_mssql_conn_params(conn_name)
                self._mssql_host_var.set(p.get("host", ""))
                self._mssql_port_var.set(str(p.get("port", "1433")))
                self._mssql_db_var.set(p.get("database", ""))
                self._mssql_auth_var.set(p.get("auth_type", "SQL"))
                self._mssql_user_var.set(p.get("user", ""))
                self._mssql_pwd_var.set(p.get("password", ""))
                self._mssql_driver_var.set(p.get("driver", "{ODBC Driver 17 for SQL Server}"))
                self._mssql_encrypt_var.set(p.get("encrypt", "yes"))
                self._mssql_trust_var.set(p.get("trust_server_cert", "yes"))

            elif conn_type == "SQLite":
                db_path = self.credential_manager.get_sqlite_conn_string(conn_name)
                self._db_path_var.set(db_path)

        except Exception as e:
            messagebox.showerror("Error", f"Could not load connection parameters: {e}")

    def _clear_form(self):
        """Reset all form variables to defaults."""
        for var in (self._odr_driver_var, self._odr_host_var, self._odr_user_var, self._odr_pwd_var,
                    self._odb_host_var, self._odb_sid_var, self._odb_user_var, self._odb_pwd_var,
                    self._pg_db_var, self._pg_user_var, self._pg_pwd_var, self._pg_sslrootcert_var,
                    self._mssql_db_var, self._mssql_user_var, self._mssql_pwd_var,
                    self._db_path_var):
            var.set("")
        self._odb_port_var.set("1521")
        self._pg_host_var.set("localhost")
        self._pg_port_var.set("5432")
        self._mssql_host_var.set("localhost")
        self._mssql_port_var.set("1433")
        self._mssql_auth_var.set("SQL")
        self._mssql_encrypt_var.set("yes")
        self._mssql_trust_var.set("yes")
        self._pg_sslmode_var.set("require")
        self._odb_host_var.set("localhost")

    # ── gather + validate form data ──────────────────────────────────────────

    def _gather_params(self):
        """
        Validate and return (db_type, params_dict).
        Raises ValueError with a human-readable message on invalid input.
        """
        db_type = self._db_type_var.get()

        if db_type == "Oracle":
            d  = self._odr_driver_var.get().strip()
            h  = self._odr_host_var.get().strip()
            u  = self._odr_user_var.get().strip()
            pw = self._odr_pwd_var.get().strip()
            if not d:  raise ValueError("Driver is required")
            if not h:  raise ValueError("Host is required")
            if not u:  raise ValueError("Username is required")
            if not pw: raise ValueError("Password is required")
            return db_type, {"driver": d, "host": h, "user": u, "password": pw}

        elif db_type == "OracleDB":
            h  = self._odb_host_var.get().strip()
            pt = self._odb_port_var.get().strip()
            s  = self._odb_sid_var.get().strip()
            u  = self._odb_user_var.get().strip()
            pw = self._odb_pwd_var.get().strip()
            if not h:  raise ValueError("Host is required")
            if not s:  raise ValueError("SID is required")
            if not u:  raise ValueError("Username is required")
            if not pw: raise ValueError("Password is required")
            try: pt = int(pt)
            except ValueError: raise ValueError("Port must be a number")
            return db_type, {"host": h, "port": pt, "sid": s, "user": u, "password": pw}

        elif db_type == "PostgreSQL":
            h   = self._pg_host_var.get().strip()
            pt  = self._pg_port_var.get().strip()
            db  = self._pg_db_var.get().strip()
            u   = self._pg_user_var.get().strip()
            pw  = self._pg_pwd_var.get().strip()
            ssl = self._pg_sslmode_var.get().strip()
            cert= self._pg_sslrootcert_var.get().strip()
            if not h:  raise ValueError("Host is required")
            if not db: raise ValueError("Database name is required")
            if not u:  raise ValueError("Username is required")
            if not pw: raise ValueError("Password is required")
            try: pt = int(pt)
            except ValueError: raise ValueError("Port must be a number")
            return db_type, {"host": h, "port": pt, "database": db,
                             "user": u, "password": pw, "sslmode": ssl, "sslrootcert": cert}

        elif db_type == "MSSQL":
            h    = self._mssql_host_var.get().strip()
            pt   = self._mssql_port_var.get().strip()
            db   = self._mssql_db_var.get().strip()
            auth = self._mssql_auth_var.get().strip()
            u    = self._mssql_user_var.get().strip()
            pw   = self._mssql_pwd_var.get().strip()
            drv  = self._mssql_driver_var.get().strip()
            enc  = self._mssql_encrypt_var.get().strip()
            trust= self._mssql_trust_var.get().strip()
            if not h:  raise ValueError("Host is required")
            if not db: raise ValueError("Database name is required")
            if auth == "SQL":
                if not u:  raise ValueError("Username is required for SQL Server Auth")
                if not pw: raise ValueError("Password is required for SQL Server Auth")
            try: pt = int(pt)
            except ValueError: raise ValueError("Port must be a number")
            return db_type, {"host": h, "port": pt, "database": db, "auth_type": auth,
                             "user": u, "password": pw, "driver": drv,
                             "encrypt": enc, "trust_server_cert": trust}

        else:  # SQLite
            p = self._db_path_var.get().strip()
            if not p: raise ValueError("Database file path is required")
            return db_type, {"path": p}

    # ── save to credential manager ────────────────────────────────────────────

    def _save_params(self, conn_name, db_type, params):
        cm = self.credential_manager
        if db_type == "Oracle":
            cm.save_oracle_odbc_user_credentials(conn_name, params["driver"], params["host"], params["user"], params["password"])
        elif db_type == "OracleDB":
            cm.save_oracledb_credentials(conn_name, params["host"], params["port"], params["sid"],
                                         params["user"], params["password"])
        elif db_type == "PostgreSQL":
            cm.save_postgresql_credentials(conn_name, params["host"], params["port"], params["database"],
                                           params["user"], params["password"],
                                           params["sslmode"], params["sslrootcert"])
        elif db_type == "MSSQL":
            cm.save_mssql_credentials(conn_name, params["host"], params["port"], params["database"],
                                      params["user"], params["password"], params["auth_type"],
                                      params["driver"], params["encrypt"], params["trust_server_cert"])
        elif db_type == "SQLite":
            cm.save_sqlite_credentials(conn_name, params["path"])

    # ── test connection (no side-effects on active connection) ────────────────

    def _test_connection(self, db_type, params, status_label, timeout=3.0):
        """Delegate to ConnectionManager with custom timeout."""
        status_label.config(text="Testing…", fg="gray")
        status_label.update_idletasks()
        
        # Pass the timeout argument here
        ok, msg = self.connection_manager.test_connection_from_params(db_type, params, timeout=timeout)
        
        status_label.config(
            text=f"✔  {msg}" if ok else f"✘  {msg}",
            fg="#1a7a1a" if ok else "#b00000",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ManageConnectionsDialog
# ═══════════════════════════════════════════════════════════════════════════════

class ManageConnectionsDialog(_ConnectionFormMixin):
    """
    Full connection manager dialog.
    Left pane: list of saved connections + action buttons.
    Right pane: scrollable edit/create form with Test & Save buttons.
    """

    def __init__(self, parent):
        self.root = parent.root
        self.parent = parent
        self.credential_manager = parent.credential_manager
        self.connection_manager = parent.connection_manager
        self._editing_name: Optional[str] = None   # None = new entry
        self._is_new = False

    def show(self):
        self._dialog = tk.Toplevel(self.root)
        self._dialog.title("Manage Connections")
        self._dialog.geometry("820x620")
        self._dialog.minsize(700, 500)
        self._dialog.transient(self.root)
        self._dialog.grab_set()

        # ── top: storage indicator ────────────────────────────────────
        top_bar = tk.Frame(self._dialog, bg="#e8edf3", pady=4)
        top_bar.pack(fill=tk.X)
        storage_text = ('Cred File' if self.credential_manager.use_cred_file_vars
                        else 'Windows Credential Manager')
        tk.Label(top_bar, text=f"Storage: {storage_text}",
                 fg="#336699", bg="#e8edf3", font=("Helvetica", 9, "italic")).pack(side=tk.LEFT, padx=10)

        # ── main split ────────────────────────────────────────────────
        paned = tk.PanedWindow(self._dialog, orient=tk.HORIZONTAL, sashwidth=5,
                               sashrelief=tk.RIDGE, bg="#c0c8d0")
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # ── LEFT pane ─────────────────────────────────────────────────
        left = tk.Frame(paned, width=220)
        paned.add(left, minsize=170)

        tk.Label(left, text="Saved Connections", font=("Helvetica", 10, "bold")).pack(pady=(6, 2))

        list_frame = tk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=6)
        vsb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self._conn_listbox = tk.Listbox(list_frame, yscrollcommand=vsb.set,
                                        selectmode=tk.SINGLE, activestyle="dotbox",
                                        font=("Helvetica", 9))
        vsb.config(command=self._conn_listbox.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._conn_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._conn_listbox.bind("<<ListboxSelect>>", self._on_list_select)

        btn_frame = tk.Frame(left)
        btn_frame.pack(fill=tk.X, padx=6, pady=6)
        for label, cmd in [
            ("＋ New",    self._action_new),
            ("✎ Edit",   self._action_edit),
            ("⧉ Clone",  self._action_clone),
            ("⌧ Delete", self._action_delete),
        ]:
            ttk.Button(btn_frame, text=label, command=cmd).pack(fill=tk.X, pady=2)

        # ── RIGHT pane ────────────────────────────────────────────────
        right = tk.Frame(paned)
        paned.add(right, minsize=380)

        # Title bar for the right pane
        self._form_title_var = tk.StringVar(value="Select a connection or click  ＋ New")
        tk.Label(right, textvariable=self._form_title_var,
                 font=("Helvetica", 10, "bold"), anchor=tk.W).pack(fill=tk.X, padx=10, pady=(6, 0))
        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=4)

        # Connection name row
        name_row = tk.Frame(right)
        name_row.pack(fill=tk.X, padx=10)
        tk.Label(name_row, text="Connection Name:", width=18, anchor=tk.W).pack(side=tk.LEFT)
        self._conn_name_var = tk.StringVar()
        self._conn_name_entry = tk.Entry(name_row, textvariable=self._conn_name_var, width=30)
        self._conn_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # DB type selector
        type_row = tk.Frame(right)
        type_row.pack(fill=tk.X, padx=10, pady=(6, 0))
        tk.Label(type_row, text="Database Type:", width=18, anchor=tk.W).pack(side=tk.LEFT)
        self._db_type_var = tk.StringVar(value="Oracle")
        for label, val in [("Oracle", "Oracle"), ("OracleDB", "OracleDB"),
                            ("PostgreSQL", "PostgreSQL"), ("SQL Server", "MSSQL"),
                            ("SQLite", "SQLite")]:
            ttk.Radiobutton(type_row, text=label, variable=self._db_type_var,
                            value=val).pack(side=tk.LEFT, padx=6)
        self._db_type_var.trace_add("write", self._toggle_db_fields)

        # Scrollable form area
        scroll_outer, _canvas, form_inner = _make_scrollable(right)
        scroll_outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self._build_form(form_inner)

        # ── bottom button row ─────────────────────────────────────────
        btn_row = tk.Frame(right)
        btn_row.pack(fill=tk.X, padx=10, pady=(4, 8))

        self._test_status = tk.Label(btn_row, text="", anchor=tk.W,
                                     font=("Helvetica", 9, "italic"))
        self._test_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(btn_row, text="Test Connection",
                   command=self._action_test).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_row, text="Save",
                   command=self._action_save).pack(side=tk.RIGHT)

        # ── bottom close bar ──────────────────────────────────────────
        close_bar = tk.Frame(self._dialog)
        close_bar.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(close_bar, text="Close", command=self._dialog.destroy).pack(side=tk.RIGHT)

        # ── Timeout Setting (Common to all) ────────────────────────────────────
        timeout_row = tk.Frame(close_bar)
        timeout_row.pack(fill=tk.X, pady=(10, 4)) # Add some separation
        
        tk.Label(timeout_row, text="Connection Timeout (seconds):", width=25, anchor=tk.W).pack(side=tk.LEFT)
        
        self._timeout_var = tk.StringVar(value="3") # Default to 3 seconds
        timeout_entry = tk.Entry(timeout_row, textvariable=self._timeout_var, width=10)
        timeout_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(timeout_row, text="(Max wait time)", font=("Helvetica", 8), fg="gray").pack(side=tk.LEFT)


        # Populate list and disable form until an action is chosen
        self._refresh_list()
        self._set_form_enabled(False)

    # ── list helpers ──────────────────────────────────────────────────────────

    def _refresh_list(self, select_name: Optional[str] = None):
        try:
            connections = self.credential_manager.get_all_connection_names()
        except Exception:
            connections = []
        self._conn_listbox.delete(0, tk.END)
        for name in connections:
            self._conn_listbox.insert(tk.END, name)
        if select_name and select_name in connections:
            idx = connections.index(select_name)
            self._conn_listbox.selection_set(idx)
            self._conn_listbox.see(idx)

    def _selected_name(self) -> Optional[str]:
        sel = self._conn_listbox.curselection()
        if not sel:
            return None
        return self._conn_listbox.get(sel[0])

    def _on_list_select(self, _event=None):
        name = self._selected_name()
        if name:
            self._editing_name = name
            self._is_new = False
            self._form_title_var.set(f"Editing: {name}")
            self._conn_name_var.set(name)
            self._set_form_enabled(True)
            self._load_connection_into_form(name)
            self._test_status.config(text="")

    # ── form enable/disable ───────────────────────────────────────────────────

    def _set_form_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self._conn_name_entry.config(state=state)
        for f in self._all_db_frames.values() if hasattr(self, '_all_db_frames') else []:
            for w in f.winfo_children():
                try:
                    w.config(state=state)
                except tk.TclError:
                    pass

    # ── action handlers ───────────────────────────────────────────────────────

    def _action_new(self):
        self._editing_name = None
        self._is_new = True
        self._form_title_var.set("New Connection")
        self._conn_name_var.set("")
        self._db_type_var.set("Oracle")
        self._clear_form()
        self._toggle_db_fields()
        self._set_form_enabled(True)
        self._test_status.config(text="")
        self._conn_name_entry.focus_set()

    def _action_edit(self):
        name = self._selected_name()
        if not name:
            messagebox.showinfo("Info", "Please select a connection to edit", parent=self._dialog)
            return
        self._on_list_select()

    def _action_clone(self):
        src = self._selected_name()
        if not src:
            messagebox.showinfo("Info", "Please select a connection to clone", parent=self._dialog)
            return
        new_name = self._ask_name(title="Clone Connection",
                                  prompt=f"New name for the clone of  '{src}':")
        if not new_name:
            return
        # Load source params then save under new name
        try:
            db_type = self.credential_manager.get_connection_type_offline(src)
            self._db_type_var.set(db_type)
            self._load_connection_into_form(src)
            _, params = self._gather_params()
            self._save_params(new_name, db_type, params)
            self.parent.populate_existing_connections_menu()
            self._refresh_list(select_name=new_name)
            self._on_list_select()
            messagebox.showinfo("Cloned",
                                f"Connection '{src}' cloned as '{new_name}'.",
                                parent=self._dialog)
        except Exception as e:
            messagebox.showerror("Error", f"Clone failed: {e}", parent=self._dialog)

    def _action_delete(self):
        name = self._selected_name()
        if not name:
            messagebox.showinfo("Info", "Please select a connection to delete", parent=self._dialog)
            return
        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Permanently delete the connection '{name}'?\n\nThis cannot be undone.",
            parent=self._dialog
        ):
            return
        if self.connection_manager.delete_connection(name):
            self.parent.populate_existing_connections_menu()
            self._refresh_list()
            self._form_title_var.set("Select a connection or click  ＋ New")
            self._conn_name_var.set("")
            self._set_form_enabled(False)
            self._test_status.config(text="")

    def _action_test(self):
        """Validate form and test the connection without saving."""
        try:
            db_type, params = self._gather_params()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e), parent=self._dialog)
            return

        # Parse timeout value
        try:
            timeout_val = float(self._timeout_var.get())
            if timeout_val <= 0:
                raise ValueError("Timeout must be positive")
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid timeout value. Please enter a positive number.", parent=self._dialog)
            return

        # Pass the timeout to the manager
        self._test_connection(db_type, params, self._test_status, timeout=timeout_val)


    def _action_save(self):
        """Validate, save (overwriting if editing), refresh list."""
        conn_name = self._conn_name_var.get().strip()
        if not conn_name:
            messagebox.showerror("Error", "Connection name is required", parent=self._dialog)
            return
        try:
            db_type, params = self._gather_params()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e), parent=self._dialog)
            return

        try:
            # If renaming, delete the old entry first
            if self._editing_name and self._editing_name != conn_name:
                self.credential_manager.delete_connection_credentials(self._editing_name)

            self._save_params(conn_name, db_type, params)
            self._editing_name = conn_name
            self._is_new = False
            self._form_title_var.set(f"Editing: {conn_name}")
            self.parent.populate_existing_connections_menu()
            self._refresh_list(select_name=conn_name)
            self._test_status.config(text=f"✔  '{conn_name}' saved", fg="#1a7a1a")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}", parent=self._dialog)

    # ── small helper ──────────────────────────────────────────────────────────

    def _ask_name(self, title: str, prompt: str) -> Optional[str]:
        """Tiny modal dialog that asks for a single string."""
        dlg = tk.Toplevel(self._dialog)
        dlg.title(title)
        dlg.geometry("380x130")
        dlg.transient(self._dialog)
        dlg.grab_set()
        tk.Label(dlg, text=prompt, wraplength=340).pack(pady=(14, 4), padx=14)
        var = tk.StringVar()
        entry = tk.Entry(dlg, textvariable=var, width=36)
        entry.pack(padx=14)
        entry.focus_set()
        result = [None]

        def _ok():
            result[0] = var.get().strip()
            dlg.destroy()

        btn_row = tk.Frame(dlg)
        btn_row.pack(pady=10)
        ttk.Button(btn_row, text="OK",     command=_ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT)
        entry.bind("<Return>", lambda _: _ok())
        dlg.wait_window()
        return result[0]

