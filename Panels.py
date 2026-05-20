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
            show=show,
            style='Treeview'
        )
        if columns:
            tree['columns'] = columns

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

PORTION_LEN = 150

class StatusBarPanel:


    def __init__(self, root, text, style):
        # Create a container frame to hold the status bar
        self.container = ttk.Frame(root)
        self.container.pack(side=tk.BOTTOM, fill=tk.X)

        # Add the status bar to the container with minimum height
        self.status_bar = ttk.Label(
            self.container,
            text=text,
            style=style,
            anchor='w'
        )
        self.status_bar.pack(fill=tk.X, pady=(2, 0))

        # Set a minimum height for the status bar
        self.status_bar.config(compound=tk.LEFT)
        self.container.update_idletasks()
        self.container.pack_propagate(False)
        self.container.config(height=self.status_bar.winfo_reqheight() + 4)

    def set_status(self, new_status):
        self.update_bar(new_status, 1)

    def update_bar(self, new_status, portion_nb):
        actual_bar_text = self.status_bar.cget("text")
        reg_portions = re.compile(r"^(.*?)(?:( {4,})(.*?))?(?:( {4,})(.*?))?$")
        matches = reg_portions.match(actual_bar_text)
        if not matches:
            return  # or handle error case

        new_status_len = len(new_status)
        spaces         = " "*(PORTION_LEN - new_status_len)
        groups         = matches.groups()

        if portion_nb == 1:
            new_bar_text = (new_status        + spaces            +
                            (groups[2] or "") + (groups[3] or "") +
                            (groups[4] or "")                     )
        elif portion_nb == 2:
            new_bar_text = ((groups[0] or "") + (groups[1] or "") +
                            new_status        + spaces            +
                            (groups[4] or "")                     )
        elif portion_nb == 3:
            new_bar_text = ((groups[0] or "") + (groups[1] or "") +
                            (groups[2] or "") + (groups[3] or "") +
                            new_status                            )
        else:
            return  # invalid portion number

        self.status_bar.config(text=new_bar_text)
            
    
    def set_query_result_status(self, new_query_result_status):
        self.update_bar(new_query_result_status, 2)