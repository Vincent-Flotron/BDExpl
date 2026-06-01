from Panels import *


class PanelSQLQueryEditor:
    def __init__(self, panel_query_result, db_connection, query_manager):
        self.panel_query_result  = panel_query_result
        self.db_connection       = db_connection
        self.query_manager       = query_manager
        self.tab_results         = {}  # Store results for each tab
        self.zoom_level          = 100  # Default zoom level
        self.last_created_tab_id = None

    def setup(self, parent, root, theme):
        """Panel 2: SQL Query Editor with tabs"""
        self.parent = parent
        self.root = root
        self.theme = theme

        self.sql_files = {}
        self.tab_counter = 0

        editor_frame = ttk.Frame(self.parent, style='TFrame')
        self.parent.add(editor_frame, weight=1)

        # Header with zoom controls
        header_frame = ttk.Frame(editor_frame, style='TFrame')
        header_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(header_frame, text="Query Editor", style='Bold.TLabel').pack(side=tk.LEFT, pady=2)

        # Zoom controls
        zoom_frame = ttk.Frame(header_frame, style='TFrame')
        zoom_frame.pack(side=tk.RIGHT, padx=5)

        self.zoom_label = ttk.Label(zoom_frame, text=f"{self.zoom_level}%", style='TLabel')
        self.zoom_label.pack(side=tk.RIGHT, padx=5)

        ttk.Button(zoom_frame, text="+", command=self.zoom_in, width=2).pack(side=tk.RIGHT, padx=2)
        ttk.Button(zoom_frame, text="-", command=self.zoom_out, width=2).pack(side=tk.RIGHT, padx=2)
        ttk.Button(zoom_frame, text="↻", command=self.reset_zoom, width=2).pack(side=tk.RIGHT, padx=2)

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
        ttk.Button(toolbar, text="Execute (F5)",      command=self.execute, style='TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Execute Selection", command=self.execute_selection, style='TButton').pack(side=tk.LEFT, padx=2)

        self.sql_notebook = ttk.Notebook(editor_frame, style='TNotebook')
        self.sql_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.new_sql_tab()

        self.root.bind('<Control-n>', lambda e: self.new_sql_tab())
        self.root.bind('<Control-s>', lambda e: self.save_current_sql())
        self.root.bind('<F5>', lambda e: self.execute())

        self.sql_notebook.bind('<Button-2>', self.close_current_tab)
        self.sql_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)


    def zoom_in(self):
        """Increase the zoom level."""
        self.zoom_level = min(200, self.zoom_level + 10)
        self._apply_zoom_to_all_tabs()
        self.zoom_label.config(text=f"{self.zoom_level}%")

    def zoom_out(self):
        """Decrease the zoom level."""
        self.zoom_level = max(50, self.zoom_level - 10)
        self._apply_zoom_to_all_tabs()
        self.zoom_label.config(text=f"{self.zoom_level}%")

    def reset_zoom(self):
        """Reset the zoom level to default."""
        self.zoom_level = 100
        self._apply_zoom_to_all_tabs()
        self.zoom_label.config(text=f"{self.zoom_level}%")

    def _apply_zoom_to_all_tabs(self):
        """Apply the current zoom level to all SQL text widgets."""
        for tab_id, info in self.sql_files.items():
            if "widget" in info:
                info["widget"].set_zoom(self.zoom_level)

    def set_zoom(self, zoom_level):
        """Set the zoom level."""
        self.zoom_level = max(50, min(200, zoom_level))
        self._apply_zoom_to_all_tabs()
        self.zoom_label.config(text=f"{self.zoom_level}%")


    def on_tab_changed(self, event):
        """Handle tab change event to display the corresponding result"""
        tab_id, info = self.get_current_sql_tab()
        tabHasJustBeenCreated = self.last_created_tab_id and self.last_created_tab_id == tab_id
        if not tabHasJustBeenCreated and tab_id and tab_id in self.tab_results:
            result_data = self.tab_results[tab_id]
            if result_data["type"] == "results":
                self.panel_query_result.display_results(
                    result_data["columns"],
                    result_data["rows"],
                    result_data["description"]
                )
            elif result_data["type"] == "message":
                self.panel_query_result.display_message(result_data["message"])
            elif result_data["type"] == "error":
                self.panel_query_result.display_error(result_data["error"])
        self.last_created_tab_id = tab_id

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
        queries = self.get_queries_instance()
        clause  = queries.limit_results_to(limit)

        self.insert_at_cursor(clause)

    def get_connection_type(self):
        """Get the type of the current database connection"""
        return self.db_connection.get_connection_type()

    def insert_edit_separator_in_actual_tab(self):
        tab_id, info = self.get_current_sql_tab()
        if not info:
            return
        widget = info["widget"]
        widget.edit_separator()

    def insert_at_cursor(self, text):
        """Insert text at the current cursor position in the active editor"""
        tab_id, info = self.get_current_sql_tab()
        if not info:
            return

        widget = info["widget"]
        widget.edit_separator()
        self.insert_edit_separator_in_actual_tab() # for undo/redo
        widget.insert(tk.INSERT, text)
        widget.edit_separator()
        widget.see(tk.INSERT)  # Scroll to make the insertion point visible
        widget.focus_set()     # Set focus back to the editor
        self.insert_edit_separator_in_actual_tab() # for undo/redo
        widget.on_content_changed()

    def insert_order_by(self, col_name, direction):
        """Insert/replace 'ORDER BY <col_name> <direction>' before LIMIT clause or at end."""
        tab_id, info = self.get_current_sql_tab()
        if not info:
            return

        widget = info["widget"]
        widget.edit_separator()

        current_text = widget.get("1.0", "end-1c")
        
        # Pattern to match existing ORDER BY clauses (to replace)
        import re
        order_by_pattern = r'ORDER\s+BY\s+[A-Za-z0-9_\s\n,]*?(?:ASC|DESC)?'
        order_by_match = re.search(order_by_pattern, current_text, re.IGNORECASE)
        
        # Pattern to match LIMIT or FETCH FIRST clauses
        limit_pattern = r'(LIMIT\s+\d+|FETCH\s+FIRST\s+\d+\s+ROWS\s+ONLY)'
        limit_match = re.search(limit_pattern, current_text, re.IGNORECASE)
        
        if order_by_match:
            # Replace existing ORDER BY clause
            insert_start = order_by_match.start()
            insert_end = order_by_match.end()
            
            # Find the start of the line containing ORDER BY
            line_start = current_text.rfind('\n', 0, insert_start) + 1
            if line_start == 0:
                line_start = 0
            
            # Check if there's content before ORDER BY on the same line
            prefix = "\n" if line_start > 0 and current_text[line_start-1] != '\n' else ""
            
            # Find where the line ends
            line_end = current_text.find('\n', insert_end)
            if line_end == -1:
                line_end = len(current_text)
            
            # Replace the entire ORDER BY line
            new_text = f"{prefix}ORDER BY {col_name} {direction}"
            
            self.insert_edit_separator_in_actual_tab()
            widget.delete(f"1.0+{line_start}c", f"1.0+{line_end}c")
            widget.insert(f"1.0+{line_start}c", new_text)
            widget.edit_separator()
            widget.see(f"1.0+{line_start}c")
            widget.focus_set()
            self.insert_edit_separator_in_actual_tab()
            widget.on_content_changed()
        elif limit_match:
            # Insert before LIMIT clause
            match_start = limit_match.start()
            line_start = current_text.rfind('\n', 0, match_start) + 1
            if line_start == 0:
                line_start = 0
            
            insert_pos = f"1.0+{line_start}c"
            prefix = "\n" if line_start > 0 and current_text[line_start-1] != '\n' else ""
            
            self.insert_edit_separator_in_actual_tab()
            widget.insert(insert_pos, f"{prefix}ORDER BY {col_name} {direction}\n")
            widget.edit_separator()
            widget.see(insert_pos)
            widget.focus_set()
            self.insert_edit_separator_in_actual_tab()
            widget.on_content_changed()
        else:
            # Append at the end
            prefix = "\n" if current_text and not current_text.endswith("\n") else ""

            self.insert_edit_separator_in_actual_tab()
            widget.insert(tk.END, f"{prefix}ORDER BY {col_name} {direction}")
            widget.edit_separator()
            widget.see(tk.END)
            widget.focus_set()
            self.insert_edit_separator_in_actual_tab()
            widget.on_content_changed()

    def display_error(self, error: str):
        """Display error in result panel"""
        self.panel_query_result.display_error(error)

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
            width_limit   = 300
            width         = max(max_width, default_width)
            width         = min(width, width_limit)
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

    def _create_context_menu(self, tree, copy_command, export_command, copy_all_command=None):
        """Helper: Create a context menu for a treeview."""
        commands = [
            ("Copy Selected", copy_command),
        ]

        if copy_all_command:
            commands.append(("Copy All", copy_all_command))

        commands.append(("Export to CSV", export_command))

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

    def _copy_all_to_clipboard(self, tree):
        """Helper: Copy all rows (including headers) to clipboard in tabular format"""
        columns = list(tree["columns"])
        selected_values = []

        # Add header row to copied data
        header_values = ['\t'.join(str(col) for col in columns)]
        selected_values.extend(header_values)

        # Add all data rows
        for item in tree.get_children():
            values = tree.item(item)['values']
            formatted_row = '\t'.join(str(value) for value in values)
            selected_values.append(formatted_row)

        self.root.clipboard_clear()
        self.root.clipboard_append('\n'.join(selected_values))
        self.root.update()

    def show_table_keys(self, schema: str, table: str):
        """Fetch and display table or view keys (primary and foreign) in a new tab."""
        try:
            cursor  = self.db_connection.current_connection.cursor()
            queries = self.get_queries_instance()

            cursor   = self.query_manager.cursor_execute(queries.get_table_keys(schema, table), cursor)
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
                lambda: self._export_to_csv(tree, f"{table}_keys"),
                lambda: self._copy_all_to_clipboard(tree)
            )
            tree.bind("<Button-3>", lambda event: context_menu.post(event.x_root, event.y_root))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load table keys: {str(e)}")

    # Update the show_table_structure method in PanelSQLQueryEditor
    def show_table_structure(self, schema: str, table: str):
        """Fetch and display table or view structure in a new tab."""
        try:
            cursor  = self.db_connection.current_connection.cursor()
            queries = self.get_queries_instance()
            cursor  = self.query_manager.cursor_execute(queries.get_table_structure(schema, table), cursor)
            columns = [desc[0] for desc in cursor.description]
            rows    = cursor.fetchall()

            tree    = self._create_result_tab(f"{table} (Structure)", columns, rows)

            context_menu = self._create_context_menu(
                tree,
                lambda: self._copy_selected_rows(tree),
                lambda: self._export_to_csv(tree, f"{table}_structure"),
                lambda: self._copy_all_to_clipboard(tree)
            )
            tree.bind("<Button-3>", lambda event: context_menu.post(event.x_root, event.y_root))

            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load table structure: {str(e)}")

    def get_queries_instance(self):
        return self.db_connection.get_queries_instance(self.db_connection.current_connection)

    # Update the show_table_indexes method in PanelSQLQueryEditor
    def show_table_indexes(self, schema: str, table: str, index_name: str | None = None):
        """Fetch and display table indexes in a new tab."""
        try:
            cursor  = self.db_connection.current_connection.cursor()
            queries = self.get_queries_instance()
            cursor  = self.query_manager.cursor_execute(queries.get_table_indexes(schema, table), cursor)
            columns = [desc[0] for desc in cursor.description]
            rows    = cursor.fetchall()
            cursor.close()

            if not rows:
                messagebox.showinfo("Info", f"No indexes found for table {table}.")
                return

            tree = self._create_result_tab(f"{table} (Indexes)", columns, rows)

            context_menu = self._create_context_menu(
                tree,
                lambda: self._copy_selected_rows(tree),
                lambda: self._export_to_csv(tree, f"{table}_indexes"),
                lambda: self._copy_all_to_clipboard(tree)
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
            self,
            content_frame,
            wrap=tk.NONE,
            yscrollcommand=text_scroll.set,
            undo=True,
            maxundo=1000,
            **self.theme.sql_editor_style
        )

        text_widget.bind("<Control-z>",       lambda e: (self.undo(), "break"))
        text_widget.bind("<Control-y>",       lambda e: (self.redo(), "break"))
        text_widget.bind("<Control-Shift-Z>", lambda e: (self.redo(), "break"))

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.config(command=text_widget.yview)

        text_widget.edit_reset()
        text_widget.edit_modified(False)

        # Focus the new text widget
        text_widget.focus_set()

        # Set the initial zoom level for the new text widget
        text_widget.set_zoom(self.zoom_level)

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

        self.last_created_tab_id = tab_id

        return tab_id

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

    def add_undo_cyclic_separator(self):
        """Undo the last action in the current SQL tab"""
        _, info = self.get_current_sql_tab()
        if info:
            try:
                info["widget"].after(500, lambda: info["widget"].edit_separator())
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
        self.add_undo_cyclic_separator() # increase the group splitting for the undo, redo functionality
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

    def execute(self, selection_only=False):
        """Execute SQL query from current tab"""

        sql = None
        if not self.db_connection.current_connection:
            messagebox.showwarning("Not Connected", "Please connect to a database first")
            return

        tab_id, info = self.get_current_sql_tab()
        if not info:
            return

        if selection_only:
            try:
                sql = info["widget"].get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            except tk.TclError:
                messagebox.showwarning("No Selection", "Please select SQL text to execute")
        else:
            sql = info["widget"].get('1.0', 'end-1c').strip()
            
        if sql:
            self.run_query(sql)

    def execute_selection(self):
        """Execute selected SQL text"""
        self.execute(selection_only=True)


    def run_query(self, sql: str):
        """Execute SQL and display results"""
        # Clear previous results first
        self.panel_query_result.display_message("Executing query...")

        # Add a small delay to ensure the user sees the clearing
        self.root.after(150, lambda: self._execute_query_after_delay(sql))

    def _execute_query_after_delay(self, sql: str):
        """Execute the query after a small delay"""
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
                self.panel_query_result.display_results(
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
                self.panel_query_result.display_message(result["message"])
        else:
            # Store the error for this tab
            self.tab_results[tab_id] = {
                "type": "error",
                "error": result["error"]
            }
            self.panel_query_result.display_error(result["error"])

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
                self.panel_query_result.display_message("No query results to display")

    def display_message(self, message: str):
        """Display message in result panel"""
        self.panel_query_result.display_message(message)

