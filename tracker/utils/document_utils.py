import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import subprocess
import tempfile
from tracker.core.models import Document, Contact, Application

def open_document(doc_id, parent=None):
    """Open a document with the default application"""
    document = Document.get_by_id(doc_id)
    
    if not document:
        messagebox.showerror("Error", "Document not found.")
        return
    
    temp_dir = os.path.join(os.path.expanduser("~"), ".outreach_tracker")
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_path = os.path.join(temp_dir, f"{document.name}.{document.file_type}")
    
    try:
        with open(temp_path, "wb") as f:
            f.write(document.file_content)
        
        if os.name == 'nt':
            os.startfile(temp_path)
        elif os.name == 'posix':
            opener = 'open' if os.uname().sysname == 'Darwin' else 'xdg-open'
            subprocess.call([opener, temp_path])
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open document: {e}")

def view_document_details(doc_id, parent):
    """View document details in a popup"""
    document = Document.get_by_id(doc_id)
    
    if not document:
        messagebox.showerror("Error", "Document not found.")
        return
    
    try:
        date = datetime.strptime(document.created_at, "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%Y")
    except:
        date = document.created_at or ""

    popup = tk.Toplevel(parent)
    popup.title(f"Document Details: {document.name}")
    popup.geometry("500x400")
    popup.transient(parent)
    
    details_frame = ttk.LabelFrame(popup, text="Document Information")
    details_frame.pack(fill="x", padx=10, pady=10, expand=False)
    
    ttk.Label(details_frame, text=f"Name: {document.name}").pack(anchor="w", padx=10, pady=2)
    ttk.Label(details_frame, text=f"Type: {document.type}").pack(anchor="w", padx=10, pady=2)
    ttk.Label(details_frame, text=f"Version: {document.version}").pack(anchor="w", padx=10, pady=2)
    ttk.Label(details_frame, text=f"File Format: {document.file_type.upper()}").pack(anchor="w", padx=10, pady=2)
    ttk.Label(details_frame, text=f"Created: {date}").pack(anchor="w", padx=10, pady=2)
    
    if document.notes:
        notes_frame = ttk.LabelFrame(popup, text="Notes")
        notes_frame.pack(fill="both", padx=10, pady=10, expand=True)
        
        notes_text = tk.Text(notes_frame, wrap="word")
        notes_scrollbar = ttk.Scrollbar(notes_frame, command=notes_text.yview)
        notes_text.configure(yscrollcommand=notes_scrollbar.set)
        
        notes_text.pack(side="left", fill="both", expand=True)
        notes_scrollbar.pack(side="right", fill="y")
        
        notes_text.insert("1.0", document.notes)
        notes_text.config(state="disabled")
    
    button_frame = ttk.Frame(popup)
    button_frame.pack(fill="x", pady=10)
    
    open_btn = ttk.Button(button_frame, text="Open Document", command=lambda: open_document(doc_id))
    open_btn.pack(side="left", padx=5)
    
    close_btn = ttk.Button(button_frame, text="Close", command=popup.destroy)
    close_btn.pack(side="right", padx=5)

def unlink_document(doc_id, item_id, item_type, parent=None, callback=None):
    """Unlink a document from an item (contact or application)"""
    if messagebox.askyesno("Confirm", "Remove link to this document?"):
        document = Document.get_by_id(doc_id)
        if document:
            document.unlink_from(item_type, item_id)
            
            if callback:
                callback()

def upload_document(parent, item_id=None, item_type=None, callback=None):
    """Upload a new document and optionally link it to an item"""
    file_path = filedialog.askopenfilename(
        title="Upload Document",
        filetypes=[
            ("Document Files", "*.pdf *.doc *.docx *.txt"),
            ("PDF Files", "*.pdf"),
            ("Word Documents", "*.doc *.docx"),
            ("Text Files", "*.txt"),
            ("All Files", "*.*")
        ]
    )
    
    if not file_path:
        return
    
    upload_popup = tk.Toplevel(parent)
    upload_popup.title("Document Details")
    upload_popup.geometry("400x350")
    upload_popup.transient(parent)
    
    ttk.Label(upload_popup, text="Document Name:").pack(anchor="w", padx=20, pady=(20, 0))
    name_var = tk.StringVar(value=os.path.basename(file_path))
    name_entry = ttk.Entry(upload_popup, textvariable=name_var, width=40)
    name_entry.pack(anchor="w", padx=20)
    
    ttk.Label(upload_popup, text="Document Type:").pack(anchor="w", padx=20, pady=(10, 0))
    type_var = tk.StringVar(value="Resume")
    type_combo = ttk.Combobox(upload_popup, textvariable=type_var, 
                            values=["Resume", "Cover Letter", "Portfolio", "References", "Other"], 
                            state="readonly", width=20)
    type_combo.pack(anchor="w", padx=20)
    
    ttk.Label(upload_popup, text="Version:").pack(anchor="w", padx=20, pady=(10, 0))
    version_var = tk.StringVar(value="1.0")
    version_entry = ttk.Entry(upload_popup, textvariable=version_var, width=20)
    version_entry.pack(anchor="w", padx=20)
    
    ttk.Label(upload_popup, text="Notes:").pack(anchor="w", padx=20, pady=(10, 0))
    notes_frame = ttk.Frame(upload_popup)
    notes_frame.pack(fill="x", padx=20, pady=(0, 5))
    
    notes_text = tk.Text(notes_frame, wrap="word", height=5)
    notes_scrollbar = ttk.Scrollbar(notes_frame, orient="vertical", command=notes_text.yview)
    notes_text.configure(yscrollcommand=notes_scrollbar.set)
    
    notes_text.pack(side="left", fill="both", expand=True)
    notes_scrollbar.pack(side="right", fill="y")
    
    def save_uploaded_document():
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            file_type = os.path.splitext(file_path)[1][1:] or "txt"
            
            document = Document(
                name=name_var.get(),
                type=type_var.get(),
                version=version_var.get(),
                file_content=file_content,
                file_type=file_type,
                notes=notes_text.get("1.0", "end-1c")
            )
            document.save()
            
            if item_id and item_type:
                document.link_to(item_type, item_id)
            
            upload_popup.destroy()
            
            if callback:
                callback()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload document: {e}")
    
    button_frame = ttk.Frame(upload_popup)
    button_frame.pack(pady=15)
    
    save_button = ttk.Button(button_frame, text="Save & Link Document" if item_id else "Save Document", 
                          command=save_uploaded_document)
    save_button.pack(side="left", padx=5)
    
    cancel_button = ttk.Button(button_frame, text="Cancel", command=upload_popup.destroy)
    cancel_button.pack(side="left", padx=5)

def manage_linked_documents(item_id, item_type, parent):
    """
    Manage documents linked to a contact or application
    
    Parameters:
    - item_id: ID of the contact or application
    - item_type: 'contact' or 'application'
    - parent: Parent window
    """
    if item_type == 'contact':
        item = Contact.get_by_id(item_id)
        if not item:
            messagebox.showerror("Error", "Contact not found.")
            return
        item_title = f"{item.name} at {item.company}"
    else:
        item = Application.get_by_id(item_id)
        if not item:
            messagebox.showerror("Error", "Application not found.")
            return
        item_title = f"{item.title} at {item.name}"
    
    popup = tk.Toplevel(parent)
    popup.title(f"Manage Documents for: {item.name if item_type == 'contact' else item.title}")
    popup.geometry("700x500")
    popup.transient(parent)
    
    tk.Label(popup, text=f"Link Documents to: {item_title}", font=("Arial", 12, "bold")).pack(pady=10)
    
    frame = ttk.Frame(popup)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    columns = ("Linked?", "Name", "Type", "Version", "Date")
    doc_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="none")
    
    doc_tree.heading("Linked?", text="Linked?")
    doc_tree.column("Linked?", width=50, anchor="center")
    
    for col in columns[1:]:
        doc_tree.heading(col, text=col)
        doc_tree.column(col, width=100, anchor="w")
    
    doc_scrollbar = ttk.Scrollbar(frame, orient="vertical", command=doc_tree.yview)
    doc_tree.configure(yscrollcommand=doc_scrollbar.set)
    
    doc_tree.pack(side="left", fill="both", expand=True)
    doc_scrollbar.pack(side="right", fill="y")
    
    checked_items = {}
    
    def load_documents():
        for item in doc_tree.get_children():
            doc_tree.delete(item)
        
        checked_items.clear()
        
        all_documents = Document.find_all()
        
        if item_type == 'contact':
            linked_docs = Contact.get_by_id(item_id).get_linked_documents()
        else:
            linked_docs = Application.get_by_id(item_id).get_linked_documents()
        
        linked_doc_ids = [doc.id for doc in linked_docs]
        
        for doc in all_documents:
            is_linked = doc.id in linked_doc_ids
            
            try:
                date = datetime.strptime(doc.created_at, "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%Y")
            except:
                date = doc.created_at or ""
            
            item_id_tree = doc_tree.insert("", "end", values=("✓" if is_linked else "✗", doc.name, doc.type, doc.version, date))
            
            checked_items[item_id_tree] = {
                "doc_id": doc.id,
                "checked": is_linked
            }
    
    def on_doc_tree_click(event):
        region = doc_tree.identify_region(event.x, event.y)
        if region == "cell":
            column = int(doc_tree.identify_column(event.x).replace('#', ''))
            if column == 1:
                item_id_tree = doc_tree.identify_row(event.y)
                if item_id_tree in checked_items:
                    checked_items[item_id_tree]["checked"] = not checked_items[item_id_tree]["checked"]
                    
                    values = list(doc_tree.item(item_id_tree, "values"))
                    values[0] = "✓" if checked_items[item_id_tree]["checked"] else "✗"
                    doc_tree.item(item_id_tree, values=values)
    
    doc_tree.bind("<Button-1>", on_doc_tree_click)
    
    def save_document_links():
        for tree_item_id, info in checked_items.items():
            doc_id = info["doc_id"]
            is_checked = info["checked"]
            document = Document.get_by_id(doc_id)
            
            if is_checked:
                document.link_to(item_type, item_id)
            else:
                document.unlink_from(item_type, item_id)
        
        messagebox.showinfo("Success", "Document links updated successfully!")
        popup.destroy()
    
    search_frame = ttk.Frame(popup)
    search_frame.pack(fill="x", pady=5)
    
    tk.Label(search_frame, text="Search:").pack(side="left")
    doc_search_var = tk.StringVar()
    doc_search = ttk.Entry(search_frame, textvariable=doc_search_var, width=30)
    doc_search.pack(side="left", padx=5)
    
    def search_documents():
        search_text = doc_search_var.get().strip().lower()
        if not search_text:
            load_documents()
            return
            
        for item_id in doc_tree.get_children():
            values = doc_tree.item(item_id, 'values')
            if search_text in values[1].lower() or search_text in values[2].lower():
                doc_tree.item(item_id, tags=('visible',))
            else:
                doc_tree.detach(item_id)
    
    search_btn = ttk.Button(search_frame, text="Search", command=search_documents)
    search_btn.pack(side="left", padx=5)
    
    upload_btn = ttk.Button(
        search_frame, 
        text="Upload New", 
        command=lambda: upload_document(popup, item_id, item_type, load_documents)
    )
    upload_btn.pack(side="right", padx=5)
    
    button_frame = ttk.Frame(popup)
    button_frame.pack(fill="x", pady=10)
    
    save_btn = ttk.Button(button_frame, text="Save Changes", command=save_document_links)
    save_btn.pack(side="left", padx=5)
    
    cancel_btn = ttk.Button(button_frame, text="Cancel", command=popup.destroy)
    cancel_btn.pack(side="left", padx=5)
    
    def view_selected_document():
        selected_items = doc_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select a document to view.")
            return
        
        item_id_tree = selected_items[0]
        if item_id_tree in checked_items:
            doc_id = checked_items[item_id_tree]["doc_id"]
            open_document(doc_id)
    
    view_btn = ttk.Button(button_frame, text="View Selected", command=view_selected_document)
    view_btn.pack(side="right", padx=5)
    
    load_documents()

def view_linked_documents(item_id, item_type, parent):
    """
    View documents linked to an item (contact or application)
    
    Parameters:
    - item_id: ID of the contact or application
    - item_type: 'contact' or 'application'
    - parent: Parent window
    """
    if item_type == 'contact':
        item = Contact.get_by_id(item_id)
        if not item:
            messagebox.showerror("Error", "Contact not found.")
            return
        item_title = f"{item.name} at {item.company}"
    else:
        item = Application.get_by_id(item_id)
        if not item:
            messagebox.showerror("Error", "Application not found.")
            return
        item_title = f"{item.title} at {item.name}"
    
    if item_type == 'contact':
        documents = Contact.get_by_id(item_id).get_linked_documents()
    else:
        documents = Application.get_by_id(item_id).get_linked_documents()
    
    popup = tk.Toplevel(parent)
    popup.title(f"Documents for: {item.name if item_type == 'contact' else item.title}")
    popup.geometry("600x400")
    popup.transient(parent)
    
    tk.Label(popup, text=f"Linked Documents for: {item_title}", font=("Arial", 12, "bold")).pack(pady=10)
    
    if not documents:
        tk.Label(popup, text=f"No documents linked to this {item_type}.").pack(pady=20)
        
        def open_doc_manager():
            popup.destroy()
            manage_linked_documents(item_id, item_type, parent)
            
        tk.Button(popup, text="Link Documents", command=open_doc_manager).pack(pady=10)
    else:
        frame = ttk.Frame(popup)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Name", "Type", "Version", "Date Added")
        doc_tree = ttk.Treeview(frame, columns=columns, show="headings")
        
        for col in columns:
            doc_tree.heading(col, text=col)
            doc_tree.column(col, width=100, anchor="w")
        
        doc_scrollbar = ttk.Scrollbar(frame, orient="vertical", command=doc_tree.yview)
        doc_tree.configure(yscrollcommand=doc_scrollbar.set)
        
        doc_tree.pack(side="left", fill="both", expand=True)
        doc_scrollbar.pack(side="right", fill="y")
        
        for doc in documents:
            try:
                date = datetime.strptime(doc.created_at, "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%Y")
            except:
                date = doc.created_at or ""
            
            doc_tree.insert("", "end", iid=doc.id, values=(doc.name, doc.type, doc.version, date))
        
        def on_doc_double_click(event):
            item_id_tree = doc_tree.identify_row(event.y)
            if item_id_tree:
                open_document(item_id_tree)
                
        doc_tree.bind("<Double-1>", on_doc_double_click)
        
        def show_doc_context_menu(event):
            item_id_tree = doc_tree.identify_row(event.y)
            if not item_id_tree:
                return
                
            doc_tree.selection_set(item_id_tree)
            
            context_menu = tk.Menu(doc_tree, tearoff=0)
            context_menu.add_command(
                label="Open Document", 
                command=lambda: open_document(item_id_tree)
            )
            context_menu.add_command(
                label="View Details", 
                command=lambda: view_document_details(item_id_tree, popup)
            )
            context_menu.add_separator()
            context_menu.add_command(
                label="Unlink Document", 
                command=lambda: unlink_document(
                    item_id_tree, item_id, item_type, 
                    parent=popup, 
                    callback=lambda: view_linked_documents(item_id, item_type, parent)
                )
            )
            
            context_menu.tk_popup(event.x_root, event.y_root)
        
        doc_tree.bind("<Button-3>", show_doc_context_menu)
        
        button_frame = ttk.Frame(popup)
        button_frame.pack(fill="x", pady=10)
        
        open_btn = ttk.Button(button_frame, text="Open Selected", 
                           command=lambda: open_document(doc_tree.selection()[0]) if doc_tree.selection() else None)
        open_btn.pack(side="left", padx=5)
        
        manage_btn = ttk.Button(button_frame, text="Manage Documents", 
                             command=lambda: (popup.destroy(), manage_linked_documents(item_id, item_type, parent)))
        manage_btn.pack(side="left", padx=5)
        
        close_btn = ttk.Button(button_frame, text="Close", command=popup.destroy)
        close_btn.pack(side="right", padx=5)