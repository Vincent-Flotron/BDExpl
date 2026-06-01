# DBExp — Database Explorer

A Windows/Linux desktop application built with Python and Tkinter for exploring and querying Oracle, PostgreSQL, and SQLite databases.

**Credential Management Options:**
1. **Windows Credential Manager** - Primary method for Windows systems, storing credentials securely without plain-text disk storage.
2. **Environment Cred File** - Alternative for cross-platform use (Linux/Windows):
   - Stores credentials in `~/dbexp_cred` (Linux/macOS) or `~\dbexp_cred` (Windows)

---

## Features

### Multi-database support
DBExp connects to five types of databases:

- **Oracle (ODBC)** — via the `pyodbc` driver using the `{Oracle dans OraClientXHome1}` ODBC driver. Requires Oracle Client 19 installed on the machine.
- **Oracle (OracleDB)** — via the `oracledb` Python driver (thin mode, no Oracle Client required), connecting with host, port, and SID.
- **PostgreSQL** — via `psycopg2`, with full SSL support (modes: `require`, `verify-ca`, `verify-full`, `prefer`, `allow`, `disable`) and optional CA certificate.
- **Microsoft SQL Server** — via `pyodbc` with any installed MSSQL ODBC driver (tested with "ODBC Driver 17/18 for SQL Server"). Supports both SQL Server Authentication and Windows Authentication, with configurable Encrypt and TrustServerCertificate settings.
- **SQLite** — by selecting a `.db`, `.sqlite`, or `.sqlite3` file on disk.

### Connection management
Connections are saved by name into Windows Credential Manager and can be reused across sessions. Each connection stores its type (`Oracle`, `OracleDB`, `PostgreSQL`, `MSSQL`, `SQLite`) and all required parameters. Connection names must not contain underscores (used internally as separators in credential key names).

From the **Connection** menu you can:
- **Connect with Existing** — pick a previously saved connection from the list.
- **Connect with New Credentials** — fill in a form, save the credentials, and immediately connect.
- **Disconnect** — close the active database connection.

### Database object explorer (left panel)
A tree view that loads the schema structure of the connected database. Expanding a schema lazy-loads its contents. Supported object types depend on the database engine:

| Object type        | Oracle | OracleDB | PostgreSQL | SQL Server | SQLite |
|--------------------|:------:|:--------:|:----------:|:----------:|:------:|
| Tables             | ✓     | ✓        | ✓          | ✓          | ✓      |
| Views              | ✓     | ✓        | ✓          | ✓          | ✗      |
| Stored procedures  | ✓     | ✓        | ✓          | ✓          | ✗      |
| Stored functions   | ✓     | ✓        | ✓          | ✓          | ✗      |
| Packages           | ✓     | ✓        | ✗          | ✗          | ✗      |

Right-clicking on a tree node opens a context menu with actions relevant to that object type, such as viewing data, structure, keys, indexes, triggers, procedure/function/package source, view query, view dependencies, or view comment.

### SQL query editor (middle panel)
A multi-tab SQL editor with:
- **Syntax highlighting** for SQL keywords, string literals, and comments.
- **Auto-indentation** aligned to the previous line on Enter.
- **Tab key** inserts spaces (not a hard tab character).
- **Ctrl+K+C** (on selected text) toggles line comments (`--`).
- **Ctrl+K+U** removes `--` comments from the selection.
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

### Status bar
Shows the current connection name and database type, or "Not connected" when idle.

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
| `pyodbc`                | Oracle connections via ODBC driver; SQL Server connections  |
| `oracledb`              | Oracle connections in thin mode (no Oracle Client required) |
| `psycopg2-binary`       | PostgreSQL connections                                      |
| `pywin32` (`win32cred`) | Windows Credential Manager access                           |

Install all at once:

```
pip install pyodbc oracledb psycopg2-binary pywin32
```

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

