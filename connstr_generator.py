import win32cred
from typing import List, Dict, Optional

ROOT_NAME = "DBExp"

def get_conn_string(connection_name: str, use_root_name: bool = True):
    if not type(connection_name) == str:
        raise ValueError(f"connection_name '{connection_name}' is not of type str")
    def get_cred(name: str) -> str:
        try:
            cred = win32cred.CredRead(name, win32cred.CRED_TYPE_GENERIC, 0)
        except Exception as e:
            print(f"Error with name '{name}': {str(e)}")
            return None
        return cred["CredentialBlob"].decode("utf-16")

    if use_root_name:
        root_name = f"{ROOT_NAME}_"
    else:
        root_name = ""

    driver   = get_cred(f"{root_name}{connection_name}_DRIVER")
    server   = get_cred(f"{root_name}{connection_name}_SERVER")
    database = get_cred(f"{root_name}{connection_name}_Database")
    dbq      = get_cred(f"{root_name}{connection_name}_DBQ")
    uid      = get_cred(f"{root_name}{connection_name}_UID")
    pwd      = get_cred(f"{root_name}{connection_name}_PWD")

    connString = f"\
DRIVER={driver};\
SERVER={server};\
Database={database};\
DBQ={dbq};\
UID={uid};\
PWD={pwd}"
    
    return connString


def save_odbc_user_credentials(connection_name: str, host: str ,user: str, password: str, use_root_name: bool = True):
    save_odbc_connection_credentials(driver          = "{Oracle dans OraClient19Home1}",
                                     connection_name = connection_name,
                                     host            = host,
                                     user            = user,
                                     password        = password,
                                     use_root_name   = use_root_name)


def save_odbc_connection_credentials(driver: str, connection_name: str, host: str, user: str, password: str, use_root_name: bool = True):
    """Save connection credentials to Windows Credential Manager"""
    if "_" in connection_name:
        raise ValueError("Underscores are not allowed in connection names")

    def save_in_win_cred(name: str, value: str):
        """Save credential to Windows Credential Manager"""
        try:
            credential = {
                "TargetName": name,
                "Type": win32cred.CRED_TYPE_GENERIC,
                "CredentialBlob": value,  # <-- MUST be str, not bytes
                "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
            }

            win32cred.CredWrite(credential, 0)

        except Exception as e:
            raise Exception(f"Failed to save credential '{name}': {str(e)}")

    if use_root_name:
        root_name = f"{ROOT_NAME}_"
    else:
        root_name = ""

    # Save all connection parameters
    save_in_win_cred(f"{root_name}{connection_name}_DRIVER", driver)
    save_in_win_cred(f"{root_name}{connection_name}_SERVER", host)
    save_in_win_cred(f"{root_name}{connection_name}_Database", host)  # For Oracle, database is often the same as server
    save_in_win_cred(f"{root_name}{connection_name}_DBQ", host)       # DBQ is often the same as server for Oracle
    save_in_win_cred(f"{root_name}{connection_name}_UID", user)
    save_in_win_cred(f"{root_name}{connection_name}_PWD", password)

def find_credentials_starting_with(prefix: str) -> List[Dict]:
    """Find all credentials whose TargetName starts with the given prefix"""
    try:
        # Use the prefix with wildcard
        filter_string = f"{prefix}*"
        creds = win32cred.CredEnumerate(filter_string, 0)
        return creds
    except Exception as e:
        # No credentials found matching the filter
        print(f"No credentials found starting with '{prefix}': {e}")
        return []

def parse_credential_name(target_name: str) -> Optional[str]:
    """
    Parse a credential target name to extract the connection name.
    Credential names follow the pattern: {ROOT_NAME}_{connection_name}_{TYPE}
    """
    if not target_name.startswith(f"{ROOT_NAME}_"):
        return None

    # Remove the DBExp_ prefix
    parts = target_name.split('_')

    if len(parts) == 3:
        return parts[1]

    return None

def get_all_connection_names() -> List[str]:
    """Get a list of all connection names from Windows Credential Manager"""
    connections = []
    try:
        creds = find_credentials_starting_with(f"{ROOT_NAME}_")

        # Use a set to avoid duplicates
        unique_names = set()

        for cred in creds:
            name = parse_credential_name(cred["TargetName"])
            if name and name not in unique_names:
                unique_names.add(name)

        return sorted(list(unique_names))
    except Exception as e:
        print(f"Error getting connection names: {str(e)}")
        return []
    
def delete_connection_credentials(connection_name: str):
    """Delete connection credentials from Windows Credential Manager"""
    def delete_cred(name: str):
        """Delete credential from Windows Credential Manager"""
        try:
            # First try to read the credential to verify it exists
            cred = win32cred.CredRead(name, win32cred.CRED_TYPE_GENERIC, 0)
            if cred:
                win32cred.CredDelete(name, win32cred.CRED_TYPE_GENERIC, 0)
        except Exception as e:
            # If credential doesn't exist, that's fine
            if "not found" not in str(e).lower():
                raise Exception(f"Failed to delete credential '{name}': {str(e)}")

    # Delete all connection parameters
    delete_cred(f"{ROOT_NAME}_{connection_name}_DRIVER")
    delete_cred(f"{ROOT_NAME}_{connection_name}_SERVER")
    delete_cred(f"{ROOT_NAME}_{connection_name}_Database")
    delete_cred(f"{ROOT_NAME}_{connection_name}_DBQ")
    delete_cred(f"{ROOT_NAME}_{connection_name}_UID")
    delete_cred(f"{ROOT_NAME}_{connection_name}_PWD")    