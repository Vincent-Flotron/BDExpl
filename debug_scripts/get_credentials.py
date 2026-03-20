import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))
from connstr_generator import get_conn_string, get_sqlite_conn_string, get_postgresql_conn_params, get_connection_type, delete_connection_credentials

# connection_name = "sif-dwh-appsrv"
# params = get_postgresql_conn_params(connection_name)
connection_name = "PCE-report-vevey"
params = get_conn_string(connection_name)
# ssl_args = {"sslmode": params["sslmode"]}
print(params)
