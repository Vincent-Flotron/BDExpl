from Panels import *


class PanelDatabaseTree:
    def __init__(self, parent, db_connection, panel_sql_query_editor, query_manager):
        self.parent = parent
        self.db_connection = db_connection
        self.panel_sql_query_editor = panel_sql_query_editor
        self.queries = None  # Will be set based on connection type
        self.query_manager = query_manager
        self.zoom_level = 100  # Default zoom level

    def setup(self):
        """Panel 1: Database object tree"""
        left_frame = ttk.Frame(self.parent, style='TFrame')
        self.parent.add(left_frame, weight=1)

        # Header with zoom controls
        header_frame = ttk.Frame(left_frame, style='TFrame')
        header_frame.pack(fill=tk.X, padx=4, pady=2)

        ttk.Label(left_frame, text="Database Objects", style='Bold.TLabel').pack(pady=5)

        # Zoom controls
        zoom_frame = ttk.Frame(header_frame, style='TFrame')
        zoom_frame.pack(side=tk.RIGHT, padx=5)

        self.zoom_label = ttk.Label(zoom_frame, text=f"{self.zoom_level}%", style='TLabel')
        self.zoom_label.pack(side=tk.RIGHT, padx=5)

        ttk.Button(zoom_frame, text="+", command=self.zoom_in, width=2).pack(side=tk.RIGHT, padx=2)
        ttk.Button(zoom_frame, text="-", command=self.zoom_out, width=2).pack(side=tk.RIGHT, padx=2)
        ttk.Button(zoom_frame, text="↻", command=self.reset_zoom, width=2).pack(side=tk.RIGHT, padx=2)


        # ── Search bar ────────────────────────────────────────────────
        search_frame = ttk.Frame(left_frame, style='TFrame')
        search_frame.pack(fill=tk.X, padx=4, pady=(0, 2))

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind("<Return>", self.search_in_tree)

        # "Everywhere" checkbox
        self.search_everywhere_var = tk.BooleanVar(value=False)
        in_every_schema_cb = ttk.Checkbutton(
            search_frame, text="In every schema",
            variable=self.search_everywhere_var,
            command=self._update_search_checkboxes_state
        )
        in_every_schema_cb.pack(side=tk.LEFT, padx=(4, 0))

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
                                          variable=self.search_tables_var, state='enabled')
        self._cb_views  = ttk.Checkbutton(type_frame, text="views",
                                          variable=self.search_views_var,  state='enabled')
        self._cb_procs  = ttk.Checkbutton(type_frame, text="procedures",
                                          variable=self.search_procedures_var, state='enabled')
        self._cb_funcs  = ttk.Checkbutton(type_frame, text="functions",
                                          variable=self.search_functions_var,  state='enabled')
        self._cb_pkgs   = ttk.Checkbutton(type_frame, text="packages",
                                          variable=self.search_packages_var,   state='enabled')

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
        self.breadcrumb_frame = ttk.Frame(left_frame, style='TFrame', height=32)
        self.breadcrumb_frame.pack(fill=tk.X, padx=4, pady=2)
        self.breadcrumb_frame.pack_propagate(False) # Prevent shrinking to fit children

        # Internal search state
        self._search_results       = []
        self._search_results_index = 0
        self._search_results_term  = ""

        # Treeview with scrollbars
        tree_container = ttk.Frame(left_frame, style='TFrame')
        tree_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.db_tree = Helper.create_treeview_with_scrollbars(tree_container)
        self.db_tree.configure(style='DBTree.Treeview')

        # Context menu for tables
        table_commands = [
            ("View first 100 rows",  lambda: self.view_table_data(100)),
            ("View first 1000 rows", lambda: self.view_table_data(1000)),
            ("-------------------------", None),
            ("View Structure",       lambda: self.panel_sql_query_editor.show_table_structure(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("View Indexes",         lambda: self.panel_sql_query_editor.show_table_indexes(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("View Keys",            lambda: self.panel_sql_query_editor.show_table_keys(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("-------------------------", None),
            ("Clone Table",          lambda: self.clone_table()),
            ("-------------------------", None),
            ("Count Records",        lambda: self.count_records()),
            ("-------------------------", None),
            ("Empty Table",          lambda: self.empty_table()),
            ("Delete Table",         lambda: self.delete_table())
        ]
        self.table_context_menu = Helper.create_context_menu(self.db_tree, table_commands)

        # Context menu for views
        view_commands = [
            ("View first 100 rows",  lambda: self.view_view_data(100)),
            ("View first 1000 rows", lambda: self.view_view_data(1000)),
            ("-------------------------", None),
            ("View Structure",       lambda: self.show_view_structure(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("View Query",           lambda: self.view_view_query(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("View Dependencies",    lambda: self.show_view_dependencies(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("View Comment",         lambda: self.show_view_comment(
                *self.db_tree.item(self.db_tree.selection()[0])['values'][0:3:2]
            )),
            ("-------------------------", None),
            ("Count Records",        lambda: self.count_records()),
            ("-------------------------", None),
            ("Delete View",          lambda: self.delete_view())
        ]
        self.view_context_menu = Helper.create_context_menu(self.db_tree, view_commands)

        self.db_tree.bind("<Button-3>",         self.show_tree_context_menu)
        self.db_tree.bind("<Double-1>",         lambda e: self.view_table_data(100))
        self.db_tree.bind("<<TreeviewOpen>>",   self.on_tree_expand)
        self.db_tree.bind("<<TreeviewSelect>>", lambda e: self._update_search_checkboxes_state())
        self.db_tree.bind("<<TreeviewSelect>>", self._update_breadcrumbs)



    def clone_table(self):
        """Clone the selected table with a unique name (_clone1, _clone2, etc.)"""
        selected = self.db_tree.selection()
        if not selected:
            return

        values = self.db_tree.item(selected[0])['values']
        if len(values) < 3 or values[1] != 'table':
            return

        schema         = values[0]
        original_table = values[2]
        queries        = self.get_queries_instance()

        # Generate unique name
        base_name = original_table
        counter   = 1
        new_table = f"{base_name}_clone{counter}"

        try:
            cursor = self.db_connection.current_connection.cursor()
            
            # Check if table exists, increment counter if so
            while True:
                cursor = self.query_manager.cursor_execute(queries.table_exists(schema, new_table), cursor)
                count  = cursor.fetchone()[0]
                if count == 0:
                    break
                counter += 1
                new_table = f"{base_name}_clone{counter}"

            # Execute clone SQL
            clone_sql = queries.get_clone_sql(schema, original_table, new_table)
            cursor    = self.query_manager.cursor_execute(clone_sql, cursor)
            self.db_connection.current_connection.commit()
            
            messagebox.showinfo("Success", f"Table '{original_table}' cloned to '{new_table}'")
            
            # Refresh tree
            self.load_database_objects()
            
            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clone table: {str(e)}")

    def count_records(self):
        """Count and display records for all selected tables or views, updating their tree nodes."""
        selected_items = self.db_tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select at least one table or view")
            return

        cursor = None
        try:
            cursor  = self.db_connection.current_connection.cursor()
            queries = self.get_queries_instance()
            
            # Track if we skipped any invalid selections to notify the user later
            invalid_selection_found = False

            for item in selected_items:
                values = self.db_tree.item(item)['values']
                if len(values) < 3:
                    continue
                    
                schema   = values[0]
                obj_type = values[1]
                obj_name = values[2]
                
                # Skip items that aren't tables or views
                if obj_type not in ('table', 'view'):
                    invalid_selection_found = True
                    continue

                # Get and execute the count SQL
                count_sql = queries.count_records_sql(schema, obj_name)
                cursor    = self.query_manager.cursor_execute(count_sql, cursor)
                result    = cursor.fetchone()
                count     = result[0] if result else 0

                # Update the tree node text to show the count
                current_text = self.db_tree.item(item)['text']
                new_text     = TextManip.update_spaced_line(current_text, f"{count:\u00A0>9,} rows".replace(",", "'"), 2, 28)
                self.db_tree.item(item, text=new_text)

            if invalid_selection_found:
                messagebox.showwarning("Invalid Selection", "Some selected items were skipped because they are not tables or views.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to count records: {str(e)}")
            
        finally:
            # Ensures the cursor is closed at the very end, regardless of success or exceptions
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass


    def empty_table(self):
        """Empty the selected table (remove all rows)."""
        selected = self.db_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a table to empty")
            return

        values = self.db_tree.item(selected[0])['values']
        if len(values) < 3 or values[1] != 'table':
            messagebox.showwarning("Not a Table", "Selected item is not a table")
            return

        schema = values[0]
        table_name = values[2]

        confirm = messagebox.askyesno(
            "Confirm Empty",
            f"Are you sure you want to permanently remove all rows from table '{table_name}' in schema '{schema}'?\n"
            "This action cannot be undone."
        )

        if not confirm:
            return

        try:
            cursor = self.db_connection.current_connection.cursor()
            queries = self.get_queries_instance()

            # Get the empty SQL
            empty_sql = queries.empty_table_sql(schema, table_name)

            # Execute the empty SQL through QueryManager
            self.query_manager.cursor_execute(empty_sql, cursor)

            # Commit the transaction
            self.db_connection.current_connection.commit()
            messagebox.showinfo("Success", f"Table '{table_name}' emptied successfully")

            # Refresh the tree (optional, but good practice to update counts if displayed)
            self.load_database_objects()

            cursor.close()

        except Exception as e:
            self.db_connection.current_connection.rollback()
            messagebox.showerror("Error", f"Failed to empty table: {str(e)}")


    def delete_table(self):
        """Delete the selected table."""
        selected = self.db_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a table to delete")
            return

        values = self.db_tree.item(selected[0])['values']
        if len(values) < 3 or values[1] != 'table':
            messagebox.showwarning("Not a Table", "Selected item is not a table")
            return

        schema = values[0]
        table_name = values[2]

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to permanently delete table '{table_name}' in schema '{schema}'?\n"
            "This action cannot be undone."
        )

        if not confirm:
            return

        try:
            cursor = self.db_connection.current_connection.cursor()
            queries = self.get_queries_instance()

            # Get the delete SQL
            delete_sql = queries.delete_table_sql(schema, table_name)

            # Execute the delete SQL through QueryManager
            self.query_manager.cursor_execute(delete_sql, cursor)

            # Commit the transaction
            self.db_connection.current_connection.commit()
            messagebox.showinfo("Success", f"Table '{table_name}' deleted successfully")

            # Refresh the tree
            self.load_database_objects()

            cursor.close()

        except Exception as e:
            self.db_connection.current_connection.rollback()
            messagebox.showerror("Error", f"Failed to delete table: {str(e)}")


    def delete_view(self):
        """Delete the selected view."""
        selected = self.db_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a view to delete")
            return

        values = self.db_tree.item(selected[0])['values']
        if len(values) < 3 or values[1] != 'view':
            messagebox.showwarning("Not a View", "Selected item is not a view")
            return

        schema = values[0]
        view_name = values[2]

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to permanently delete view '{view_name}' in schema '{schema}'?\n"
            "This action cannot be undone."
        )

        if not confirm:
            return

        try:
            cursor = self.db_connection.current_connection.cursor()
            queries = self.get_queries_instance()

            # Get the delete SQL
            delete_sql = queries.delete_view_sql(schema, view_name)

            # Execute the delete SQL through QueryManager
            self.query_manager.cursor_execute(delete_sql, cursor)

            # Commit the transaction
            self.db_connection.current_connection.commit()
            messagebox.showinfo("Success", f"View '{view_name}' deleted successfully")

            # Refresh the tree
            self.load_database_objects()

            cursor.close()

        except Exception as e:
            self.db_connection.current_connection.rollback()
            messagebox.showerror("Error", f"Failed to delete view: {str(e)}")


    def zoom_in(self):
        """Increase the zoom level."""
        self.zoom_level = min(200, self.zoom_level + 10)
        self._apply_zoom()
        self.zoom_label.config(text=f"{self.zoom_level}%")

    def zoom_out(self):
        """Decrease the zoom level."""
        self.zoom_level = max(50, self.zoom_level - 10)
        self._apply_zoom()
        self.zoom_label.config(text=f"{self.zoom_level}%")

    def reset_zoom(self):
        """Reset the zoom level to default."""
        self.zoom_level = 100
        self._apply_zoom()
        self.zoom_label.config(text=f"{self.zoom_level}%")

    def _apply_zoom(self):
        """Apply the current zoom level to the treeview."""
        font_size = int(9 * (self.zoom_level / 100))  # Base size is 9
        row_height = font_size + 12  # Dynamically scale row height
        
        style = ttk.Style()
        style.configure('DBTree.Treeview', font=('Helvetica', font_size), rowheight=row_height)
        style.configure('DBTree.Treeview.Heading', font=('Helvetica', font_size, 'bold'))

    def set_zoom(self, zoom_level):
        """Set the zoom level."""
        self.zoom_level = max(50, min(200, zoom_level))
        self._apply_zoom()
        self.zoom_label.config(text=f"{self.zoom_level}%")

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
            sql = self.get_first_x_rows(schema, table_or_view, limit)

            tab_id = self.panel_sql_query_editor.new_sql_tab()
            self.panel_sql_query_editor.set_text_without_undo(
                self.panel_sql_query_editor.sql_files[tab_id]["widget"],
                sql
            )
            self.panel_sql_query_editor.sql_files[tab_id]["modified"] = False

            tab_name = f"{table_or_view} ({limit} rows)"
            self.panel_sql_query_editor.sql_notebook.tab(
                self.panel_sql_query_editor.sql_files[tab_id]["frame"],
                text=tab_name
            )
            self.panel_sql_query_editor.run_query(sql)

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

            tree = self.panel_sql_query_editor._create_result_tab(f"{view} (Dependencies)", columns, rows)

            context_menu = self.panel_sql_query_editor._create_context_menu(
                tree,
                lambda: self.panel_sql_query_editor._copy_selected_rows(tree),
                lambda: self.panel_sql_query_editor._export_to_csv(tree, f"{view}_dependencies")
            )
            tree.bind("<Button-3>", lambda event: context_menu.tk_popup(event.x_root, event.y_root))

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

                tab_id = self.panel_sql_query_editor.new_sql_tab()
                self.panel_sql_query_editor.set_text_without_undo(
                    self.panel_sql_query_editor.sql_files[tab_id]["widget"],
                    view_body
                )
                self.panel_sql_query_editor.sql_files[tab_id]["modified"] = False
                tab_name = f"{view_name} (View)"
                self.panel_sql_query_editor.sql_notebook.tab(
                    self.panel_sql_query_editor.sql_files[tab_id]["frame"],
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

            tree = self.panel_sql_query_editor._create_result_tab(f"{view} (Structure)", columns, rows)

            context_menu = self.panel_sql_query_editor._create_context_menu(
                tree,
                lambda: self.panel_sql_query_editor._copy_selected_rows(tree),
                lambda: self.panel_sql_query_editor._export_to_csv(tree, f"{view}_structure")
            )
            tree.bind("<Button-3>", lambda event: context_menu.tk_popup(event.x_root, event.y_root))

            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load view structure: {str(e)}")


    def show_tree_context_menu(self, event):
        clicked_item = self.db_tree.identify_row(event.y)
        if not clicked_item:
            return

        slected_items = self.db_tree.selection()
        # Only reset selection if the right-clicked clicked_item isn't already selected
        if clicked_item not in self.db_tree.selection():
            self.db_tree.selection_set(clicked_item)

        values = self.db_tree.item(clicked_item)['values']

        if not values:
            return

        obj_type = values[1]

        selection_contains_same_types = True
        last_item_type  = None
        for item in slected_items:
            item_type = self.db_tree.item(clicked_item)['values'][1]
            if    last_item_type \
              and item_type != last_item_type:
                selection_contains_same_types = False


        if selection_contains_same_types:
            try:
                # -------------------------------
                # TABLES & VIEWS
                # -------------------------------
                if obj_type == 'table':
                    self.table_context_menu.tk_popup(event.x_root, event.y_root)

                elif obj_type == 'view':
                    self.view_context_menu.tk_popup(event.x_root, event.y_root)

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
                    package_name = self.db_tree.item(self.db_tree.parent(clicked_item))['text']
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
        else:
            messagebox.showerror("Error", "please select same types")


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
                tab_id = self.panel_sql_query_editor.new_sql_tab()
                self.panel_sql_query_editor.set_text_without_undo(
                    self.panel_sql_query_editor.sql_files[tab_id]["widget"],
                    comment
                )
                self.panel_sql_query_editor.sql_files[tab_id]["modified"] = False
                tab_name = f"{view} (Comment)"
                self.panel_sql_query_editor.sql_notebook.tab(
                    self.panel_sql_query_editor.sql_files[tab_id]["frame"],
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

                tab_id = self.panel_sql_query_editor.new_sql_tab()
                self.panel_sql_query_editor.set_text_without_undo(
                    self.panel_sql_query_editor.sql_files[tab_id]["widget"],
                    view_query
                )
                self.panel_sql_query_editor.sql_files[tab_id]["modified"] = False
                tab_name = f"{view} (Query)"
                self.panel_sql_query_editor.sql_notebook.tab(
                    self.panel_sql_query_editor.sql_files[tab_id]["frame"],
                    text=tab_name
                )
            else:
                messagebox.showinfo("Info", f"No query found for view {view}.")
        except Exception as e:
            # Passer l'erreur brute au panneau de résultats
            self.panel_sql_query_editor.display_message(str(e))


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
            sql = self.get_first_x_rows(schema, view, limit)


            tab_id = self.panel_sql_query_editor.new_sql_tab()
            self.panel_sql_query_editor.set_text_without_undo(
                self.panel_sql_query_editor.sql_files[tab_id]["widget"],
                sql
            )
            self.panel_sql_query_editor.sql_files[tab_id]["modified"] = False

            tab_name = f"{view} ({limit} rows)"
            self.panel_sql_query_editor.sql_notebook.tab(
                self.panel_sql_query_editor.sql_files[tab_id]["frame"],
                text=tab_name
            )
            self.panel_sql_query_editor.run_query(sql)

    def get_first_x_rows(self, schema, table_or_view, limit):
        queries = self.get_queries_instance()
        query_get_col_names = queries.get_col_names(schema, table_or_view)
        result = self.query_manager.execute_query(query_get_col_names)
        if result['success'] == True:
            col_names = queries.extract_col_names(result['rows'])
            return queries.get_first_x_rows(schema, table_or_view, limit, col_names)
        else:
            raise Exception(f"No columns found for table or view: {schema}.{table_or_view} !")
        

    def view_trigger_content(self, schema: str, trigger_name: str):
        """View content of selected trigger in Query Editor"""
        try:
            cursor = self.db_connection.current_connection.cursor()
            queries = self.get_queries_instance()
            cursor = self.query_manager.cursor_execute(queries.get_trigger_body(schema, trigger_name), cursor)
            result = cursor.fetchone()
            cursor.close()

            if result:
                tab_id = self.panel_sql_query_editor.new_sql_tab()
                self.panel_sql_query_editor.set_text_without_undo(
                    self.panel_sql_query_editor.sql_files[tab_id]["widget"],
                    result[0]
                )
                self.panel_sql_query_editor.sql_files[tab_id]["modified"] = False
                tab_name = f"{trigger_name} (Trigger)"
                self.panel_sql_query_editor.sql_notebook.tab(
                    self.panel_sql_query_editor.sql_files[tab_id]["frame"],
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

                tab_id = self.panel_sql_query_editor.new_sql_tab()
                self.panel_sql_query_editor.set_text_without_undo(
                    self.panel_sql_query_editor.sql_files[tab_id]["widget"],
                    procedure_body
                )
                self.panel_sql_query_editor.sql_files[tab_id]["modified"] = False
                tab_name = f"{procedure_name} (Procedure)"
                self.panel_sql_query_editor.sql_notebook.tab(
                    self.panel_sql_query_editor.sql_files[tab_id]["frame"],
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

                tab_id = self.panel_sql_query_editor.new_sql_tab()
                self.panel_sql_query_editor.set_text_without_undo(
                    self.panel_sql_query_editor.sql_files[tab_id]["widget"],
                    function_body
                )
                self.panel_sql_query_editor.sql_files[tab_id]["modified"] = False
                tab_name = f"{function_name} (Function)"
                self.panel_sql_query_editor.sql_notebook.tab(
                    self.panel_sql_query_editor.sql_files[tab_id]["frame"],
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

            tab_id = self.panel_sql_query_editor.new_sql_tab()
            self.panel_sql_query_editor.set_text_without_undo(
                self.panel_sql_query_editor.sql_files[tab_id]["widget"],
                package_source
            )

            self.panel_sql_query_editor.sql_files[tab_id]["modified"] = False

            self.panel_sql_query_editor.sql_notebook.tab(
                self.panel_sql_query_editor.sql_files[tab_id]["frame"],
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
            tab_id = self.panel_sql_query_editor.new_sql_tab()
            self.panel_sql_query_editor.set_text_without_undo(
                self.panel_sql_query_editor.sql_files[tab_id]["widget"],
                procedure_body
            )

            self.panel_sql_query_editor.sql_files[tab_id]["modified"] = False

            overload_text = f" (Overload {overload})" if overload is not None else ""
            tab_name = f"{package_name}.{procedure_name}{overload_text}"

            self.panel_sql_query_editor.sql_notebook.tab(
                self.panel_sql_query_editor.sql_files[tab_id]["frame"],
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

            tree = self.panel_sql_query_editor._create_result_tab(
                f"{package_name}.{procedure_name} (Parameters)",
                columns,
                rows
            )

            context_menu = self.panel_sql_query_editor._create_context_menu(
                tree,
                lambda: self.panel_sql_query_editor._copy_selected_rows(tree),
                lambda: self.panel_sql_query_editor._export_to_csv(tree, f"{package_name}_{procedure_name}_parameters")
            )
            tree.bind("<Button-3>", lambda event: context_menu.tk_popup(event.x_root, event.y_root))

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
            clean_text = item_text.split(' (')[0].split(' '*4)[0]
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
