import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import signal
from DBConnection        import DBConnection
from Panels              import StatusBarPanel
from PanelSQLQueryEditor import PanelSQLQueryEditor
from PanelDatabaseTree   import PanelDatabaseTree
from PanelQueryResult    import PanelQueryResult
from ConnectionManager   import ConnectionManager
from CredentialManager   import CredentialManager
from QueryManager        import QueryManager
from ConnectionDialogs   import DeleteConnectionDialog, NewConnectionDialog
from version             import VERSION

class Theme:
    def __init__(self, root):
        self.root = root

    def setup(self):
        """Configure a professional light theme with improved styling"""
        # Color palette
        bg_color        = '#f5f7fa'  # Lighter background
        primary_color   = '#4a90e2'  # Softer blue
        secondary_color = '#d0d9e3'  # Light gray-blue
        text_color      = '#333333'  # Darker text for better readability
        accent_color    = '#357abd'  # Slightly darker blue for accents
        border_color    = '#d1d5db'  # Subtle border color
        highlight_color = '#e5e7eb'  # For highlighted elements
        success_color   = '#2ecc71'  # Green for success messages
        error_color     = '#e74c3c'  # Red for errors
        refresh_color   = '#666633'  # Custom color for refresh button

        self.style = ttk.Style()
        self.style.theme_use('clam')  # Best theme for custom styling

        # Configure root window
        self.root.configure(bg=bg_color)

        # Style for frames
        self.style.configure('TFrame', background=bg_color, bordercolor=border_color)

        # Style for labels
        self.style.configure('TLabel',
                            background=bg_color,
                            foreground=text_color,
                            font=('Helvetica', 10))
        self.style.configure('Bold.TLabel',
                            font=('Helvetica', 10, 'bold'),
                            foreground=text_color)
        self.style.configure('Status.TLabel',
                            background=secondary_color,
                            foreground=text_color,
                            anchor='w',
                            relief='flat',
                            font=('Helvetica', 9))

        # Style for buttons
        self.style.configure('TButton',
                            font=('Helvetica', 9),
                            borderwidth=1,
                            padding=8,
                            background=primary_color,
                            foreground='white')
        self.style.map('TButton',
                    background=[('active', accent_color), ('!active', primary_color)],
                    relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

        # Style for SQL helper buttons (green)
        self.style.configure('SQLHelper.TButton',
                            font=('Helvetica', 9),
                            borderwidth=1,
                            padding=8,
                            background=success_color,
                            foreground='white')
        self.style.map('SQLHelper.TButton',
                    background=[('active', '#27ae60'), ('!active', success_color)],
                    relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

        # Style for refresh button (custom color)
        self.style.configure('Refresh.TButton',
                            font=('Helvetica', 9),
                            borderwidth=1,
                            padding=4,
                            width=4,
                            background=refresh_color,
                            foreground='white')
        self.style.map('Refresh.TButton',
                    background=[('active', '#55552a'), ('!active', refresh_color)],
                    relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

        # Style for notebook (tabs)
        self.style.configure('TNotebook',
                            background=bg_color,
                            borderwidth=0)
        self.style.configure('TNotebook.Tab',
                            font=('Helvetica', 9),
                            padding=[12, 6],
                            background=highlight_color,
                            foreground=text_color)
        self.style.map('TNotebook.Tab',
                    background=[('selected', bg_color), ('!selected', highlight_color)],
                    expand=[('selected', [1, 1, 1, 0])])

        # Style for treeview
        self.style.configure('Treeview',
                            font=('Helvetica', 9),
                            rowheight=28,
                            background=bg_color,
                            fieldbackground=bg_color,
                            foreground=text_color,
                            bordercolor=border_color,
                            highlightthickness=0)
        self.style.map('Treeview',
                    background=[('selected', primary_color)],
                    foreground=[('selected', 'white')])
        self.style.configure('Treeview.Heading',
                            font=('Helvetica', 10, 'bold'),
                            foreground=text_color,
                            padding=[5, 5])

        # Style for Nautilus/ariane wire/breadcumb
        self.style.configure('Breadcrumb.TButton',
                padding=2,
                font=('Segoe UI', 9, 'bold'))

        # Style for entry and combobox
        self.style.configure('TEntry',
                            fieldbackground='#ffffff',
                            foreground=text_color,
                            insertcolor=text_color,
                            bordercolor=border_color)
        self.style.configure('TCombobox',
                            fieldbackground='#ffffff',
                            foreground=text_color,
                            bordercolor=border_color)

        # Style for scrollbar
        self.style.configure('TScrollbar',
                            background=secondary_color,
                            troughcolor=bg_color,
                            bordercolor=border_color,
                            arrowcolor=text_color,
                            width=12)

        # Style for separators
        self.style.configure('TSeparator',
                            background=border_color)

        # Style for radio buttons
        self.style.configure('TRadiobutton',
                            background=bg_color,
                            foreground=text_color,
                            font=('Helvetica', 9))

        # Style tab close button
        self.style.configure('Close.TButton',
                    font=('Helvetica', 9, 'bold'),
                    borderwidth=1,
                    padding=2,
                    background=error_color,
                    foreground='white')
        
        # Monospace font
        self.style.configure('Error.Treeview', font=('Courier New', 10))  # Monospace font

        # Configure custom style for SQL editor text
        self.sql_editor_style = {
            'bg': '#ffffff',
            'fg': text_color,
            'insertbackground': text_color,
            'selectbackground': primary_color,
            'selectforeground': 'white',
            'padx': 8,
            'pady': 8,
            'borderwidth': 0,
            'highlightthickness': 1,
            'highlightcolor': border_color,
            'highlightbackground': border_color,
            'font': ('Consolas', 10)
        }


class DBExp:
    """Database Explorer - Scalable multi-database GUI tool"""

    CONFIG_FILE = "dbexp_config.json"

    def __init__(self, root):
        self.root = root
        self.root.title(f"DBExp - Database Explorer v{VERSION}")
        self.root.geometry("1600x1000")

        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        # Database connection
        self.db_connection = DBConnection()

        # Configuration
        self.config = self.load_config()

        # Queries
        self.query_manager = None

        # Connection
        self.credential_manager = CredentialManager(False)

        # Setup theme and UI
        self.theme = Theme(self.root)
        self.theme.setup()
        self.setup_ui()

        # Initialize existing_connections_menu before setup_menu
        self.existing_connections_menu = tk.Menu(self.root, tearoff=0)

        self.setup_menu()

        # Apply saved zoom settings
        self.apply_saved_zoom_settings()

    def setup_ui(self):
        """Create the three-panel interface"""
        # Main container with PanedWindow for resizable panels
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Create status bar first to ensure it's always visible
        self.status_bar_panel = StatusBarPanel(main_container, text="Not connected", style='Status.TLabel')

        # Main paned window for the rest of the UI
        main_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.query_result_panel     = PanelQueryResult(self.root, self.status_bar_panel)
        self.query_manager          = QueryManager(self.db_connection, self.query_result_panel)
        self.sql_query_editor_panel = PanelSQLQueryEditor(self.query_result_panel, self.db_connection, self.query_manager)
        self.query_result_panel.set_sql_query_editor(self.sql_query_editor_panel)

        # Left Panel: DB Treeview
        self.database_tree_panel    = PanelDatabaseTree(main_paned, self.db_connection, self.sql_query_editor_panel, self.query_manager)
        self.database_tree_panel.setup()

        # Right container for SQL Query and Query Result
        right_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned, weight=3)

        # Middle Panel: SQL Query Editor
        self.sql_query_editor_panel.setup(right_paned, self.root, self.theme)

        # Bottom Panel: Query Result
        self.query_result_panel.setup(right_paned, self.config)

        # Connection manager
        self.connection_manager = ConnectionManager(
            self.root,
            self.db_connection,
            self.database_tree_panel,
            self.status_bar_panel,
            self.credential_manager
        )

    def load_config(self) -> dict:
        """Load persistent configuration"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self):
        """Save persistent configuration"""
        # Save zoom settings
        if hasattr(self, 'database_tree_panel'):
            self.config["database_tree_zoom"] = self.database_tree_panel.zoom_level
        if hasattr(self, 'sql_query_editor_panel'):
            self.config["query_editor_zoom"] = self.sql_query_editor_panel.zoom_level
        if hasattr(self, 'query_result_panel'):
            self.config["query_result_zoom"] = self.query_result_panel.zoom_level

        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

    def apply_saved_zoom_settings(self):
        """Apply saved zoom settings to all panels"""
        if hasattr(self, 'database_tree_panel') and "database_tree_zoom" in self.config:
            self.database_tree_panel.set_zoom(self.config["database_tree_zoom"])

        if hasattr(self, 'sql_query_editor_panel') and "query_editor_zoom" in self.config:
            self.sql_query_editor_panel.set_zoom(self.config["query_editor_zoom"])

        if hasattr(self, 'query_result_panel') and "query_result_zoom" in self.config:
            self.query_result_panel.set_zoom(self.config["query_result_zoom"])

    def setup_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Connection menu
        conn_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Connection", menu=conn_menu)

        # Add submenu for storage method selection
        storage_menu = tk.Menu(conn_menu, tearoff=0)
        conn_menu.add_cascade(label="Storage Method", menu=storage_menu)

        # Storage method options
        self.storage_method_var = tk.StringVar(value="credman" if not self.credential_manager.use_env_vars else "envvars")
        storage_menu.add_radiobutton(
            label="Windows Credential Manager",
            variable=self.storage_method_var,
            value="credman",
            command=self.change_storage_method
        )
        storage_menu.add_radiobutton(
            label="Environment Variables",
            variable=self.storage_method_var,
            value="envvars",
            command=self.change_storage_method
        )

        # Add submenu for existing connections
        self.existing_connections_menu = tk.Menu(conn_menu, tearoff=0)
        conn_menu.add_cascade(label="Connect with Existing", menu=self.existing_connections_menu)

        # Add submenu for new connection
        conn_menu.add_command(label="Connect with New Credentials", command=self.show_new_connection_dialog)

        # Add delete connection command
        conn_menu.add_command(label="Delete Connection", command=self.show_delete_connection_dialog)

        conn_menu.add_separator()
        conn_menu.add_command(label="Disconnect", command=self.connection_manager.disconnect)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New SQL",     command=self.sql_query_editor_panel.new_sql_tab)
        file_menu.add_command(label="Open SQL...", command=self.sql_query_editor_panel.open_sql_file)
        file_menu.add_command(label="Save",        command=self.sql_query_editor_panel.save_current_sql)
        file_menu.add_command(label="Save As...",  command=self.sql_query_editor_panel.save_sql_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Query menu
        query_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Query", menu=query_menu)
        query_menu.add_command(label="Execute (F5)",      command=self.sql_query_editor_panel.execute)
        query_menu.add_command(label="Execute Selection", command=self.sql_query_editor_panel.execute_selection)

        # Populate existing connections menu
        self.populate_existing_connections_menu()

    def change_storage_method(self):
        """Change the storage method between Windows Credential Manager and environment variables"""
        current_method = self.storage_method_var.get()
        new_use_env_vars = (current_method == "envvars")

        # If already using the selected method, do nothing
        if self.credential_manager.use_env_vars == new_use_env_vars:
            return


        # Create new connection string generator with the new storage method
        self.credential_manager.set_use_env_vars(use_env_vars=new_use_env_vars)

        # Update the menu to show the new storage method is active
        self.storage_method_var.set(current_method)

        # Refresh the existing connections menu (will be empty with new storage)
        self.populate_existing_connections_menu()

        messagebox.showinfo(
            "Storage Method Changed",
            f"Storage method changed to {'Environment Variables' if new_use_env_vars else 'Windows Credential Manager'}."
        )


    def show_delete_connection_dialog(self):
        """Show delete connection dialog and return deleted connection name if any."""
        dialog = DeleteConnectionDialog( self )
        return dialog.show()

    def show_new_connection_dialog(self):
        """Show new connection dialog and return True if saved successfully."""
        dialog = NewConnectionDialog( self )
        return dialog.show()

    def populate_existing_connections_menu(self):
        """Populate the existing connections menu with available connections"""
        try:
            connections = self.credential_manager.get_all_connection_names()

            # Clear existing items
            self.existing_connections_menu.delete(0, tk.END)

            # Add connections to menu
            for conn_name in connections:
                self.existing_connections_menu.add_command(
                    label=conn_name,
                    command=lambda name=conn_name: self.connection_manager.connect_with_credman(name)
                )

            # If no connections, add a disabled item
            if not connections:
                self.existing_connections_menu.add_command(
                    label="No connections available",
                    state="disabled"
                )

        except Exception as e:
            extra_info = ""
            if str(e) == "Windows Credential Manager is only available on Windows systems.":
                extra_info = "\n\nAutomatically switched to environment variables."
                self.setup_menu()

            messagebox.showwarning("Error", f"Failed to load existing connections: {str(e)}{extra_info}")

    def close_keys_tab(self, frame):
        print("close_keys_tab")
        self.sql_query_editor_panel.close_keys_tab(frame)

    def shutdown(self, *args):
        """Gracefully shutdown application and close DB connections"""
        # Save zoom settings before shutting down
        self.save_config()
        self.connection_manager.disconnect()
        self.root.quit()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = DBExp(root)

    # Load the image
    resources_path = os.path.join(os.path.dirname(__file__), "resources")
    icon_path = os.path.join(resources_path, "icon.png")

    try:
        icon = tk.PhotoImage(file=icon_path)
        # Set it as the icon
        root.iconphoto(True, icon)  # The 'True' argument makes it apply to all future top-level windows too
        # Keep a reference to prevent garbage collection
        root.icon = icon  # Store as an attribute
    except Exception as e:
        print(f"Could not load icon: {e}")

    # Graceful shutdown on signals
    signal.signal(signal.SIGINT,  lambda sig, frame: app.shutdown())
    signal.signal(signal.SIGTERM, lambda sig, frame: app.shutdown())

    root.mainloop()

if __name__ == "__main__":
    main()