import sys
import argparse
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))
from connstr_generator import get_conn_string, get_oracledb_conn_params, get_sqlite_conn_string, get_postgresql_conn_params

# Connection type constants
ORACLE_DRIVER     = "oracle-driver"
ORACLE_DRIVERLESS = "oracle-driver-less"
SQLITE            = "sqlite"
POSTGRESQL        = "postgresql"

def main():
    parser = argparse.ArgumentParser(description='Get database connection parameters')
    parser.add_argument('db_type', choices=[ORACLE_DRIVER, ORACLE_DRIVERLESS, SQLITE, POSTGRESQL],
                       help='Type of database connection')
    parser.add_argument('connection_name', help='Name of the connection')
    args = parser.parse_args()

    if args.db_type == ORACLE_DRIVER:
        params = get_conn_string(args.connection_name)
    elif args.db_type == ORACLE_DRIVERLESS:
        params = get_oracledb_conn_params(args.connection_name)
    elif args.db_type == SQLITE:
        params = get_sqlite_conn_string(args.connection_name)
    elif args.db_type == POSTGRESQL:
        params = get_postgresql_conn_params(args.connection_name)

    print(params)

if __name__ == "__main__":
    main()