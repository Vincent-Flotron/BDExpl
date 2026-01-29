import pyodbc

class DBConnection:
    def __init__(self):
        self.connections = {}
        self.current_connection = None

    def add_connection(self, name, host, port, user, password, db_type="Oracle", ssh_tunnel=None):
        self.connections[name] = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "db_type": db_type,
            "ssh_tunnel": ssh_tunnel,
        }

    def connect(self, name):
        conn_details = self.connections[name]
        conn_str = f"DRIVER={{Oracle}};SERVER={conn_details['host']};PORT={conn_details['port']};UID={conn_details['user']};PWD={conn_details['password']}"
        return pyodbc.connect(conn_str)
