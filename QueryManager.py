from typing import Dict, Any, List, Tuple


class Queries:
    """
    Centralized Oracle SQL dictionary queries.
    All queries here reflect how Oracle *actually* stores source code.
    """

    # ------------------------------------------------------------------
    # TABLES / BASIC OBJECTS
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # PROCEDURES / FUNCTIONS (STANDALONE)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # PACKAGES
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # PACKAGE SOURCE EXTRACTION (IMPORTANT)
    # ------------------------------------------------------------------

    @staticmethod
    def extract_packaged_routine(
        source_lines: List[Tuple[int, str]],
        routine_name: str
    ) -> str:
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

    # ------------------------------------------------------------------
    # VIEWS
    # ------------------------------------------------------------------

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
