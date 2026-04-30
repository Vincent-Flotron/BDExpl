import sys
import argparse
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))
from connstr_generator import ConnectionStringGenerator
# get_conn_string, get_oracledb_conn_params, get_sqlite_conn_string, get_postgresql_conn_params, get_mssql_conn_params

# Connection type constants
ORACLE_DRIVER     = "oracle-driver"
ORACLE_DRIVERLESS = "oracle-driver-less"
SQLITE            = "sqlite"
POSTGRESQL        = "postgresql"
MSSQL             = "mssql"

def main():
    parser = argparse.ArgumentParser(description='Get database connection parameters')
    parser.add_argument('cred_man', choices=["win", "env_var"],
                       help='Type the credential manager to use')
    parser.add_argument('db_type', choices=[ORACLE_DRIVER, ORACLE_DRIVERLESS, SQLITE, POSTGRESQL, MSSQL],
                       help='Type of database connection')
    
    parser.add_argument('connection_name', help='Name of the connection')
    args = parser.parse_args()


    connStrGen = ConnectionStringGenerator()
    if args.db_type == ORACLE_DRIVER:
        params = connStrGen.get_conn_string(args.connection_name)
    elif args.db_type == ORACLE_DRIVERLESS:
        params = connStrGen.get_oracledb_conn_params(args.connection_name)
    elif args.db_type == SQLITE:
        params = connStrGen.get_sqlite_conn_string(args.connection_name)
    elif args.db_type == POSTGRESQL:
        params = connStrGen.get_postgresql_conn_params(args.connection_name)
    elif args.db_type == MSSQL:
        params = connStrGen.get_mssql_conn_params(args.connection_name)

    print(params)

if __name__ == "__main__":
    main()