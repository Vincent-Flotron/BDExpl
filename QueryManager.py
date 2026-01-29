from typing import Dict, Any, List, Tuple
from abc import ABC, abstractmethod

# ======================================================================
# QUERY INTERFACE
# ======================================================================

class Queries(ABC):
    """Abstract base class for database queries"""

    @abstractmethod
    def get_first_x_rows(self, schema, table, limit):
        pass

    @abstractmethod
    def get_all_schemas_with_their_table_count(self):
        pass

    @abstractmethod
    def get_all_table_names_in_schema(self, schema):
        pass

    @abstractmethod
    def get_table_primary_keys(self, schema, table):
        pass

    @abstractmethod
    def get_table_foreign_keys(self, schema, table):
        pass

    @abstractmethod
    def get_table_structure(self, schema, table):
        pass

    @abstractmethod
    def get_table_indexes(self, schema, table):
        pass

    @abstractmethod
    def count_table_indexes(self, schema, table):
        pass

    @abstractmethod
    def count_table_prim_and_foreign_keys(self, schema, table):
        pass

    @abstractmethod
    def get_table_triggers(self, schema, table):
        pass

    @abstractmethod
    def get_all_procedures_in_schema(self, schema):
        pass

    @abstractmethod
    def get_all_functions_in_schema(self, schema):
        pass

    @abstractmethod
    def count_procedures_in_schema(self, schema):
        pass

    @abstractmethod
    def count_functions_in_schema(self, schema):
        pass

    @abstractmethod
    def get_procedure_body(self, schema, procedure_name):
        pass

    @abstractmethod
    def get_function_body(self, schema, function_name):
        pass

    @abstractmethod
    def get_all_packages_in_schema(self, schema):
        pass

    @abstractmethod
    def count_packages_in_schema(self, schema):
        pass

    @abstractmethod
    def get_package_spec(self, schema, package_name):
        pass

    @abstractmethod
    def get_package_body(self, schema, package_name):
        pass

    @abstractmethod
    def get_package_functions_and_procedures(self, schema, package_name):
        pass

    @abstractmethod
    def extract_packaged_routine(self, source_lines, routine_name):
        pass

    @abstractmethod
    def get_all_views_in_schema(self, schema):
        pass

    @abstractmethod
    def count_views_in_schema(self, schema):
        pass

    @abstractmethod
    def get_view_body(self, schema, view_name):
        pass

    @abstractmethod
    def get_view_query(self, schema, view_name):
        pass

    @abstractmethod
    def get_view_structure(self, schema, view_name):
        pass

    @abstractmethod
    def get_view_dependencies(self, schema, view_name):
        pass

    @abstractmethod
    def get_view_comment(self, schema, view_name):
        pass

# ======================================================================
# ORACLE QUERIES
# ======================================================================

class QueriesOracle(Queries):
    """Oracle-specific SQL queries"""

    @staticmethod
    def get_first_x_rows(schema, table, limit):
        return f"SELECT * FROM {schema}.{table} WHERE ROWNUM <= {limit}"

    @staticmethod
    def get_all_schemas_with_their_table_count():
        return """
            SELECT owner, COUNT(*) AS table_count
            FROM all_tables
            WHERE owner NOT IN ('SYS', 'SYSTEM', 'OUTLN', 'DBSNMP')
            GROUP BY owner
            ORDER BY owner
        """

    @staticmethod
    def get_all_table_names_in_schema(schema):
        return f"""
            SELECT table_name
            FROM all_tables
            WHERE owner = '{schema}'
            ORDER BY table_name
        """

    @staticmethod
    def get_table_primary_keys(schema, table):
        return f"""
                SELECT
                    cols.column_name,
                    cons.constraint_type
                FROM all_constraints cons
                JOIN all_cons_columns cols
                    ON cons.constraint_name = cols.constraint_name
                    AND cons.owner = cols.owner
                WHERE cons.owner = '{schema}'
                    AND cons.table_name = '{table}'
                    AND cons.constraint_type = 'P'
                ORDER BY cols.position
            """

    @staticmethod
    def get_table_foreign_keys(schema, table):
        return f"""
                SELECT
                    cols.column_name,
                    cons.constraint_type,
                    cons.r_owner,
                    cons.r_constraint_name,
                    cons_pk.table_name AS referenced_table
                FROM all_constraints cons
                JOIN all_cons_columns cols
                    ON cons.constraint_name = cols.constraint_name
                    AND cons.owner = cols.owner
                JOIN all_constraints cons_pk
                    ON cons.r_constraint_name = cons_pk.constraint_name
                    AND cons.r_owner = cons_pk.owner
                WHERE cons.owner = '{schema}'
                    AND cons.table_name = '{table}'
                    AND cons.constraint_type = 'R'
                ORDER BY cols.position
            """

    @staticmethod
    def get_table_structure(schema, table):
        return f"""
                SELECT
                    column_name AS fieldname,
                    data_type AS type,
                    data_length,
                    data_precision,
                    data_scale,
                    nullable
                FROM all_tab_columns
                WHERE owner = '{schema}' AND table_name = '{table}'
                ORDER BY column_id
            """

    @staticmethod
    def get_table_indexes(schema, table):
        return f"""
                SELECT
                    i.index_name,
                    i.index_type,
                    i.uniqueness,
                    COUNT(ic.column_name) AS column_count,
                    LISTAGG(ic.column_name, ', ')
                        WITHIN GROUP (ORDER BY ic.column_position) AS columns
                FROM all_indexes i
                JOIN all_ind_columns ic
                    ON i.owner = ic.index_owner
                AND i.index_name = ic.index_name
                WHERE i.owner = '{schema}'
                AND i.table_name = '{table}'
                GROUP BY
                    i.index_name,
                    i.index_type,
                    i.uniqueness
                ORDER BY i.index_name
            """

    @staticmethod
    def count_table_indexes(schema, table):
        return f"""
            SELECT COUNT(DISTINCT index_name)
            FROM all_ind_columns
            WHERE table_owner = '{schema}' AND table_name = '{table}'
        """

    @staticmethod
    def count_table_prim_and_foreign_keys(schema, table):
        return f"""
                SELECT COUNT(*)
                FROM all_constraints
                WHERE owner = '{schema}'
                    AND table_name = '{table}'
                    AND constraint_type IN ('P', 'R')
            """

    @staticmethod
    def get_table_triggers(schema, table):
        return f"""
                SELECT trigger_name
                FROM all_triggers
                WHERE owner = '{schema}' AND table_name = '{table}'
                ORDER BY trigger_name
            """

    @staticmethod
    def get_all_procedures_in_schema(schema):
        return f"""
            SELECT object_name
            FROM all_objects
            WHERE owner = '{schema}'
              AND object_type = 'PROCEDURE'
            ORDER BY object_name
        """

    @staticmethod
    def get_all_functions_in_schema(schema):
        return f"""
            SELECT object_name
            FROM all_objects
            WHERE owner = '{schema}'
              AND object_type = 'FUNCTION'
            ORDER BY object_name
        """

    @staticmethod
    def count_procedures_in_schema(schema):
        return f"""
            SELECT COUNT(*)
            FROM all_objects
            WHERE owner = '{schema}'
              AND object_type = 'PROCEDURE'
        """

    @staticmethod
    def count_functions_in_schema(schema):
        return f"""
            SELECT COUNT(*)
            FROM all_objects
            WHERE owner = '{schema}'
              AND object_type = 'FUNCTION'
        """

    @staticmethod
    def get_procedure_body(schema, procedure_name):
        return f"""
            SELECT line, text
            FROM all_source
            WHERE owner = '{schema}'
              AND name = '{procedure_name}'
              AND type = 'PROCEDURE'
            ORDER BY line
        """

    @staticmethod
    def get_function_body(schema, function_name):
        return f"""
            SELECT line, text
            FROM all_source
            WHERE owner = '{schema}'
              AND name = '{function_name}'
              AND type = 'FUNCTION'
            ORDER BY line
        """

    @staticmethod
    def get_all_packages_in_schema(schema):
        return f"""
            SELECT object_name
            FROM all_objects
            WHERE owner = '{schema}'
              AND object_type = 'PACKAGE'
            ORDER BY object_name
        """

    @staticmethod
    def count_packages_in_schema(schema):
        return f"""
            SELECT COUNT(*)
            FROM all_objects
            WHERE owner = '{schema}'
              AND object_type = 'PACKAGE'
        """

    @staticmethod
    def get_package_spec(schema, package_name):
        """
        Package specification (declarations only)
        """
        return f"""
            SELECT line, text
            FROM all_source
            WHERE owner = '{schema}'
              AND name = '{package_name}'
              AND type = 'PACKAGE'
            ORDER BY line
        """

    @staticmethod
    def get_package_body(schema, package_name):
        """
        Package body (actual implementation)
        """
        return f"""
            SELECT line, text
            FROM all_source
            WHERE owner = '{schema}'
              AND name = '{package_name}'
              AND type = 'PACKAGE BODY'
            ORDER BY line
        """

    @staticmethod
    def get_package_functions_and_procedures(schema, package_name):
        """
        Lists procedures/functions inside a package.
        Overload info comes from ALL_PROCEDURES.
        """
        return f"""
            SELECT procedure_name, object_type, overload
            FROM all_procedures
            WHERE owner = '{schema}'
              AND object_name = '{package_name}'
              AND procedure_name IS NOT NULL
            ORDER BY procedure_name, overload
        """

    @staticmethod
    def extract_packaged_routine(source_lines, routine_name):
        """
        Extracts a single FUNCTION or PROCEDURE body from a PACKAGE BODY.
        Oracle does NOT store this separately.
        This is how SQL Developer does it internally.
        """
        routine_name = routine_name.upper()
        inside = False
        buffer = []

        for _, line in source_lines:
            upper = line.upper()

            if (
                f"PROCEDURE {routine_name}" in upper
                or f"FUNCTION {routine_name}" in upper
            ):
                inside = True

            if inside:
                buffer.append(line)
                if f"END {routine_name}" in upper:
                    break

        return "".join(buffer)

    @staticmethod
    def get_all_views_in_schema(schema):
        return f"""
            SELECT object_name
            FROM all_objects
            WHERE owner = '{schema}'
              AND object_type = 'VIEW'
            ORDER BY object_name
        """

    @staticmethod
    def count_views_in_schema(schema):
        return f"""
            SELECT COUNT(*)
            FROM all_objects
            WHERE owner = '{schema}'
              AND object_type = 'VIEW'
        """

    @staticmethod
    def get_view_body(schema, view_name):
        return f"""
            SELECT text
            FROM all_source
            WHERE owner = '{schema}'
              AND name = '{view_name}'
              AND type = 'VIEW'
            ORDER BY line
        """

    @staticmethod
    def get_view_query(schema, view_name):
        return f"""
            SELECT text
            FROM all_views
            WHERE owner = '{schema}'
              AND view_name = '{view_name}'
        """

    @staticmethod
    def get_view_structure(schema, view_name):
        return f"""
                SELECT
                    column_name,
                    data_type,
                    data_length,
                    data_precision,
                    data_scale,
                    nullable
                FROM all_tab_columns
                WHERE owner = '{schema}'
                    AND table_name = '{view_name}'
                ORDER BY column_id
            """

    @staticmethod
    def get_view_dependencies(schema, view_name):
        return f"""
                SELECT
                    referenced_owner AS schema_name,
                    referenced_name AS table_name,
                    referenced_type
                FROM all_dependencies
                WHERE owner = '{schema}'
                    AND name = '{view_name}'
                    AND referenced_type IN ('TABLE', 'VIEW')
                ORDER BY referenced_name
                """

    @staticmethod
    def get_view_comment(schema, view_name):
        return f"""
                SELECT comments
                FROM all_tab_comments
                WHERE owner = '{schema}'
                    AND table_name = '{view_name}'
                    AND comments IS NOT NULL
                """

# ======================================================================
# SQLITE QUERIES
# ======================================================================

class QueriesSQLite(Queries):
    """SQLite-specific SQL queries"""

    @staticmethod
    def get_first_x_rows(schema, table, limit):
        # SQLite doesn't have schemas, so we ignore the schema parameter
        return f"SELECT * FROM {table} LIMIT {limit}"

    @staticmethod
    def get_all_schemas_with_their_table_count():
        # SQLite doesn't have schemas, so we return a single entry
        return """
            SELECT 'main' AS name, COUNT(*) AS table_count
            FROM sqlite_master
            WHERE type='table'
        """

    @staticmethod
    def get_all_table_names_in_schema(schema):
        # SQLite doesn't have schemas, so we ignore the schema parameter
        return """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """

    @staticmethod
    def get_table_primary_keys(schema, table):
        return f"""
            SELECT
                m.name AS column_name,
                'P' AS constraint_type
            FROM pragma_table_info('{table}') m
            JOIN pragma_table_info('{table}') pk
                ON m.pk = 1
            WHERE m.pk = 1
            ORDER BY m.cid
        """

    @staticmethod
    def get_table_foreign_keys(schema, table):
        return f"""
            SELECT
                f.from AS column_name,
                'R' AS constraint_type,
                NULL AS r_owner,
                f.id AS r_constraint_name,
                f.table AS referenced_table
            FROM pragma_foreign_keys('{table}') f
            ORDER BY f.id
        """

    @staticmethod
    def get_table_structure(schema, table):
        return f"""
            SELECT
                name AS fieldname,
                type AS type,
                NULL AS data_length,
                NULL AS data_precision,
                NULL AS data_scale,
                CASE WHEN notnull = 1 THEN 'N' ELSE 'Y' END AS nullable
            FROM pragma_table_info('{table}')
            ORDER BY cid
        """

    @staticmethod
    def get_table_indexes(schema, table):
        return f"""
            SELECT
                name AS index_name,
                CASE WHEN unique = 1 THEN 'UNIQUE' ELSE 'NORMAL' END AS index_type,
                CASE WHEN unique = 1 THEN 'UNIQUE' ELSE 'NONUNIQUE' END AS uniqueness,
                COUNT(*) AS column_count,
                GROUP_CONCAT(name) AS columns
            FROM pragma_index_list('{table}')
            JOIN pragma_index_info(name) ON seqno >= 0
            GROUP BY name
            ORDER BY name
        """

    @staticmethod
    def count_table_indexes(schema, table):
        return f"""
            SELECT COUNT(*)
            FROM pragma_index_list('{table}')
        """

    @staticmethod
    def count_table_prim_and_foreign_keys(schema, table):
        return f"""
            SELECT
                (SELECT COUNT(*) FROM pragma_table_info('{table}') WHERE pk = 1) +
                (SELECT COUNT(*) FROM pragma_foreign_keys('{table}'))
        """

    @staticmethod
    def get_table_triggers(schema, table):
        return f"""
            SELECT name
            FROM sqlite_master
            WHERE type='trigger' AND tbl_name='{table}'
            ORDER BY name
        """

    @staticmethod
    def get_all_procedures_in_schema(schema):
        # Example implementation for SQLite
        # This is a placeholder implementation; actual implementation may vary
        query = f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '{schema}%'"
        return query

    @staticmethod
    def get_all_functions_in_schema(schema):
        # SQLite doesn't have functions in the same way as Oracle
        return "SELECT NULL AS object_name WHERE 0=1"

    @staticmethod
    def count_procedures_in_schema(schema):
        # Example implementation for SQLite
        # This is a placeholder implementation; actual implementation may vary
        query = f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE '{schema}%'"
        return query

    @staticmethod
    def count_functions_in_schema(schema):
        # SQLite doesn't have functions in the same way as Oracle
        return "SELECT 0"

    @staticmethod
    def get_procedure_body(schema, procedure_name):
        # SQLite doesn't have stored procedures
        return "SELECT NULL AS line, NULL AS text WHERE 0=1"

    @staticmethod
    def get_function_body(schema, function_name):
        # SQLite doesn't have functions in the same way as Oracle
        return "SELECT NULL AS line, NULL AS text WHERE 0=1"

    @staticmethod
    def get_all_packages_in_schema(schema):
        # SQLite doesn't have packages
        return "SELECT NULL AS object_name WHERE 0=1"

    @staticmethod
    def count_packages_in_schema(schema):
        # SQLite doesn't have packages
        return "SELECT 0"

    @staticmethod
    def get_package_spec(schema, package_name):
        # SQLite doesn't have packages
        return "SELECT NULL AS line, NULL AS text WHERE 0=1"

    @staticmethod
    def get_package_body(schema, package_name):
        # SQLite doesn't have packages
        return "SELECT NULL AS line, NULL AS text WHERE 0=1"

    @staticmethod
    def get_package_functions_and_procedures(schema, package_name):
        # SQLite doesn't have packages
        return "SELECT NULL AS procedure_name, NULL AS object_type, NULL AS overload WHERE 0=1"

    @staticmethod
    def extract_packaged_routine(source_lines, routine_name):
        # SQLite doesn't have packages, so this is not applicable
        return ""

    @staticmethod
    def get_all_views_in_schema(schema):
        return """
            SELECT name
            FROM sqlite_master
            WHERE type='view'
            ORDER BY name
        """

    @staticmethod
    def count_views_in_schema(schema):
        return """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type='view'
        """

    @staticmethod
    def get_view_body(schema, view_name):
        return f"""
            SELECT sql AS text
            FROM sqlite_master
            WHERE type='view' AND name='{view_name}'
        """

    @staticmethod
    def get_view_query(schema, view_name):
        return f"""
            SELECT sql AS text
            FROM sqlite_master
            WHERE type='view' AND name='{view_name}'
        """

    @staticmethod
    def get_view_structure(schema, view_name):
        return f"""
            SELECT
                name AS column_name,
                type AS data_type,
                NULL AS data_length,
                NULL AS data_precision,
                NULL AS data_scale,
                CASE WHEN notnull = 1 THEN 'N' ELSE 'Y' END AS nullable
            FROM pragma_table_info('{view_name}')
            ORDER BY cid
        """

    @staticmethod
    def get_view_dependencies(schema, view_name):
        return f"""
            SELECT
                NULL AS schema_name,
                tbl_name AS table_name,
                'TABLE' AS referenced_type
            FROM sqlite_master
            WHERE type='table' AND sql LIKE '%{view_name}%'
            UNION ALL
            SELECT
                NULL AS schema_name,
                name AS table_name,
                'VIEW' AS referenced_type
            FROM sqlite_master
            WHERE type='view' AND name != '{view_name}' AND sql LIKE '%{view_name}%'
            ORDER BY table_name
        """

    @staticmethod
    def get_view_comment(schema, view_name):
        # SQLite doesn't have view comments in the same way as Oracle
        return "SELECT NULL AS comments WHERE 0=1"

       

# ======================================================================
# QUERY MANAGER
# ======================================================================

class QueryManager:
    """
    Executes SQL and dispatches results to the UI.
    """

    def __init__(self, db_connection, query_result_panel):
        self.db_connection = db_connection
        self.query_result_panel = query_result_panel

    def execute_query(self, sql: str) -> Dict[str, Any]:
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(sql)

            if cursor.description:
                columns = [d[0] for d in cursor.description]
                rows = cursor.fetchall()
                return {
                    "success": True,
                    "columns": columns,
                    "rows": rows,
                    "description": cursor.description,
                    "rowcount": len(rows),
                }
            else:
                self.db_connection.current_connection.commit()
                return {
                    "success": True,
                    "message": f"Query executed successfully ({cursor.rowcount} row(s))",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_query(self, sql: str):
        result = self.execute_query(sql)

        if result["success"]:
            if "columns" in result:
                self.query_result_panel.display_results(
                    result["columns"],
                    result["rows"],
                    result["description"],
                )
            else:
                self.query_result_panel.display_message(result["message"])
        else:
            self.query_result_panel.display_error(result["error"])
