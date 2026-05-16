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


class StatusBarPanel:
    def __init__(self, root, text, style):
        self.root = root
        self.status_bar = ttk.Label(self.root, text=text, style=style)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def set_status(self, new_status):
        self.status_bar.config(text=new_status)
