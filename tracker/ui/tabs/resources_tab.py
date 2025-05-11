import tkinter as tk
from tkinter import ttk
from tracker.ui.tabs.resources.documents_tab import build_documents_tab
from tracker.ui.tabs.resources.templates_tab import build_templates_tab

def build_resources_tab(parent):
    """Build the resources tab with documents and templates"""
    resources_notebook = ttk.Notebook(parent)
    resources_notebook.pack(fill="both", expand=True)
    
    documents_tab = ttk.Frame(resources_notebook)
    templates_tab = ttk.Frame(resources_notebook)
    
    resources_notebook.add(documents_tab, text="Documents")
    resources_notebook.add(templates_tab, text="Message Templates")
    
    build_documents_tab(documents_tab)
    
    build_templates_tab(templates_tab)