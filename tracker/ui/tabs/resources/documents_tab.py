import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import subprocess
import tempfile
from datetime import datetime
from tracker.core.models import Document, Contact, Application
from tracker.core.database import get_connection
from tracker.utils.ui_components import create_search_frame, create_filter_combobox, truncate_text, format_date
from tracker.utils.document_utils import open_document as utils_open_document

try:
    from PIL import Image, ImageTk
    import fitz
    HAS_PDF_PREVIEW = True
except ImportError:
    HAS_PDF_PREVIEW = False

DOCUMENT_TYPES = ["Resume", "Cover Letter", "Portfolio", "References", "Other"]
MAX_PREVIEW_SIZE = 5 * 1024 * 1024

def build_documents_tab(parent):
    main_frame = tk.Frame(parent)
    main_frame.pack(fill="both", expand=True)
    
    paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
    paned_window.pack(fill="both", expand=True)
    
    list_frame = ttk.Frame(paned_window)
    
    actions_frame = ttk.Frame(list_frame)
    actions_frame.pack(fill="x", pady=5)
    
    filter_var = create_filter_combobox(
        actions_frame, 
        "Filter:", 
        ["All"] + DOCUMENT_TYPES,
        lambda: refresh_documents()
    )
    
    upload_button = ttk.Button(actions_frame, text="Upload Document",
                            command=lambda: upload_document())
    upload_button.pack(side="right", padx=5)
    
    search_frame_obj, search_var = create_search_frame(
        list_frame,
        search_callback=lambda: refresh_documents(),
        reset_callback=lambda: (search_var.set(""), filter_var.set("All"), refresh_documents())
    )
    
    tree_frame = ttk.Frame(list_frame)
    tree_frame.pack(fill="both", expand=True, pady=5)
    
    columns = ("Name", "Type", "Version", "Date Added")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
    
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100, anchor="w")
    
    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    preview_frame = ttk.LabelFrame(paned_window, text="Document Preview")
    
    preview_content = ttk.Frame(preview_frame)
    preview_content.pack(fill="both", expand=True, padx=10, pady=10)
    
    title_label = ttk.Label(preview_content, text="Select a document to preview", font=("Arial", 14, "bold"))
    title_label.pack(pady=10)
    
    info_frame = ttk.Frame(preview_content)
    info_frame.pack(fill="x", pady=5)
    
    type_label = ttk.Label(info_frame, text="Type: ")
    type_label.grid(row=0, column=0, sticky="w", padx=5, pady=2)
    
    version_label = ttk.Label(info_frame, text="Version: ")
    version_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)
    
    date_label = ttk.Label(info_frame, text="Date: ")
    date_label.grid(row=2, column=0, sticky="w", padx=5, pady=2)
    
    preview_area_frame = ttk.LabelFrame(preview_content, text="Content Preview")
    preview_area_frame.pack(fill="both", expand=True, pady=10)
    
    preview_canvas = tk.Canvas(preview_area_frame, bg="white")
    preview_canvas.pack(fill="both", expand=True, padx=5, pady=5)
    
    text_preview = tk.Text(preview_area_frame, wrap="word", height=20)
    text_preview_scrollbar = ttk.Scrollbar(preview_area_frame, orient="vertical", command=text_preview.yview)
    text_preview.configure(yscrollcommand=text_preview_scrollbar.set)
    
    notes_frame = ttk.LabelFrame(preview_content, text="Notes")
    notes_frame.pack(fill="x", expand=False, pady=10)
    
    notes_text = tk.Text(notes_frame, wrap="word", height=4, width=30)
    notes_scrollbar = ttk.Scrollbar(notes_frame, orient="vertical", command=notes_text.yview)
    notes_text.configure(yscrollcommand=notes_scrollbar.set)
    
    notes_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    notes_scrollbar.pack(side="right", fill="y", pady=5)
    notes_text.config(state="disabled")
    
    button_frame = ttk.Frame(preview_content)
    button_frame.pack(fill="x", pady=10)
    
    open_button = ttk.Button(button_frame, text="Open Document")
    open_button.pack(side="left", padx=5)
    
    link_button = ttk.Button(button_frame, text="Link to...")
    link_button.pack(side="left", padx=5)
    
    edit_button = ttk.Button(button_frame, text="Edit Details")
    edit_button.pack(side="left", padx=5)
    
    delete_button = ttk.Button(button_frame, text="Delete Document")
    delete_button.pack(side="left", padx=5)
    
    usage_button = ttk.Button(button_frame, text="View Usage")
    usage_button.pack(side="left", padx=5)
    
    paned_window.add(list_frame)
    paned_window.add(preview_frame)
    
    current_doc_id = None
    
    def upload_document():
        """Open file dialog to select and upload a new document"""
        file_path = filedialog.askopenfilename(
            title="Select Document",
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
        
        popup = tk.Toplevel()
        popup.title("Document Details")
        popup.geometry("400x350")
        popup.transient(parent)
        
        ttk.Label(popup, text="Document Name:").pack(anchor="w", padx=20, pady=(20, 0))
        name_var = tk.StringVar(value=os.path.basename(file_path))
        name_entry = ttk.Entry(popup, textvariable=name_var, width=40)
        name_entry.pack(anchor="w", padx=20)
        
        ttk.Label(popup, text="Document Type:").pack(anchor="w", padx=20, pady=(10, 0))
        type_var = tk.StringVar(value=DOCUMENT_TYPES[0])
        type_combo = ttk.Combobox(popup, textvariable=type_var, 
                                values=DOCUMENT_TYPES, 
                                state="readonly", width=20)
        type_combo.pack(anchor="w", padx=20)
        
        ttk.Label(popup, text="Version:").pack(anchor="w", padx=20, pady=(10, 0))
        version_var = tk.StringVar(value="1.0")
        version_entry = ttk.Entry(popup, textvariable=version_var, width=20)
        version_entry.pack(anchor="w", padx=20)
        
        ttk.Label(popup, text="Notes:").pack(anchor="w", padx=20, pady=(10, 0))
        notes_frame = ttk.Frame(popup)
        notes_frame.pack(fill="x", padx=20, pady=(0, 5))
        
        notes_text = tk.Text(notes_frame, wrap="word", height=5)
        notes_scrollbar = ttk.Scrollbar(notes_frame, orient="vertical", command=notes_text.yview)
        notes_text.configure(yscrollcommand=notes_scrollbar.set)
        
        notes_text.pack(side="left", fill="both", expand=True)
        notes_scrollbar.pack(side="right", fill="y")
        
        def save_document():
            """Save the uploaded document to the database"""
            try:
                with open(file_path, "rb") as f:
                    file_content = f.read()
                
                file_type = os.path.splitext(file_path)[1][1:] or "txt"
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                document = Document(
                    name=name_var.get(),
                    type=type_var.get(),
                    version=version_var.get(),
                    file_content=file_content,
                    file_type=file_type,
                    notes=notes_text.get("1.0", "end-1c"),
                    created_at=current_time
                )
                document.save()
                
                messagebox.showinfo("Success", "Document uploaded successfully!")
                popup.destroy()
                refresh_documents()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload document: {e}")
        
        button_frame = ttk.Frame(popup)
        button_frame.pack(pady=15)
        
        save_button = ttk.Button(button_frame, text="Save Document", command=save_document)
        save_button.pack(side="left", padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=popup.destroy)
        cancel_button.pack(side="left", padx=5)
    
    def link_document(doc_id, doc_name):
        """Open a dialog to link document to contacts or applications"""
        popup = tk.Toplevel()
        popup.title(f"Link Document: {doc_name}")
        popup.geometry("600x500")
        popup.transient(parent)
        
        tab_control = ttk.Notebook(popup)
        tab_control.pack(fill="both", expand=True, padx=10, pady=10)
        
        contacts_tab = ttk.Frame(tab_control)
        applications_tab = ttk.Frame(tab_control)
        
        tab_control.add(contacts_tab, text="Contacts")
        tab_control.add(applications_tab, text="Applications")
        
        contacts_frame = ttk.Frame(contacts_tab)
        contacts_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        search_frame = ttk.Frame(contacts_frame)
        search_frame.pack(fill="x", pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side="left")
        contact_search_var = tk.StringVar()
        contact_search = ttk.Entry(search_frame, textvariable=contact_search_var, width=30)
        contact_search.pack(side="left", padx=5)
        
        contacts_list_frame = ttk.Frame(contacts_frame)
        contacts_list_frame.pack(fill="both", expand=True, pady=5)
        
        contacts_columns = ("Name", "Company", "Title")
        contacts_tree = ttk.Treeview(contacts_list_frame, columns=contacts_columns, show="headings", selectmode="extended")
        
        for col in contacts_columns:
            contacts_tree.heading(col, text=col)
            contacts_tree.column(col, width=100)
        
        contacts_scrollbar = ttk.Scrollbar(contacts_list_frame, orient="vertical", command=contacts_tree.yview)
        contacts_tree.configure(yscrollcommand=contacts_scrollbar.set)
        
        contacts_tree.pack(side="left", fill="both", expand=True)
        contacts_scrollbar.pack(side="right", fill="y")
        
        applications_frame = ttk.Frame(applications_tab)
        applications_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        app_search_frame = ttk.Frame(applications_frame)
        app_search_frame.pack(fill="x", pady=5)
        
        ttk.Label(app_search_frame, text="Search:").pack(side="left")
        app_search_var = tk.StringVar()
        app_search = ttk.Entry(app_search_frame, textvariable=app_search_var, width=30)
        app_search.pack(side="left", padx=5)
        
        app_list_frame = ttk.Frame(applications_frame)
        app_list_frame.pack(fill="both", expand=True, pady=5)
        
        app_columns = ("Job Title", "Company", "Status")
        app_tree = ttk.Treeview(app_list_frame, columns=app_columns, show="headings", selectmode="extended")
        
        for col in app_columns:
            app_tree.heading(col, text=col)
            app_tree.column(col, width=100)
        
        app_scrollbar = ttk.Scrollbar(app_list_frame, orient="vertical", command=app_tree.yview)
        app_tree.configure(yscrollcommand=app_scrollbar.set)
        
        app_tree.pack(side="left", fill="both", expand=True)
        app_scrollbar.pack(side="right", fill="y")
        
        def load_contacts(search_text=""):
            """Load contacts and preselect those linked to the document"""
            for item in contacts_tree.get_children():
                contacts_tree.delete(item)
            
            document = Document.get_by_id(doc_id)
            if not document:
                return
                
            linked_contacts = []
            for usage in document.find_related('contact'):
                linked_contacts.append(usage.id)
                
            contacts = Contact.find_all()
            if search_text:
                contacts = [c for c in contacts if search_text.lower() in c.name.lower() 
                           or search_text.lower() in c.company.lower()]
            
            for contact in contacts:
                contacts_tree.insert("", "end", iid=contact.id, values=(
                    contact.name, contact.company, contact.title))
                if contact.id in linked_contacts:
                    contacts_tree.selection_add(contact.id)
        
        def load_applications(search_text=""):
            """Load applications and preselect those linked to the document"""
            for item in app_tree.get_children():
                app_tree.delete(item)
            
            document = Document.get_by_id(doc_id)
            if not document:
                return
                
            linked_applications = []
            for usage in document.find_related('application'):
                linked_applications.append(usage.id)
                
            applications = Application.find_all()
            if search_text:
                applications = [a for a in applications if search_text.lower() in a.title.lower() 
                               or search_text.lower() in a.name.lower()]
            
            for application in applications:
                app_tree.insert("", "end", iid=application.id, values=(
                    application.title, application.name, application.status))
                if application.id in linked_applications:
                    app_tree.selection_add(application.id)
        
        def search_contacts():
            load_contacts(contact_search_var.get())
        
        def search_applications():
            load_applications(app_search_var.get())
        
        contact_search.bind("<Return>", lambda e: search_contacts())
        app_search.bind("<Return>", lambda e: search_applications())
        
        ttk.Button(search_frame, text="Search", command=search_contacts).pack(side="left", padx=5)
        ttk.Button(app_search_frame, text="Search", command=search_applications).pack(side="left", padx=5)
        
        actions_frame = ttk.Frame(popup)
        actions_frame.pack(fill="x", pady=10)
        
        def link_selected():
            """Save selected links between document and contacts/applications"""
            tab_index = tab_control.index(tab_control.select())
            document = Document.get_by_id(doc_id)
            
            if not document:
                messagebox.showerror("Error", "Document not found")
                return
                
            if tab_index == 0:
                selected_items = contacts_tree.selection()
                document.unlink_all_from('contact')
                
                for item_id in selected_items:
                    document.link_to('contact', item_id)
                
                message = f"Document linked to {len(selected_items)} contact(s) successfully!"
                
            else:
                selected_items = app_tree.selection()
                document.unlink_all_from('application')
                
                for item_id in selected_items:
                    document.link_to('application', item_id)
                
                message = f"Document linked to {len(selected_items)} application(s) successfully!"
            
            messagebox.showinfo("Success", message)
            popup.destroy()
        
        link_btn = ttk.Button(actions_frame, text="Save Links", command=link_selected)
        link_btn.pack(side="left", padx=5)
        
        cancel_btn = ttk.Button(actions_frame, text="Cancel", command=popup.destroy)
        cancel_btn.pack(side="left", padx=5)
        
        load_contacts()
        load_applications()
    
    def refresh_documents():
        """Refresh the document list with filtering applied"""
        for item in tree.get_children():
            tree.delete(item)
        
        where_clause = ""
        params = []
        
        if filter_var.get() != "All":
            where_clause = "type = ?"
            params.append(filter_var.get())
        
        if search_var.get():
            search_param = f"%{search_var.get()}%"
            if where_clause:
                where_clause += " AND (name LIKE ? OR version LIKE ? OR notes LIKE ?)"
            else:
                where_clause = "(name LIKE ? OR version LIKE ? OR notes LIKE ?)"
            params.extend([search_param, search_param, search_param])
        
        documents = Document.find_all(where_clause, tuple(params))
        
        for doc in documents:
            date_str = format_date(doc.created_at, "%Y-%m-%d %H:%M:%S", "%m/%d/%Y")
            tree.insert("", "end", iid=doc.id, values=(doc.name, doc.type, doc.version, date_str))
    
    def clear_preview_area():
        """Clear the document preview area"""
        preview_canvas.delete("all")
        preview_canvas.pack(fill="both", expand=True)
        
        text_preview.pack_forget()
        text_preview_scrollbar.pack_forget()
        text_preview.delete("1.0", "end")
    
    def show_document_preview(file_content, file_type):
        """Display preview of document content if possible"""
        clear_preview_area()
        
        if len(file_content) > MAX_PREVIEW_SIZE:
            preview_canvas.create_text(
                preview_canvas.winfo_width() // 2, 
                preview_canvas.winfo_height() // 2,
                text="File is too large to preview.\nPlease use the 'Open Document' button.",
                justify=tk.CENTER
            )
            return
            
        file_type = file_type.lower()
        
        if file_type == "txt":
            preview_canvas.pack_forget()
            text_preview.pack(side="left", fill="both", expand=True)
            text_preview_scrollbar.pack(side="right", fill="y")
            
            try:
                text_content = file_content.decode('utf-8')
                text_preview.insert("1.0", text_content)
                text_preview.config(state="disabled")
            except UnicodeDecodeError:
                text_preview.insert("1.0", "Unable to decode text content.")
                text_preview.config(state="disabled")
                
        elif file_type == "pdf" and HAS_PDF_PREVIEW:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(file_content)
                    tmp_path = tmp.name
                
                pdf_document = fitz.open(tmp_path)
                if pdf_document.page_count > 0:
                    page = pdf_document.load_page(0)
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    canvas_width = preview_canvas.winfo_width() or 400
                    canvas_height = preview_canvas.winfo_height() or 400
                    
                    img_ratio = img.width / img.height
                    canvas_ratio = canvas_width / canvas_height
                    
                    if img_ratio > canvas_ratio:
                        new_width = canvas_width
                        new_height = int(canvas_width / img_ratio)
                    else:
                        new_height = canvas_height
                        new_width = int(canvas_height * img_ratio)
                    
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    photo = ImageTk.PhotoImage(img)
                    preview_canvas.create_image(canvas_width//2, canvas_height//2, image=photo, anchor=tk.CENTER)
                    
                    preview_canvas.image = photo
                    
                pdf_document.close()
                os.unlink(tmp_path)
            except Exception as e:
                preview_canvas.create_text(
                    preview_canvas.winfo_width() // 2, 
                    preview_canvas.winfo_height() // 2,
                    text=f"Failed to preview PDF: {e}",
                    justify=tk.CENTER
                )
        else:
            preview_canvas.create_text(
                preview_canvas.winfo_width() // 2, 
                preview_canvas.winfo_height() // 2,
                text=f"Preview not available for {file_type} files.\n\nUse 'Open Document' to view.",
                justify=tk.CENTER
            )

    def on_document_select(event):
        """Handle selection of a document in the tree view"""
        nonlocal current_doc_id
        
        selected_items = tree.selection()
        if not selected_items:
            return
        
        item_id = selected_items[0]
        current_doc_id = item_id
        
        document = Document.get_by_id(item_id)
        
        if not document:
            return
        
        title_label.config(text=document.name)
        type_label.config(text=f"Type: {document.type}")
        version_label.config(text=f"Version: {document.version}")
        
        date_str = format_date(document.created_at, "%Y-%m-%d %H:%M:%S", "%m/%d/%Y")
        date_label.config(text=f"Date Added: {date_str}")
        
        notes_text.config(state="normal")
        notes_text.delete("1.0", "end")
        if document.notes:
            notes_text.insert("1.0", document.notes)
        notes_text.config(state="disabled")
        
        if document.file_content:
            show_document_preview(document.file_content, document.file_type)
        
        open_button.config(state="normal")
        link_button.config(state="normal")
        edit_button.config(state="normal")
        delete_button.config(state="normal")
        usage_button.config(state="normal")
    
    tree.bind("<<TreeviewSelect>>", on_document_select)
    
    def show_document_context_menu(event):
        """Show context menu for right-click on document"""
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
        
        tree.selection_set(item_id)
        
        context_menu = tk.Menu(tree, tearoff=0)
        context_menu.add_command(label="Open Document", command=lambda: open_document(item_id))
        context_menu.add_command(label="Link Document", command=lambda: link_document(item_id, tree.item(item_id, 'values')[0]))
        context_menu.add_command(label="Edit Details", command=lambda: edit_document_details(item_id))
        context_menu.add_command(label="View Usage", command=lambda: view_document_usage(item_id))
        context_menu.add_separator()
        context_menu.add_command(label="Delete", command=lambda: delete_document(item_id))
        
        context_menu.tk_popup(event.x_root, event.y_root)
    
    tree.bind("<Button-3>", show_document_context_menu)
    
    def open_document(doc_id):
        """Open document with system's default application"""
        utils_open_document(doc_id, parent)
    
    def edit_document_details(doc_id):
        """Edit document metadata"""
        document = Document.get_by_id(doc_id)
        if not document:
            messagebox.showerror("Error", "Document not found.")
            return
        
        popup = tk.Toplevel()
        popup.title("Edit Document Details")
        popup.geometry("400x350")
        popup.transient(parent)
        
        ttk.Label(popup, text="Document Name:").pack(anchor="w", padx=20, pady=(20, 0))
        name_var = tk.StringVar(value=document.name)
        name_entry = ttk.Entry(popup, textvariable=name_var, width=40)
        name_entry.pack(anchor="w", padx=20)
        
        ttk.Label(popup, text="Document Type:").pack(anchor="w", padx=20, pady=(10, 0))
        type_var = tk.StringVar(value=document.type)
        type_combo = ttk.Combobox(popup, textvariable=type_var, 
                                values=DOCUMENT_TYPES, 
                                state="readonly", width=20)
        type_combo.pack(anchor="w", padx=20)
        
        ttk.Label(popup, text="Version:").pack(anchor="w", padx=20, pady=(10, 0))
        version_var = tk.StringVar(value=document.version)
        version_entry = ttk.Entry(popup, textvariable=version_var, width=20)
        version_entry.pack(anchor="w", padx=20)
        
        ttk.Label(popup, text="Notes:").pack(anchor="w", padx=20, pady=(10, 0))
        notes_frame = ttk.Frame(popup)
        notes_frame.pack(fill="x", padx=20, pady=(0, 5))
        
        notes_text = tk.Text(notes_frame, wrap="word", height=5)
        notes_scrollbar = ttk.Scrollbar(notes_frame, orient="vertical", command=notes_text.yview)
        notes_text.configure(yscrollcommand=notes_scrollbar.set)
        
        notes_text.pack(side="left", fill="both", expand=True)
        notes_scrollbar.pack(side="right", fill="y")
        
        if document.notes:
            notes_text.insert("1.0", document.notes)
        
        def save_changes():
            """Save document detail changes"""
            document.name = name_var.get()
            document.type = type_var.get()
            document.version = version_var.get()
            document.notes = notes_text.get("1.0", "end-1c")
            document.save()
            
            messagebox.showinfo("Success", "Document details updated.")
            popup.destroy()
            refresh_documents()
            
            if doc_id == current_doc_id:
                on_document_select(None)
        
        button_frame = ttk.Frame(popup)
        button_frame.pack(pady=15)
        
        save_button = ttk.Button(button_frame, text="Save Changes", command=save_changes)
        save_button.pack(side="left", padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=popup.destroy)
        cancel_button.pack(side="left", padx=5)
    
    def delete_document(doc_id):
        """Delete document after confirmation"""
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this document?")
        if not confirm:
            return
        
        document = Document.get_by_id(doc_id)
        if document:
            document.delete()
        
        messagebox.showinfo("Success", "Document deleted successfully.")
        refresh_documents()
        
        if doc_id == current_doc_id:
            title_label.config(text="Select a document to preview")
            type_label.config(text="Type: ")
            version_label.config(text="Version: ")
            date_label.config(text="Date: ")
            
            notes_text.config(state="normal")
            notes_text.delete("1.0", "end")
            notes_text.config(state="disabled")
            
            clear_preview_area()
            
            open_button.config(state="disabled")
            link_button.config(state="disabled")
            edit_button.config(state="disabled")
            delete_button.config(state="disabled")
            usage_button.config(state="disabled")
    
    def view_document_usage(doc_id):
        """View where document is being used"""
        document = Document.get_by_id(doc_id)
        if not document:
            messagebox.showerror("Error", "Document not found.")
            return
            
        popup = tk.Toplevel()
        popup.title(f"Document Usage: {document.name}")
        popup.geometry("600x400")
        popup.transient(parent)
        
        ttk.Label(popup, text=f"Usage History for: {document.name}", font=("Arial", 12, "bold")).pack(pady=10)
        
        contact_usages = document.find_related('contact')
        application_usages = document.find_related('application')
        
        if not contact_usages and not application_usages:
            ttk.Label(popup, text="This document hasn't been linked to any contacts or applications yet.").pack(pady=20)
            ttk.Label(popup, text="Use the 'Link to...' button to associate this document with contacts or applications.").pack()
        else:
            columns = ("Type", "Name", "Date Linked")
            usage_tree = ttk.Treeview(popup, columns=columns, show="headings")
            
            for col in columns:
                usage_tree.heading(col, text=col)
                usage_tree.column(col, width=150, anchor="w")
            
            scrollbar = ttk.Scrollbar(popup, orient="vertical", command=usage_tree.yview)
            usage_tree.configure(yscrollcommand=scrollbar.set)
            
            usage_tree.pack(fill="both", expand=True, padx=10, pady=10)
            scrollbar.pack(side="right", fill="y")
            
            for contact in contact_usages:
                contact = Contact.get_by_id(contact.id)
                if contact:
                    date_str = format_date(document.created_at, "%Y-%m-%d %H:%M:%S", "%m/%d/%Y")
                    usage_tree.insert("", "end", values=("Contact", contact.name, date_str))
            
            for app in application_usages:
                application = Application.get_by_id(app.id)
                if application:
                    item_name = f"{application.title} at {application.name}"
                    date_str = format_date(document.created_at, "%Y-%m-%d %H:%M:%S", "%m/%d/%Y")
                    usage_tree.insert("", "end", values=("Application", item_name, date_str))
        
        ttk.Button(popup, text="Close", command=popup.destroy).pack(pady=10)
        ttk.Button(popup, text="Link to More...", 
                command=lambda: (popup.destroy(), link_document(doc_id, document.name))).pack(pady=(0, 10))
    
    open_button.config(command=lambda: open_document(current_doc_id), state="disabled")
    link_button.config(command=lambda: link_document(current_doc_id, title_label.cget("text")), state="disabled")
    edit_button.config(command=lambda: edit_document_details(current_doc_id), state="disabled")
    delete_button.config(command=lambda: delete_document(current_doc_id), state="disabled")
    usage_button.config(command=lambda: view_document_usage(current_doc_id), state="disabled")
    
    def configure_sash(event=None):
        """Configure the paned window sash position"""
        width = paned_window.winfo_width()
        if width > 1:
            paned_window.sashpos(0, width // 2)
    
    paned_window.bind("<Configure>", configure_sash)
    
    def on_resize(event=None):
        """Update document preview when window is resized"""
        if current_doc_id:
            document = Document.get_by_id(current_doc_id)
            if document:
                show_document_preview(document.file_content, document.file_type)
    
    preview_canvas.bind("<Configure>", on_resize)
    
    refresh_documents()