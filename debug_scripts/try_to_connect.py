import pyodbc
from credentials import (SERVER, PORT, DATABASE)

conn_str = f"DRIVER={{SQL Server}};SERVER={SERVER},{PORT};DATABASE={DATABASE};Trusted_Connection=yes;"
conn = pyodbc.connect(conn_str)


conn.close()
