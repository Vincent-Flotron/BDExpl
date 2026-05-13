import tkinter as tk
import datetime
import csv
import os
import re
from tkinter      import ttk, filedialog, messagebox
from decimal      import Decimal
from SQLText      import SQLText
from typing       import List, Tuple


class Tooltip:
    """Simple tooltip class for tkinter widgets"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip, text=self.text, justify='left',
                        background="#ffffe0", relief='solid', borderwidth=1,
                        font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class Helper:
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
    def __init__(self, parent, db_connection, sql_query_editor_panel, query_manager):
        self.parent = parent
        self.db_connection = db_connection
        self.sql_query_editor_panel = sql_query_editor_panel
        self.queries = None  # Will be set based on connection type
        self.query_manager = query_manager

    def setup(self):
        """Panel 1: Database object tree"""
        left_frame = ttk.Frame(self.parent, style='TFrame')
        self.parent.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Database Objects", style='Bold.TLabel').pack(pady=5)

        # ── Search bar ────────────────────────────────────────────────
        search_frame = ttk.Frame(left_frame, style='TFrame')
        search_frame.pack(fill=tk.X, padx=4, pady=(0, 2))

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<Return>", self.search_in_tree)

        # "Everywhere" checkbox
        self.search_everywhere_var = tk.BooleanVar(value=False)
        everywhere_cb = ttk.Checkbutton(
            search_frame, text="everywhere",
            variable=self.search_everywhere_var,
            command=self._update_search_checkboxes_state
        )
        everywhere_cb.pack(side=tk.LEFT, padx=(4, 0))

        # Object-type filter checkboxes
        type_frame = ttk.Frame(left_frame, style='TFrame')
        type_frame.pack(fill=tk.X, padx=4, pady=(0, 4))

        self.search_tables_var     = tk.BooleanVar(value=True)
        self.search_views_var      = tk.BooleanVar(value=True)
        self.search_procedures_var = tk.BooleanVar(value=True)
        self.search_functions_var  = tk.BooleanVar(value=True)
        self.search_packages_var   = tk.BooleanVar(value=True)

        # Track states
        vars_to_watch = [
            self.search_everywhere_var, self.search_tables_var, 
            self.search_views_var, self.search_procedures_var,
            self.search_functions_var, self.search_packages_var
        ]
        
        for var in vars_to_watch:
            var.trace_add("write", self._reset_search_session)

        self._cb_tables = ttk.Checkbutton(type_frame, text="tables",
                                          variable=self.search_tables_var, state='disabled')
        self._cb_views  = ttk.Checkbutton(type_frame, text="views",
                                          variable=self.search_views_var,  state='disabled')
        self._cb_procs  = ttk.Checkbutton(type_frame, text="procedures",
                                          variable=self.search_procedures_var, state='disabled')
        self._cb_funcs  = ttk.Checkbutton(type_frame, text="functions",
                                          variable=self.search_functions_var,  state='disabled')
        self._cb_pkgs   = ttk.Checkbutton(type_frame, text="packages",
                                          variable=self.search_packages_var,   state='disabled')

        self._type_checkboxes = [
            self._cb_tables, self._cb_views,
            self._cb_procs,  self._cb_funcs, self._cb_pkgs,
        ]
        for cb in self._type_checkboxes:
            cb.pack(side=tk.LEFT, padx=1)

        # left_frame
        # ── Refresh Frame ────────────────────────────────────────────────
        self.refresh_frame = ttk.Frame(left_frame, style='TFrame')
        self.refresh_frame.pack(fill=tk.X, padx=4, pady=2)

        refresh_btn = ttk.Button(self.refresh_frame, text="⟳", command=self.load_database_objects, style='Refresh.TButton')
        refresh_btn.pack(side=tk.RIGHT, padx=2, ipady=2)

        # Add tooltip
        Tooltip(refresh_btn, "Refresh database tree")

        
        # ── Breadcrumb Frame ──────────────────────────────────────────────
        # Container for ariane wire (Nautilus style)
        self.breadcrumb_frame = ttk.Frame(left_frame, style='TFrame')
        self.breadcrumb_frame.pack(fill=tk.X, padx=4, pady=2)

        # Internal search state
        self._search_results       = []
        self._search_results_index = 0
        self._search_results_term  = ""

        # Treeview with scrollbars
        tree_container = ttk.Frame(left_frame, style='TFrame')
        tree_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.db_tree = Helper.create_treeview_with_scrollbars(tree_container)

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
        self.table_context_menu = Helper.create_context_menu(self.db_tree, table_commands)

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
        self.view_context_menu = Helper.create_context_menu(self.db_tree, view_commands)

        self.db_tree.bind("<Button-3>", self.show_tree_context_menu)
        self.db_tree.bind("<Double-1>", lambda e: self.view_table_data(100))
        self.db_tree.bind("<<TreeviewOpen>>", self.on_tree_expand)
        self.db_tree.bind("<<TreeviewSelect>>", lambda e: self._update_search_checkboxes_state())
        self.db_tree.bind("<<TreeviewSelect>>", self._update_breadcrumbs)

    def on_tree_expand(self, event):
        """Handle tree expansion - lazy load table children (indexes, keys, triggers), schema children (procedures, functions, packages, views), and package children (functions, procedures)"""
        item = self.db_tree.focus()
        if not item:
            return

        values = self.db_tree.item(item)['values']
        if not values or len(values) < 2:
            return

        queries = self.get_queries_instance()

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
            queries = self.get_queries_instance()
            sql = queries.get_first_x_rows(schema, table_or_view, limit)

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
            queries = self.get_queries_instance()

            cursor = self.query_manager.cursor_execute(queries.count_table_indexes(schema, table), cursor)
            index_count = cursor.fetchone()[0]
            if index_count > 0:
                self.db_tree.insert(
                    table_node, 'end',
                    text=f'Indexes ({index_count})',
                    values=(schema, 'indexes_summary', table)
                )

            cursor = self.query_manager.cursor_execute(queries.count_table_prim_and_foreign_keys(schema, table), cursor)
            key_count = cursor.fetchone()[0]
            if key_count > 0:
                self.db_tree.insert(
                    table_node, 'end',
                    text=f'Keys ({key_count})',
                    values=(schema, 'keys_summary', table)
                )

            cursor = self.query_manager.cursor_execute(queries.get_table_triggers(schema, table), cursor)
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
            queries = self.get_queries_instance()

            # Load procedures
            cursor = self.query_manager.cursor_execute(queries.count_procedures_in_schema(schema), cursor)
            procedure_count = cursor.fetchone()[0]
            if procedure_count > 0:
                procedures_node = self.db_tree.insert(
                    schema_node, 'end',
                    text=f'Procedures ({procedure_count})',
                    values=(schema, 'procedures_folder')
                )

                cursor = self.query_manager.cursor_execute(queries.get_all_procedures_in_schema(schema), cursor)
                procedures = cursor.fetchall()
                for (procedure_name,) in procedures:
                    self.db_tree.insert(
                        procedures_node, 'end',
                        text=procedure_name,
                        values=(schema, 'procedure', procedure_name)
                    )

            # Load functions
            cursor = self.query_manager.cursor_execute(queries.count_functions_in_schema(schema), cursor)
            function_count = cursor.fetchone()[0]
            if function_count > 0:
                functions_node = self.db_tree.insert(
                    schema_node, 'end',
                    text=f'Functions ({function_count})',
                    values=(schema, 'functions_folder')
                )

                cursor = self.query_manager.cursor_execute(queries.get_all_functions_in_schema(schema), cursor)
                functions = cursor.fetchall()
                for (function_name,) in functions:
                    self.db_tree.insert(
                        functions_node, 'end',
                        text=function_name,
                        values=(schema, 'function', function_name)
                    )

            # Load packages
            cursor = self.query_manager.cursor_execute(queries.count_packages_in_schema(schema), cursor)
            package_count = cursor.fetchone()[0]
            if package_count > 0:
                packages_node = self.db_tree.insert(
                    schema_node, 'end',
                    text=f'Packages ({package_count})',
                    values=(schema, 'packages_folder')
                )

                cursor = self.query_manager.cursor_execute(queries.get_all_packages_in_schema(schema), cursor)
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
            cursor = self.query_manager.cursor_execute(queries.count_views_in_schema(schema), cursor)
            view_count = cursor.fetchone()[0]
            if view_count > 0:
                views_node = self.db_tree.insert(
                    schema_node, 'end',
                    text=f'Views ({view_count})',
                    values=(schema, 'views_folder')
                )

                cursor = self.query_manager.cursor_execute(queries.get_all_views_in_schema(schema), cursor)
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
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_view_dependencies(schema, view), cursor)
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
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_view_body(schema, view_name), cursor)
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
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_view_structure(schema, view), cursor)
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
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_view_comment(schema, view), cursor)
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
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_view_query(schema, view), cursor)
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
            queries = self.get_queries_instance()

            cursor = self.query_manager.cursor_execute(queries.get_package_functions_and_procedures(schema, package_name), cursor)
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

    def get_queries_instance(self):
        return self.db_connection.get_queries_instance(self.db_connection.current_connection)


    def load_database_objects(self):
        """Load database objects into tree with basic queries"""
        if not self.db_connection.current_connection:
            messagebox.showwarning("Not Connected", "Please connect to a database first")
            return

        self.db_tree.delete(*self.db_tree.get_children())

        try:
            cursor = self.db_connection.current_connection.cursor()
            queries = self.get_queries_instance()

            cursor = self.query_manager.cursor_execute(queries.get_all_schemas_with_their_table_count(), cursor)
            schemas = cursor.fetchall()

            # Clean ariane wire when connecting to a new db
            for widget in self.breadcrumb_frame.winfo_children():
                widget.destroy()

            self.db_tree.delete(*self.db_tree.get_children())

            for schema, table_count in schemas:
                schema_node = self.db_tree.insert('', 'end', text=f"{schema} ({table_count} tables)", values=(schema, 'schema'))

                # Insert tables folder first
                tables_node = self.db_tree.insert(schema_node, 'end', text=f'Tables ({table_count})', values=(schema, 'tables_folder'))

                # Add loading placeholder for schema children (procedures, functions, and packages) after tables
                loading_placeholder = self.db_tree.insert(schema_node, 'end', text='Loading...', values=(schema, 'loading'))

                cursor = self.query_manager.cursor_execute(queries.get_all_table_names_in_schema(schema), cursor)
                table_results = cursor.fetchall()
                for (table,) in table_results:
                    table_node = self.db_tree.insert(tables_node, 'end', text=table, values=(schema, 'table', table))
                    self.db_tree.insert(table_node, 'end', text='Loading...', values=(schema, 'loading'))

                try:
                    cursor = self.query_manager.cursor_execute(queries.get_current_session_roles(), cursor)
                    roles = cursor.fetchall()
                    roles_node = self.db_tree.insert(schema_node, 'end', text=f'Roles ({len(roles)})', values=(schema, 'roles_folder'))
                    for (role,) in roles:
                        self.db_tree.insert(roles_node, 'end', text=role, values=(schema, 'role', role))
                except:
                    roles_node = self.db_tree.insert(schema_node, 'end', text='Roles (0)', values=(schema, 'roles_folder'))

                try:
                    cursor = self.query_manager.cursor_execute(queries.get_current_session_privileges(), cursor)
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
            queries = self.get_queries_instance()
            sql = queries.get_first_x_rows(schema, view, limit)

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
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_trigger_body(schema, trigger_name), cursor)
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
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_procedure_body(schema, procedure_name), cursor)
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
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_function_body(schema, function_name), cursor)
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
            queries = self.get_queries_instance()

            # 1️⃣ Try PACKAGE BODY first
            cursor = self.query_manager.cursor_execute(queries.get_package_body(schema, package_name), cursor)
            rows = cursor.fetchall()

            # 2️⃣ Fallback to PACKAGE SPEC if BODY not visible
            if not rows:
                cursor = self.query_manager.cursor_execute(queries.get_package_spec(schema, package_name), cursor)
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
            queries = self.get_queries_instance()

            # 1️⃣ Load FULL package body
            cursor = self.query_manager.cursor_execute(queries.get_package_body(schema, package_name), cursor)
            source = cursor.fetchall()

            if not source:
                cursor = self.query_manager.cursor_execute(queries.get_package_spec(schema, package_name), cursor)
                source = cursor.fetchall()

            cursor.close()

            if not source:
                messagebox.showinfo(
                    "Info",
                    f"No package body found for {package_name}"
                )
                return

            # 2️⃣ Extract only the selected procedure/function
            procedure_body = queries.extract_packaged_routine(
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
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_package_function_or_procedure_parameters(schema, package_name, procedure_name, overload), cursor)
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

    # ------------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------------

    def _update_search_checkboxes_state(self, *args):
        """Enable type-filter checkboxes only when a schema is selected or 'everywhere' is on."""
        everywhere = self.search_everywhere_var.get()
        if everywhere:
            state = 'normal'
        else:
            selection = self.db_tree.selection()
            if selection:
                values = self.db_tree.item(selection[0])['values']
                item_type = values[1] if len(values) > 1 else ''
                state = 'normal' if item_type == 'schema' else 'disabled'
            else:
                state = 'disabled'

        for cb in self._type_checkboxes:
            cb.config(state=state)

    def _ensure_schema_loaded(self, schema_node):
        """Force-load procedures/functions/packages/views for a schema if not yet expanded."""
        children = self.db_tree.get_children(schema_node)
        # The loading placeholder is always the second child (index 1), right after
        # the tables_folder.  If it is still present the schema hasn't been expanded.
        if len(children) > 1:
            second_values = self.db_tree.item(children[1])['values']
            if second_values and len(second_values) > 1 and second_values[1] == 'loading':
                self.db_tree.delete(children[1])
                schema_name = self.db_tree.item(schema_node)['values'][0]
                self.load_schema_children(schema_node, schema_name)

    def _collect_folder_matches(self, folder_node, term):
        """Return all direct children of *folder_node* whose name contains *term*."""
        results = []
        for child in self.db_tree.get_children(folder_node):
            child_values = self.db_tree.item(child)['values']
            # Leaf objects always have at least 3 values: (schema, type, name)
            if len(child_values) >= 3:
                name = str(child_values[2])
                if term.lower() in name.lower():
                    results.append(child)
        return results

    def _search_in_schema_node(self, schema_node, term,
                                tables, views, procedures, functions, packages):
        """Return all matching items inside *schema_node* for the requested types."""
        results = []

        # Lazy-load procedures, functions, packages, views if requested
        if procedures or functions or packages or views:
            self._ensure_schema_loaded(schema_node)

        folder_type_map = {
            'tables_folder':     tables,
            'views_folder':      views,
            'procedures_folder': procedures,
            'functions_folder':  functions,
            'packages_folder':   packages,
        }

        for folder_node in self.db_tree.get_children(schema_node):
            folder_values = self.db_tree.item(folder_node)['values']
            if not folder_values or len(folder_values) < 2:
                continue
            folder_type = folder_values[1]
            if folder_type_map.get(folder_type, False):
                results += self._collect_folder_matches(folder_node, term)

        return results

    def search_in_tree(self, event=None):
        """
        Search for objects in the tree and select the first (or next) match.

        Behaviour:
        • If 'everywhere' is checked: search across all schemas using the
          type-filter checkboxes (tables, views, procedures, functions, packages).
        • If a schema is selected: search within that schema using the type filters.
        • If a leaf object (table, view, procedure …) is selected: search siblings
          inside the same folder, ignoring the type filters.
        • Pressing ENTER again cycles to the next match in the result list.
        """
        term = self.search_var.get().strip()
        if not term:
            return

        everywhere  = self.search_everywhere_var.get()
        do_tables   = self.search_tables_var.get()
        do_views    = self.search_views_var.get()
        do_procs    = self.search_procedures_var.get()
        do_funcs    = self.search_functions_var.get()
        do_pkgs     = self.search_packages_var.get()

        selection = self.db_tree.selection()
        results   = []

        if everywhere:
            # ── Search across ALL schemas ──────────────────────────────
            for schema_node in self.db_tree.get_children(''):
                node_vals = self.db_tree.item(schema_node)['values']
                if node_vals and node_vals[1] == 'schema':
                    results += self._search_in_schema_node(
                        schema_node, term,
                        do_tables, do_views, do_procs, do_funcs, do_pkgs
                    )

        elif not selection:
            messagebox.showinfo("Search", "Please select an item in the tree or check 'everywhere'.")
            return

        else:
            selected_item = selection[0]
            values    = self.db_tree.item(selected_item)['values']
            item_type = values[1] if len(values) > 1 else ''

            if item_type == 'schema':
                # ── Search within the selected schema ──────────────────
                results += self._search_in_schema_node(
                    selected_item, term,
                    do_tables, do_views, do_procs, do_funcs, do_pkgs
                )

            elif item_type in ('tables_folder', 'views_folder',
                               'procedures_folder', 'functions_folder',
                               'packages_folder'):
                # ── Search within the selected folder ──────────────────
                results += self._collect_folder_matches(selected_item, term)

            else:
                # ── Leaf or sub-item: search siblings (parent folder) ──
                parent = self.db_tree.parent(selected_item)
                if not parent:
                    return
                parent_values = self.db_tree.item(parent)['values']
                parent_type   = parent_values[1] if len(parent_values) > 1 else ''

                if parent_type in ('tables_folder', 'views_folder',
                                   'procedures_folder', 'functions_folder',
                                   'packages_folder'):
                    # Direct child of a folder — search all siblings
                    results += self._collect_folder_matches(parent, term)

                elif parent_type == 'schema':
                    # The selected item *is* a folder node itself — search its contents
                    results += self._collect_folder_matches(selected_item, term)

                else:
                    # Deeper nesting (trigger, index …) — search among siblings
                    results += self._collect_folder_matches(parent, term)

        if not results:
            messagebox.showinfo("Search", f"No result found for '{term}'.")
            return

        # ── Cycle through results on repeated ENTER ──────────────────
        if term != self._search_results_term:
            # New term: reset cycle
            self._search_results       = results
            self._search_results_term  = term
            self._search_results_index = 0
        else:
            # Same term: advance to next match
            self._search_results_index = (
                (self._search_results_index + 1) % len(self._search_results)
            )

        target = self._search_results[self._search_results_index]

        # Ensure parent nodes are open so the item is reachable
        parent = self.db_tree.parent(target)
        if parent:
            self.db_tree.item(parent, open=True)
            grandparent = self.db_tree.parent(parent)
            if grandparent:
                self.db_tree.item(grandparent, open=True)

        self.db_tree.selection_set(target)
        self.db_tree.see(target)
        self.db_tree.focus(target)

    def _reset_search_session(self, *args):
        """Clears cached search results to force a new search."""
        self._search_results = []
        self._search_results_index = 0
        self._search_results_term = ""


    def _update_breadcrumbs(self, event=None):
        # 1. Remove old breadcrumb buttons
        for widget in self.breadcrumb_frame.winfo_children():
            widget.destroy()

        selected = self.db_tree.selection()
        if not selected:
            return

        item_id = selected[0]
        path_items = []

        # 2. Walk up from child to parent to build the full path
        temp_id = item_id
        while temp_id:
            item_text = self.db_tree.item(temp_id)['text']
            # Clean the text (e.g. "schema (2823 tables)" -> "schema")
            clean_text = item_text.split(' (')[0]
            path_items.insert(0, (temp_id, clean_text))
            temp_id = self.db_tree.parent(temp_id)

        # 3. Create breadcrumb buttons horizontally
        for i, (original_id, label) in enumerate(path_items):
            # Add a ">" separator between buttons
            if i > 0:
                ttk.Label(
                    self.breadcrumb_frame,
                    text=">",
                    foreground="gray"
                ).pack(side=tk.LEFT, padx=2)

            btn = ttk.Button(
                self.breadcrumb_frame,
                text=label,
                style='Breadcrumb.TButton',  # Optional: flatter button style
                command=lambda idx=original_id: self._on_breadcrumb_click(idx)
            )
            btn.pack(side=tk.LEFT)


    def _on_breadcrumb_click(self, item_id):
        # Select the clicked item
        self.db_tree.selection_set(item_id)
        self.db_tree.see(item_id)
        self.db_tree.focus(item_id)

        # Collapse all children of the clicked item
        children = self.db_tree.get_children(item_id)
        for child in children:
            self._collapse_all(child)

        # Optional: also collapse the clicked item itself (strict Nautilus behavior)
        # self.db_tree.item(item_id, open=False)


    def _collapse_all(self, item_id):
        """Recursively collapses all child nodes."""
        self.db_tree.item(item_id, open=False)
        for child in self.db_tree.get_children(item_id):
            self._collapse_all(child)


class SQLQueryEditorPanel:
    def __init__(self, query_result_panel, db_connection, query_manager):
        self.query_result_panel = query_result_panel
        self.db_connection = db_connection
        self.query_manager = query_manager
        self.tab_results = {}  # Store results for each tab

    def setup(self, parent, root, theme):
        """Panel 2: SQL Query Editor with tabs"""
        self.parent = parent
        self.root = root
        self.theme = theme

        self.sql_files = {}
        self.tab_counter = 0

        editor_frame = ttk.Frame(self.parent, style='TFrame')
        self.parent.add(editor_frame, weight=1)

        ttk.Label(editor_frame, text="Query Editor", style='Bold.TLabel').pack(fill=tk.X, padx=5, pady=2)

        # SQL Helper Buttons Frame
        sql_helper_frame = ttk.Frame(editor_frame, style='TFrame')
        sql_helper_frame.pack(fill=tk.X, padx=5, pady=2)

        # Add SQL helper buttons
        self.add_sql_helper_buttons(sql_helper_frame)

        toolbar = ttk.Frame(editor_frame, style='TFrame')
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="New", command=self.new_sql_tab, style='TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open", command=self.open_sql_file, style='TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save", command=self.save_current_sql, style='TButton').pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Execute (F5)", command=self.execute, style='TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Execute Selection", command=self.execute_selection, style='TButton').pack(side=tk.LEFT, padx=2)

        self.sql_notebook = ttk.Notebook(editor_frame, style='TNotebook')
        self.sql_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.new_sql_tab()

        self.root.bind('<Control-n>', lambda e: self.new_sql_tab())
        self.root.bind('<Control-s>', lambda e: self.save_current_sql())
        self.root.bind('<F5>', lambda e: self.execute())

        self.sql_notebook.bind('<Button-2>', self.close_current_tab)
        self.sql_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        """Handle tab change event to display the corresponding result"""
        tab_id, info = self.get_current_sql_tab()
        if tab_id and tab_id in self.tab_results:
            result_data = self.tab_results[tab_id]
            if result_data["type"] == "results":
                self.query_result_panel.display_results(
                    result_data["columns"],
                    result_data["rows"],
                    result_data["description"]
                )
            elif result_data["type"] == "message":
                self.query_result_panel.display_message(result_data["message"])
            elif result_data["type"] == "error":
                self.query_result_panel.display_error(result_data["error"])

    def add_sql_helper_buttons(self, parent_frame):
        """Add buttons for inserting common SQL clauses"""
        # Frame for limit buttons
        limit_frame = ttk.Frame(parent_frame, style='TFrame')
        limit_frame.pack(side=tk.LEFT, padx=2)

        ttk.Label(limit_frame, text="Limit:", style='TLabel').pack(side=tk.LEFT)

        # Create buttons for different limit values
        limit_values = [10, 50, 100, 500, 1000]
        for limit in limit_values:
            btn = ttk.Button(
                limit_frame,
                text=str(limit),
                command=lambda l=limit: self.insert_limit_clause(l),
                style='SQLHelper.TButton',
                width=4
            )
            btn.pack(side=tk.LEFT, padx=1)

        # Frame for other SQL helpers
        helper_frame = ttk.Frame(parent_frame, style='TFrame')
        helper_frame.pack(side=tk.LEFT, padx=10)

        ttk.Button(
            helper_frame,
            text="ORDER BY",
            command=lambda: self.insert_at_cursor("ORDER BY "),
            style='SQLHelper.TButton'
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            helper_frame,
            text="GROUP BY",
            command=lambda: self.insert_at_cursor("GROUP BY "),
            style='SQLHelper.TButton'
        ).pack(side=tk.LEFT, padx=2)

    def insert_limit_clause(self, limit):
        """Insert the appropriate LIMIT clause based on database type"""
        if not self.db_connection.current_connection:
            messagebox.showwarning("Not Connected", "Please connect to a database first")
            return

        # Get the current connection type
        conn_type = self.get_connection_type()

        if conn_type == "Oracle" or conn_type == "OracleDB":
            clause = f"FETCH FIRST {limit} ROWS ONLY"
        elif conn_type == "PostgreSQL":
            clause = f"LIMIT {limit}"
        elif conn_type == "SQLite":
            clause = f"LIMIT {limit}"
        else:
            clause = f"LIMIT {limit}"  # Default to standard SQL

        self.insert_at_cursor(clause)

    def get_connection_type(self):
        """Get the type of the current database connection"""
        return self.db_connection.get_connection_type()

    def insert_at_cursor(self, text):
        """Insert text at the current cursor position in the active editor"""
        tab_id, info = self.get_current_sql_tab()
        if not info:
            return

        widget = info["widget"]
        widget.insert(tk.INSERT, text)
        widget.see(tk.INSERT)  # Scroll to make the insertion point visible
        widget.focus_set()     # Set focus back to the editor

    def display_error(self, error: str):
        """Display error in result panel"""
        self.query_result_panel.display_error(error)

    def _create_result_tab(self, title, columns, rows):
        """Helper: Create a result tab with a treeview."""
        frame = ttk.Frame(self.sql_notebook, style='TFrame')
        tree_container = ttk.Frame(frame, style='TFrame')
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tree = Helper.create_treeview_with_scrollbars(tree_container, columns, 'tree headings')

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

        # Create close button with consistent positioning
        close_button = ttk.Button(
            frame,
            text='×',
            command=lambda: self.close_result_tab(frame),
            style='Close.TButton',
            width=2
        )
        close_button.place(relx=1.0, rely=0, anchor='ne', x=-23, y=8)

        self.sql_notebook.add(frame, text=title)
        self.sql_notebook.select(frame)

        return tree

    def _create_context_menu(self, tree, copy_command, export_command):
        """Helper: Create a context menu for a treeview."""
        commands = [
            ("Copy Selected", copy_command),
            ("Export to CSV", export_command)
        ]
        context_menu = Helper.create_context_menu(tree, commands)
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
            queries = self.get_queries_instance()

            cursor = self.query_manager.cursor_execute(queries.get_table_keys(schema, table), cursor)
            raw_rows = cursor.fetchall()
            cursor.close()

            if not raw_rows:
                messagebox.showinfo("Info", f"No keys found for {table}.")
                return

            columns = ["Key name", "Key Type", "Column name", "Ref. Schema", "Ref. Table", "Ref. Constraint"]
            # Replace None with "" so the Treeview never shows "None"
            rows = [tuple("" if v is None else v for v in row) for row in raw_rows]

            tree = self._create_result_tab(f"{table} (Keys)", columns, rows)

            context_menu = self._create_context_menu(
                tree,
                lambda: self._copy_selected_rows(tree),
                lambda: self._export_to_csv(tree, f"{table}_keys")
            )
            tree.bind("<Button-3>", lambda event: context_menu.post(event.x_root, event.y_root))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load table keys: {str(e)}")

    # Update the show_table_structure method in SQLQueryEditorPanel
    def show_table_structure(self, schema: str, table: str):
        """Fetch and display table or view structure in a new tab."""
        try:
            cursor = self.db_connection.current_connection.cursor()
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_table_structure(schema, table), cursor)
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

    def get_queries_instance(self):
        return self.db_connection.get_queries_instance(self.db_connection.current_connection)

    # Update the show_table_indexes method in SQLQueryEditorPanel
    def show_table_indexes(self, schema: str, table: str, index_name: str | None = None):
        """Fetch and display table indexes in a new tab."""
        try:
            cursor = self.db_connection.current_connection.cursor()
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_table_indexes(schema, table), cursor)
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

        # Create a frame to hold both the text widget and close button
        main_frame = ttk.Frame(self.sql_notebook, style='TFrame')

        # Create a container frame for the close button and text widget
        content_frame = ttk.Frame(main_frame, style='TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)

        text_scroll = ttk.Scrollbar(content_frame, style='TScrollbar')
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = SQLText(
            content_frame,
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

        # Add close button to the main frame (not content frame)
        close_btn = ttk.Button(
            main_frame,
            text='×',
            command=lambda: self.close_tab(tab_id),
            style='Close.TButton',
            width=2
        )
        close_btn.place(relx=1.0, rely=0, anchor='ne', x=-17, y=2)

        self.sql_notebook.add(main_frame, text=f"Untitled {self.tab_counter}")
        self.sql_notebook.select(main_frame)

        self.sql_files[tab_id] = {
            "path": None,
            "modified": False,
            "widget": text_widget,
            "frame": main_frame,
            "content_frame": content_frame
        }

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
        # Get the tab index that was clicked on
        tab_index = self.sql_notebook.index("@%d,%d" % (event.x, event.y))

        if tab_index == "none":
            return

        # Get the tab ID from the index
        tab_id = self.sql_notebook.tabs()[int(tab_index)]

        # Find the tab in our sql_files dictionary
        for tid, info in self.sql_files.items():
            if str(info["frame"]) == str(tab_id):
                self.close_tab(tid)
                return

        # If it's a result tab (not in sql_files), just close it
        self.sql_notebook.forget(tab_id)

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
        """Open SQL file(s)"""
        filepaths = filedialog.askopenfilenames(
            title="Open SQL File(s)",
            filetypes=[("SQL Files", "*.sql"), ("All Files", "*.*")]
        )

        if not filepaths:
            return

        for filepath in filepaths:
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
                messagebox.showerror("Error", f"Failed to open file {filepath}: {str(e)}")


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

    def execute(self):
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
        result = self.query_manager.execute_query(sql)

        # Get current tab
        tab_id, info = self.get_current_sql_tab()
        if not tab_id:
            return

        if result["success"]:
            if "columns" in result:
                # Store the result for this tab
                self.tab_results[tab_id] = {
                    "type": "results",
                    "columns": result["columns"],
                    "rows": result["rows"],
                    "description": result["description"]
                }
                self.query_result_panel.display_results(
                    result["columns"],
                    result["rows"],
                    result["description"],
                )
            else:
                # Store the message for this tab
                self.tab_results[tab_id] = {
                    "type": "message",
                    "message": result["message"]
                }
                self.query_result_panel.display_message(result["message"])
        else:
            # Store the error for this tab
            self.tab_results[tab_id] = {
                "type": "error",
                "error": result["error"]
            }
            self.query_result_panel.display_error(result["error"])

    def close_tab(self, tab_id):
        """Close the specified tab"""
        if tab_id in self.sql_files:
            if self.sql_files[tab_id]["modified"]:
                if not messagebox.askyesno("Unsaved Changes", "This file has unsaved changes. Close anyway?"):
                    return
            self.sql_notebook.forget(self.sql_files[tab_id]["frame"])
            del self.sql_files[tab_id]

            # Remove the result for this tab
            if tab_id in self.tab_results:
                del self.tab_results[tab_id]

            # Clear the result panel if this was the current tab
            current_tab = self.sql_notebook.select()
            if not current_tab:
                self.query_result_panel.display_message("No query results to display")

    def display_message(self, message: str):
        """Display message in result panel"""
        self.query_result_panel.display_message(message)

class QueryResultPanel:
    def __init__(self, root, db_connection):
        self.root = root
        self.db_connection = db_connection
        self.current_codepage = 'utf-8'

        # ── Sort state ────────────────────────────────────────────────
        self._sort_col     = None
        self._sort_reverse = False

        # ── Data store (original, unformatted rows) ───────────────────
        self._all_rows            = []
        self._all_unique_columns  = []

        # ── Search state ──────────────────────────────────────────────
        self._search_col_vars = {}          # col_name → BooleanVar
        self._search_var      = None        # StringVar for the search entry
        self._select_all_var  = None        # BooleanVar for the "All" checkbox
        self._regex_var       = None

        # ── UI references (populated in setup) ───────────────────────
        self._match_info      = None
        self._clear_sort_btn  = None
        self._cb_canvas       = None
        self._cb_inner        = None
        self._cb_window       = None

        # ── Misc ──────────────────────────────────────────────────────
        self.raw_error_text   = None

    # ─────────────────────────────────────────────────────────────────
    # SETUP
    # ─────────────────────────────────────────────────────────────────

    def setup(self, parent, config):
        """Panel 3: Query Result Grid"""
        self.parent = parent
        self.config = config

        result_frame = ttk.Frame(self.parent, style='TFrame')
        self.parent.add(result_frame, weight=1)

        # ── Header ───────────────────────────────────────────────────
        header = ttk.Frame(result_frame, style='TFrame')
        header.pack(fill=tk.X, padx=5, pady=(5, 2))
        ttk.Label(header, text="Query Result", style='Bold.TLabel').pack(side=tk.LEFT)

        # ── Search / Filter block ─────────────────────────────────────
        search_outer = ttk.Frame(result_frame, style='TFrame')
        search_outer.pack(fill=tk.X, padx=5, pady=(0, 3))

        # Row 1 ‒ input + action buttons
        search_row = ttk.Frame(search_outer, style='TFrame')
        search_row.pack(fill=tk.X)

        ttk.Label(search_row, text="Search:", style='TLabel').pack(side=tk.LEFT, padx=(0, 4))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_search())
        ttk.Entry(search_row, textvariable=self._search_var, width=28).pack(side=tk.LEFT)

        self._regex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            search_row,
            text="Regex",
            variable=self._regex_var,
            command=self._apply_search,
            style='TCheckbutton'
        ).pack(side=tk.LEFT, padx=(2, 4))

        ttk.Button(
            search_row, text="✕",
            command=self._clear_search,
            style='TButton', width=2
        ).pack(side=tk.LEFT, padx=(2, 10))

        self._match_info = ttk.Label(search_row, text="", style='TLabel')
        self._match_info.pack(side=tk.LEFT, padx=(0, 12))

        self._clear_sort_btn = ttk.Button(
            search_row, text="⊗ Clear Sort",
            command=self._clear_sort,
            style='TButton',
            state='disabled'
        )
        self._clear_sort_btn.pack(side=tk.LEFT)

        # Row 2 ‒ per-column checkboxes (horizontal-scrollable)
        cb_container = ttk.Frame(search_outer, style='TFrame')
        cb_container.pack(fill=tk.X, pady=(3, 0))

        ttk.Label(cb_container, text="In:", style='TLabel').pack(side=tk.LEFT, padx=(0, 3))

        self._select_all_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            cb_container, text="All",
            variable=self._select_all_var,
            command=self._on_select_all_toggle
        ).pack(side=tk.LEFT, padx=(0, 2))

        ttk.Separator(cb_container, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=2
        )

        # Canvas + horizontal scrollbar for many columns
        canvas_wrapper = ttk.Frame(cb_container, style='TFrame')
        canvas_wrapper.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._cb_canvas = tk.Canvas(canvas_wrapper, height=26, highlightthickness=0)
        self._cb_canvas.pack(fill=tk.X, expand=True)

        cb_hscroll = ttk.Scrollbar(
            canvas_wrapper, orient=tk.HORIZONTAL,
            command=self._cb_canvas.xview,
            style='TScrollbar'
        )
        cb_hscroll.pack(fill=tk.X)
        self._cb_canvas.configure(xscrollcommand=cb_hscroll.set)

        self._cb_inner  = ttk.Frame(self._cb_canvas, style='TFrame')
        self._cb_window = self._cb_canvas.create_window((0, 0), window=self._cb_inner, anchor='nw')

        self._cb_inner.bind("<Configure>",  self._on_cb_frame_configure)
        self._cb_canvas.bind("<Configure>", self._on_cb_canvas_configure)

        # Sync canvas background with TFrame theme colour
        try:
            bg = ttk.Style().lookup('TFrame', 'background')
            if bg:
                self._cb_canvas.configure(bg=bg)
        except Exception:
            pass

        # ── Result grid ───────────────────────────────────────────────
        grid_container = ttk.Frame(result_frame, style='TFrame')
        grid_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.result_tree = Helper.create_treeview_with_scrollbars(
            grid_container, show='tree headings'
        )

        # Tag used to highlight matching rows
        self.result_tree.tag_configure('match', background='#fffacd')   # lemon-chiffon

        self.result_tree.bind("<Shift-MouseWheel>", self.on_shift_mousewheel)

        self.result_info = ttk.Label(result_frame, text="", style='TLabel', anchor=tk.W)
        self.result_info.pack(fill=tk.X, padx=5, pady=2)

        commands = [
            ("Copy Selected",       self.copy_selected_rows),
            ("Export to CSV",       self.export_to_csv),
            ("Reset Column Widths", self.reset_column_widths),
        ]
        self.result_context_menu = Helper.create_context_menu(self.result_tree, commands)

        self.result_tree.bind("<Button-3>",   self.show_result_context_menu)
        self.result_tree.bind("<Configure>",  self.on_tree_configure)

    # ─────────────────────────────────────────────────────────────────
    # CANVAS / CHECKBOX HELPERS
    # ─────────────────────────────────────────────────────────────────

    def _on_cb_frame_configure(self, event):
        self._cb_canvas.configure(scrollregion=self._cb_canvas.bbox("all"))

    def _on_cb_canvas_configure(self, event):
        # Keep the embedded frame's height in sync with the canvas
        self._cb_canvas.itemconfig(self._cb_window, height=event.height)

    def _rebuild_search_checkboxes(self):
        """Destroy old per-column checkboxes and create fresh ones."""
        for w in self._cb_inner.winfo_children():
            w.destroy()
        self._search_col_vars.clear()

        for col in self._all_unique_columns:
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                self._cb_inner,
                text=col,
                variable=var,
                command=self._on_col_checkbox_change
            ).pack(side=tk.LEFT, padx=2)
            self._search_col_vars[col] = var

        self._select_all_var.set(True)
        self._cb_inner.update_idletasks()
        self._cb_canvas.configure(scrollregion=self._cb_canvas.bbox("all"))

    # ─────────────────────────────────────────────────────────────────
    # CHECKBOX CALLBACKS
    # ─────────────────────────────────────────────────────────────────

    def _on_col_checkbox_change(self):
        """Called when any individual column checkbox is toggled."""
        all_on = all(v.get() for v in self._search_col_vars.values())
        self._select_all_var.set(all_on)
        self._apply_search()

    def _on_select_all_toggle(self):
        """Set every column checkbox to match the 'All' toggle."""
        state = self._select_all_var.get()
        for var in self._search_col_vars.values():
            var.set(state)
        self._apply_search()

    # ─────────────────────────────────────────────────────────────────
    # SEARCH
    # ─────────────────────────────────────────────────────────────────

    def _apply_search(self):
        self._refresh_display()

    def _clear_search(self):
        """Clear the search entry (triggers trace → _refresh_display)."""
        self._search_var.set("")

    # ─────────────────────────────────────────────────────────────────
    # SORT
    # ─────────────────────────────────────────────────────────────────

    def _sort_by_column(self, col):
        """Toggle sort direction on *col*; ascending on first click."""
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col     = col
            self._sort_reverse = False

        # Refresh all column headings
        for c in self._all_unique_columns:
            if c == self._sort_col:
                arrow = " ▼" if self._sort_reverse else " ▲"
                self.result_tree.heading(c, text=c + arrow)
            else:
                self.result_tree.heading(c, text=c)

        self._clear_sort_btn.config(state='normal')
        self._refresh_display()

    def _clear_sort(self):
        """Remove the active sort and restore original order."""
        self._sort_col     = None
        self._sort_reverse = False

        for c in self._all_unique_columns:
            self.result_tree.heading(c, text=c)

        self._clear_sort_btn.config(state='disabled')
        self._refresh_display()

    # ─────────────────────────────────────────────────────────────────
    # CORE RENDER PIPELINE  (filter → sort → display)
    # ─────────────────────────────────────────────────────────────────
    def _refresh_display(self):
        if not self._all_unique_columns:
            return

        search_term = self._search_var.get().strip()
        use_regex = self._regex_var.get() if self._regex_var else False

        # Indices of columns included in the search
        if self._search_col_vars:
            search_indices = [
                self._all_unique_columns.index(c)
                for c, v in self._search_col_vars.items()
                if v.get() and c in self._all_unique_columns
            ]
        else:
            search_indices = list(range(len(self._all_unique_columns)))

        # ── 1. Filter ────────────────────────────────────────────────
        pattern = None
        if search_term and search_indices:
            try:
                if use_regex:
                    # Compile regex pattern (case-insensitive)
                    pattern = re.compile(search_term, re.IGNORECASE)
                    filtered = [
                        row for row in self._all_rows
                        if any(
                            pattern.search(str(row[i] if i < len(row) else ''))
                            for i in search_indices
                        )
                    ]
                else:
                    # Standard substring search (case-insensitive)
                    filtered = [
                        row for row in self._all_rows
                        if any(
                            search_term.lower() in str(row[i] if i < len(row) else '').lower()
                            for i in search_indices
                        )
                    ]
            except re.error as e:
                # Handle invalid regex (e.g., unbalanced parentheses)
                filtered = []
                self._match_info.config(
                    text=f"Regex error: {str(e)}",
                    foreground='#cc4400'
                )
        else:
            filtered = list(self._all_rows)

        # ── 2. Sort ──────────────────────────────────────────────────
        if self._sort_col and self._sort_col in self._all_unique_columns:
            col_idx = self._all_unique_columns.index(self._sort_col)

            def _key(row):
                val = row[col_idx] if col_idx < len(row) else None
                if val is None:
                    return (2, 0.0, '')
                s = str(val)
                try:
                    return (0, float(s.replace(' ', '').replace(',', '.')), '')
                except ValueError:
                    return (1, 0.0, s.lower())

            filtered.sort(key=_key, reverse=self._sort_reverse)

        # ── 3. Render ────────────────────────────────────────────────
        self.result_tree.delete(*self.result_tree.get_children())

        for row in filtered:
            formatted = []
            for i, v in enumerate(row):
                # Standard string conversion
                if v is None:
                    val_str = ''
                elif isinstance(v, (datetime.datetime, datetime.date)):
                    val_str = str(v)
                else:
                    val_str = str(v)

                # --- UPDATED CELL-SPECIFIC HIGHLIGHT LOGIC ---
                if search_term and i in search_indices:
                    if use_regex:
                        # Use the compiled regex pattern for highlighting
                        if pattern and pattern.search(val_str):
                            formatted.append(f"▶ {val_str}")
                        else:
                            formatted.append(val_str)
                    else:
                        # Standard substring search for highlighting
                        if search_term.lower() in val_str.lower():
                            formatted.append(f"▶ {val_str}")
                        else:
                            formatted.append(val_str)
                else:
                    formatted.append(val_str)

            self.result_tree.insert('', 'end', values=formatted)

        # ── 4. Update info labels ────────────────────────────────────
        total = len(self._all_rows)
        shown = len(filtered)

        if search_term:
            if shown == 0:
                self._match_info.config(text="No matches", foreground='#cc4400')
            else:
                self._match_info.config(
                    text=f"{shown} match{'es' if shown != 1 else ''}",
                    foreground='#227722'
                )
            self.result_info.config(text=f"{shown}/{total} row(s) shown")
        else:
            if self._match_info:
                self._match_info.config(text="")
            self.result_info.config(text=f"{total} row(s) displayed")

        self.update_column_widths()

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC DISPLAY METHODS
    # ─────────────────────────────────────────────────────────────────

    def display_results(self, columns: List[str], rows: List[Tuple], description):
        """Display query results in the grid with sorting and search enabled."""
        self.result_tree.delete(*self.result_tree.get_children())

        # ── Deduplicate column names ──────────────────────────────────
        column_counts = {}
        unique_columns = []

        for col in columns:
            if col in column_counts:
                column_counts[col] += 1
                unique_columns.append(f"{col} (#{column_counts[col]})")
            else:
                column_counts[col] = 1
                unique_columns.append(col)

        # Number the first occurrence of any duplicated column name
        for i, col in enumerate(columns):
            if (column_counts[col] > 1
                    and not re.match(rf"{re.escape(col)} \(#\d+\)", unique_columns[i])):
                unique_columns[i] = f"{col} (#1)"

        # ── Store master data ─────────────────────────────────────────
        self._all_rows           = list(rows)
        self._all_unique_columns = unique_columns

        # ── Reset sort ────────────────────────────────────────────────
        self._sort_col     = None
        self._sort_reverse = False
        if self._clear_sort_btn:
            self._clear_sort_btn.config(state='disabled')

        # ── Configure treeview columns with sort-click handlers ───────
        self.result_tree['columns'] = unique_columns
        self.result_tree.column('#0', width=0, stretch=tk.NO)

        for col in unique_columns:
            self.result_tree.column(col, minwidth=100, width=150,
                                    stretch=tk.NO, anchor=tk.W)
            self.result_tree.heading(
                col, text=col, anchor=tk.W,
                command=lambda c=col: self._sort_by_column(c)
            )

        # ── Rebuild per-column search checkboxes ──────────────────────
        if self._cb_inner is not None:
            self._rebuild_search_checkboxes()

        # ── Clear previous search term and re-render ──────────────────
        # Setting the var triggers the trace which calls _refresh_display.
        # If it was already empty, force a direct refresh.
        if self._search_var:
            prev = self._search_var.get()
            self._search_var.set("")
            if prev == "":
                self._refresh_display()   # trace won't fire when value is unchanged
        else:
            self._refresh_display()

    def display_error(self, error: str):
        """Display error in the result panel (clears sort / search state)."""
        self._reset_state()

        match = re.search(r"\('(.*?)', '(.*?)'\)", str(error))
        if match:
            error_name = match.group(1)
            error_text = match.group(2)
            error_text = (error_text
                          .replace('\\x00', '')
                          .replace('\\n', '\n')
                          .replace('\\r', '\r'))
            error = f"{error_name}: {error_text}"
        else:
            error = str(error)

        self.raw_error_text = error

        self.result_tree.delete(*self.result_tree.get_children())
        self.result_tree['columns'] = ['Error']
        self.result_tree.column('#0', width=0, stretch=tk.NO)
        self.result_tree.column('Error', width=800)
        self.result_tree.heading('Error', text='SQL Error')
        self.result_tree.insert('', 'end', values=[error])

    def display_message(self, message: str):
        """Display a plain message in the result panel."""
        self._reset_state()

        self.result_tree.delete(*self.result_tree.get_children())
        self.result_tree['columns'] = ['Message']
        self.result_tree.column('#0', width=0, stretch=tk.NO)
        self.result_tree.column('Message', width=800)
        self.result_tree.heading('Message', text='Message')
        self.result_tree.insert('', 'end', values=[message])

    def _reset_state(self):
        """Clear all sort / search / data state (used by error & message displays)."""
        self._all_rows           = []
        self._all_unique_columns = []
        self._sort_col           = None
        self._sort_reverse       = False

        if self._clear_sort_btn:
            self._clear_sort_btn.config(state='disabled')
        if self._match_info:
            self._match_info.config(text="")
        if self._search_var:
            # Suppress the trace temporarily by using the underlying tk variable
            self._search_var.set("")
        if self._cb_inner is not None:
            self._rebuild_search_checkboxes()
        if hasattr(self, 'result_info'):
            self.result_info.config(text="")

    # ─────────────────────────────────────────────────────────────────
    # COLUMN WIDTHS
    # ─────────────────────────────────────────────────────────────────

    def update_column_widths(self):
        """Auto-size columns based on content (capped at 300 px)."""
        for col in self.result_tree['columns']:
            max_width = 0
            col_index = list(self.result_tree['columns']).index(col)
            for item in self.result_tree.get_children():
                cell_value = self.result_tree.item(item)['values'][col_index]
                text_width = len(str(cell_value)) * 8
                if text_width > max_width:
                    max_width = text_width
            width = min(max(max_width, 150), 300)
            self.result_tree.column(col, width=width)
        self.result_tree.update_idletasks()

    def reset_column_widths(self):
        """Reset all columns to 150 px."""
        for col in self.result_tree['columns']:
            self.result_tree.column(col, width=150)
        self.result_tree.update_idletasks()

    # ─────────────────────────────────────────────────────────────────
    # MISC / UNCHANGED METHODS
    # ─────────────────────────────────────────────────────────────────

    def on_shift_mousewheel(self, event):
        """Horizontal scroll with Shift+MouseWheel."""
        self.result_tree.xview_scroll(-1 * event.delta, "units")
        return "break"

    def on_tree_configure(self, event):
        pass

    def show_result_context_menu(self, event):
        self.result_context_menu.post(event.x_root, event.y_root)

    def copy_selected_rows(self):
        """Copy selected rows to clipboard (tab-separated)."""
        selected = self.result_tree.selection()
        if not selected:
            return
        lines = [
            '\t'.join(str(v) for v in self.result_tree.item(item)['values'])
            for item in selected
        ]
        self.root.clipboard_clear()
        self.root.clipboard_append('\n'.join(lines))
        self.root.update()

    def export_to_csv(self):
        """Export currently visible rows to a CSV file."""
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

class StatusBarPanel:
    def __init__(self, root, text, style):
        self.root = root
        self.status_bar = ttk.Label(self.root, text=text, style=style)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def set_status(self, new_status):
        self.status_bar.config(text=new_status)
