import tkinter as tk
from tkinter import ttk
from tracker.resources.documents_tab import build_documents_tab
from tracker.resources.templates_tab import build_templates_tab

def build_resources_tab(parent):
    # Create notebook for sub-tabs
    sub_notebook = ttk.Notebook(parent)
    sub_notebook.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Create sub-tabs
    documents_tab = ttk.Frame(sub_notebook)
    templates_tab = ttk.Frame(sub_notebook)
    
    sub_notebook.add(documents_tab, text="📄 Documents")
    sub_notebook.add(templates_tab, text="✉️ Templates")
    
    # Build each sub-tab
    build_documents_tab(documents_tab)
    build_templates_tab(templates_tab)