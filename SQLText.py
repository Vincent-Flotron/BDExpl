from tkinter import Text
import tkinter as tk
import re

class SQLText(Text):
    """A Text widget with SQL syntax highlighting using regex."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind("<KeyRelease>", self.on_key_release)
        self.bind("<ButtonRelease-1>", self.on_key_release)
        self.bind("<Configure>", self.on_key_release)

        # Bind Tab key to insert 2 spaces instead
        self.bind("<Tab>", self.indent_selection_right)
        self.bind("<Shift-Tab>", self.indent_selection_left)

        # Define regex patterns for SQL syntax
        self.sql_keywords = r"\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|JOIN|INNER|LEFT|RIGHT|OUTER|"\
            + r"GROUP\s+BY|ORDER\s+BY|HAVING|CREATE|TABLE|DROP|ALTER|"\
            + r"AND|OR|NOT|IS|NULL|AS|IN|LIKE|BETWEEN|EXISTS|UNION|ALL|DISTINCT|"\
            + r"CASE|WHEN|THEN|ELSE|END|COUNT|SUM|AVG|MIN|MAX|VALUES|INTO|"\
            + r"SET|DEFAULT|PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK|INDEX|VIEW|"\
            + r"TRIGGER|PROCEDURE|FUNCTION|GRANT|REVOKE|"\
            + r"COMMIT|ROLLBACK|BEGIN|TRANSACTION|DECLARE|EXEC|EXECUTE|WITH|"\
            + r"ROWNUM)\b"

        self.sql_operators = r"=|!=|<>|<=|>=|<|>|\+|-|\*|/|%"

        self.sql_functions = r"\b(COUNT|SUM|AVG|MIN|MAX|"\
            + r"UPPER|LOWER|SUBSTRING|CONCAT|LENGTH|"\
            + r"ROUND|CAST|COALESCE|"\
            + r"NOW|CURRENT_DATE|CURRENT_TIMESTAMP|"\
            + r"NVL|SUBSTR)\b"

        self.sql_string_pattern = r"'[^']*'"
        self.sql_comment_pattern = r"--.*?$|/\*.*?\*/"

        # Define colors for syntax highlighting
        self.colors = {
            'keyword': 'blue',
            'operator': 'purple',
            'function': 'darkorange',
            'string': 'green',
            'comment': 'gray'
        }

    def on_key_release(self, event=None):
        """Highlight SQL syntax on key release."""
        self.highlight()

    def highlight(self):
        """Apply SQL syntax highlighting using regex."""
        self.mark_set("range_start", "1.0")
        self.tag_remove("keyword", "1.0", "end")
        self.tag_remove("operator", "1.0", "end")
        self.tag_remove("function", "1.0", "end")
        self.tag_remove("string", "1.0", "end")
        self.tag_remove("comment", "1.0", "end")

        text = self.get("1.0", "end-1c")

        if len(text.strip()) > 1:
            # Highlight keywords
            self.highlight_pattern(self.sql_keywords, "keyword", self.colors["keyword"])

            # Highlight operators
            self.highlight_pattern(self.sql_operators, "operator", self.colors["operator"])

            # Highlight functions
            self.highlight_pattern(self.sql_functions, "function", self.colors["function"])

            # Highlight strings
            self.highlight_pattern(self.sql_string_pattern, "string", self.colors["string"])

            # Highlight comments
            self.highlight_pattern(self.sql_comment_pattern, "comment", self.colors["comment"], regex=True)

    def highlight_pattern(self, pattern, tag, color, regex=True):
        """Highlight a specific pattern in the text."""
        self.mark_set("range_start", "1.0")
        text = self.get("1.0", "end-1c")

        # Remove extra whitespace and newlines from multi-line patterns
        pattern = re.sub(r'\s+', ' ', pattern.strip())

        matches_iter = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches_iter:
            start_pos = f"1.0 + {match.start()} chars"
            end_pos = f"1.0 + {match.end()} chars"

            self.tag_add(tag, start_pos, end_pos)
            self.tag_config(tag, foreground=color)

    def insert_spaces(self, event):
        """Insert 2 spaces instead of a tab character."""
        self.insert("insert", "  ")
        return "break"  # Prevent default tab behavior

    def indent_selection_left(self, event):
        """Indent selected text to the left (shift + tab)."""
        try:
            # Check if there's a selection
            if self.tag_ranges("sel"):
                # Get the selection range
                sel_range = self.tag_ranges("sel")
                start_pos = sel_range[0]
                end_pos = sel_range[1]

                # Get the selected text
                selected_text = self.get(start_pos, end_pos)

                # Remove 2 spaces from the beginning of each line
                lines = selected_text.split('\n')
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

                return "break"
        except tk.TclError:
            pass
        return "break"
    
    def indent_selection_right(self, event):
        """Indent selected text to the right (tab)."""
        try:
            # Check if there's a selection
            if self.tag_ranges("sel"):
                # Get the selection range
                sel_range = self.tag_ranges("sel")
                start_pos = sel_range[0]
                end_pos = sel_range[1]

                # Get the selected text
                selected_text = self.get(start_pos, end_pos)

                # Add 2 spaces to the beginning of each line
                lines = selected_text.split('\n')
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
        return "break"