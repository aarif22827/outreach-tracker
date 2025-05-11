import tkinter as tk
from tkinter import ttk, font
from datetime import datetime

def create_search_frame(parent, search_callback, reset_callback=None):
    """
    Create a standard search frame with search entry and buttons
    
    Parameters:
    - parent: Parent widget
    - search_callback: Function to call when search is performed
    - reset_callback: Function to call when reset button is clicked
    
    Returns:
    - frame: The search frame
    - search_var: StringVar for the search entry
    """
    search_frame = tk.Frame(parent)
    search_frame.pack(fill="x", pady=5, padx=10)
    
    tk.Label(search_frame, text="Search:").pack(side="left")
    search_var = tk.StringVar()
    search_entry = tk.Entry(search_frame, textvariable=search_var, width=30)
    search_entry.pack(side="left", padx=5)
    
    search_button = tk.Button(search_frame, text="Search", command=search_callback)
    search_button.pack(side="left", padx=10)
    
    if reset_callback:
        reset_button = tk.Button(search_frame, text="Reset", command=reset_callback)
        reset_button.pack(side="left")
    
    search_entry.bind("<Return>", lambda event: search_callback())
    
    return search_frame, search_var

def create_filter_combobox(parent, label_text, values, callback=None):
    """
    Create a standard filter combobox
    
    Parameters:
    - parent: Parent widget
    - label_text: Text for the combobox label
    - values: List of values for the combobox
    - callback: Function to call when selection changes
    
    Returns:
    - filter_var: StringVar for the combobox
    """
    tk.Label(parent, text=label_text).pack(side="left", padx=(20, 5))
    filter_var = tk.StringVar(value=values[0])
    filter_combo = ttk.Combobox(parent, textvariable=filter_var, 
                              values=values, width=20, state="readonly")
    filter_combo.pack(side="left")
    
    if callback:
        filter_combo.bind("<<ComboboxSelected>>", lambda e: callback())
    
    return filter_var

def create_sortable_treeview(parent, columns, sort_callback):
    """
    Create a treeview with sortable columns
    
    Parameters:
    - parent: Parent widget
    - columns: List of column names
    - sort_callback: Function to call when column heading is clicked, 
                    should accept column name as parameter
    
    Returns:
    - tree: The treeview widget
    """
    table_frame = tk.Frame(parent)
    table_frame.pack(fill="both", expand=True)
    
    tree = ttk.Treeview(table_frame, columns=columns, show="headings")
    
    for col in columns:
        tree.heading(col, text=col, command=lambda c=col: sort_callback(c))
        tree.column(col, width=110, anchor="w")
    
    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)
    
    return tree, table_frame

def truncate_text(text, max_length=50):
    """Truncate text to max_length and add ellipsis if necessary"""
    if not text:
        return ""
    text = text.replace("\n", " ")
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text

def format_date(date_str, input_format="%Y-%m-%d %H:%M:%S", output_format="%m/%d/%Y"):
    """Format a date string from one format to another"""
    if not date_str:
        return ""
    try:
        date_obj = datetime.strptime(date_str, input_format)
        return date_obj.strftime(output_format)
    except ValueError:
        return date_str

def add_scrollbars_to_text(parent, height=5, width=40):
    """Create a text widget with scrollbars"""
    frame = tk.Frame(parent)
    
    text_widget = tk.Text(frame, height=height, width=width, wrap="word")
    scrollbar = tk.Scrollbar(frame, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    return frame, text_widget

def resize_treeview_columns(tree, event):
    """Auto-resize treeview columns based on content"""
    region = tree.identify_region(event.x, event.y)
    if region == "separator":
        column = tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1
        
        columns = tree.cget("columns")
        if 0 <= column_index < len(columns):
            col_name = columns[column_index]
            
            current_width = tree.column(col_name, "width")
            
            header_width = font.Font().measure(col_name) + 20
            max_width = header_width
            
            for item in tree.get_children():
                values = tree.item(item, 'values')
                if column_index < len(values):
                    cell_value = str(values[column_index])
                    cell_width = font.Font().measure(cell_value) + 20
                    max_width = max(max_width, cell_width)
            
            tree.column(col_name, width=max(100, max_width))