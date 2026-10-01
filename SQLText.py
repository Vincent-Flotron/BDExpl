from tkinter import Text, Toplevel, Frame, Label, Entry, Button, Scrollbar, StringVar, BooleanVar
from tkinter import ttk
import tkinter as tk
import re
import json
from collections import deque

class SearchReplaceDialog(Toplevel):
    """Search and Replace dialog like Notepad++ with CTRL+F - passes results to panel_query_result tab."""
    
    MAX_HISTORY = 30
    
    def __init__(self, parent, sql_text_widget, panel_query_result, use_regex=False, case_sensitive=False, search_history=None, replace_history=None):
        super().__init__(parent)
        self.sql_text = sql_text_widget
        self.panel_query_result = panel_query_result
        self.title("Find and Replace")
        
        # Load settings from parameters (saved from config)
        self.use_regex = use_regex
        self.case_sensitive = case_sensitive
        
        # Load history from parameters
        self.search_history = deque(search_history or [], maxlen=self.MAX_HISTORY)
        self.replace_history = deque(replace_history or [], maxlen=self.MAX_HISTORY)
        
        # Center the dialog on the parent window
        self.transient(parent)
        
        # Allow clicking outside the dialog to interact with other windows (like search results tab)
        # Don't use grab_set() - it blocks interaction with other windows
        self.focus_set()
        
        self.matches = []  # List of (line, col_start, col_end, text) tuples
        self.current_match_index = -1
        
        self.setup_ui()
        
        # Center the dialog on screen after UI is created
        self.after(100, self.center_dialog)
    
    def open_replace_tab(self):
        """Open the dialog with Replace tab focused."""
        self.notebook.select(1)  # Select Replace tab (index 1)
        self.replace_search_entry.focus_set()
        
    def center_dialog(self):
        """Center the dialog on the parent window."""
        self.update_idletasks()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        self.geometry(f"+{x}+{y}")
        
    def setup_ui(self):
        """Setup the tabbed search/replace dialog UI."""
        # Initialize search tags list on the SQLText widget
        self.sql_text._search_tags = []
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create Search tab
        self.search_tab = Frame(self.notebook)
        self.notebook.add(self.search_tab, text="Search")
        self.setup_search_tab()
        
        # Create Replace tab
        self.replace_tab = Frame(self.notebook)
        self.notebook.add(self.replace_tab, text="Replace")
        self.setup_replace_tab()
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    
    def setup_search_tab(self):
        """Setup the Search tab UI."""
        # Search bar frame
        search_frame = Frame(self.search_tab)
        search_frame.pack(fill=tk.X, padx=5, pady=10)
        
        Label(search_frame, text="Find:").pack(side=tk.LEFT, padx=2)
        
        self.search_var = StringVar()
        # Use Combobox for history dropdown
        self.search_entry = ttk.Combobox(search_frame, textvariable=self.search_var, width=50, values=list(self.search_history))
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Bind Enter key to search
        self.search_entry.bind("<Return>", lambda e: self.search())
        
        # Options frame
        options_frame = Frame(self.search_tab)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.case_sensitive_var = BooleanVar(value=self.case_sensitive)
        case_check = tk.Checkbutton(options_frame, text="Match Case", variable=self.case_sensitive_var)
        case_check.pack(side=tk.LEFT, padx=2)
        
        self.regex_var = BooleanVar(value=self.use_regex)
        regex_check = tk.Checkbutton(options_frame, text="Regex", variable=self.regex_var)
        regex_check.pack(side=tk.LEFT, padx=2)
        
        # Bind checkbox changes to save settings
        self.case_sensitive_var.trace_add("write", self.on_setting_changed)
        self.regex_var.trace_add("write", self.on_setting_changed)
        
        # Buttons frame
        button_frame = Frame(self.search_tab)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        Button(button_frame, text="Find All", command=self.search).pack(side=tk.LEFT, padx=2)
        Button(button_frame, text="Find Next", command=self.find_next).pack(side=tk.LEFT, padx=2)
        Button(button_frame, text="Clear", command=self.clear_results).pack(side=tk.LEFT, padx=2)
        Button(button_frame, text="Close", command=self.close).pack(side=tk.LEFT, padx=2)
        
        # Results count label
        self.results_label = Label(self.search_tab, text="")
        self.results_label.pack(fill=tk.X, padx=5, pady=5)
    
    def setup_replace_tab(self):
        """Setup the Replace tab UI."""
        # Search bar frame
        search_frame = Frame(self.replace_tab)
        search_frame.pack(fill=tk.X, padx=5, pady=10)
        
        Label(search_frame, text="Find:").pack(side=tk.LEFT, padx=2)
        
        self.replace_search_var = StringVar()
        # Use Combobox for history dropdown
        self.replace_search_entry = ttk.Combobox(search_frame, textvariable=self.replace_search_var, width=50, values=list(self.search_history))
        self.replace_search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Replace bar frame
        replace_frame = Frame(self.replace_tab)
        replace_frame.pack(fill=tk.X, padx=5, pady=5)
        
        Label(replace_frame, text="Replace:").pack(side=tk.LEFT, padx=2)
        
        self.replace_var = StringVar()
        # Use Combobox for history dropdown
        self.replace_entry = ttk.Combobox(replace_frame, textvariable=self.replace_var, width=50, values=list(self.replace_history))
        self.replace_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Options frame
        options_frame = Frame(self.replace_tab)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.replace_case_sensitive_var = BooleanVar(value=self.case_sensitive)
        case_check = tk.Checkbutton(options_frame, text="Match Case", variable=self.replace_case_sensitive_var)
        case_check.pack(side=tk.LEFT, padx=2)
        
        self.replace_regex_var = BooleanVar(value=self.use_regex)
        regex_check = tk.Checkbutton(options_frame, text="Regex", variable=self.replace_regex_var)
        regex_check.pack(side=tk.LEFT, padx=2)
        
        # Bind checkbox changes to save settings
        self.replace_case_sensitive_var.trace_add("write", self.on_setting_changed)
        self.replace_regex_var.trace_add("write", self.on_setting_changed)
        
        # Buttons frame row 1
        button_frame = Frame(self.replace_tab)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        Button(button_frame, text="Find All", command=self.replace_find_all).pack(side=tk.LEFT, padx=2)
        Button(button_frame, text="Find Next", command=self.replace_find_next).pack(side=tk.LEFT, padx=2)
        Button(button_frame, text="Clear", command=self.replace_clear).pack(side=tk.LEFT, padx=2)
        Button(button_frame, text="Close", command=self.close).pack(side=tk.LEFT, padx=2)
        
        # Buttons frame row 2
        replace_button_frame = Frame(self.replace_tab)
        replace_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        Button(replace_button_frame, text="Replace", command=self.replace_one).pack(side=tk.LEFT, padx=2)
        Button(replace_button_frame, text="Replace All", command=self.replace_all).pack(side=tk.LEFT, padx=2)
        
        # Results count label
        self.replace_results_label = Label(self.replace_tab, text="")
        self.replace_results_label.pack(fill=tk.X, padx=5, pady=5)
    
    def on_tab_changed(self, event):
        """Handle tab change event."""
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0:  # Search tab
            self.search_entry.focus_set()
        else:  # Replace tab
            self.replace_search_entry.focus_set()
    
    def on_setting_changed(self, *args):
        """Save search settings when checkboxes are toggled."""
        # Update parent window's search settings through sql_text widget
        if hasattr(self.sql_text, 'panel_sql_query_editor') and hasattr(self.sql_text.panel_sql_query_editor, 'root'):
            self.sql_text.panel_sql_query_editor.root.search_use_regex = self.regex_var.get()
            self.sql_text.panel_sql_query_editor.root.search_case_sensitive = self.case_sensitive_var.get()
    
    def get_search_flags(self, use_regex_var, case_sensitive_var):
        """Get regex flags based on settings."""
        flags = re.MULTILINE
        if not case_sensitive_var.get():
            flags |= re.IGNORECASE
        return flags
    
    def search(self, event=None):
        """Perform search and send results to panel_query_result tab."""
        search_text = self.search_var.get()
        use_regex = self.regex_var.get()
        case_sensitive = self.case_sensitive_var.get()
        
        if not search_text:
            return
        
        # Add to search history
        if search_text not in self.search_history:
            self.search_history.appendleft(search_text)
            # Update combobox values
            self.search_entry.config(values=list(self.search_history))
            self.replace_search_entry.config(values=list(self.search_history))
        
        self.clear_highlights()
        self.matches = []
        
        # Get all text
        full_text = self.sql_text.get("1.0", "end-1c")
        
        # Determine flags for regex
        flags = re.MULTILINE
        if not case_sensitive:
            flags |= re.IGNORECASE
        
        # Use regex or literal search based on checkbox
        if use_regex:
            # Use regex directly (user provides valid regex)
            try:
                pattern = search_text
                re.compile(pattern, flags)  # Validate regex
            except re.error as e:
                self.results_label.config(text=f"Invalid regex: {e}")
                return
        else:
            # Escape special regex characters for literal search
            pattern = re.escape(search_text)
        
        # Find all matches
        for line_num, line in enumerate(full_text.split('\n'), 1):
            for match in re.finditer(pattern, line, flags):
                col_start = match.start()
                col_end = match.end()
                preview = line[max(0, col_start-20):min(len(line), col_end+20)]
                if col_start < 20:
                    preview = line[:min(len(line), col_end+20)]
                self.matches.append((line_num, col_start, col_end, match.group(), preview))
        
        # Reset current match index
        self.current_match_index = -1
        
        # Update results label
        self.results_label.config(text=f"Found {len(self.matches)} match(es)")
        
        # Highlight all matches in editor
        self.highlight_all_matches()
        
        # Send results to panel_query_result tab
        if self.panel_query_result:
            self.panel_query_result.display_search_results(self.matches, search_text)
    
    def highlight_all_matches(self):
        """Highlight all found matches in the editor."""
        self.clear_highlights()
        
        for i, (line_num, col_start, col_end, matched_text, preview) in enumerate(self.matches):
            tag_name = f"search_match_{i}"
            start_pos = f"{line_num}.{col_start}"
            end_pos = f"{line_num}.{col_end}"
            self.sql_text.tag_config(tag_name, background="#ffff00", foreground="black")
            self.sql_text.tag_add(tag_name, start_pos, end_pos)
            self.sql_text._search_tags.append(tag_name)
    
    def clear_highlights(self):
        """Clear search highlights from editor."""
        if hasattr(self.sql_text, '_search_tags'):
            for tag in self.sql_text._search_tags:
                try:
                    self.sql_text.tag_delete(tag)
                except tk.TclError:
                    pass
            self.sql_text._search_tags = []
    
    def clear_results(self):
        """Clear search results and highlights without erasing search field."""
        self.results_label.config(text="")
        self.matches = []
        self.current_match_index = -1
        self.clear_highlights()
        # Also clear the tab results
        if self.panel_query_result:
            self.panel_query_result.clear_search_results()
    
    def close(self):
        """Close the search dialog."""
        self.clear_highlights()
        self.destroy()
    
    def find_next(self):
        """Navigate to the next match in the editor."""
        if not self.matches:
            return
        
        # Increment match index
        self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        
        # Get the match
        line_num, col_start, col_end, matched_text, preview = self.matches[self.current_match_index]
        
        # Navigate to the match
        self.sql_text.mark_set("insert", f"{line_num}.{col_start}")
        self.sql_text.see(f"{line_num}.{col_start}")
        self.sql_text.focus_set()
        
        # Update status label
        self.results_label.config(text=f"Match {self.current_match_index + 1} of {len(self.matches)}")
    
    # Replace tab methods
    def replace_find_all(self, event=None):
        """Perform search from Replace tab."""
        # Temporarily sync search tab vars from replace tab vars
        self.search_var.set(self.replace_search_var.get())
        self.regex_var.set(self.replace_regex_var.get())
        self.case_sensitive_var.set(self.replace_case_sensitive_var.get())
        self.search()
        # Update the replace tab label
        self.replace_results_label.config(text=self.results_label.cget("text"))
    
    def replace_find_next(self, event=None):
        """Find next match from Replace tab."""
        # If no matches yet, do a search first
        if not self.matches:
            self.replace_find_all()
        else:
            self.find_next()
            self.replace_results_label.config(text=self.results_label.cget("text"))
    
    def replace_clear(self):
        """Clear replace tab results without erasing search/replace fields."""
        self.replace_results_label.config(text="")
        self.matches = []
        self.current_match_index = -1
        self.clear_highlights()
        if self.panel_query_result:
            self.panel_query_result.clear_search_results()
    
    def _do_replace(self, match_text, replace_text, use_regex):
        """Perform a single replacement at the current match location."""
        if not self.matches:
            return False
        
        # Get current match
        line_num, col_start, col_end, matched_text, preview = self.matches[self.current_match_index]
        
        # Get the text widget content
        full_text = self.sql_text.get("1.0", "end-1c")
        lines = full_text.split('\n')
        
        if use_regex:
            # For regex, use re.sub with the replacement
            # Support for capture groups $1, $2, etc. - convert to \1, \2
            py_replace_text = re.sub(r'\$(\d+)', r'\\\1', replace_text)
            try:
                new_text = re.sub(match_text, py_replace_text, lines[line_num - 1], count=1)
            except re.error:
                return False
        else:
            # Literal replacement
            new_text = lines[line_num - 1].replace(matched_text, replace_text, 1)
        
        # Update the line
        lines[line_num - 1] = new_text
        new_full_text = '\n'.join(lines)
        
        # Save undo state before modification
        if hasattr(self.sql_text, 'panel_sql_query_editor'):
            self.sql_text.panel_sql_query_editor.add_undo_cyclic_separator()
        
        # Update the text widget
        self.sql_text.delete("1.0", "end")
        self.sql_text.insert("1.0", new_full_text)
        
        # Re-run search to update matches
        self.search()
        self.replace_results_label.config(text=self.results_label.cget("text"))
        
        return True
    
    def replace_one(self, event=None):
        """Replace the current match."""
        search_text = self.replace_search_var.get()
        replace_text = self.replace_var.get()
        use_regex = self.replace_regex_var.get()
        case_sensitive = self.replace_case_sensitive_var.get()
        
        if not search_text:
            return
        
        # Add to history
        if search_text not in self.search_history:
            self.search_history.appendleft(search_text)
            self.search_entry.config(values=list(self.search_history))
            self.replace_search_entry.config(values=list(self.search_history))
        if replace_text not in self.replace_history:
            self.replace_history.appendleft(replace_text)
            self.replace_entry.config(values=list(self.replace_history))
        
        # Sync search tab vars from replace tab vars
        self.search_var.set(search_text)
        self.regex_var.set(use_regex)
        self.case_sensitive_var.set(case_sensitive)
        
        # If no matches yet, do a search first
        if not self.matches:
            self.search()
            self.replace_results_label.config(text=self.results_label.cget("text"))
            if not self.matches:
                return
        
        # Navigate to first match if not yet positioned
        if self.current_match_index == -1:
            self.current_match_index = 0
            line_num, col_start, col_end, matched_text, preview = self.matches[self.current_match_index]
            self.sql_text.mark_set("insert", f"{line_num}.{col_start}")
            self.sql_text.see(f"{line_num}.{col_start}")
            self.sql_text.focus_set()
            self.replace_results_label.config(text=f"Match {self.current_match_index + 1} of {len(self.matches)}")
            return
        
        # Perform replacement
        if self._do_replace(search_text, replace_text, use_regex):
            # Move to next match
            if self.matches:
                self.current_match_index = (self.current_match_index + 1) % len(self.matches)
                line_num, col_start, col_end, matched_text, preview = self.matches[self.current_match_index]
                self.sql_text.mark_set("insert", f"{line_num}.{col_start}")
                self.sql_text.see(f"{line_num}.{col_start}")
                self.sql_text.focus_set()
                self.replace_results_label.config(text=f"Match {self.current_match_index + 1} of {len(self.matches)}")
    
    def replace_all(self, event=None):
        """Replace all matches in the document."""
        search_text = self.replace_search_var.get()
        replace_text = self.replace_var.get()
        use_regex = self.replace_regex_var.get()
        case_sensitive = self.replace_case_sensitive_var.get()
        
        if not search_text:
            return
        
        # Add to history
        if search_text not in self.search_history:
            self.search_history.appendleft(search_text)
            self.search_entry.config(values=list(self.search_history))
            self.replace_search_entry.config(values=list(self.search_history))
        if replace_text not in self.replace_history:
            self.replace_history.appendleft(replace_text)
            self.replace_entry.config(values=list(self.replace_history))
        
        # Sync search tab vars from replace tab vars
        self.search_var.set(search_text)
        self.regex_var.set(use_regex)
        self.case_sensitive_var.set(case_sensitive)
        
        # Do initial search
        self.search()
        
        if not self.matches:
            self.replace_results_label.config(text="No matches found")
            return
        
        flags = re.MULTILINE
        if not case_sensitive:
            flags |= re.IGNORECASE
        
        # Get the text widget content
        full_text = self.sql_text.get("1.0", "end-1c")
        
        if use_regex:
            # For regex, use re.sub with the replacement
            # Support for capture groups $1, $2, etc. - convert to \1, \2
            py_replace_text = re.sub(r'\$(\d+)', r'\\\1', replace_text)
            try:
                new_text = re.sub(search_text, py_replace_text, full_text, flags=flags)
            except re.error as e:
                self.replace_results_label.config(text=f"Invalid regex: {e}")
                return
        else:
            # Literal replacement
            new_text = full_text.replace(search_text, replace_text)
        
        # Save undo state before modification
        if hasattr(self.sql_text, 'panel_sql_query_editor'):
            self.sql_text.panel_sql_query_editor.add_undo_cyclic_separator()
        
        # Update the text widget
        self.sql_text.delete("1.0", "end")
        self.sql_text.insert("1.0", new_text)
        
        # Clear highlights and re-search
        self.clear_highlights()
        self.matches = []
        self.current_match_index = -1
        
        # Search again in the modified text to show updated results
        self.search()
        
        count = len(self.matches)
        self.replace_results_label.config(text=f"Replaced all occurrences. Found {count} remaining match(es).")
        
        # Clear the tab results
        if self.panel_query_result:
            self.panel_query_result.clear_search_results()


class SQLText(Text):
    """A Text widget with SQL syntax highlighting using regex."""

    def __init__(self, panel_sql_query_editor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panel_sql_query_editor = panel_sql_query_editor

        # Create a frame to hold the line numbers and text widget
        self.container = tk.Frame(self.master)
        self.container.pack(side=tk.LEFT, fill=tk.Y)

        # Create canvas for line numbers
        self.line_numbers = tk.Canvas(
            self.container,
            width=40,
            bg='#f0f0f0',
            highlightthickness=0
        )
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        # Re-pack the main text widget
        self.pack_forget()
        self.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Bind events - optimized for performance
        # Only KeyRelease triggers syntax highlighting (debounced)
        self.bind("<KeyRelease>",      self.on_key_release_event)
        self.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.bind("<Configure>",       self.on_configure)
        self.bind("<MouseWheel>",      self.on_scroll)
        self.bind("<Button-4>",        self.on_scroll)  # Linux scroll up
        self.bind("<Button-5>",        self.on_scroll)  # Linux scroll down

        # Bind Tab key to insert 2 spaces instead
        self.bind("<Tab>",             self.indent_selection_right)
        self.bind("<Shift-Tab>",       self.indent_selection_left)

        # Bind Enter key to align with previous line
        self.bind("<Return>",          self.align_with_previous_line)

        # Track if CTRL+K was pressed before CTRL+C or CTRL+U
        self.ctrl_k_pressed = False
        self.bind("<Control-k>",       self.set_ctrl_k_flag)
        self.bind("<Control-c>",       self.handle_ctrl_c_comment)
        self.bind("<Control-u>",       self.handle_ctrl_u_uncomment)

        # Reset the flag on any other key press
        self.bind("<Key>",             self.reset_ctrl_k_flag, add="+")

        # Initialize search tags list
        self._search_tags = []

        # Bind CTRL+F for search dialog
        self.bind("<Control-f>",       self.open_search_dialog)
        # Bind CTRL+H for replace dialog
        self.bind("<Control-h>",       self.open_replace_dialog)

        # Column Selection Mode (like VSCode's SHIFT+ALT + Click)
        self.column_selection_active = False
        self.column_selection_start = None  # (line, col) tuple - where selection starts
        self.column_selection_end = None    # (line, col) tuple - where selection ends
        self.column_selection_anchor = None # (line, col) tuple - cursor position when SHIFT+ALT pressed
        self._column_selection_tags = []    # Track selection tags
        self._column_mode_enabled = False   # SHIFT+ALT is currently held
        
        # Bind SHIFT+ALT for column selection mode
        self.bind("<Shift-Alt_L>",     self.on_alt_shift_press)
        self.bind("<Shift-Alt_R>",     self.on_alt_shift_press)
        self.bind("<Alt-Shift_L>",     self.on_alt_shift_press)
        self.bind("<Alt-Shift_R>",     self.on_alt_shift_press)
        self.bind("<KeyRelease-Alt_L>", self.on_modifier_release)
        self.bind("<KeyRelease-Alt_R>", self.on_modifier_release)
        self.bind("<KeyRelease-Shift_L>", self.on_modifier_release)
        self.bind("<KeyRelease-Shift_R>", self.on_modifier_release)
        
        # Bind mouse click for column selection (when SHIFT+ALT is held)
        self.bind("<Alt-Button-1>", self.on_alt_click)
        
        # Bind key/mouse events to clear column selection
        self.bind("<Button-1>", self.on_mouse_click_clear_column)
        self.bind("<Left>",     self.on_cursor_movement_clear_column)
        self.bind("<Right>",    self.on_cursor_movement_clear_column)
        self.bind("<Up>",       self.on_cursor_movement_clear_column)
        self.bind("<Down>",     self.on_cursor_movement_clear_column)
        self.bind("<Home>",     self.on_cursor_movement_clear_column)
        self.bind("<End>",      self.on_cursor_movement_clear_column)
        self.bind("<Prior>",    self.on_cursor_movement_clear_column)  # Page Up
        self.bind("<Next>",     self.on_cursor_movement_clear_column)  # Page Down
        
        # Bind key events for column selection mode (using add="+" to not overwrite existing bindings)
        self.bind("<Key>",             self.handle_column_selection_key, add="+")
        self.bind("<BackSpace>",       self.handle_column_selection_backspace, add="+")
        self.bind("<Delete>",          self.handle_column_selection_delete, add="+")
        self.bind("<Control-c>",       self.handle_column_selection_copy, add="+")
        self.bind("<Control-C>",       self.handle_column_selection_copy, add="+")
        self.bind("<Control-v>",       self.handle_column_selection_paste, add="+")
        self.bind("<Control-V>",       self.handle_column_selection_paste, add="+")
        self.bind("<Escape>",          self.clear_column_selection, add="+")
        
        # VSCode-like line moving: ALT+Up/Down to move lines
        self.bind("<Alt-Up>",          self.move_line_up)
        self.bind("<Alt-Down>",        self.move_line_down)
        
        # VSCode-like line copying: CTRL+D to copy line down
        self.bind("<Control-d>",       self.copy_line_down)
        
        # Override double-click to select word including underscores
        # Bind to our widget - returning "break" will prevent the default Text widget behavior
        self.bind("<Double-Button-1>", self.select_word_under_cursor)

        # Define colors for syntax highlighting
        self.colors = {
            'keyword':   'blue',
            'operator':  'purple',
            'function': "#997A24",
            'type':     "#117E99",
            'string':   'green',
            'string2':  'green',
            'comment':  'gray',
            'number':   '#098658'
        }

        # Pre-compile regex patterns for SQL syntax (optimized for speed)
        self.compiled_patterns = {
            'keyword': re.compile(
                r"\b(TO|ALL|ALTER|ALTER\s+SESSION|ALTER\s+SYSTEM|ANALYZE|AND|ANY|AS|AUDIT|AUTONOMOUS\s+TRANSACTION|BEGIN|"
                r"ON\s+CONFLICT|ON\s+DELETE\s+CASCADE|DO\s+NOTHING|"
                r"BETWEEN|BULK\s+COLLECT|CALL|CASE|CHECK|CLOSE|CLUSTER|COMMENT|COMMIT|COMMITTED|"
                r"CONNECT|CONNECT\s+BY|CONSTRAINT|CONTINUE|CREATE|CROSS\s+JOIN|CURSOR|DECLARE|DECODE|DEFAULT|"
                r"DELETE|DISCONNECT|DISTINCT|DROP|DUAL|DYNAMIC|ELSE|ELSIF|END|EXCEPTION|"
                r"EXECUTE|EXISTS|EXIT|EXPLAIN|FETCH|FOR|FOR\s+UPDATE|FORALL|FOREIGN\s+KEY|FROM|"
                r"FULL\s+JOIN|FULL\s+OUTER\s+JOIN|FUNCTION|GOTO|GRANT|GROUP\s+BY|HAVING|HINT|IF|IMMEDIATE|"
                r"IN|INDEX|INNER\s+JOIN|INSERT|INTERSECT|IS\s+NOT\s+NULL|IS\s+NULL|ISOLATION\s+LEVEL|JOIN|LEFT\s+JOIN|"
                r"LEFT\s+OUTER\s+JOIN|LEVEL|I?LIKE|SIMILAR\s+TO|LOCK|LOOP|MERGE|MINUS|NATURAL\s+JOIN|NOAUDIT|NOT\s+EXISTS|"
                r"NOT\s+IN|NOT\s+NULL|NULL|NVL|OPEN|OPTIMIZER|OR|ORDER\s+BY|PACKAGE|PARTITION|PASSWORD|ASC|DESC|FIRST|ROWS|ONLY|"
                r"PLAN|PRIMARY\s+KEY|PRIOR|PROCEDURE|PROFILE|RAISE|READ\s+ONLY|RECORD|RENAME|RESOURCE|"
                r"RETURN|REVOKE|RIGHT\s+JOIN|RIGHT\s+OUTER\s+JOIN|ROLE|ROLLBACK|ROWID|ROWNUM|SAVEPOINT|SELECT|"
                r"SET\s+ROLE|SET\s+TRANSACTION|SHUTDOWN|SOME|START\s+WITH|STARTUP|SUBPARTITION|SYSDATE|SYSTIMESTAMP|THEN|"
                r"TRUNCATE|TYPE|UNION|UNION\s+ALL|UNIQUE|UNLIMITED|UPDATE|USER|USING|WHEN|"
                r"WHERE|WHILE|WITH|TABLE|VALUES|ADD|REFERENCES|SET|"
                r"LIMIT|ON|VIEW|INTO|TIME +ZONE|WITHOUT +TIME +ZONE|RETURNS|TRIGGER|LANGUAGE|BEFORE|EACH|ROW|RESTRICT|REPLACE|"
                r"NOTICE|RETURNING|YEAR|FALSE|TRUE|GENERATED\s+BY|IDENTITY|SCHEMA|SHOW|TIMEZONE|COLLATE|CURRENT)\b",
                re.IGNORECASE | re.MULTILINE
            ),
            'operator': re.compile(
                r"(=|!=|<>|<=|>=|<|>|\+|-|\*|/|%)",
                re.MULTILINE
            ),
            'function': re.compile(
                r"\b(ABS|ACOS|ADD_MONTHS|ASCII|ASIN|ATAN|ATAN2|AVG|"
                r"CASE\s+WHEN|CAST|CEIL|CHR|COALESCE|CONCAT|COS|COUNT|CURRENT_DATE|CURRENT_TIMESTAMP|"
                r"DECODE|DENSE_RANK|EXP|EXTRACT|FIRST_VALUE|FLOOR|GROUPING|"
                r"HEXTORAW|INITCAP|INSTR|LAG|LAST_DAY|LAST_VALUE|LEAD|"
                r"LENGTH|LISTAGG|LN|LOCALTIMESTAMP|LOG|LOWER|LPAD|LTRIM|MAX|MIN|"
                r"MOD|MONTHS_BETWEEN|NEXT_DAY|NULLIF|NUMTODSINTERVAL|NUMTOYMINTERVAL|NVL|NVL2|POWER|RANK|"
                r"RAWTOHEX|REGEXP_INSTR|REGEXP_REPLACE|REGEXP_SUBSTR|ROUND|ROW_NUMBER|RPAD|"
                r"RTRIM|SIN|SOUNDEX|SQRT|STDDEV|SUBSTR|SUM|"
                r"TAN|TO_CHAR|TO_DATE|TO_NUMBER|TO_TIMESTAMP|TRIM|"
                r"TRUNC|UID|UPPER|USER|VARIANCE|VSIZE|clock_timestamp|NOW|ENUM|varying)\b",
                re.IGNORECASE | re.MULTILINE
            ),
            'type': re.compile(
                r"\b(TIMESTAMPG|TIMESTAMP|TIMESTAMPTZ|SERIAL|BIGSERIAL|VARCHAR|NUMERIC|BIGINT|"
                r"TEXT|INTEGER|INT|DATE|BOOLEAN|plpgsql|character)\b",
                re.IGNORECASE | re.MULTILINE
            ),
            'string': re.compile(
                r"'[^'\r\n]*'",
                re.MULTILINE
            ),
            'string2': re.compile(
                r'"[^"\r\n]*"',
                re.MULTILINE
            ),
            'comment': re.compile(
                r"(--.*?$|/\*.*?\*/)",
                re.MULTILINE
            ),
            'number': re.compile(
                r"\b\d+\b",
                re.MULTILINE
            )
        }

        # Define tag order for proper highlighting precedence (strings/comments first to avoid keyword highlighting inside them)
        self.highlight_order = ['string', 'string2', 'comment', 'keyword', 'function', 'type', 'operator', 'number']

        # Configure tag colors once during initialization
        for tag_name, color in self.colors.items():
            self.tag_config(tag_name, foreground=color)

        # Debouncing for syntax highlighting (prevents freezing on large files)
        self._highlight_timer = None
        self._HIGHLIGHT_DELAY_MS = 150  # Delay in ms before highlighting after keystroke

        # Initialize zoom level
        self.zoom_level = 100  # Default 100%

        # Draw line numbers initially
        self.draw_line_numbers()

    def on_key_release_event(self, event=None):
        """Handle key release with debounced highlighting."""
        # Cancel any pending highlight
        if self._highlight_timer is not None:
            self.after_cancel(self._highlight_timer)
        
        # Update line numbers immediately (fast operation)
        self.draw_line_numbers()
        
        # Schedule highlighting after delay (instead of immediate)
        self._highlight_timer = self.after(self._HIGHLIGHT_DELAY_MS, self._do_highlight)

    def on_mouse_release(self, event=None):
        """Handle mouse button release - only update line numbers."""
        self.draw_line_numbers()
        # Don't trigger highlighting on mouse click

    def on_configure(self, event=None):
        """Handle widget resize - only update line numbers."""
        self.draw_line_numbers()
        # Don't trigger highlighting on resize

    def yview(self, *args):
        """Override yview to handle scrollbar dragging and update highlighting."""
        result = super().yview(*args)
        self.draw_line_numbers()
        self.highlight_visible()  # Highlight newly visible lines
        return result

    def on_scroll(self, event):
        """Handle scroll events."""
        if event.delta:
            self.yview_scroll(-1*(event.delta//120), "units")
        elif event.num == 4:  # Linux scroll up
            self.yview_scroll(-1, "units")
        elif event.num == 5:  # Linux scroll down
            self.yview_scroll(1, "units")

        self.draw_line_numbers()
        self.highlight_visible()  # Highlight newly visible lines
        return "break"

    def draw_line_numbers(self):
        """Draw line numbers on the canvas."""
        self.line_numbers.delete("all")

        total_lines = int(self.index('end-1c').split('.')[0])

        # Dynamically size the canvas width to fit the digit count + padding
        font_size = int(10 * (self.zoom_level / 100))
        digit_count = len(str(total_lines))
        # ~7px per digit at size 10, scaled + 12px padding
        canvas_width = int(digit_count * 7 * (self.zoom_level / 100)) + 12
        self.line_numbers.config(width=canvas_width)

        first_visible_line = int(self.index("@0,0").split('.')[0])
        last_visible_line = int(self.index("@0," + str(self.winfo_height())).split('.')[0])

        # Get the text widget's font metrics for better alignment
        font = ('Consolas', font_size)
        font_metrics = self.tk.call("font", "metrics", font)

        # Extract line spacing
        line_spacing_match = re.search(r'-linespace\s+(\d+)', str(font_metrics))
        line_height = int(line_spacing_match.group(1)) if line_spacing_match else 9  # Default to 9 if not found

        for line in range(first_visible_line, min(last_visible_line + 1, total_lines + 1)):
            bbox = self.bbox(f"{line}.0")
            y = bbox[1] + line_height / 2  # Small adjustment for better vertical alignment

            self.line_numbers.create_text(
                canvas_width - 4, y,
                text=str(line),
                anchor="e",
                fill="#666666",
                font=font
            )

    def set_zoom(self, zoom_level):
        """Set the zoom level for the text widget."""
        self.zoom_level = max(50, min(200, zoom_level))
        font_size = int(10 * (self.zoom_level / 100))
        self.configure(font=('Consolas', font_size))
        self.draw_line_numbers()
        return self.zoom_level

    def zoom_in(self):
        """Increase the zoom level."""
        return self.set_zoom(self.zoom_level + 10)

    def zoom_out(self):
        """Decrease the zoom level."""
        return self.set_zoom(self.zoom_level - 10)

    def reset_zoom(self):
        """Reset the zoom level to default."""
        return self.set_zoom(100)


    def align_with_previous_line(self, event=None):
        """Align cursor with the start of the previous line when pressing Enter."""
        try:
            # Get current cursor position
            current_pos = self.index("insert")

            # Get the line number of the current position
            current_line = int(current_pos.split('.')[0])

            # If we're not on the first line, get the previous line
            if current_line > 1:
                prev_line = current_line
                prev_line_start = f"{current_line}.0"

                # Get the text of the previous line
                prev_line_text = self.get(prev_line_start, f"{prev_line}.end")

                # Find the first non-whitespace character in the previous line
                first_char_pos = 0
                
                # Count spaces for lines containing only spaces
                if re.search("^( |\t)+$", prev_line_text):
                    first_char_pos = len(prev_line_text)
                # Count spaces at beginning of line 
                else:
                    for i, char in enumerate(prev_line_text):
                        if not char.isspace():
                            first_char_pos = i
                            break

                # Calculate the column position to align with
                align_column = first_char_pos

                # Insert a newline and move cursor to the aligned position
                self.insert("insert", "\n")
                self.insert("insert", " "*align_column)

                return "break"  # Prevent default Enter behavior
        except tk.TclError:
            pass
        return None  # Allow default Enter behavior if something goes wrong

    def set_ctrl_k_flag(self, event=None):
        """Set flag when CTRL+K is pressed."""
        self.ctrl_k_pressed = True
        return "break"

    def reset_ctrl_k_flag(self, event=None):
        """Reset flag on any key press that's not CTRL+C or CTRL+U."""
        # Only reset if it's not the 'c' or 'u' key with Control modifier
        if not ((event.keysym in ('c', 'u')) and (event.state & 0x4)):
            self.ctrl_k_pressed = False

    def handle_ctrl_c_comment(self, event=None):
        """Handle CTRL+C when CTRL+K was pressed before - adds SQL comments."""
        if self.ctrl_k_pressed:
            self.ctrl_k_pressed = False
            self.comment_selection()
            return "break"
        # If CTRL+K wasn't pressed, allow normal CTRL+C (copy) behavior
        return None

    def handle_ctrl_u_uncomment(self, event=None):
        """Handle CTRL+U when CTRL+K was pressed before - removes SQL comments."""
        if self.ctrl_k_pressed:
            self.ctrl_k_pressed = False
            self.uncomment_selection()
            return "break"
        # If CTRL+K wasn't pressed, do nothing special
        return None

    def comment_selection(self, event=None):
        """Add SQL line comments (--) to lines.
        - With selection: comment all selected lines
        - Without selection: comment current line at cursor position
        """
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab() # for undo/redo
        try:
            # Get current cursor position
            cursor_pos   = self.index(tk.INSERT)
            current_line = int(cursor_pos.split('.')[0])

            # Check if there's a selection
            if self.tag_ranges("sel"):
                # Get the selection range - convert Tcl_Obj to strings
                sel_range = [str(self.index(pos)) for pos in self.tag_ranges("sel")]
                start_pos = sel_range[0]
                end_pos   = sel_range[1]

                # Get the selected text
                selected_text = self.get(start_pos, end_pos)

                # Add -- to the beginning of each line
                lines     = selected_text.split('\n')
                new_lines = []
                for line in lines:
                    new_lines.append('-- ' + line)
                new_text = '\n'.join(new_lines)

                # Replace the selected text with the modified version
                self.delete(start_pos, end_pos)
                self.insert(start_pos, new_text)

                # Restore the selection
                new_end_pos = self.index(f"{start_pos}+{len(new_text)} chars")
                self.tag_add("sel", start_pos, new_end_pos)
                self.tag_raise("sel")
            else:
                # No selection - comment current line only
                line_start = f"{current_line}.0"
                line_end   = f"{current_line}.end"
                line_text  = self.get(line_start, line_end)

                # Add comment to the beginning of the line
                self.replace(line_start, line_end, '-- ' + line_text)

                # Move cursor to maintain relative position
                cursor_col = int(cursor_pos.split('.')[1])
                self.mark_set(tk.INSERT, f"{current_line}.{cursor_col + 3}")

            return "break"
        except tk.TclError:
            pass
        finally:
            self.panel_sql_query_editor.insert_edit_separator_in_actual_tab() # for undo/redo
        return "break"

    def uncomment_selection(self, event=None):
        """Remove SQL line comments (--) from lines.
        - With selection: uncomment all selected lines
        - Without selection: uncomment current line at cursor position
        """
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab() # for undo/redo
        try:
            # Get current cursor position
            cursor_pos   = self.index(tk.INSERT)
            current_line = int(cursor_pos.split('.')[0])

            # Check if there's a selection
            if self.tag_ranges("sel"):
                # Get the selection range
                sel_range = self.tag_ranges("sel")
                start_pos = sel_range[0]
                end_pos   = sel_range[1]

                # Get the selected text
                selected_text = self.get(start_pos, end_pos)

                # Remove -- from the beginning of each line
                lines     = selected_text.split('\n')
                new_lines = []
                for line in lines:
                    # Remove "-- " or "--" from the start of the line
                    if line.startswith('-- '):
                        new_lines.append(line[3:])
                    elif line.startswith('--'):
                        new_lines.append(line[2:])
                    else:
                        new_lines.append(line)
                new_text = '\n'.join(new_lines)

                # Replace the selected text with the modified version
                self.delete(start_pos, end_pos)
                self.insert(start_pos, new_text)

                # Restore the selection
                new_end_pos = self.index(f"{start_pos}+{len(new_text)} chars")
                self.tag_add("sel", start_pos, new_end_pos)
                self.tag_raise("sel")
            else:
                # No selection - uncomment current line only
                line_start = f"{current_line}.0"
                line_end   = f"{current_line}.end"
                line_text  = self.get(line_start, line_end)

                # Remove comment from the beginning of the line
                if line_text.startswith('-- '):
                    new_line = line_text[3:]
                    self.replace(line_start, line_end, new_line)

                    # Move cursor to maintain relative position
                    cursor_col = int(cursor_pos.split('.')[1])
                    if cursor_col >= 3:  # Only adjust if cursor was after the comment
                        self.mark_set(tk.INSERT, f"{current_line}.{cursor_col - 3}")
                elif line_text.startswith('--'):
                    new_line = line_text[2:]
                    self.replace(line_start, line_end, new_line)

                    # Move cursor to maintain relative position
                    cursor_col = int(cursor_pos.split('.')[1])
                    if cursor_col >= 2:  # Only adjust if cursor was after the comment
                        self.mark_set(tk.INSERT, f"{current_line}.{cursor_col - 2}")

            return "break"
        except tk.TclError:
            pass
        finally:
            self.panel_sql_query_editor.insert_edit_separator_in_actual_tab() # for undo/redo
        return "break"

    def on_key_release(self, event=None):
        """Highlight SQL syntax on key release."""
        self.highlight()

    def refresh_highlighting(self):
        """Refresh syntax highlighting for all content. Call this after programmatically setting text."""
        self.highlight()

    def _do_highlight(self):
        """Perform syntax highlighting after debounce delay."""
        self._highlight_timer = None
        self.highlight_visible()

    def highlight_visible(self):
        """Apply syntax highlighting only to visible lines for better performance."""
        try:
            # Get visible range
            first_line = int(self.index("@0,0").split('.')[0])
            last_line = int(self.index(f"@0,{self.winfo_height()}").split('.')[0])
            total_lines = int(self.index("end-1c").split('.')[0])
            
            # Add buffer lines above and below viewport for smoother scrolling
            buffer = 5
            start_line = max(1, first_line - buffer)
            end_line = min(total_lines, last_line + buffer)
            
            # Get text for visible range only
            start_pos = f"{start_line}.0"
            end_pos = f"{end_line}.end"
            text = self.get(start_pos, end_pos)
            
            # Remove tags only from visible range
            for tag in self.colors.keys():
                self.tag_remove(tag, start_pos, end_pos)
            
            if len(text.strip()) < 2:
                return
            
            # Pre-split text into lines for efficient line-based processing
            lines = text.split('\n')
            
            # Highlight in order of precedence
            for tag_name in self.highlight_order:
                compiled_pattern = self.compiled_patterns[tag_name]
                current_line_num = start_line
                
                for line_content in lines:
                    # Find all matches in this line
                    for match in compiled_pattern.finditer(line_content):
                        start_col = match.start()
                        end_col = match.end()
                        self.tag_add(tag_name, f"{current_line_num}.{start_col}", f"{current_line_num}.{end_col}")
                    current_line_num += 1
                    
        except (ValueError, tk.TclError):
            # Fallback to full highlight on error
            self.highlight()

    def highlight(self):
        """Apply SQL syntax highlighting using pre-compiled regex patterns (full document)."""
        # Remove all tags
        for tag in self.colors.keys():
            self.tag_remove(tag, "1.0", "end")

        text = self.get("1.0", "end-1c")

        if len(text.strip()) > 1:
            # Highlight in order of precedence (strings/comments first to avoid highlighting keywords inside them)
            for tag_name in self.highlight_order:
                compiled_pattern = self.compiled_patterns[tag_name]
                
                # Find and highlight all matches using pre-compiled pattern
                for match in compiled_pattern.finditer(text):
                    start_pos = f"1.0 + {match.start()} chars"
                    end_pos = f"1.0 + {match.end()} chars"
                    self.tag_add(tag_name, start_pos, end_pos)

    def insert_spaces(self, event):
        """Insert 2 spaces instead of a tab character."""
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab() # for undo/redo
        self.insert("insert", "  ")
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab() # for undo/redo
        return "break"  # Prevent default tab behavior

    def indent_selection_left(self, event):
        """Indent text to the left (shift + tab).
        - With selection: unindent all selected lines
        - Without selection: unindent current line at cursor position
        """
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab() # for undo/redo
        try:
            # Get current cursor position
            cursor_pos   = self.index(tk.INSERT)
            current_line = int(cursor_pos.split('.')[0])

            # Check if there's a selection
            if self.tag_ranges("sel"):
                # Get the selection range
                sel_range = self.tag_ranges("sel")
                start_pos = sel_range[0]
                end_pos   = sel_range[1]

                # Get the selected text
                selected_text = self.get(start_pos, end_pos)

                # Remove 2 spaces from the beginning of each line
                lines     = selected_text.split('\n')
                new_lines = []
                for line in lines:
                    if line.startswith('  '):
                        new_lines.append(line[2:])
                    else:
                        new_lines.append(line)
                new_text = '\n'.join(new_lines)

                # Replace the selected text with the modified version
                self.delete(start_pos, end_pos)
                self.insert(start_pos, new_text)

                # Restore the selection
                new_end_pos = self.index(f"{start_pos}+{len(new_text)} chars")
                self.tag_add("sel", start_pos, new_end_pos)
                self.tag_raise("sel")
            else:
                # No selection - unindent current line only
                line_start = f"{current_line}.0"
                line_end   = f"{current_line}.end"
                line_text  = self.get(line_start, line_end)

                # Remove 2 spaces from beginning if present
                if line_text.startswith('  '):
                    new_line = line_text[2:]
                    self.replace(line_start, line_end, new_line)

                    # Move cursor to same relative position
                    cursor_col = int(cursor_pos.split('.')[1])
                    if cursor_col > 1:  # Don't go before line start
                        self.mark_set(tk.INSERT, f"{current_line}.{cursor_col-2}")

            return "break"
        except tk.TclError:
            pass
        finally:
            self.panel_sql_query_editor.insert_edit_separator_in_actual_tab() # for undo/redo
    
    def indent_selection_right(self, event):
        """Indent selected text to the right (tab)."""
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab() # for undo/redo
        try:
            # Check if there's a selection
            if self.tag_ranges("sel"):
                # Get the selection range
                sel_range = self.tag_ranges("sel")
                start_pos = sel_range[0]
                end_pos   = sel_range[1]

                # Get the selected text
                selected_text = self.get(start_pos, end_pos)

                # Add 2 spaces to the beginning of each line
                lines     = selected_text.split('\n')
                new_lines = []
                for line in lines:
                    new_lines.append('  ' + line)
                new_text = '\n'.join(new_lines)

                # Replace the selected text with the modified version
                self.delete(start_pos, end_pos)
                self.insert(start_pos, new_text)

                # Restore the selection
                new_end_pos = self.index(f"{start_pos}+{len(new_text)} chars")
                self.tag_add("sel", start_pos, new_end_pos)
                self.tag_raise("sel")

                return "break"
            else:
                self.insert_spaces(event)
                
        except tk.TclError:
            pass
        finally:
            self.panel_sql_query_editor.insert_edit_separator_in_actual_tab() # for undo/redo
        return "break"

    def on_alt_shift_press(self, event=None):
        """Handle Alt+Shift key press - store cursor position as anchor for column selection."""
        self._column_mode_enabled = True
        # Store current cursor position as the anchor point for column selection
        self.column_selection_anchor = self.index("insert")
        self.update_line_numbers_style()
        return None  # Allow normal key propagation

    def on_modifier_release(self, event=None):
        """Handle modifier key release."""
        self._column_mode_enabled = False
        self.update_line_numbers_style()
        return None

    def on_alt_click(self, event=None):
        """Handle click while SHIFT+ALT is held - create column selection from anchor to click."""
        if self._column_mode_enabled and self.column_selection_anchor:
            # Get the click position
            click_pos = self.index(f"@{event.x},{event.y}")
            # Create column selection from anchor to click position
            self.column_selection_start = self.column_selection_anchor
            self.column_selection_end = click_pos
            self.column_selection_active = True
            self.update_column_selection()
            return "break"
        return None

    def on_mouse_click_clear_column(self, event=None):
        """Clear column selection on normal mouse click (when not in SHIFT+ALT mode)."""
        # Only clear if not in column mode (SHIFT+ALT not held)
        if not self._column_mode_enabled and self.column_selection_active:
            # Schedule clearing after the click is processed
            self.after(10, self.clear_column_selection)
        return None

    def on_cursor_movement_clear_column(self, event=None):
        """Clear column selection on cursor movement keys."""
        # Only clear if not actively in column selection mode
        if not self._column_mode_enabled:
            self.clear_column_selection()
        return None

    def update_line_numbers_style(self):
        """Update line numbers background to indicate column selection mode."""
        if self._column_mode_enabled or self.column_selection_active:
            self.line_numbers.config(bg='#fff3cd')  # Yellow-ish background
        else:
            self.line_numbers.config(bg='#f0f0f0')  # Default background

    def update_column_selection(self):
        """Update the visual column selection highlighting."""
        # Remove previous column selection tags
        for tag in self._column_selection_tags:
            try:
                self.tag_delete(tag)
            except tk.TclError:
                pass
        self._column_selection_tags = []

        if not self.column_selection_start or not self.column_selection_end:
            return

        # Parse start and end positions
        start_line, start_col = map(int, self.column_selection_start.split('.'))
        end_line, end_col = map(int, self.column_selection_end.split('.'))

        # Normalize so start is always before end
        if start_line > end_line or (start_line == end_line and start_col > end_col):
            start_line, end_line = end_line, start_line
            start_col, end_col = end_col, start_col

        # Create column selection - select same columns across all lines
        tag_index = 0
        for line in range(start_line, end_line + 1):
            # Get the line content to handle short lines
            try:
                line_end = int(self.index(f"{line}.end").split('.')[1])
                # Clamp column positions to line length
                actual_start_col = min(start_col, line_end)
                actual_end_col = min(end_col, line_end)
                
                if actual_start_col < actual_end_col:
                    tag_name = f"column_sel_{tag_index}"
                    self.tag_config(tag_name, background='#3390ff', foreground='white')
                    self.tag_add(tag_name, f"{line}.{actual_start_col}", f"{line}.{actual_end_col}")
                    self._column_selection_tags.append(tag_name)
                    tag_index += 1
            except tk.TclError:
                break

        # Remove normal selection since we're using custom column selection
        self.tag_remove("sel", "1.0", "end")

    def get_column_selection_text(self):
        """Get the text from column selection."""
        if not self.column_selection_start or not self.column_selection_end:
            return ""

        # Parse start and end positions
        start_line, start_col = map(int, self.column_selection_start.split('.'))
        end_line, end_col = map(int, self.column_selection_end.split('.'))

        # Normalize so start is always before end
        if start_line > end_line or (start_line == end_line and start_col > end_col):
            start_line, end_line = end_line, start_line
            start_col, end_col = end_col, start_col

        # Get column selection text
        lines = []
        for line in range(start_line, end_line + 1):
            try:
                line_end = int(self.index(f"{line}.end").split('.')[1])
                actual_start_col = min(start_col, line_end)
                actual_end_col = min(end_col, line_end)
                line_text = self.get(f"{line}.{actual_start_col}", f"{line}.{actual_end_col}")
                lines.append(line_text)
            except tk.TclError:
                break

        return '\n'.join(lines)

    def delete_column_selection(self):
        """Delete the column selection and update selection positions."""
        if not self.column_selection_start or not self.column_selection_end:
            return

        # Parse start and end positions
        start_line, start_col = map(int, self.column_selection_start.split('.'))
        end_line, end_col = map(int, self.column_selection_end.split('.'))

        # Normalize so start is always before end
        if start_line > end_line or (start_line == end_line and start_col > end_col):
            start_line, end_line = end_line, start_line
            start_col, end_col = end_col, start_col

        # Calculate width of selection for later
        selection_width = end_col - start_col

        # Delete column by column (from bottom to top to preserve line numbers)
        for line in range(end_line, start_line - 1, -1):
            try:
                line_end = int(self.index(f"{line}.end").split('.')[1])
                actual_start_col = min(start_col, line_end)
                actual_end_col = min(end_col, line_end)
                if actual_start_col < actual_end_col:
                    self.delete(f"{line}.{actual_start_col}", f"{line}.{actual_end_col}")
            except tk.TclError:
                break

        # Update selection to new (collapsed) position
        self.column_selection_end = f"{start_line}.{start_col}"
        self.update_column_selection()

    def insert_in_column_selection(self, text):
        """Insert text at each line of column selection."""
        if not self.column_selection_start or not self.column_selection_end:
            return

        # Parse start and end positions
        start_line, start_col = map(int, self.column_selection_start.split('.'))
        end_line, end_col = map(int, self.column_selection_end.split('.'))

        # Normalize so start is always before end
        if start_line > end_line or (start_line == end_line and start_col > end_col):
            start_line, end_line = end_line, start_line
            start_col, end_col = end_col, start_col

        # Insert text at each line (from top to bottom to maintain correct line positions)
        for line in range(start_line, end_line + 1):
            try:
                line_end = int(self.index(f"{line}.end").split('.')[1])
                insert_col = min(start_col, line_end)
                self.insert(f"{line}.{insert_col}", text)
            except tk.TclError:
                break

        # Update selection to reflect new positions (shifted by text length)
        text_len = len(text)
        self.column_selection_start = f"{start_line}.{start_col + text_len}"
        self.column_selection_end = f"{end_line}.{end_col + text_len}"
        self.update_column_selection()

    def clear_column_selection(self, event=None):
        """Clear the column selection visual and state."""
        # Remove column selection tags
        for tag in self._column_selection_tags:
            try:
                self.tag_delete(tag)
            except tk.TclError:
                pass
        self._column_selection_tags = []
        self.column_selection_start = None
        self.column_selection_end = None
        self.column_selection_anchor = None
        self.column_selection_active = False
        self.update_line_numbers_style()
    
    def on_content_changed(self):
        """Notify that content has changed - for undo/redo tracking."""
        pass

    def handle_column_selection_key(self, event=None):
        """Handle key press in column selection mode - insert character at each line of selection."""
        # Only handle if column selection is active
        if not self.column_selection_active or not self.column_selection_start or not self.column_selection_end:
            return None

        # Get the character to insert
        char = event.char
        if not char or len(char) != 1:
            return None

        # Delete current selection and insert character
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab()
        self.delete_and_insert_in_column_selection(char)
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab()
        return "break"

    def delete_and_insert_in_column_selection(self, text):
        """Delete column selection and insert text at each line - atomic operation."""
        if not self.column_selection_start or not self.column_selection_end:
            return

        # Parse and normalize positions
        start_line, start_col = map(int, self.column_selection_start.split('.'))
        end_line, end_col = map(int, self.column_selection_end.split('.'))

        if start_line > end_line or (start_line == end_line and start_col > end_col):
            start_line, end_line = end_line, start_line
            start_col, end_col = end_col, start_col

        # For each line, delete the selection and insert new text
        for line in range(start_line, end_line + 1):
            try:
                line_end = int(self.index(f"{line}.end").split('.')[1])
                actual_start_col = min(start_col, line_end)
                actual_end_col = min(end_col, line_end)
                
                # Delete the selected portion
                if actual_start_col < actual_end_col:
                    self.delete(f"{line}.{actual_start_col}", f"{line}.{actual_end_col}")
                
                # Insert the new text at the start position
                self.insert(f"{line}.{actual_start_col}", text)
            except tk.TclError:
                break

        # Update selection to reflect new positions (shifted by text length)
        text_len = len(text)
        self.column_selection_start = f"{start_line}.{start_col + text_len}"
        self.column_selection_end = f"{end_line}.{end_col + text_len}"
        self.update_column_selection()

    def handle_column_selection_backspace(self, event=None):
        """Handle backspace in column selection mode."""
        if not self.column_selection_active or not self.column_selection_start or not self.column_selection_end:
            return None

        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab()
        self.delete_column_selection()
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab()
        return "break"

    def handle_column_selection_delete(self, event=None):
        """Handle delete in column selection mode."""
        if not self.column_selection_active or not self.column_selection_start or not self.column_selection_end:
            return None

        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab()
        self.delete_column_selection()
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab()
        return "break"

    def handle_column_selection_copy(self, event=None):
        """Handle copy in column selection mode - copy column text to clipboard."""
        if not self.column_selection_active or not self.column_selection_start or not self.column_selection_end:
            # Allow default copy behavior when column selection is not active
            return None

        # Get the column selection text
        column_text = self.get_column_selection_text()
        if column_text:
            self.clipboard_clear()
            self.clipboard_append(column_text)
            self.update_idletasks()
        return "break"

    def handle_column_selection_paste(self, event=None):
        """Handle paste in column selection mode - paste clipboard content at each line."""
        if not self.column_selection_active or not self.column_selection_start or not self.column_selection_end:
            return None

        try:
            # Get clipboard content
            clipboard_text = self.clipboard_get()
            if not clipboard_text:
                return None

            self.panel_sql_query_editor.insert_edit_separator_in_actual_tab()
            
            # Delete current selection first
            self.delete_column_selection()
            
            # Split clipboard into lines
            lines_to_paste = clipboard_text.split('\n')
            
            # Parse selection positions
            start_line, start_col = map(int, self.column_selection_start.split('.'))
            end_line, end_col = map(int, self.column_selection_end.split('.'))
            
            # Normalize
            if start_line > end_line or (start_line == end_line and start_col > end_col):
                start_line, end_line = end_line, start_line
                start_col, end_col = end_col, start_col
            
            # Insert each line at corresponding row
            for i, line in enumerate(range(start_line, end_line + 1)):
                try:
                    line_end = int(self.index(f"{line}.end").split('.')[1])
                    insert_col = min(start_col, line_end)
                    # Get the corresponding clipboard line (cycle if needed)
                    paste_line = lines_to_paste[i % len(lines_to_paste)]
                    self.insert(f"{line}.{insert_col}", paste_line)
                except tk.TclError:
                    break
            
            self.clear_column_selection()
            self.panel_sql_query_editor.insert_edit_separator_in_actual_tab()
            return "break"
        except tk.TclError:
            return None

    # =========================================================================
    # VSCode-like Line Moving and Copying
    # =========================================================================
    
    def move_line_up(self, event=None):
        """Move the current line or selected lines up by one line (Alt+Up)."""
        if self._column_mode_enabled or self.column_selection_active:
            return None  # Do nothing in column selection mode
        
        # Get selection range
        try:
            sel_start = self.index("sel.first")
            sel_end = self.index("sel.last")
            has_selection = True
        except tk.TclError:
            has_selection = False
            sel_start = self.index("insert linestart")
            sel_end = self.index("insert lineend")
        
        # Get line numbers
        start_line_num = int(sel_start.split('.')[0])
        end_line_num = int(sel_end.split('.')[0])
        
        # Can't move first line up
        if start_line_num == 1:
            return "break"
        
        # Get the text of the line(s) to move (without trailing newline)
        lines_to_move = []
        for line_num in range(start_line_num, end_line_num + 1):
            line_text = self.get(f"{line_num}.0", f"{line_num}.end")
            lines_to_move.append(line_text)
        
        # Get the text of the line above
        prev_line_num = start_line_num - 1
        prev_line_text = self.get(f"{prev_line_num}.0", f"{prev_line_num}.end")
        
        # Build the new text: lines_to_move + prev_line
        # We'll replace from prev_line_num.0 to end of end_line_num
        end_of_selection = self.index(f"{end_line_num}.end")
        
        # Create replacement text
        new_text = '\n'.join(lines_to_move) + '\n' + prev_line_text
        
        # Delete and replace
        self.delete(f"{prev_line_num}.0", end_of_selection)
        self.insert(f"{prev_line_num}.0", new_text)
        
        # Restore selection on the moved lines (now at prev_line_num)
        new_start_line = prev_line_num
        new_end_line = prev_line_num + len(lines_to_move) - 1
        self.tag_remove("sel", "1.0", "end")
        self.tag_add("sel", f"{new_start_line}.0", f"{new_end_line}.end")
        
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab()
        return "break"
    
    def move_line_down(self, event=None):
        """Move the current line or selected lines down by one line (Alt+Down)."""
        if self._column_mode_enabled or self.column_selection_active:
            return None  # Do nothing in column selection mode
        
        # Get selection range
        try:
            sel_start = self.index("sel.first")
            sel_end = self.index("sel.last")
            has_selection = True
        except tk.TclError:
            has_selection = False
            sel_start = self.index("insert linestart")
            sel_end = self.index("insert lineend")
        
        # Get line numbers
        start_line_num = int(sel_start.split('.')[0])
        end_line_num = int(sel_end.split('.')[0])
        
        # Get total lines
        last_line = int(self.index("end-1c").split('.')[0])
        
        # Can't move last line down
        if end_line_num >= last_line:
            return "break"
        
        # Get the text of the line(s) to move
        lines_to_move = []
        for line_num in range(start_line_num, end_line_num + 1):
            line_text = self.get(f"{line_num}.0", f"{line_num}.end")
            lines_to_move.append(line_text)
        
        # Get the text of the line below
        next_line_num = end_line_num + 1
        next_line_text = self.get(f"{next_line_num}.0", f"{next_line_num}.end")
        
        # Build the new text: next_line + lines_to_move
        end_of_selection = self.index(f"{end_line_num}.end")
        
        # Create replacement text
        new_text = next_line_text + '\n' + '\n'.join(lines_to_move)
        
        # Delete and replace
        self.delete(f"{start_line_num}.0", f"{next_line_num}.end")
        self.insert(f"{start_line_num}.0", new_text)
        
        # Restore selection on the moved lines (now shifted down by 1)
        new_start_line = start_line_num + 1
        new_end_line = start_line_num + len(lines_to_move)
        self.tag_remove("sel", "1.0", "end")
        self.tag_add("sel", f"{new_start_line}.0", f"{new_end_line}.end")
        
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab()
        return "break"
    
    def copy_line_up(self, event=None):
        """Copy the current line or selected lines above - DISABLED."""
        # This functionality has been disabled. Use Ctrl+D to copy line down.
        return None
    
    def copy_line_down(self, event=None):
        """Copy the current line or selected lines below (Ctrl+D)."""
        if self._column_mode_enabled or self.column_selection_active:
            return None  # Do nothing in column selection mode
        
        # Get selection range
        try:
            sel_start = self.index("sel.first")
            sel_end = self.index("sel.last")
            has_selection = True
        except tk.TclError:
            has_selection = False
        
        if has_selection:
            # Get the line numbers for the selection
            start_line_num = int(sel_start.split('.')[0])
            end_line_num = int(sel_end.split('.')[0])
            
            # Get the text of the selected lines (without trailing newline)
            lines_to_copy = []
            for line_num in range(start_line_num, end_line_num + 1):
                line_text = self.get(f"{line_num}.0", f"{line_num}.end")
                lines_to_copy.append(line_text)
            
            # Position to insert: after the last selected line
            insert_pos = f"{end_line_num}.end"
            
            # Insert the copied lines below
            text_to_insert = '\n' + '\n'.join(lines_to_copy)
            self.insert(insert_pos, text_to_insert)
            
            # Select the copied lines
            new_start_line = end_line_num + 1
            new_end_line = new_start_line + len(lines_to_copy) - 1
            self.tag_remove("sel", "1.0", "end")
            self.tag_add("sel", f"{new_start_line}.0", f"{new_end_line}.end")
        else:
            # No selection - copy current line
            current_line_num = int(self.index("insert").split('.')[0])
            line_text = self.get(f"{current_line_num}.0", f"{current_line_num}.end")
            
            # Insert a copy below
            insert_pos = f"{current_line_num}.end"
            self.insert(insert_pos, '\n' + line_text)
            
            # Select the copied line
            new_line_num = current_line_num + 1
            self.tag_remove("sel", "1.0", "end")
            self.tag_add("sel", f"{new_line_num}.0", f"{new_line_num}.end")
        
        self.panel_sql_query_editor.insert_edit_separator_in_actual_tab()
        return "break"
    
    def select_word_under_cursor(self, event=None):
        """Select the word under the cursor, including underscores but excluding punctuation.
        
        Double-click behavior similar to VSCode: selects identifiers with underscores,
        but stops at punctuation like dots, commas, quotes, etc.
        """
        # Get the click position - format is "@x,y" (with comma, not @x@y)
        click_pos = self.index(f"@{event.x},{event.y}")
        
        # Get the character at the click position
        char = self.get(click_pos)
        
        # If it's whitespace or punctuation, don't select anything
        punctuation = '.,;:()[]{}"\'`@#$%^&*+-=/|<>?\\'
        if char and (char.isspace() or char in punctuation):
            # Allow default behavior (which will deselect or do nothing)
            return None
        
        # Define what characters are part of a "word" (alphanumeric + underscore)
        # This matches VSCode's identifier selection behavior
        def is_word_char(c):
            return c.isalnum() or c == '_'
        
        # Get the line content
        line_start = f"{click_pos} linestart"
        line_end = f"{click_pos} lineend"
        line_text = self.get(line_start, line_end)
        
        # Calculate the column position in the line
        col = int(click_pos.split('.')[1])
        
        # Find the start of the word
        word_start = col
        while word_start > 0:
            c = line_text[word_start - 1] if word_start > 0 else ''
            if is_word_char(c):
                word_start -= 1
            else:
                break
        
        # Find the end of the word
        word_end = col
        while word_end < len(line_text):
            c = line_text[word_end] if word_end < len(line_text) else ''
            if is_word_char(c):
                word_end += 1
            else:
                break
        
        # Select the word
        start_pos = f"{line_start} + {word_start} chars"
        end_pos = f"{line_start} + {word_end} chars"
        
        self.tag_remove("sel", "1.0", "end")
        self.tag_add("sel", start_pos, end_pos)
        self.see(click_pos)
        
        return "break"

    def open_search_dialog(self, event=None):
        """Open the search and replace dialog (CTRL+F)."""
        # Get search settings from the main app if available
        search_use_regex = False
        search_case_sensitive = False
        search_history = []
        replace_history = []
        if hasattr(self.panel_sql_query_editor, 'root'):
            root = self.panel_sql_query_editor.root
            search_use_regex = getattr(root, 'search_use_regex', False)
            search_case_sensitive = getattr(root, 'search_case_sensitive', False)
            search_history = getattr(root, 'search_history', [])
            replace_history = getattr(root, 'replace_history', [])
        
        search_dialog = SearchReplaceDialog(self.master, self, self.panel_sql_query_editor.panel_query_result,
                                            search_use_regex, search_case_sensitive, search_history, replace_history)
        return "break"
    
    def open_replace_dialog(self, event=None):
        """Open the search and replace dialog focused on Replace tab (CTRL+H)."""
        # Get search settings from the main app if available
        search_use_regex = False
        search_case_sensitive = False
        search_history = []
        replace_history = []
        if hasattr(self.panel_sql_query_editor, 'root'):
            root = self.panel_sql_query_editor.root
            search_use_regex = getattr(root, 'search_use_regex', False)
            search_case_sensitive = getattr(root, 'search_case_sensitive', False)
            search_history = getattr(root, 'search_history', [])
            replace_history = getattr(root, 'replace_history', [])
        
        search_dialog = SearchReplaceDialog(self.master, self, self.panel_sql_query_editor.panel_query_result,
                                            search_use_regex, search_case_sensitive, search_history, replace_history)
        # Open with Replace tab focused
        search_dialog.open_replace_tab()
        return "break"