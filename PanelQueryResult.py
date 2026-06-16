from Panels import *

class PanelQueryResult:
    def __init__(self, root, panel_status_bar):
        self.root                    = root
        self.current_codepage        = 'utf-8'
        self.zoom_level              = 100
        self.panel_status_bar        = panel_status_bar
        self.panel_sql_query_editor  = None   # set later via set_sql_query_editor()
        self.reg_thousand_sep1       = re.compile(r"^(-?)(\d{1,3})(\d{3})(?:(\.)(\d+))?$")
        self.reg_thousand_sep2       = re.compile(r"^(-?)(\d{1,3})(\d{3})(\d{3})(?:(\.)(\d+))?$")
        self.reg_thousand_sep3       = re.compile(r"^(-?)(\d{1,3})(\d{3})(\d{3})(\d{3})(?:(\.)(\d+))?$")
        self.reg_thousand_sep4       = re.compile(r"^(-?)(\d{1,3})(\d{3})(\d{3})(\d{3})(\d{3})(?:(\.)(\d+))?$")
        self.reg_thousand_sep5       = re.compile(r"^(-?)(\d{1,3})(\d{3})(\d{3})(\d{3})(\d{3})(\d{3})(?:(\.)(\d+))?$")
        self.reg_thousand_sep6       = re.compile(r"^(-?)(\d{1,3})(\d{3})(\d{3})(\d{3})(\d{3})(\d{3})(\d{3})(?:(\.)(\d+))?$")
        self.thousand_sep            = "'"
        self.cols_anchor             = {}

    def set_sql_query_editor(self, panel_sql_query_editor):
        """Wire up the SQL editor panel so ORDER BY clicks can insert text there."""
        self.panel_sql_query_editor = panel_sql_query_editor

    def zoom_in(self):
        """Increase the zoom level."""
        self.zoom_level = min(200, self.zoom_level + 10)
        self._apply_zoom()
        if self.zoom_label:
            self.zoom_label.config(text=f"{self.zoom_level}%")

    def zoom_out(self):
        """Decrease the zoom level."""
        self.zoom_level = max(50, self.zoom_level - 10)
        self._apply_zoom()
        if self.zoom_label:
            self.zoom_label.config(text=f"{self.zoom_level}%")

    def reset_zoom(self):
        """Reset the zoom level to default."""
        self.zoom_level = 100
        self._apply_zoom()
        if self.zoom_label:
            self.zoom_label.config(text=f"{self.zoom_level}%")

    def _apply_zoom(self):
        """Apply the current zoom level to the treeview."""
        if not self.result_tree:
            return

        font_size = int(9 * (self.zoom_level / 100))  # Base size is 9
        row_height = font_size + 12  # Dynamically scale row height
        
        style = ttk.Style()
        style.configure('ResultTree.Treeview', font=('Helvetica', font_size), rowheight=row_height)
        style.configure('ResultTree.Treeview.Heading', font=('Helvetica', font_size, 'bold'))

        # Update column widths after font change
        if self.result_tree.get_children():
            self.update_column_widths()

    def set_zoom(self, zoom_level):
        """Set the zoom level."""
        self.zoom_level = max(50, min(200, zoom_level))
        self._apply_zoom()
        if self.zoom_label:
            self.zoom_label.config(text=f"{self.zoom_level}%")

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
        header.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(header, text="Query Result", style='Bold.TLabel').pack(side=tk.LEFT)

        # Zoom controls
        zoom_frame = ttk.Frame(header, style='TFrame')
        zoom_frame.pack(side=tk.RIGHT, padx=5)

        self.zoom_label = ttk.Label(zoom_frame, text=f"{self.zoom_level}%", style='TLabel')
        self.zoom_label.pack(side=tk.RIGHT, padx=5)

        ttk.Button(zoom_frame, text="+", command=self.zoom_in, width=2).pack(side=tk.RIGHT, padx=2)
        ttk.Button(zoom_frame, text="-", command=self.zoom_out, width=2).pack(side=tk.RIGHT, padx=2)
        ttk.Button(zoom_frame, text="↻", command=self.reset_zoom, width=2).pack(side=tk.RIGHT, padx=2)

        # ── Result grid ───────────────────────────────────────────────
        grid_container = ttk.Frame(result_frame, style='TFrame')
        grid_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.result_tree = Helper.create_treeview_with_scrollbars(grid_container, show='tree headings')
        self.result_tree.configure(style='ResultTree.Treeview')
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.result_tree.bind("<Shift-MouseWheel>", self.on_shift_mousewheel)

        # Remove the result_info label from here since we'll use the status bar
        commands = [
            ("Copy Selected",       self.copy_selected_rows),
            ("Copy All",            self.copy_all_rows),
            ("Export to CSV",       self.export_to_csv),
            ("Reset Column Widths", self.reset_column_widths),
        ]
        self.result_context_menu = Helper.create_context_menu(self.result_tree, commands)

        self.result_tree.bind("<Button-3>",   self.show_result_context_menu)
        self.result_tree.bind("<Configure>",  self.on_tree_configure)

        # Stocker le texte brut des erreurs pour rafraîchissement
        self.raw_error_text = None

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC DISPLAY METHODS
    # ─────────────────────────────────────────────────────────────────

    def _format_value_with_thousands_separator(self, value):
        """Format numeric values with thousands separator (')."""

        if value is None:
            return ""

        if isinstance(value, (Decimal, int)):
            match = self.reg_thousand_sep1.match(str(value))
            if match:
                groups = match.groups()
                return f"{groups[0] or ''}{groups[1] or ''}{self.thousand_sep}{groups[2] or ''}{groups[3] or ''}{groups[4] or ''}".format(":.5f")
            match = self.reg_thousand_sep2.match(str(value))
            if match:
                groups = match.groups()
                return f"{groups[0] or ''}{groups[1] or ''}{self.thousand_sep}{groups[2] or ''}{self.thousand_sep}{groups[3] or ''}{groups[4] or ''}{groups[5] or ''}"
            match = self.reg_thousand_sep3.match(str(value))
            if match:
                groups = match.groups()
                return f"{groups[0] or ''}{groups[1] or ''}{self.thousand_sep}{groups[2] or ''}{self.thousand_sep}{groups[3] or ''}{self.thousand_sep}{groups[4] or ''}{groups[5] or ''}{groups[6] or ''}"
            match = self.reg_thousand_sep4.match(str(value))
            if match:
                groups = match.groups()
                return f"{groups[0] or ''}{groups[1] or ''}{self.thousand_sep}{groups[2] or ''}{self.thousand_sep}{groups[3] or ''}{self.thousand_sep}{groups[4] or ''}{self.thousand_sep}{groups[5] or ''}{groups[6] or ''}{groups[7] or ''}"
            match = self.reg_thousand_sep5.match(str(value))
            if match:
                groups = match.groups()
                return f"{groups[0] or ''}{groups[1] or ''}{self.thousand_sep}{groups[2] or ''}{self.thousand_sep}{groups[3] or ''}{self.thousand_sep}{groups[4] or ''}{self.thousand_sep}{groups[5] or ''}{self.thousand_sep}{groups[6] or ''}{groups[7] or ''}{groups[8] or ''}"
            match = self.reg_thousand_sep6.match(str(value))
            if match:
                groups = match.groups()
                return f"{groups[0] or ''}{groups[1] or ''}{self.thousand_sep}{groups[2] or ''}{self.thousand_sep}{groups[3] or ''}{self.thousand_sep}{groups[4] or ''}{self.thousand_sep}{groups[5] or ''}{self.thousand_sep}{groups[6] or ''}{self.thousand_sep}{groups[7] or ''}{groups[8] or ''}{groups[9] or ''}"

        return str(value)



    def display_results(self, columns: List[str], rows: List[Tuple], description):
        """Display query results in grid with duplicate column name handling"""
        self.result_tree.delete(*self.result_tree.get_children())

        # Handle duplicate column names by adding numbered suffixes
        column_counts = {}
        unique_columns = []
        for col in columns:
            if col in column_counts:
                column_counts[col] += 1
                unique_col = f"{col} (#{column_counts[col]})"
            else:
                column_counts[col] = 1
                unique_col = col
            unique_columns.append(unique_col)

        for i, col in enumerate(columns):
            if column_counts[col] > 1 and not re.match(rf"{re.escape(col)} \(#\d+\)", unique_columns[i]):
                unique_columns[i] = f"{col} (#1)"

        self.result_tree['columns'] = unique_columns
        self.result_tree.column('#0', width=0, stretch=tk.NO)

        # Indentify justification for columns
        self.cols_anchor = {}
        if len(rows) > 0:
            for i, cell, col_name in zip(range(len(unique_columns)), rows[0], unique_columns):
                # dive until a valid cell value
                j     = 0
                j_max = len(rows)
                while not cell and not j >= j_max:
                    cell = rows[j][i]
                    j += 1;

                if isinstance(cell, (int, Decimal, float)):
                    self.cols_anchor[col_name] = tk.E
                else:
                    self.cols_anchor[col_name] = tk.W
        else:
            for col_name in unique_columns:
                self.cols_anchor[col_name] = tk.W


        for col in unique_columns:
            self.result_tree.column(col, minwidth=100, width=150, stretch=tk.NO, anchor=self.cols_anchor[col])
            self.result_tree.heading(col, text=col, anchor=tk.W)

        # Seed max widths from header labels so they're never under-sized
        max_widths = [len(col) * 8 for col in unique_columns]

        # ── 1. Format all rows up-front ───────────────────────────────────────────
        formatted_rows = [
            tuple(self._format_value_with_thousands_separator(v) for v in row)
            for row in rows
        ]
        row_count = len(formatted_rows)

        # ── 2. Column-wise width pass (one max() per column, not one branch per cell)
        if formatted_rows:
            for i, col_cells in enumerate(zip(*formatted_rows)):
                col_max = max(len(c) for c in col_cells) * 8
                if col_max > max_widths[i]:
                    max_widths[i] = col_max

        # ── 3. Bulk-insert via direct Tcl call ────────────────────────────────────
        _tk_call   = self.result_tree.tk.call
        _tree_path = self.result_tree._w
        for formatted_row in formatted_rows:
            _tk_call(_tree_path, 'insert', '', 'end', '-values', formatted_row)

        # Apply widths directly — no Treeview re-query needed
        for col, w in zip(unique_columns, max_widths):
            self.result_tree.column(col, width=min(max(w, 150), 300))
        self.result_tree.update_idletasks()

        # Update status bar instead of result_info
        self.panel_status_bar.set_query_result_status(f"{row_count} row(s) displayed")

    def display_error(self, error: str):
        """Display error in result panel"""

        error = error.replace('\\x00', '').replace('\\n', '\n').replace('\\r', '\r')

        # Store the cleaned error text
        self.raw_error_text = error

        # Display the cleaned error
        self.result_tree.delete(*self.result_tree.get_children())
        self.result_tree['columns'] = ['Error']
        self.result_tree.column('#0',    width=0,  stretch=tk.NO)
        self.result_tree.column('Error', width=800)
        self.result_tree.heading('Error', text='SQL Error')

        # Configure monospace font for error display
        self.result_tree.configure(style='Error.Treeview')

        for err in error.splitlines():
            self.result_tree.insert('', 'end', values=[err])

        # Update status bar
        self.panel_status_bar.set_query_result_status("Error executing query")

    def display_message(self, message: str):
        """Display a plain message in the result panel."""
        self.result_tree.delete(*self.result_tree.get_children())
        self.result_tree['columns'] = ['Message']
        self.result_tree.column('#0',      width=0,   stretch=tk.NO)
        self.result_tree.column('Message', width=800)
        self.result_tree.heading('Message', text='Message')
        self.result_tree.insert('', 'end', values=[message])

        # Update status bar
        self.panel_status_bar.set_query_result_status("Message displayed")

    # ─────────────────────────────────────────────────────────────────
    # COLUMN WIDTHS
    # ─────────────────────────────────────────────────────────────────

    def update_column_widths(self):
        """Auto-size columns based on content (capped at 300 px).
        
        Called standalone when the tree is mutated outside display_results.
        display_results computes widths inline and does NOT call this.
        """
        columns = self.result_tree['columns']
        max_widths = [len(col) * 8 for col in columns]

        # One pass: read all values once per item, update every column together
        for item in self.result_tree.get_children():
            values = self.result_tree.item(item, 'values')
            for i, cell in enumerate(values):
                w = len(str(cell)) * 8
                if w > max_widths[i]:
                    max_widths[i] = w

        for col, w in zip(columns, max_widths):
            anchor = self.cols_anchor[col]
            if not anchor:
                anchor = tk.E
            self.result_tree.column(col, width=min(max(w, 150), 300), anchor=anchor)
        self.result_tree.update_idletasks()

    def reset_column_widths(self):
        """Reset all columns to 150 px."""
        for col in self.result_tree['columns']:
            anchor = self.cols_anchor[col]
            if not anchor:
                anchor = tk.E
            self.result_tree.column(col, width=150, anchor=anchor)
        self.result_tree.update_idletasks()

    # ─────────────────────────────────────────────────────────────────
    # MISC / UNCHANGED METHODS
    # ─────────────────────────────────────────────────────────────────

    def on_shift_mousewheel(self, event):
        """Horizontal scroll with Shift+MouseWheel."""
        self.result_tree.xview_scroll(-1 * event.delta, "units")
        return "break"

    def on_tree_configure(self, event):
        """Handle Treeview configuration changes"""
        pass

    def show_result_context_menu(self, event):
        region = self.result_tree.identify_region(event.x, event.y)
        if region == "heading":
            col_id = self.result_tree.identify_column(event.x)
            if col_id and col_id != '#0':
                col_name = self.result_tree.heading(col_id)['text']
                self._show_order_by_menu(event, col_name)
        else:
            self.result_context_menu.tk_popup(event.x_root, event.y_root)

    def _show_order_by_menu(self, event, col_name):
        """Show a small context menu to insert ORDER BY ASC/DESC into the SQL editor."""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label=f"ORDER BY {col_name} ASC",
            command=lambda: self._insert_order_by(col_name, "ASC")
        )
        menu.add_command(
            label=f"ORDER BY {col_name} DESC",
            command=lambda: self._insert_order_by(col_name, "DESC")
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _insert_order_by(self, col_name, direction):
        """Delegate the ORDER BY insertion to the SQL editor panel."""
        if self.panel_sql_query_editor:
            self.panel_sql_query_editor.insert_order_by(col_name, direction)

    def copy_selected_rows(self):
        """Copy selected rows to clipboard (tab-separated)."""
        selected = self.result_tree.selection()
        if not selected:
            return
        lines = [
            '\t'.join(
                str(v).replace('\n', ' ').replace('\r', ' ') if v else ''
                for v in self.result_tree.item(item)['values']
            )
            for item in selected
        ]
        self.root.clipboard_clear()
        self.root.clipboard_append('\n'.join(lines))
        self.root.update()

    def copy_all_rows(self):
        """Copy all rows to clipboard (tab-separated) including column headers."""
        all_items = self.result_tree.get_children()
        if not all_items:
            return

        # Get column headers
        columns = self.result_tree['columns']

        # Create header line
        header_line = '\t'.join(str(col) for col in columns)

        # Create data lines
        lines = [
            '\t'.join(
                str(v).replace('\n', ' ').replace('\r', ' ') if v else ''
                for v in self.result_tree.item(item)['values']
            )
            for item in all_items
        ]

        # Combine header and data
        self.root.clipboard_clear()
        self.root.clipboard_append(header_line + '\n' + '\n'.join(lines))
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
                        row = [
                            str(v).replace('\n', ' ').replace('\r', ' ') if v else ''
                            for v in self.result_tree.item(item)['values']
                        ]
                        writer.writerow(row)
                messagebox.showinfo("Success", f"Data exported to {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export data: {str(e)}")