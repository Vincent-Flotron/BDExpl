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

        # Bind Enter key to align with previous line
        self.bind("<Return>", self.align_with_previous_line)

        # Track if CTRL+K was pressed before CTRL+C or CTRL+U
        self.ctrl_k_pressed = False
        self.bind("<Control-k>", self.set_ctrl_k_flag)
        self.bind("<Control-c>", self.handle_ctrl_c_comment)
        self.bind("<Control-u>", self.handle_ctrl_u_uncomment)

        # Reset the flag on any other key press
        self.bind("<Key>", self.reset_ctrl_k_flag, add="+")

        # Define regex patterns for SQL syntax
        self.sql_keywords = r"\b(ALL|ALTER|ALTER\s+SESSION|ALTER\s+SYSTEM|ANALYZE|AND|ANY|AS|AUDIT|AUTONOMOUS\s+TRANSACTION|BEGIN|"\
            + r"BETWEEN|BULK\s+COLLECT|CALL|CASE|CHECK|CLOSE|CLUSTER|COMMENT|COMMIT|COMMITTED|"\
            + r"CONNECT|CONNECT\s+BY|CONSTRAINT|CONTINUE|CREATE|CROSS\s+JOIN|CURSOR|DECLARE|DECODE|DEFAULT|"\
            + r"DELETE|DISCONNECT|DISTINCT|DROP|DUAL|DYNAMIC|ELSE|ELSIF|END|EXCEPTION|"\
            + r"EXECUTE|EXISTS|EXIT|EXPLAIN|FETCH|FOR|FOR\s+UPDATE|FORALL|FOREIGN\s+KEY|FROM|"\
            + r"FULL\s+JOIN|FULL\s+OUTER\s+JOIN|FUNCTION|GOTO|GRANT|GROUP\s+BY|HAVING|HINT|IF|IMMEDIATE|"\
            + r"IN|INDEX|INNER\s+JOIN|INSERT|INTERSECT|IS\s+NOT\s+NULL|IS\s+NULL|ISOLATION\s+LEVEL|JOIN|LEFT\s+JOIN|"\
            + r"LEFT\s+OUTER\s+JOIN|LEVEL|LIKE|LOCK|LOOP|MERGE|MINUS|NATURAL\s+JOIN|NOAUDIT|NOT\s+EXISTS|"\
            + r"NOT\s+IN|NOT\s+NULL|NULL|NVL|OPEN|OPTIMIZER|OR|ORDER\s+BY|PACKAGE|PARTITION|PASSWORD|"\
            + r"PLAN|PRIMARY\s+KEY|PRIOR|PROCEDURE|PROFILE|RAISE|READ\s+ONLY|RECORD|RENAME|RESOURCE|"\
            + r"RETURN|REVOKE|RIGHT\s+JOIN|RIGHT\s+OUTER\s+JOIN|ROLE|ROLLBACK|ROWID|ROWNUM|SAVEPOINT|SELECT|"\
            + r"SET\s+ROLE|SET\s+TRANSACTION|SHUTDOWN|SOME|START\s+WITH|STARTUP|SUBPARTITION|SYSDATE|SYSTIMESTAMP|THEN|"\
            + r"TRUNCATE|TYPE|UNION|UNION\s+ALL|UNIQUE|UNLIMITED|UPDATE|USER|USING|WHEN|"\
            + r"WHERE|WHILE|WITH)\b"

        self.sql_operators = r"=|!=|<>|<=|>=|<|>|\+|-|\*|/|%"

        self.sql_functions = r"\b(ABS|ACOS|ADD_MONTHS|ASCII|ASIN|ATAN|ATAN2|AVG|AVG|AVG|"\
            + r"CASE\s+WHEN|CAST|CEIL|CHR|COALESCE|CONCAT|COS|COUNT|CURRENT_DATE|CURRENT_TIMESTAMP|"\
            + r"DECODE|DENSE_RANK|DENSE_RANK|END|EXP|EXTRACT|FIRST_VALUE|FIRST_VALUE|FLOOR|GROUPING|"\
            + r"HEXTORAW|INITCAP|INSTR|LAG|LAG|LAST_DAY|LAST_VALUE|LAST_VALUE|LEAD|LEAD|"\
            + r"LENGTH|LISTAGG|LN|LOCALTIMESTAMP|LOG|LOWER|LPAD|LTRIM|MAX|MIN|"\
            + r"MOD|MONTHS_BETWEEN|NEXT_DAY|NULLIF|NUMTODSINTERVAL|NUMTOYMINTERVAL|NVL|NVL2|POWER|RANK|"\
            + r"RANK|RAWTOHEX|REGEXP_INSTR|REGEXP_REPLACE|REGEXP_SUBSTR|REPLACE|ROUND|ROW_NUMBER|ROW_NUMBER|RPAD|"\
            + r"RTRIM|SIN|SOUNDEX|SQRT|STDDEV|SUBSTR|SUM|SUM|SUM|SYSDATE|"\
            + r"TAN|THEN|TO_CHAR|TO_CHAR|TO_DATE|TO_DATE|TO_NUMBER|TO_TIMESTAMP|TO_TIMESTAMP|TRIM|"\
            + r"TRUNC|UID|UPPER|USER|VARIANCE|VSIZE)\b"

        self.sql_string_pattern  = r"'[^']*'"
        self.sql_string_pattern2 = r'"[^"]*"'
        self.sql_comment_pattern = r"--.*?$|/\*.*?\*/"

        # Define colors for syntax highlighting
        self.colors = {
            'keyword': 'blue',
            'operator': 'purple',
            'function': 'darkorange',
            'string': 'green',
            'string2': 'green',
            'comment': 'gray'
        }

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
        """Add SQL line comments (--) to selected lines."""
        try:
            # Check if there's a selection
            if self.tag_ranges("sel"):
                # Get the selection range - convert Tcl_Obj to strings
                sel_range = [str(self.index(pos)) for pos in self.tag_ranges("sel")]
                start_pos = sel_range[0]
                end_pos = sel_range[1]

                # Get the selected text
                selected_text = self.get(start_pos, end_pos)

                # Add -- to the beginning of each line
                lines = selected_text.split('\n')
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

                return "break"
        except tk.TclError:
            pass
        return "break"

    def uncomment_selection(self, event=None):
        """Remove SQL line comments (--) from selected lines."""
        try:
            # Check if there's a selection
            if self.tag_ranges("sel"):
                # Get the selection range
                sel_range = self.tag_ranges("sel")
                start_pos = sel_range[0]
                end_pos = sel_range[1]

                # Get the selected text
                selected_text = self.get(start_pos, end_pos)

                # Remove -- from the beginning of each line
                lines = selected_text.split('\n')
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

                return "break"
        except tk.TclError:
            pass
        return "break"

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
        self.tag_remove("string2", "1.0", "end")
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
            self.highlight_pattern(self.sql_string_pattern2, "string2", self.colors["string2"])

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