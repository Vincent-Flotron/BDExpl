from Panels import *

class PanelQueryResult:
    def __init__(self, root):
        self.root = root
        self.current_codepage = 'utf-8'
        self.zoom_level = 100

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
        style = ttk.Style()
        style.configure('Treeview', font=('Helvetica', font_size))
        style.configure('Treeview.Heading', font=('Helvetica', font_size, 'bold'))

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
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

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

        # Stocker le texte brut des erreurs pour rafraîchissement
        self.raw_error_text = None

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC DISPLAY METHODS
    # ─────────────────────────────────────────────────────────────────

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
        for col in unique_columns:
            self.result_tree.column(col, minwidth=100, width=150, stretch=tk.NO, anchor=tk.W)
            self.result_tree.heading(col, text=col, anchor=tk.W)

        # Seed max widths from header labels so they're never under-sized
        max_widths = [len(col) * 8 for col in unique_columns]

        row_count = 0
        for row in rows:
            # None → ''; everything else (datetime, Decimal, …) → str().
            # All branches of the original isinstance chain ended in str() anyway.
            formatted_row = tuple('' if v is None else str(v) for v in row)

            # Accumulate widths now — avoids a full second pass over the Treeview later
            for i, cell in enumerate(formatted_row):
                w = len(cell) * 8
                if w > max_widths[i]:
                    max_widths[i] = w

            self.result_tree.insert('', 'end', values=formatted_row)
            row_count += 1

        # Apply widths directly — no Treeview re-query needed
        for col, w in zip(unique_columns, max_widths):
            self.result_tree.column(col, width=min(max(w, 150), 300))
        self.result_tree.update_idletasks()

        self.result_info.config(text=f"{row_count} row(s) displayed")

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
            self.result_tree.column(col, width=min(max(w, 150), 300))
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
        """Handle Treeview configuration changes"""
        pass

    def show_result_context_menu(self, event):
        self.result_context_menu.post(event.x_root, event.y_root)

    def copy_selected_rows(self):
        """Copy selected rows to clipboard (tab-separated)."""
        selected = self.result_tree.selection()
        if not selected:
            return
        lines = [
            '\t'.join(
                str(v).replace('▶ ', '') if isinstance(v, str) and v.startswith('▶ ') else str(v)
                for v in self.result_tree.item(item)['values']
            )
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
                        row = [
                            str(v).replace('▶ ', '') if isinstance(v, str) and v.startswith('▶ ') else str(v)
                            for v in self.result_tree.item(item)['values']
                        ]
                        writer.writerow(row)
                messagebox.showinfo("Success", f"Data exported to {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export data: {str(e)}")

