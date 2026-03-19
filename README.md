# BDExpl
Database explorer that stores credentials on Windows Credentials Manager.

## Fonctionalities
- Connect using **ODBC** driver hard written **{Oracle dans OraClient19Home1}** to **Oracle** db.
- Connect to **PostgreSQL** databases via `psycopg2` (host, port, database, user, password).
- Connect to **SQLite** databases by file path.
- Free SQL edition with syntax highlighting.
- Exploration of **tables**, **views**, **stored procedures**, **stored functions**, **packages** (Oracle only).
- Credentials stored securely in **Windows Credential Manager** — nothing written to disk in plain text.

## Dependencies
| Package | Purpose |
|---------|---------|
| `pyodbc` | Oracle ODBC connections |
| `psycopg2` | PostgreSQL connections |
| `pywin32` (`win32cred`) | Windows Credential Manager |

Install with:
```
pip install psycopg2-binary pyodbc pywin32
```

## Saving a PostgreSQL connection
```python
from connstr_generator import save_postgresql_connection

save_postgresql_connection(
    connection_name="mydb",   # no underscores
    host="localhost",
    port=5432,
    database="mydb",
    user="postgres",
    password="secret",
)
```
