from Panels import *

class PanelQueryResult:
    def __init__(self, root, db_connection):
        self.root = root
        self.db_connection = db_connection
        self.current_codepage = 'utf-8'
        self.zoom_level = 100

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
        header.pack(fill=tk.X, padx=5, pady=(5, 2))
        ttk.Label(header, text="Query Result", style='Bold.TLabel').pack(side=tk.LEFT)

        # Zoom controls
        zoom_frame = ttk.Frame(header, style='TFrame')
        zoom_frame.pack(side=tk.RIGHT, padx=5)

        self.zoom_label = ttk.Label(zoom_frame, text=f"{self.zoom_level}%", style='TLabel')
        self.zoom_label.pack(side=tk.RIGHT, padx=5)

        ttk.Button(zoom_frame, text="+", command=self.zoom_in, width=2).pack(side=tk.RIGHT, padx=2)
        ttk.Button(zoom_frame, text="-", command=self.zoom_out, width=2).pack(side=tk.RIGHT, padx=2)
        ttk.Button(zoom_frame, text="↻", command=self.reset_zoom, width=2).pack(side=tk.RIGHT, padx=2)


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

