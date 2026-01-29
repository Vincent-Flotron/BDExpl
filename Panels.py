import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from decimal import Decimal
import datetime
from SQLText import SQLText
from typing import List, Tuple
import csv
import os
from QueryManager import QueryManager, Queries
import re

def create_treeview_with_scrollbars(container, columns=None, show='tree'):
    """Helper: Create a treeview with scrollbars."""
    tree_scroll_y = ttk.Scrollbar(container, style='TScrollbar')
    tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    tree_scroll_x = ttk.Scrollbar(container, orient=tk.HORIZONTAL, style='TScrollbar')
    tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    tree = ttk.Treeview(
        container,
        yscrollcommand=tree_scroll_y.set,
        xscrollcommand=tree_scroll_x.set,
        style='Treeview'
    )
    if columns:
        tree['columns'] = columns
        tree['show'] = show
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tree_scroll_y.config(command=tree.yview)
    tree_scroll_x.config(command=tree.xview)

    return tree

def create_context_menu(widget, commands):
    """Helper: Create a context menu for a widget."""
    menu = tk.Menu(widget, tearoff=0)
    for label, command in commands:
        menu.add_command(label=label, command=command)
    return menu

class DatabaseTreePanel:
    def __init__(self, parent, db_connection, sql_query_editor_panel):
        self.parent = parent
        self.db_connection = db_connection
        self.sql_query_editor_panel = sql_query_editor_panel

    def setup(self):
        """Panel 1: Database object tree"""
        left_frame = ttk.Frame(self.parent, style='TFrame')
        self.parent.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Database Objects", style='Bold.TLabel').pack(pady=5)

        # Treeview with scrollbars
        tree_container = ttk.Frame(left_frame, style='TFrame')
        tree_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.db_tree = create_treeview_with_scrollbars(tree_container)

        # Context menu for tables
        table_commands = [
            ("View first 100 rows", lambda: self.view_table_data(100)),
            ("View first 1000 rows", lambda: self.view_table_data(1000)),
            ("View Structure", lambda: self.sql_query_editor_panel.show_table_structure(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("View Indexes", lambda: self.sql_query_editor_panel.show_table_indexes(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("View Keys", lambda: self.sql_query_editor_panel.show_table_keys(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            ))
        ]
        self.table_context_menu = create_context_menu(self.db_tree, table_commands)

        # Context menu for views
        view_commands = [
            ("View first 100 rows", lambda: self.view_view_data(100)),
            ("View first 1000 rows", lambda: self.view_view_data(1000)),
            ("View Structure", lambda: self.show_view_structure(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("View Query", lambda: self.view_view_query(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("View Dependencies", lambda: self.show_view_dependencies(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("View Comment", lambda: self.show_view_comment(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            ))
        ]
        self.view_context_menu = create_context_menu(self.db_tree, view_commands)

        self.db_tree.bind("<Button-3>", self.show_tree_context_menu)
        self.db_tree.bind("<Double-1>", lambda e: self.view_table_data(100))
        self.db_tree.bind("<<TreeviewOpen>>", self.on_tree_expand)


    def on_tree_expand(self, event):
        """Handle tree expansion - lazy load table children (indexes, keys, triggers), schema children (procedures, functions, packages, views), and package children (functions, procedures)"""
        item = self.db_tree.focus()
        if not item:
            return

        values = self.db_tree.item(item)['values']
        if not values or len(values) < 2:
            return

        if values[1] == 'table':
            children = self.db_tree.get_children(item)
            if children and self.db_tree.item(children[0])['values'][1] == 'loading':
                self.db_tree.delete(*children)
                self.load_table_children(item, values[0], values[2])
        elif values[1] == 'schema': # case strored procedure and functions
            children = self.db_tree.get_children(item)
            if children and self.db_tree.item(children[1])['values'][1] == 'loading':
                self.db_tree.delete(children[1])
                self.load_schema_children(item, values[0])
        elif values[1] == 'package':
            children = self.db_tree.get_children(item)
            if children and self.db_tree.item(children[0])['values'][1] == 'loading':
                self.db_tree.delete(*children)
                self.load_package_children(item, values[0], values[2])

    # Modifiez la méthode view_table_data pour gérer les vues
    def view_table_data(self, limit: int):
        """View first N rows of selected table or view - creates new tab with query"""
        selected = self.db_tree.selection()
        if not selected:
            return

        values = self.db_tree.item(selected[0])['values']
        if len(values) >= 3 and (values[1] == 'table' or values[1] == 'view'):
            schema = values[0]
            table_or_view = values[2]
            sql = Queries.get_first_x_rows(schema, table_or_view, limit)

            tab_id = self.sql_query_editor_panel.new_sql_tab()
            self.sql_query_editor_panel.set_text_without_undo(
                self.sql_query_editor_panel.sql_files[tab_id]["widget"],
                sql
            )
            self.sql_query_editor_panel.sql_files[tab_id]["modified"] = False

            tab_name = f"{table_or_view} ({limit} rows)"
            self.sql_query_editor_panel.sql_notebook.tab(
                self.sql_query_editor_panel.sql_files[tab_id]["frame"],
                text=tab_name
            )
            self.sql_query_editor_panel.run_query(sql)

    def load_table_children(self, table_node, schema, table):
        """Load indexes, keys, and triggers for a table"""
        try:
            cursor = self.db_connection.current_connection.cursor()

            cursor.execute(Queries.count_table_indexes(schema, table))
            index_count = cursor.fetchone()[0]
            if index_count > 0:
                self.db_tree.insert(
                    table_node, 'end',
                    text=f'Indexes ({index_count})',
                    values=(schema, 'indexes_summary', table)
                )

            cursor.execute(Queries.count_table_prim_and_foreign_keys(schema, table))
            key_count = cursor.fetchone()[0]
            if key_count > 0:
                self.db_tree.insert(
                    table_node, 'end',
                    text=f'Keys ({key_count})',
                    values=(schema, 'keys_summary', table)
                )

            cursor.execute(Queries.get_table_triggers(schema, table))
            triggers = cursor.fetchall()
            if triggers:
                triggers_node = self.db_tree.insert(
                    table_node, 'end',
                    text=f'Triggers ({len(triggers)})',
                    values=(schema, 'triggers_folder')
                )
                for (trigger_name,) in triggers:
                    self.db_tree.insert(
                        triggers_node, 'end',
                        text=trigger_name,
                        values=(schema, 'trigger', trigger_name)
                    )

            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load table children: {str(e)}")


    def load_schema_children(self, schema_node, schema):
        """Load stored procedures, functions, packages, and views for a schema"""
        try:
            cursor = self.db_connection.current_connection.cursor()

            # Load procedures
            cursor.execute(Queries.count_procedures_in_schema(schema))
            procedure_count = cursor.fetchone()[0]
            if procedure_count > 0:
                procedures_node = self.db_tree.insert(
                    schema_node, 'end',
                    text=f'Procedures ({procedure_count})',
                    values=(schema, 'procedures_folder')
                )

                cursor.execute(Queries.get_all_procedures_in_schema(schema))
                procedures = cursor.fetchall()
                for (procedure_name,) in procedures:
                    self.db_tree.insert(
                        procedures_node, 'end',
                        text=procedure_name,
                        values=(schema, 'procedure', procedure_name)
                    )

            # Load functions
            cursor.execute(Queries.count_functions_in_schema(schema))
            function_count = cursor.fetchone()[0]
            if function_count > 0:
                functions_node = self.db_tree.insert(
                    schema_node, 'end',
                    text=f'Functions ({function_count})',
                    values=(schema, 'functions_folder')
                )

                cursor.execute(Queries.get_all_functions_in_schema(schema))
                functions = cursor.fetchall()
                for (function_name,) in functions:
                    self.db_tree.insert(
                        functions_node, 'end',
                        text=function_name,
                        values=(schema, 'function', function_name)
                    )

            # Load packages
            cursor.execute(Queries.count_packages_in_schema(schema))
            package_count = cursor.fetchone()[0]
            if package_count > 0:
                packages_node = self.db_tree.insert(
                    schema_node, 'end',
                    text=f'Packages ({package_count})',
                    values=(schema, 'packages_folder')
                )

                cursor.execute(Queries.get_all_packages_in_schema(schema))
                packages = cursor.fetchall()
                for (package_name,) in packages:
                    package_node = self.db_tree.insert(
                        packages_node, 'end',
                        text=package_name,
                        values=(schema, 'package', package_name)
                    )
                    # Add loading placeholder for package children
                    self.db_tree.insert(package_node, 'end', text='Loading...', values=(schema, 'loading'))

            # Load views
            cursor.execute(Queries.count_views_in_schema(schema))
            view_count = cursor.fetchone()[0]
            if view_count > 0:
                views_node = self.db_tree.insert(
                    schema_node, 'end',
                    text=f'Views ({view_count})',
                    values=(schema, 'views_folder')
                )

                cursor.execute(Queries.get_all_views_in_schema(schema))
                views = cursor.fetchall()
                for (view_name,) in views:
                    self.db_tree.insert(
                        views_node, 'end',
                        text=view_name,
                        values=(schema, 'view', view_name)
                    )

            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load schema children: {str(e)}")


    def show_view_dependencies(self, schema: str, view: str):
        """Fetch and display view dependencies in a new tab."""
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(Queries.get_view_dependencies(schema, view))
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            if not rows:
                messagebox.showinfo("Info", f"No dependencies found for view {view}.")
                return

            tree = self.sql_query_editor_panel._create_result_tab(f"{view} (Dependencies)", columns, rows)

            context_menu = self.sql_query_editor_panel._create_context_menu(
                tree,
                lambda: self.sql_query_editor_panel._copy_selected_rows(tree),
                lambda: self.sql_query_editor_panel._export_to_csv(tree, f"{view}_dependencies")
            )
            tree.bind("<Button-3>", lambda event: context_menu.post(event.x_root, event.y_root))

            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load view dependencies: {str(e)}")

    def view_view_content(self, schema: str, view_name: str):
        """View content of selected view in Query Editor"""
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(Queries.get_view_body(schema, view_name))
            result = cursor.fetchall()
            cursor.close()

            if result:
                # Combine all lines of the view
                view_body = '\n'.join([row[0] for row in result])

                tab_id = self.sql_query_editor_panel.new_sql_tab()
                self.sql_query_editor_panel.set_text_without_undo(
                    self.sql_query_editor_panel.sql_files[tab_id]["widget"],
                    view_body
                )
                self.sql_query_editor_panel.sql_files[tab_id]["modified"] = False
                tab_name = f"{view_name} (View)"
                self.sql_query_editor_panel.sql_notebook.tab(
                    self.sql_query_editor_panel.sql_files[tab_id]["frame"],
                    text=tab_name
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load view content: {str(e)}")


    def show_view_structure(self, schema: str, view: str):
        """Fetch and display view structure in a new tab."""
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(Queries.get_view_structure(schema, view))
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            tree = self.sql_query_editor_panel._create_result_tab(f"{view} (Structure)", columns, rows)

            context_menu = self.sql_query_editor_panel._create_context_menu(
                tree,
                lambda: self.sql_query_editor_panel._copy_selected_rows(tree),
                lambda: self.sql_query_editor_panel._export_to_csv(tree, f"{view}_structure")
            )
            tree.bind("<Button-3>", lambda event: context_menu.post(event.x_root, event.y_root))

            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load view structure: {str(e)}")

    def show_tree_context_menu(self, event):
        item = self.db_tree.identify_row(event.y)
        if not item:
            return

        self.db_tree.selection_set(item)
        values = self.db_tree.item(item)['values']

        if not values:
            return

        obj_type = values[1]

        try:
            # -------------------------------
            # TABLES & VIEWS
            # -------------------------------
            if obj_type == 'table':
                self.table_context_menu.post(event.x_root, event.y_root)

            elif obj_type == 'view':
                self.view_context_menu.post(event.x_root, event.y_root)

            # -------------------------------
            # STANDALONE OBJECTS
            # -------------------------------
            elif obj_type == 'procedure':
                self.view_procedure_content(values[0], values[2])

            elif obj_type == 'function':
                self.view_function_content(values[0], values[2])

            elif obj_type == 'trigger':
                self.view_trigger_content(values[0], values[2])

            # -------------------------------
            # PACKAGES
            # -------------------------------
            elif obj_type == 'package':
                # Right-click on package → show full body
                self.view_package_content(values[0], values[2])

            elif obj_type in ('package_procedure', 'package_function'):
                schema = values[0]
                package_name = self.db_tree.item(self.db_tree.parent(item))['text']
                package_name = package_name.split(' (')[0]  # clean label

                routine_name = values[2]
                overload = values[3] if len(values) > 3 else None

                self.view_package_function_or_procedure_content(
                    schema,
                    package_name,
                    routine_name,
                    overload
                )

        except Exception as e:
            messagebox.showerror("Error", str(e))



    def show_view_comment(self, schema: str, view: str):
        """Fetch and display view comment in a new tab."""
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(Queries.get_view_comment(schema, view))
            result = cursor.fetchone()
            cursor.close()

            if result and result[0]:
                comment = result[0]
                tab_id = self.sql_query_editor_panel.new_sql_tab()
                self.sql_query_editor_panel.set_text_without_undo(
                    self.sql_query_editor_panel.sql_files[tab_id]["widget"],
                    comment
                )
                self.sql_query_editor_panel.sql_files[tab_id]["modified"] = False
                tab_name = f"{view} (Comment)"
                self.sql_query_editor_panel.sql_notebook.tab(
                    self.sql_query_editor_panel.sql_files[tab_id]["frame"],
                    text=tab_name
                )
            else:
                messagebox.showinfo("Info", f"No comment found for view {view}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load view comment: {str(e)}")

    def view_view_query(self, schema: str, view: str):
        """View the SQL query of selected view in Query Editor"""
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(Queries.get_view_query(schema, view))
            result = cursor.fetchall()
            cursor.close()

            if result:
                # Combine all lines of the view query
                view_query = '\n'.join([row[0] for row in result])

                tab_id = self.sql_query_editor_panel.new_sql_tab()
                self.sql_query_editor_panel.set_text_without_undo(
                    self.sql_query_editor_panel.sql_files[tab_id]["widget"],
                    view_query
                )
                self.sql_query_editor_panel.sql_files[tab_id]["modified"] = False
                tab_name = f"{view} (Query)"
                self.sql_query_editor_panel.sql_notebook.tab(
                    self.sql_query_editor_panel.sql_files[tab_id]["frame"],
                    text=tab_name
                )
            else:
                messagebox.showinfo("Info", f"No query found for view {view}.")
        except Exception as e:
            # Passer l'erreur brute au panneau de résultats
            self.sql_query_editor_panel.display_message(str(e))

    def load_package_children(self, package_node, schema, package_name):
        """Load functions and procedures within a package"""
        try:
            cursor = self.db_connection.current_connection.cursor()

            cursor.execute(Queries.get_package_functions_and_procedures(schema, package_name))
            procedures = cursor.fetchall()
            
            if procedures:
                # Group by procedure name to handle overloads
                procedure_groups = {}
                for (procedure_name, object_type, overload) in procedures:
                    if procedure_name not in procedure_groups:
                        procedure_groups[procedure_name] = []
                    procedure_groups[procedure_name].append((procedure_name, object_type, overload))
                
                for procedure_name, procedure_list in procedure_groups.items():
                    if len(procedure_list) == 1:
                        # Single procedure/function
                        proc_name, proc_type, overload = procedure_list[0]
                        display_text = f"{proc_name} ({proc_type})"
                        self.db_tree.insert(
                            package_node, 'end',
                            text=display_text,
                            values=(schema, f'package_{proc_type.lower()}', proc_name)
                        )
                    else:
                        # Multiple overloads
                        for proc_name, proc_type, overload in procedure_list:
                            display_text = f"{proc_name} ({proc_type}) - Overload {overload}"
                            self.db_tree.insert(
                                package_node, 'end',
                                text=display_text,
                                values=(schema, f'package_{proc_type.lower()}', proc_name, overload)
                            )

            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load package children: {str(e)}")

    def load_database_objects(self):
        """Load Oracle database objects into tree with basic queries"""
        if not self.db_connection.current_connection:
            return

        self.db_tree.delete(*self.db_tree.get_children())

        try:
            cursor = self.db_connection.current_connection.cursor()

            cursor.execute(Queries.get_all_schemas_with_their_table_count())
            schemas = cursor.fetchall()

            for schema, table_count in schemas:
                schema_node = self.db_tree.insert('', 'end', text=f"{schema} ({table_count} tables)", values=(schema, 'schema'))

                # Insert tables folder first
                tables_node = self.db_tree.insert(schema_node, 'end', text=f'Tables ({table_count})', values=(schema, 'tables_folder'))

                # Add loading placeholder for schema children (procedures, functions, and packages) after tables
                loading_placeholder = self.db_tree.insert(schema_node, 'end', text='Loading...', values=(schema, 'loading'))

                cursor.execute(Queries.get_all_table_names_in_schema(schema))
                table_results = cursor.fetchall()
                for (table,) in table_results:
                    table_node = self.db_tree.insert(tables_node, 'end', text=table, values=(schema, 'table', table))
                    self.db_tree.insert(table_node, 'end', text='Loading...', values=(schema, 'loading'))

                try:
                    cursor.execute(Queries.get_current_session_roles())
                    roles = cursor.fetchall()
                    roles_node = self.db_tree.insert(schema_node, 'end', text=f'Roles ({len(roles)})', values=(schema, 'roles_folder'))
                    for (role,) in roles:
                        self.db_tree.insert(roles_node, 'end', text=role, values=(schema, 'role', role))
                except:
                    roles_node = self.db_tree.insert(schema_node, 'end', text='Roles (0)', values=(schema, 'roles_folder'))

                try:
                    cursor.execute(Queries.get_current_session_privileges())
                    privileges = cursor.fetchall()
                    privs_node = self.db_tree.insert(schema_node, 'end', text=f'Privileges ({len(privileges)})', values=(schema, 'privileges_folder'))
                    for (privilege,) in privileges:
                        self.db_tree.insert(privs_node, 'end', text=privilege, values=(schema, 'privilege', privilege))
                except:
                    privs_node = self.db_tree.insert(schema_node, 'end', text='Privileges (0)', values=(schema, 'privileges_folder'))

            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load database objects: {str(e)}")

    def view_view_data(self, limit: int):
        """View first N rows of selected view - creates new tab with query"""
        selected = self.db_tree.selection()
        if not selected:
            return

        values = self.db_tree.item(selected[0])['values']
        if len(values) >= 3 and values[1] == 'view':
            schema = values[0]
            view = values[2]
            sql = Queries.get_first_x_rows(schema, view, limit)

            tab_id = self.sql_query_editor_panel.new_sql_tab()
            self.sql_query_editor_panel.set_text_without_undo(
                self.sql_query_editor_panel.sql_files[tab_id]["widget"],
                sql
            )
            self.sql_query_editor_panel.sql_files[tab_id]["modified"] = False

            tab_name = f"{view} ({limit} rows)"
            self.sql_query_editor_panel.sql_notebook.tab(
                self.sql_query_editor_panel.sql_files[tab_id]["frame"],
                text=tab_name
            )
            self.sql_query_editor_panel.run_query(sql)

    def view_trigger_content(self, schema: str, trigger_name: str):
        """View content of selected trigger in Query Editor"""
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(Queries.get_trigger_body(schema, trigger_name))
            result = cursor.fetchone()
            cursor.close()

            if result:
                tab_id = self.sql_query_editor_panel.new_sql_tab()
                self.sql_query_editor_panel.set_text_without_undo(
                    self.sql_query_editor_panel.sql_files[tab_id]["widget"],
                    result[0]
                )
                self.sql_query_editor_panel.sql_files[tab_id]["modified"] = False
                tab_name = f"{trigger_name} (Trigger)"
                self.sql_query_editor_panel.sql_notebook.tab(
                    self.sql_query_editor_panel.sql_files[tab_id]["frame"],
                    text=tab_name
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load trigger content: {str(e)}")

    def view_procedure_content(self, schema: str, procedure_name: str):
        """View content of selected stored procedure in Query Editor"""
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(Queries.get_procedure_body(schema, procedure_name))
            result = cursor.fetchall()
            cursor.close()

            if result:
                # Combine all lines of the procedure
                procedure_body = ''.join(row[1] for row in result if row[1])
                
                tab_id = self.sql_query_editor_panel.new_sql_tab()
                self.sql_query_editor_panel.set_text_without_undo(
                    self.sql_query_editor_panel.sql_files[tab_id]["widget"],
                    procedure_body
                )
                self.sql_query_editor_panel.sql_files[tab_id]["modified"] = False
                tab_name = f"{procedure_name} (Procedure)"
                self.sql_query_editor_panel.sql_notebook.tab(
                    self.sql_query_editor_panel.sql_files[tab_id]["frame"],
                    text=tab_name
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load procedure content: {str(e)}")

    def view_function_content(self, schema: str, function_name: str):
        """View content of selected stored function in Query Editor"""
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(Queries.get_function_body(schema, function_name))
            result = cursor.fetchall()
            cursor.close()

            if result:
                # Combine all lines of the function
                function_body = ''.join(row[1] for row in result if row[1])
                
                tab_id = self.sql_query_editor_panel.new_sql_tab()
                self.sql_query_editor_panel.set_text_without_undo(
                    self.sql_query_editor_panel.sql_files[tab_id]["widget"],
                    function_body
                )
                self.sql_query_editor_panel.sql_files[tab_id]["modified"] = False
                tab_name = f"{function_name} (Function)"
                self.sql_query_editor_panel.sql_notebook.tab(
                    self.sql_query_editor_panel.sql_files[tab_id]["frame"],
                    text=tab_name
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load function content: {str(e)}")


    def view_package_content(self, schema: str, package_name: str):
        try:
            cursor = self.db_connection.current_connection.cursor()

            # 1️⃣ Try PACKAGE BODY first
            cursor.execute(Queries.get_package_body(schema, package_name))
            rows = cursor.fetchall()

            # 2️⃣ Fallback to PACKAGE SPEC if BODY not visible
            if not rows:
                cursor.execute(Queries.get_package_spec(schema, package_name))
                rows = cursor.fetchall()
                title_suffix = " (Spec)"
            else:
                title_suffix = " (Body)"

            cursor.close()

            if not rows:
                messagebox.showinfo(
                    "Info",
                    f"No source available for package {package_name}"
                )
                return

            package_source = ''.join(row[1] for row in rows if row[1])

            tab_id = self.sql_query_editor_panel.new_sql_tab()
            self.sql_query_editor_panel.set_text_without_undo(
                self.sql_query_editor_panel.sql_files[tab_id]["widget"],
                package_source
            )

            self.sql_query_editor_panel.sql_files[tab_id]["modified"] = False

            self.sql_query_editor_panel.sql_notebook.tab(
                self.sql_query_editor_panel.sql_files[tab_id]["frame"],
                text=f"{package_name}{title_suffix}"
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load package content: {str(e)}"
            )


    def view_package_function_or_procedure_content(
        self, schema: str, package_name: str,
        procedure_name: str, overload: int = None
    ):
        try:
            cursor = self.db_connection.current_connection.cursor()

            # 1️⃣ Load FULL package body
            cursor.execute(Queries.get_package_body(schema, package_name))
            source = cursor.fetchall()

            if not source:
                cursor.execute(Queries.get_package_spec(schema, package_name))
                source = cursor.fetchall()

            cursor.close()

            if not source:
                messagebox.showinfo(
                    "Info",
                    f"No package body found for {package_name}"
                )
                return

            # 2️⃣ Extract only the selected procedure/function
            procedure_body = Queries.extract_packaged_routine(
                source,
                procedure_name
            )

            if not procedure_body:
                messagebox.showinfo(
                    "Info",
                    f"Could not locate {procedure_name} inside {package_name}"
                )
                return

            # 3️⃣ Open in editor
            tab_id = self.sql_query_editor_panel.new_sql_tab()
            self.sql_query_editor_panel.set_text_without_undo(
                self.sql_query_editor_panel.sql_files[tab_id]["widget"],
                procedure_body
            )

            self.sql_query_editor_panel.sql_files[tab_id]["modified"] = False

            overload_text = f" (Overload {overload})" if overload is not None else ""
            tab_name = f"{package_name}.{procedure_name}{overload_text}"

            self.sql_query_editor_panel.sql_notebook.tab(
                self.sql_query_editor_panel.sql_files[tab_id]["frame"],
                text=tab_name
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load packaged procedure/function: {str(e)}"
            )


    def view_package_function_or_procedure_parameters(self, schema: str, package_name: str, procedure_name: str, overload: int = None):
        """View parameters of selected function/procedure within a package"""
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(Queries.get_package_function_or_procedure_parameters(schema, package_name, procedure_name, overload))
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()

            if not rows:
                messagebox.showinfo("Info", f"No parameters found for {package_name}.{procedure_name}.")
                return

            tree = self.sql_query_editor_panel._create_result_tab(
                f"{package_name}.{procedure_name} (Parameters)", 
                columns, 
                rows
            )

            context_menu = self.sql_query_editor_panel._create_context_menu(
                tree,
                lambda: self.sql_query_editor_panel._copy_selected_rows(tree),
                lambda: self.sql_query_editor_panel._export_to_csv(tree, f"{package_name}_{procedure_name}_parameters")
            )
            tree.bind("<Button-3>", lambda event: context_menu.post(event.x_root, event.y_root))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load package function/procedure parameters: {str(e)}")

    def clear_tree(self):
        self.db_tree.delete(*self.db_tree.get_children())

class SQLQueryEditorPanel:
    def __init__(self, query_result_panel, db_connection):
        self.query_result_panel = query_result_panel
        self.db_connection = db_connection
        self.query_manager = QueryManager(db_connection, query_result_panel)

    def setup(self, parent, root, theme):
        """Panel 2: SQL Query Editor with tabs"""
        self.parent = parent
        self.root = root
        self.theme = theme

        self.sql_files = {}
        self.tab_counter = 0

        editor_frame = ttk.Frame(self.parent, style='TFrame')
        self.parent.add(editor_frame, weight=1)

        self.sql_notebook = ttk.Notebook(editor_frame, style='TNotebook')

        ttk.Label(editor_frame, text="Query Editor", style='Bold.TLabel').pack(fill=tk.X, padx=5, pady=2)

        toolbar = ttk.Frame(editor_frame, style='TFrame')
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="New", command=self.new_sql_tab, style='TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open", command=self.open_sql_file, style='TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save", command=self.save_current_sql, style='TButton').pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Execute (F5)", command=self.execute_query, style='TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Execute Selection", command=self.execute_selection, style='TButton').pack(side=tk.LEFT, padx=2)

        self.sql_notebook = ttk.Notebook(editor_frame, style='TNotebook')
        self.sql_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.new_sql_tab()

        self.root.bind('<Control-n>', lambda e: self.new_sql_tab())
        self.root.bind('<Control-s>', lambda e: self.save_current_sql())
        self.root.bind('<F5>', lambda e: self.execute_query())

        self.sql_notebook.bind('<Button-2>', self.close_current_tab)

    def display_error(self, error: str):
        """Display error in result panel"""
        self.query_result_panel.display_error(error)

    def _create_result_tab(self, title, columns, rows):
        """Helper: Create a result tab with a treeview."""
        frame = ttk.Frame(self.sql_notebook, style='TFrame')
        tree_container = ttk.Frame(frame, style='TFrame')
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tree = create_treeview_with_scrollbars(tree_container, columns, 'tree headings')

        tree.column('#0', width=0, stretch=tk.NO)
        for col in columns:
            tree.column(col, minwidth=100, width=150, stretch=tk.NO, anchor=tk.W)
            tree.heading(col, text=col, anchor=tk.W)

        for row in rows:
            formatted_row = []
            for value in row:
                if value is None:
                    formatted_row.append('')
                elif isinstance(value, (datetime.datetime, datetime.date)):
                    formatted_row.append(str(value))
                elif isinstance(value, Decimal):
                    formatted_row.append(str(value))
                else:
                    formatted_row.append(str(value))
            tree.insert('', 'end', values=formatted_row)

        for col in columns:
            max_width = 0
            for item in tree.get_children():
                cell_value = tree.item(item)['values'][columns.index(col)]
                text_width = len(str(cell_value)) * 8
                if text_width > max_width:
                    max_width = text_width
            default_width = 150
            width_limit = 300
            width = max(max_width, default_width)
            width = min(width, width_limit)
            tree.column(col, width=width)

        tree.update_idletasks()

        close_button = ttk.Button(frame, text='×', command=lambda: self.close_result_tab(frame), style='Close.TButton')
        close_button.pack(side=tk.RIGHT, padx=2, pady=2)

        self.sql_notebook.add(frame, text=title)
        self.sql_notebook.select(frame)

        return tree

    def _create_context_menu(self, tree, copy_command, export_command):
        """Helper: Create a context menu for a treeview."""
        commands = [
            ("Copy Selected", copy_command),
            ("Export to CSV", export_command)
        ]
        context_menu = create_context_menu(tree, commands)
        return context_menu

    def _export_to_csv(self, tree, default_name):
        """Helper: Export treeview data to CSV."""
        filepath = filedialog.asksaveasfilename(
            title=f"Export {default_name} to CSV",
            defaultextension=".csv",
            initialfile=f"{default_name}.csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, delimiter='\t')
                    writer.writerow(tree['columns'])
                    for item in tree.get_children():
                        writer.writerow(tree.item(item)['values'])
                messagebox.showinfo("Success", f"{default_name} exported to {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export {default_name}: {str(e)}")

    def _copy_selected_rows(self, tree):
        """Helper: Copy selected rows to clipboard."""
        selected_items = tree.selection()
        if not selected_items:
            return

        selected_values = []
        for item in selected_items:
            values = tree.item(item)['values']
            selected_values.append('\t'.join(str(value) for value in values))

        self.root.clipboard_clear()
        self.root.clipboard_append('\n'.join(selected_values))
        self.root.update()

    def show_table_keys(self, schema: str, table: str):
        """Fetch and display table or view keys (primary and foreign) in a new tab."""
        try:
            cursor = self.db_connection.current_connection.cursor()

            # Vérifier si c'est une table ou une vue
            cursor.execute(Queries.get_table_primary_keys(schema, table))
            primary_keys = cursor.fetchall()

            cursor.execute(Queries.get_table_foreign_keys(schema, table))
            foreign_keys = cursor.fetchall()

            columns = ["Column Name", "Key Type", "Referenced Schema", "Referenced Constraint", "Referenced Table"]
            rows = []
            for pk in primary_keys:
                rows.append((pk[0], pk[1], "", "", ""))
            for fk in foreign_keys:
                rows.append((fk[0], fk[1], fk[2], fk[3], fk[4]))

            if not rows:
                messagebox.showinfo("Info", f"No keys found for {table}.")
                return

            tree = self._create_result_tab(f"{table} (Keys)", columns, rows)

            context_menu = self._create_context_menu(
                tree,
                lambda: self._copy_selected_rows(tree),
                lambda: self._export_to_csv(tree, f"{table}_keys")
            )
            tree.bind("<Button-3>", lambda event: context_menu.post(event.x_root, event.y_root))

            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load table keys: {str(e)}")

    # Modifiez la méthode show_table_structure pour gérer les vues
    def show_table_structure(self, schema: str, table: str):
        """Fetch and display table or view structure in a new tab."""
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(Queries.get_table_structure(schema, table))
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            tree = self._create_result_tab(f"{table} (Structure)", columns, rows)

            context_menu = self._create_context_menu(
                tree,
                lambda: self._copy_selected_rows(tree),
                lambda: self._export_to_csv(tree, f"{table}_structure")
            )
            tree.bind("<Button-3>", lambda event: context_menu.post(event.x_root, event.y_root))

            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load table structure: {str(e)}")

    def show_table_indexes(self, schema: str, table: str, index_name: str | None = None):
        """Fetch and display table indexes in a new tab."""
        try:
            cursor = self.db_connection.current_connection.cursor()
            cursor.execute(Queries.get_table_indexes(schema, table))
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()

            if not rows:
                messagebox.showinfo("Info", f"No indexes found for table {table}.")
                return

            tree = self._create_result_tab(f"{table} (Indexes)", columns, rows)

            context_menu = self._create_context_menu(
                tree,
                lambda: self._copy_selected_rows(tree),
                lambda: self._export_to_csv(tree, f"{table}_indexes")
            )
            tree.bind("<Button-3>", lambda event: context_menu.post(event.x_root, event.y_root))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load table indexes: {str(e)}")


    def new_sql_tab(self):
        """Create new SQL editor tab with close button"""
        self.tab_counter += 1
        tab_id = f"tab_{self.tab_counter}"

        frame = ttk.Frame(self.sql_notebook, style='TFrame')

        text_scroll = ttk.Scrollbar(frame, style='TScrollbar')
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = SQLText(
            frame,
            wrap=tk.NONE,
            yscrollcommand=text_scroll.set,
            undo=True,
            maxundo=-1,
            **self.theme.sql_editor_style
        )

        text_widget.bind("<Control-z>", lambda e: (self.undo(), "break"))
        text_widget.bind("<Control-y>", lambda e: (self.redo(), "break"))
        text_widget.bind("<Control-Shift-Z>", lambda e: (self.redo(), "break"))

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.config(command=text_widget.yview)

        text_widget.edit_reset()
        text_widget.edit_modified(False)

        # Focus the new text widget
        text_widget.focus_set()

        close_button = ttk.Button(frame, text='×', command=lambda: self.close_tab(tab_id), style='Close.TButton')
        close_button.pack(side=tk.RIGHT, padx=2, pady=2)

        self.sql_notebook.add(frame, text=f"Untitled {self.tab_counter}")
        self.sql_notebook.select(frame)

        self.sql_files[tab_id] = {"path": None, "modified": False, "widget": text_widget, "frame": frame}

        text_widget.bind('<<Modified>>', lambda e: self.mark_modified(tab_id))

        return tab_id


    def close_tab(self, tab_id):
        """Close the specified tab"""
        if tab_id in self.sql_files:
            if self.sql_files[tab_id]["modified"]:
                if not messagebox.askyesno("Unsaved Changes", "This file has unsaved changes. Close anyway?"):
                    return
            self.sql_notebook.forget(self.sql_files[tab_id]["frame"])
            del self.sql_files[tab_id]

    def close_current_tab(self, event):
        """Close the current tab when middle mouse button is pressed"""
        current_frame = self.sql_notebook.select()
        if not current_frame:
            return

        for tab_id, info in self.sql_files.items():
            if str(info["frame"]) == current_frame:
                self.close_tab(tab_id)
                return

        self.sql_notebook.forget(current_frame)

    def close_result_tab(self, frame):
        """Close the specified result tab."""
        for tab in self.sql_notebook.tabs():
            if self.sql_notebook.nametowidget(tab) == frame:
                self.sql_notebook.forget(tab)
                break

    def set_text_without_undo(self, text_widget: tk.Text, content: str):
        """Replace text without polluting the undo stack"""
        text_widget.configure(undo=False)
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", content)
        text_widget.edit_reset()
        text_widget.edit_modified(False)
        text_widget.configure(undo=True)

    def undo(self):
        """Undo the last action in the current SQL tab"""
        _, info = self.get_current_sql_tab()
        if info:
            try:
                info["widget"].edit_undo()
            except tk.TclError:
                pass

    def redo(self):
        """Redo the last undone action in the current SQL tab"""
        _, info = self.get_current_sql_tab()
        if info:
            try:
                info["widget"].edit_redo()
            except tk.TclError:
                pass

    def mark_modified(self, tab_id):
        """Mark tab as modified and update tab name"""
        if tab_id not in self.sql_files:
            return

        widget = self.sql_files[tab_id]["widget"]

        if widget.edit_modified():
            self.sql_files[tab_id]["modified"] = True
            widget.edit_modified(False)

            current_text = self.sql_notebook.tab(self.sql_files[tab_id]["frame"], "text")
            if not current_text.startswith("• "):
                self.sql_notebook.tab(self.sql_files[tab_id]["frame"], text=f"• {current_text}")

    def get_current_sql_tab(self):
        """Get current SQL tab info"""
        current_frame = self.sql_notebook.select()
        for tab_id, info in self.sql_files.items():
            if str(info["frame"]) == current_frame:
                return tab_id, info
        return None, None

    def open_sql_file(self):
        """Open SQL file"""
        filepath = filedialog.askopenfilename(
            title="Open SQL File",
            filetypes=[("SQL Files", "*.sql"), ("All Files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                tab_id = self.new_sql_tab()
                self.set_text_without_undo(self.sql_files[tab_id]["widget"], content)

                self.sql_files[tab_id]["path"] = filepath
                self.sql_files[tab_id]["modified"] = False

                filename = os.path.basename(filepath)
                self.sql_notebook.tab(self.sql_files[tab_id]["frame"], text=filename)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {str(e)}")

    def save_current_sql(self):
        """Save current SQL file and update tab name"""
        tab_id, info = self.get_current_sql_tab()
        if not info:
            return

        if info["path"]:
            self.save_sql_to_file(info["path"], info["widget"].get('1.0', 'end-1c'))
            info["modified"] = False
            current_text = self.sql_notebook.tab(info["frame"], "text")
            if current_text.startswith("• "):
                self.sql_notebook.tab(info["frame"], text=current_text[2:])
        else:
            self.save_sql_as()

    def save_sql_as(self):
        """Save SQL file as"""
        tab_id, info = self.get_current_sql_tab()
        if not info:
            return

        filepath = filedialog.asksaveasfilename(
            title="Save SQL File",
            defaultextension=".sql",
            filetypes=[("SQL Files", "*.sql"), ("All Files", "*.*")]
        )

        if filepath:
            self.save_sql_to_file(filepath, info["widget"].get('1.0', 'end-1c'))
            info["path"] = filepath
            info["modified"] = False
            self.sql_notebook.tab(info["frame"], text=os.path.basename(filepath))

    def save_sql_to_file(self, filepath, content):
        """Write content to file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def execute_query(self):
        """Execute SQL query from current tab"""
        if not self.db_connection.current_connection:
            messagebox.showwarning("Not Connected", "Please connect to a database first")
            return

        tab_id, info = self.get_current_sql_tab()
        if not info:
            return

        sql = info["widget"].get('1.0', 'end-1c').strip()
        if not sql:
            return

        self.run_query(sql)

    def execute_selection(self):
        """Execute selected SQL text"""
        if not self.db_connection.current_connection:
            messagebox.showwarning("Not Connected", "Please connect to a database first")
            return

        tab_id, info = self.get_current_sql_tab()
        if not info:
            return

        try:
            sql = info["widget"].get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            if sql:
                self.query_manager.run_query(sql)
        except tk.TclError:
            messagebox.showwarning("No Selection", "Please select SQL text to execute")

    def run_query(self, sql: str):
        """Execute SQL and display results"""
        self.query_manager.run_query(sql)

    def display_message(self, message: str):
        """Display message in result panel"""
        self.query_result_panel.display_message(message)

class QueryResultPanel:
    def __init__(self, root, db_connection):
        self.root = root
        self.db_connection = db_connection
        self.current_codepage = 'utf-8'  # Valeur par défaut

    def setup(self, parent, config):
        """Panel 3: Query Result Grid"""
        self.parent = parent
        self.config = config

        result_frame = ttk.Frame(self.parent, style='TFrame')
        self.parent.add(result_frame, weight=1)

        header = ttk.Frame(result_frame, style='TFrame')
        header.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(header, text="Query Result", style='Bold.TLabel').pack(side=tk.LEFT)

        # Ajoutez un contrôle pour sélectionner le code-page
        codepage_frame = ttk.Frame(header, style='TFrame')
        codepage_frame.pack(side=tk.RIGHT, padx=5)

        ttk.Label(codepage_frame, text="Code Page:").pack(side=tk.LEFT, padx=2)

        # Liste des code-pages courants utilisés par Oracle
        self.codepage_options = [
            'utf-8', 'iso-8859-1', 'iso-8859-15', 'windows-1252',
            'cp1252', 'cp850', 'cp437', 'cp852', 'cp857', 'cp860',
            'cp863', 'cp865', 'cp874', 'shift_jis', 'euc-jp', 'euc-kr'
        ]

        self.codepage_var = tk.StringVar(value=self.current_codepage)
        self.codepage_combobox = ttk.Combobox(
            codepage_frame,
            textvariable=self.codepage_var,
            values=self.codepage_options,
            state='readonly',
            width=12
        )
        self.codepage_combobox.pack(side=tk.LEFT, padx=2)
        self.codepage_combobox.bind('<<ComboboxSelected>>', self.on_codepage_change)

        self.show_labels = self.config.get("show_labels", False)

        self.label_var = tk.BooleanVar(value=self.show_labels)
        ttk.Radiobutton(header, text="Field Names", variable=self.label_var, value=False, command=self.toggle_labels).pack(side=tk.RIGHT, padx=5)
        ttk.Radiobutton(header, text="Field Labels", variable=self.label_var, value=True, command=self.toggle_labels).pack(side=tk.RIGHT, padx=5)

        grid_container = ttk.Frame(result_frame, style='TFrame')
        grid_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.result_tree = create_treeview_with_scrollbars(grid_container, show='tree headings')
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.result_tree.bind("<Shift-MouseWheel>", self.on_shift_mousewheel)

        self.result_info = ttk.Label(result_frame, text="", style='TLabel', anchor=tk.W)
        self.result_info.pack(fill=tk.X, padx=5, pady=2)

        commands = [
            ("Copy Selected", self.copy_selected_rows),
            ("Export to CSV", self.export_to_csv),
            ("Reset Column Widths", self.reset_column_widths)
        ]
        self.result_context_menu = create_context_menu(self.result_tree, commands)

        self.result_tree.bind("<Button-3>", self.show_result_context_menu)
        self.result_tree.bind("<Configure>", self.on_tree_configure)

        # Stocker le texte brut des erreurs pour rafraîchissement
        self.raw_error_text = None

    def on_codepage_change(self, event=None):
        """Mise à jour du code-page courant"""
        self.current_codepage = self.codepage_var.get()
        if self.raw_error_text:
            self.refresh_display()

    def decode_error_with_codepage(self, error_text, codepage):
        """Décoder un texte d'erreur avec un code-page spécifique"""
        try:
            return error_text.decode(codepage, errors='replace')
        except:
            return error_text.decode('utf-8', errors='replace')
        

    def display_error(self, error: str):
        """Display error in result panel"""

        # Extract error name and text using regex
        match = re.search(r"\('(.*?)', '(.*?)'\)", str(error))
        if match:
            error_name = match.group(1)
            error_text = match.group(2)
            # Remove escape sequences and extra whitespace
            error_text = error_text.replace('\\x00', '').replace('\\n', '\n').replace('\\r', '\r')
            error = f"{error_name}: {error_text}"
        else:
            error = str(error)


        # Store the cleaned error text
        self.raw_error_text = error

        # Display the cleaned error
        self.result_tree.delete(*self.result_tree.get_children())
        self.result_tree['columns'] = ['Error']
        self.result_tree.column('#0', width=0, stretch=tk.NO)
        self.result_tree.column('Error', width=800)
        self.result_tree.heading('Error', text='SQL Error')
        self.result_tree.insert('', 'end', values=[error])

    def refresh_display(self):
        """Rafraîchir l'affichage avec le code-page courant"""
        if self.raw_error_text:
            try:
                decoded_text = self.decode_error_with_codepage(self.raw_error_text, self.current_codepage)
                self.display_error(decoded_text)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to decode error message: {str(e)}")


    def display_message(self, message: str):
        """Display message in result panel"""
        self.result_tree.delete(*self.result_tree.get_children())
        self.result_tree['columns'] = ['Message']
        self.result_tree.column('#0', width=0, stretch=tk.NO)
        self.result_tree.column('Message', width=800)
        self.result_tree.heading('Message', text='Message')
        self.result_tree.insert('', 'end', values=[message])

    def on_shift_mousewheel(self, event):
        """Handle Shift+MouseWheel for horizontal scrolling"""
        self.result_tree.xview_scroll(-1 * (event.delta), "units")
        return "break"

    def update_column_widths(self):
        """Update column widths based on content and available space"""
        for col in self.result_tree['columns']:
            max_width = 0
            for item in self.result_tree.get_children():
                cell_value = self.result_tree.item(item)['values'][self.result_tree['columns'].index(col)]
                text_width = len(str(cell_value)) * 8
                if text_width > max_width:
                    max_width = text_width

            default_width = 150
            width_limit = 300
            width = max(max_width, default_width)
            width = min(width, width_limit)
            self.result_tree.column(col, width=width)

        self.result_tree.update_idletasks()

    def display_results(self, columns: List[str], rows: List[Tuple], description):
        """Display query results in grid"""
        self.result_tree.delete(*self.result_tree.get_children())

        self.result_tree['columns'] = columns
        self.result_tree.column('#0', width=0, stretch=tk.NO)

        for col in columns:
            self.result_tree.column(col, minwidth=100, width=150, stretch=tk.NO, anchor=tk.W)
            display_name = col
            self.result_tree.heading(col, text=display_name, anchor=tk.W)

        row_count = 0
        for row in rows:
            formatted_row = []
            for value in row:
                if value is None:
                    formatted_row.append('')
                elif isinstance(value, (datetime.datetime, datetime.date)):
                    formatted_row.append(str(value))
                elif isinstance(value, Decimal):
                    formatted_row.append(str(value))
                else:
                    formatted_row.append(str(value))

            self.result_tree.insert('', 'end', values=formatted_row)
            row_count += 1

        self.update_column_widths()

        self.result_info.config(text=f"{row_count} row(s) displayed")

    def on_tree_configure(self, event):
        """Handle Treeview configuration changes"""
        pass

    def reset_column_widths(self):
        """Reset column widths to default values"""
        for col in self.result_tree['columns']:
            self.result_tree.column(col, width=150)
        self.result_tree.update_idletasks()

    def show_result_context_menu(self, event):
        """Show context menu on result tree"""
        self.result_context_menu.post(event.x_root, event.y_root)

    def copy_selected_rows(self):
        """Copy selected rows to clipboard"""
        selected_items = self.result_tree.selection()
        if not selected_items:
            return

        selected_values = []
        for item in selected_items:
            values = self.result_tree.item(item)['values']
            selected_values.append('\t'.join(str(value) for value in values))

        self.root.clipboard_clear()
        self.root.clipboard_append('\n'.join(selected_values))
        self.root.update()

    def export_to_csv(self):
        """Export query results to CSV file"""
        if not self.result_tree.get_children():
            messagebox.showwarning("No Data", "No data to export")
            return

        filepath = filedialog.asksaveasfilename(
            title="Export to CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, delimiter='\t')
                    writer.writerow(self.result_tree['columns'])
                    for item in self.result_tree.get_children():
                        writer.writerow(self.result_tree.item(item)['values'])
                messagebox.showinfo("Success", f"Data exported to {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export data: {str(e)}")

    def toggle_labels(self):
        """Toggle between field names and labels"""
        self.show_labels = self.label_var.get()
        self.save_config()

class StatusBarPanel:
    def __init__(self, root, text, style):
        self.root = root
        self.status_bar = ttk.Label(self.root, text=text, style=style)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def set_status(self, new_status):
        self.status_bar.config(text=new_status)
