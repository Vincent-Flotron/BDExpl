# DBExp — Database Explorer

A Windows desktop application built with Python and Tkinter for exploring and querying Oracle, PostgreSQL, and SQLite databases. Connection credentials are stored securely in the **Windows Credential Manager** — no passwords ever written to disk in plain text.

---

## Features

### Multi-database support
DBExp connects to four types of databases:

- **Oracle (ODBC)** — via the `pyodbc` driver using the `{Oracle dans OraClient19Home1}` ODBC driver. Requires Oracle Client 19 installed on the machine.
- **Oracle (OracleDB)** — via the `oracledb` Python driver (thin mode, no Oracle Client required), connecting with host, port, and SID.
- **PostgreSQL** — via `psycopg2`, with full SSL support (modes: `require`, `verify-ca`, `verify-full`, `prefer`, `allow`, `disable`) and optional CA certificate.
- **SQLite** — by selecting a `.db`, `.sqlite`, or `.sqlite3` file on disk.

### Connection management
Connections are saved by name into Windows Credential Manager and can be reused across sessions. Each connection stores its type (`Oracle`, `OracleDB`, `PostgreSQL`, `SQLite`) and all required parameters. Connection names must not contain underscores (used internally as separators in credential key names).

From the **Connection** menu you can:
- **Connect with Existing** — pick a previously saved connection from the list.
- **Connect with New Credentials** — fill in a form, save the credentials, and immediately connect.
- **Delete Connection** — permanently remove a saved connection's credentials from Windows Credential Manager.
- **Disconnect** — close the active database connection.

### Database object explorer (left panel)
A tree view that loads the schema structure of the connected database. Expanding a schema lazy-loads its contents. Supported object types depend on the database engine:

| Object type        | Oracle | OracleDB | PostgreSQL | SQLite |
|--------------------|:------:|:--------:|:----------:|:------:|
| Tables             | ✓     | ✓        | ✓          | ✓      |
| Views              | ✓     | ✓        | ✓          | ✗      |
| Stored procedures  | ✓     | ✓        | ✓          | ✗      |
| Stored functions   | ✓     | ✓        | ✓          | ✗      |
| Packages           | ✓     | ✓        | ✗          | ✗      |

Right-clicking on a tree node opens a context menu with actions relevant to that object type, such as viewing data, structure, keys, indexes, triggers, procedure/function/package source, view query, view dependencies, or view comment.

### SQL query editor (middle panel)
A multi-tab SQL editor with:
- **Syntax highlighting** for SQL keywords, string literals, and comments.
- **Auto-indentation** aligned to the previous line on Enter.
- **Tab key** inserts spaces (not a hard tab character).
- **Ctrl+C** (on selected text) toggles line comments (`--`).
- **Ctrl+U** removes `--` comments from the selection.
- **Shift+Tab** / **Tab** indent or de-indent the selection.
- **Ctrl+Z / Ctrl+Y** undo/redo.
- **F5** executes the full query in the active tab.
- **Execute Selection** runs only the highlighted portion of the query.
- Multiple tabs can be open simultaneously; each tab can be saved to a `.sql` file.
- The **File** menu provides New SQL, Open SQL, Save, and Save As actions.

### Query results (bottom panel)
Query results are displayed in a scrollable table. The panel supports:
- Copying selected rows to the clipboard.
- Exporting results to CSV.
- A **codepage selector** for controlling character encoding when copying/exporting.
- A **Show Labels** toggle.

### Status bar
Shows the current connection name and database type, or "Not connected" when idle.

---

## Project structure

| File                   | Role                  |
|------------------------|-----------------------|
| `DBExpl.py`            | Application entry point. Initialises the Tkinter window, assembles all panels, sets up the menu bar, and manages the new/delete connection dialogs. Also defines the `Theme` class that configures all ttk widget styles. |
| `Panels.py`            | All UI panels: `DatabaseTreePanel` (left tree view), `SQLQueryEditorPanel` (middle editor with tabs), `QueryResultPanel` (bottom results grid), `StatusBarPanel` (bottom bar). Also contains the `Helper` utility for creating scrollable treeviews and context menus. |
| `SQLText.py`           | Custom `tkinter.Text` subclass that adds SQL syntax highlighting, keyboard shortcuts (comment/uncomment, indent, auto-indent), and undo/redo support. Used as the editor widget inside each SQL tab. |
| `connection.py`        | `DBConnection` class — holds the active connection object and provides `connect_*` factory methods for each database type. Also has `get_queries_instance()` which returns the right `Queries` subclass based on the connection type. |
| `ConnectionManager.py` | `ConnectionManager` class — bridges the GUI and the credential store. Reads saved credentials via `connstr_generator`, builds the appropriate connection, updates the status bar, and triggers the tree reload. Also handles disconnect and credential deletion. |
| `connstr_generator.py` | All interactions with Windows Credential Manager (`win32cred`). Provides `save_*` functions to persist connection parameters, `get_*` functions to retrieve them, `get_all_connection_names()` to list saved connections, `get_connection_type()` to detect the database engine, and `delete_connection_credentials()` to remove all keys for a given connection. The credential key naming convention is `DBExp_{connection_name}_{FIELD}`. |
| `QueryManager.py`      | Abstract `Queries` base class and three concrete implementations: `QueriesOracle`, `QueriesSQLite`, `QueriesPostgreSQL`. Each implements the same set of SQL queries adapted to the engine's system catalog (e.g. `ALL_TABLES` for Oracle, `sqlite_master` for SQLite, `information_schema` for PostgreSQL). Also contains `QueryManager`, which executes a query against the active connection and returns columns + rows. |
| `make_exe.ps1`         | PowerShell one-liner that packages the application into a standalone Windows executable using PyInstaller (`--onefile --windowed`), with `win32timezone` included as a hidden import (required by `pywin32`). |

---

## debug_scripts/

Utility scripts for development and troubleshooting. They are **not** needed to run the application.

| File                  | Purpose        |
|-----------------------|----------------|
| `get_credentials.py`  | CLI tool to print the stored connection parameters for a given connection name. Takes two arguments: the database type (`oracle-driver`, `oracle-driver-less`, `sqlite`, `postgresql`) and the connection name. Useful for verifying that credentials were saved correctly in Windows Credential Manager without opening the GUI. |
| `print_keywords.py`   | Prints the full list of SQL keywords that `SQLText` uses for syntax highlighting. Each keyword is printed on its own line. Helpful when updating or auditing the keyword list in `SQLText.py`. |
| `testcase.py`         | Unit test for `QueriesSQLite` using an in-memory SQLite database. Currently tests `count_procedures_in_schema()`. Run with `python -m unittest debug_scripts/testcase.py`. |
| `test_connection.ps1` | PowerShell script that calls `Test-NetConnection` to check TCP reachability of a host/port pair. Takes `-ComputerName` and `-Port` as mandatory parameters. Useful for diagnosing network issues before attempting a database connection (e.g. verifying that a PostgreSQL port is open through a firewall). |

---

## Dependencies

| Package                 | Purpose                                                     |
|-------------------------|-------------------------------------------------------------|
| `pyodbc`                | Oracle connections via ODBC driver                          |
| `oracledb`              | Oracle connections in thin mode (no Oracle Client required) |
| `psycopg2-binary`       | PostgreSQL connections                                      |
| `pywin32` (`win32cred`) | Windows Credential Manager access                           |

Install all at once:

```
pip install pyodbc oracledb psycopg2-binary pywin32
```

> **Oracle ODBC driver:** the application is hardcoded to use the driver named `{Oracle dans OraClient19Home1}`. If your Oracle Client installation uses a different driver name, update `save_odbc_user_credentials()` in `connstr_generator.py`.

---

## Running

```
python DBExpl.py
```

## Building a standalone executable

```powershell
.\make_exe.ps1
```

This produces a single `DBExpl.exe` in the `dist/` folder via PyInstaller.

---

## Saving connections programmatically

If you need to pre-populate connections without going through the GUI, import from `connstr_generator` directly:

```python
from connstr_generator import (
    save_odbc_user_credentials,
    save_oracledb_connection,
    save_postgresql_connection,
    save_sqlite_connection,
)

# Oracle via ODBC
save_odbc_user_credentials("myoracle", host="MYSERVER", user="scott", password="tiger")

# Oracle via oracledb (no ODBC driver needed)
save_oracledb_connection("myoracledb", host="localhost", port=1521, sid="ORCL", user="scott", password="tiger")

# PostgreSQL
save_postgresql_connection("mypg", host="localhost", port=5432, database="mydb",
                           user="postgres", password="secret", sslmode="require")

# SQLite
save_sqlite_connection("mydb", db_path=r"C:\data\mydb.sqlite3")
```

> Connection names must not contain underscores.
