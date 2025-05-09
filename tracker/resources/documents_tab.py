import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
import os
import subprocess
import tempfile
from datetime import datetime
from tracker.database import get_connection
import base64
from io import BytesIO

# For PDF preview (optional - requires additional packages)
try:
    from PIL import Image, ImageTk
    import fitz  # PyMuPDF
    HAS_PDF_PREVIEW = True
except ImportError:
    HAS_PDF_PREVIEW = False

# Document types
DOCUMENT_TYPES = ["Resume", "Cover Letter", "Portfolio", "References", "Other"]

# Max file size for preview (5MB)
MAX_PREVIEW_SIZE = 5 * 1024 * 1024

def build_documents_tab(parent):
    # Use simple frames with pack instead of PanedWindow
    main_frame = tk.Frame(parent)
    main_frame.pack(fill="both", expand=True)
    
    # Create horizontal paned window without weight configuration
    paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
    paned_window.pack(fill="both", expand=True)
    
    # Left side - Document list
    list_frame = ttk.Frame(paned_window)
    
    # Top actions bar
    actions_frame = ttk.Frame(list_frame)
    actions_frame.pack(fill="x", pady=5)
    
    # Filter by type
    ttk.Label(actions_frame, text="Filter:").pack(side="left")
    filter_var = tk.StringVar(value="All")
    filter_combo = ttk.Combobox(actions_frame, textvariable=filter_var, 
                             values=["All"] + DOCUMENT_TYPES, 
                             state="readonly", width=15)
    filter_combo.pack(side="left", padx=5)
    
    # Upload button
    upload_button = ttk.Button(actions_frame, text="Upload Document",
                            command=lambda: upload_document())
    upload_button.pack(side="right", padx=5)
    
    # Search field
    search_var = tk.StringVar()
    search_entry = ttk.Entry(actions_frame, textvariable=search_var, width=20)
    search_entry.pack(side="right", padx=5)
    ttk.Label(actions_frame, text="Search:").pack(side="right")
    
    # Documents treeview
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
    
    # Right side - Preview panel
    preview_frame = ttk.LabelFrame(paned_window, text="Document Preview")
    
    # Preview content
    preview_content = ttk.Frame(preview_frame)
    preview_content.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Title and info display
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
    
    # Actual document preview area
    preview_area_frame = ttk.LabelFrame(preview_content, text="Content Preview")
    preview_area_frame.pack(fill="both", expand=True, pady=10)
    
    # Preview canvas for images/PDFs
    preview_canvas = tk.Canvas(preview_area_frame, bg="white")
    preview_canvas.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Text preview for text documents - initially hidden
    text_preview = tk.Text(preview_area_frame, wrap="word", height=20)
    text_preview_scrollbar = ttk.Scrollbar(preview_area_frame, orient="vertical", command=text_preview.yview)
    text_preview.configure(yscrollcommand=text_preview_scrollbar.set)
    
    # Notes and details
    notes_frame = ttk.LabelFrame(preview_content, text="Notes")
    notes_frame.pack(fill="x", expand=False, pady=10)
    
    notes_text = tk.Text(notes_frame, wrap="word", height=4, width=30)
    notes_scrollbar = ttk.Scrollbar(notes_frame, orient="vertical", command=notes_text.yview)
    notes_text.configure(yscrollcommand=notes_scrollbar.set)
    
    notes_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    notes_scrollbar.pack(side="right", fill="y", pady=5)
    notes_text.config(state="disabled")
    
    # Action buttons
    button_frame = ttk.Frame(preview_content)
    button_frame.pack(fill="x", pady=10)
    
    open_button = ttk.Button(button_frame, text="Open Document")
    open_button.pack(side="left", padx=5)
    
    edit_button = ttk.Button(button_frame, text="Edit Details")
    edit_button.pack(side="left", padx=5)
    
    delete_button = ttk.Button(button_frame, text="Delete Document")
    delete_button.pack(side="left", padx=5)
    
    usage_button = ttk.Button(button_frame, text="View Usage")
    usage_button.pack(side="left", padx=5)
    
    # Add the frames to the paned window without weights
    paned_window.add(list_frame)
    paned_window.add(preview_frame)
    
    # Current document tracking
    current_doc_id = None
    
    # Upload document function
    def upload_document():
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
        
        # Create a popup for document details
        popup = tk.Toplevel()
        popup.title("Document Details")
        popup.geometry("400x350")
        popup.transient(parent)
        
        # Document details form
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
            try:
                with open(file_path, "rb") as f:
                    file_content = f.read()
                
                file_type = os.path.splitext(file_path)[1][1:]  # Get extension without dot
                
                conn = get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO documents 
                    (name, type, version, file_content, file_type, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    name_var.get(),
                    type_var.get(),
                    version_var.get(),
                    file_content,
                    file_type,
                    notes_text.get("1.0", "end-1c")
                ))
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Success", "Document uploaded successfully!")
                popup.destroy()
                refresh_documents()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload document: {e}")
        
        # Buttons
        button_frame = ttk.Frame(popup)
        button_frame.pack(pady=15)
        
        save_button = ttk.Button(button_frame, text="Save Document", command=save_document)
        save_button.pack(side="left", padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=popup.destroy)
        cancel_button.pack(side="left", padx=5)
    
    # Refresh document list
    def refresh_documents():
        for item in tree.get_children():
            tree.delete(item)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT id, name, type, version, created_at FROM documents"
        params = []
        
        if filter_var.get() != "All":
            query += " WHERE type = ?"
            params.append(filter_var.get())
        
        if search_var.get():
            if "WHERE" in query:
                query += " AND (name LIKE ? OR version LIKE ? OR notes LIKE ?)"
            else:
                query += " WHERE (name LIKE ? OR version LIKE ? OR notes LIKE ?)"
            
            search_param = f"%{search_var.get()}%"
            params.extend([search_param, search_param, search_param])
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        
        for row in cursor.fetchall():
            doc_id = row[0]
            name = row[1]
            doc_type = row[2]
            version = row[3]
            try:
                date = datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%Y")
            except:
                date = row[4]
            
            tree.insert("", "end", iid=doc_id, values=(name, doc_type, version, date))
        
        conn.close()
    
    # Clear preview area
    def clear_preview_area():
        # Clear canvas
        preview_canvas.delete("all")
        preview_canvas.pack(fill="both", expand=True)
        
        # Hide and clear text preview
        text_preview.pack_forget()
        text_preview_scrollbar.pack_forget()
        text_preview.delete("1.0", "end")
    
    # Show document preview based on file type
    def show_document_preview(file_content, file_type):
        clear_preview_area()
        
        # If file is large (>5MB), don't attempt preview
        if len(file_content) > MAX_PREVIEW_SIZE:
            preview_canvas.create_text(
                preview_canvas.winfo_width() // 2, 
                preview_canvas.winfo_height() // 2,
                text="File is too large to preview.\nPlease use the 'Open Document' button.",
                justify=tk.CENTER
            )
            return
            
        # Handle different file types
        file_type = file_type.lower()
        
        if file_type == "txt":
            # Show text preview
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
                # Create temporary file for PyMuPDF
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(file_content)
                    tmp_path = tmp.name
                
                # Open PDF and render first page
                pdf_document = fitz.open(tmp_path)
                if pdf_document.page_count > 0:
                    page = pdf_document.load_page(0)  # First page
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    
                    # Convert to PIL Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Resize if needed
                    canvas_width = preview_canvas.winfo_width() or 400
                    canvas_height = preview_canvas.winfo_height() or 400
                    
                    # Keep aspect ratio
                    img_ratio = img.width / img.height
                    canvas_ratio = canvas_width / canvas_height
                    
                    if img_ratio > canvas_ratio:
                        # Image is wider than canvas
                        new_width = canvas_width
                        new_height = int(canvas_width / img_ratio)
                    else:
                        # Image is taller than canvas
                        new_height = canvas_height
                        new_width = int(canvas_height * img_ratio)
                    
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Create PhotoImage and display on canvas
                    photo = ImageTk.PhotoImage(img)
                    preview_canvas.create_image(canvas_width//2, canvas_height//2, image=photo, anchor=tk.CENTER)
                    
                    # Keep reference to prevent garbage collection
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
            # For other file types, show file type icon or message
            preview_canvas.create_text(
                preview_canvas.winfo_width() // 2, 
                preview_canvas.winfo_height() // 2,
                text=f"Preview not available for {file_type} files.\n\nUse 'Open Document' to view.",
                justify=tk.CENTER
            )

    # Show document details when selected
    def on_document_select(event):
        nonlocal current_doc_id
        
        selected_items = tree.selection()
        if not selected_items:
            return
        
        item_id = selected_items[0]
        current_doc_id = item_id
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, type, version, file_content, file_type, notes, created_at
            FROM documents WHERE id = ?
        ''', (item_id,))
        
        doc = cursor.fetchone()
        conn.close()
        
        if not doc:
            return
        
        name, doc_type, version, file_content, file_type, notes, created_at = doc
        
        # Update display
        title_label.config(text=name)
        type_label.config(text=f"Type: {doc_type}")
        version_label.config(text=f"Version: {version}")
        
        try:
            date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%Y")
        except:
            date = created_at
        
        date_label.config(text=f"Date Added: {date}")
        
        # Update notes
        notes_text.config(state="normal")
        notes_text.delete("1.0", "end")
        if notes:
            notes_text.insert("1.0", notes)
        notes_text.config(state="disabled")
        
        # Show document preview
        if file_content:
            show_document_preview(file_content, file_type)
        
        # Enable buttons
        open_button.config(state="normal")
        edit_button.config(state="normal")
        delete_button.config(state="normal")
        usage_button.config(state="normal")
    
    tree.bind("<<TreeviewSelect>>", on_document_select)
    
    # Context menu for documents
    def show_document_context_menu(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
        
        tree.selection_set(item_id)
        
        context_menu = tk.Menu(tree, tearoff=0)
        context_menu.add_command(label="Open Document", command=lambda: open_document(item_id))
        context_menu.add_command(label="Edit Details", command=lambda: edit_document_details(item_id))
        context_menu.add_command(label="View Usage", command=lambda: view_document_usage(item_id))
        context_menu.add_separator()
        context_menu.add_command(label="Delete", command=lambda: delete_document(item_id))
        
        context_menu.tk_popup(event.x_root, event.y_root)
    
    tree.bind("<Button-3>", show_document_context_menu)
    
    # Document actions
    def open_document(doc_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT file_content, file_type, name FROM documents WHERE id = ?", (doc_id,))
        doc = cursor.fetchone()
        conn.close()
        
        if not doc:
            messagebox.showerror("Error", "Document not found.")
            return
        
        file_content, file_type, name = doc
        
        # Create a temporary file and open it
        temp_dir = os.path.join(os.path.expanduser("~"), ".outreach_tracker")
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_path = os.path.join(temp_dir, f"{name}.{file_type}")
        
        try:
            with open(temp_path, "wb") as f:
                f.write(file_content)
            
            # Open with default application
            if os.name == 'nt':  # Windows
                os.startfile(temp_path)
            elif os.name == 'posix':  # macOS, Linux
                opener = 'open' if os.uname().sysname == 'Darwin' else 'xdg-open'
                subprocess.call([opener, temp_path])
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open document: {e}")
    
    def edit_document_details(doc_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, type, version, notes FROM documents WHERE id = ?", (doc_id,))
        doc = cursor.fetchone()
        conn.close()
        
        if not doc:
            messagebox.showerror("Error", "Document not found.")
            return
        
        name, doc_type, version, notes = doc
        
        # Create popup for editing
        popup = tk.Toplevel()
        popup.title("Edit Document Details")
        popup.geometry("400x350")
        popup.transient(parent)
        
        ttk.Label(popup, text="Document Name:").pack(anchor="w", padx=20, pady=(20, 0))
        name_var = tk.StringVar(value=name)
        name_entry = ttk.Entry(popup, textvariable=name_var, width=40)
        name_entry.pack(anchor="w", padx=20)
        
        ttk.Label(popup, text="Document Type:").pack(anchor="w", padx=20, pady=(10, 0))
        type_var = tk.StringVar(value=doc_type)
        type_combo = ttk.Combobox(popup, textvariable=type_var, 
                                values=DOCUMENT_TYPES, 
                                state="readonly", width=20)
        type_combo.pack(anchor="w", padx=20)
        
        ttk.Label(popup, text="Version:").pack(anchor="w", padx=20, pady=(10, 0))
        version_var = tk.StringVar(value=version)
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
        
        if notes:
            notes_text.insert("1.0", notes)
        
        def save_changes():
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE documents
                SET name = ?, type = ?, version = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                name_var.get(),
                type_var.get(),
                version_var.get(),
                notes_text.get("1.0", "end-1c"),
                doc_id
            ))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Success", "Document details updated.")
            popup.destroy()
            refresh_documents()
            
            # Update preview if this is the current document
            if doc_id == current_doc_id:
                on_document_select(None)
        
        button_frame = ttk.Frame(popup)
        button_frame.pack(pady=15)
        
        save_button = ttk.Button(button_frame, text="Save Changes", command=save_changes)
        save_button.pack(side="left", padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=popup.destroy)
        cancel_button.pack(side="left", padx=5)
    
    def delete_document(doc_id):
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this document?")
        if not confirm:
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Delete document
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        
        # Also delete any usage records
        cursor.execute("DELETE FROM document_usage WHERE document_id = ?", (doc_id,))
        
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Success", "Document deleted successfully.")
        refresh_documents()
        
        # Clear preview if this was the current document
        if doc_id == current_doc_id:
            title_label.config(text="Select a document to preview")
            type_label.config(text="Type: ")
            version_label.config(text="Version: ")
            date_label.config(text="Date: ")
            
            notes_text.config(state="normal")
            notes_text.delete("1.0", "end")
            notes_text.config(state="disabled")
            
            clear_preview_area()
            
            # Disable buttons
            open_button.config(state="disabled")
            edit_button.config(state="disabled")
            delete_button.config(state="disabled")
            usage_button.config(state="disabled")
    
    def view_document_usage(doc_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get document name
        cursor.execute("SELECT name FROM documents WHERE id = ?", (doc_id,))
        doc_name = cursor.fetchone()[0]
        
        # Get usage information
        cursor.execute('''
            SELECT u.id, u.related_type, u.related_id, u.created_at,
                CASE 
                    WHEN u.related_type = 'contact' THEN o.name
                    WHEN u.related_type = 'application' THEN a.title || ' at ' || a.name
                    ELSE 'Unknown'
                END as item_name
            FROM document_usage u
            LEFT JOIN outreaches o ON u.related_id = o.id AND u.related_type = 'contact'
            LEFT JOIN applications a ON u.related_id = a.id AND u.related_type = 'application'
            WHERE u.document_id = ?
        ''', (doc_id,))
        
        usage_data = cursor.fetchall()
        conn.close()
        
        # Create popup to display usage
        popup = tk.Toplevel()
        popup.title(f"Document Usage: {doc_name}")
        popup.geometry("600x400")
        popup.transient(parent)
        
        ttk.Label(popup, text=f"Usage History for: {doc_name}", font=("Arial", 12, "bold")).pack(pady=10)
        
        if not usage_data:
            ttk.Label(popup, text="This document hasn't been used yet.").pack(pady=20)
        else:
            # Create treeview to display usage
            columns = ("Used For", "Item", "Date Used")
            usage_tree = ttk.Treeview(popup, columns=columns, show="headings")
            
            for col in columns:
                usage_tree.heading(col, text=col)
                usage_tree.column(col, width=150, anchor="w")
            
            scrollbar = ttk.Scrollbar(popup, orient="vertical", command=usage_tree.yview)
            usage_tree.configure(yscrollcommand=scrollbar.set)
            
            usage_tree.pack(fill="both", expand=True, padx=10, pady=10)
            scrollbar.pack(side="right", fill="y")
            
            for usage in usage_data:
                usage_id, related_type, related_id, created_at, item_name = usage
                
                related_type_display = "Contact" if related_type == "contact" else "Application"
                
                try:
                    date_used = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%Y")
                except:
                    date_used = created_at
                
                usage_tree.insert("", "end", iid=usage_id, values=(related_type_display, item_name, date_used))
        
        ttk.Button(popup, text="Close", command=popup.destroy).pack(pady=10)
    
    # Connect button actions
    open_button.config(command=lambda: open_document(current_doc_id), state="disabled")
    edit_button.config(command=lambda: edit_document_details(current_doc_id), state="disabled")
    delete_button.config(command=lambda: delete_document(current_doc_id), state="disabled")
    usage_button.config(command=lambda: view_document_usage(current_doc_id), state="disabled")
    
    # Connect filter and search actions
    filter_combo.bind("<<ComboboxSelected>>", lambda e: refresh_documents())
    search_entry.bind("<Return>", lambda e: refresh_documents())
    
    # Initial load
    refresh_documents()
    
    # Set up the initial position of the sash to divide space roughly equally
    def configure_sash(event=None):
        width = paned_window.winfo_width()
        if width > 1:
            paned_window.sashpos(0, width // 2)
    
    paned_window.bind("<Configure>", configure_sash)
    
    # Adjust canvas and preview when window resizes
    def on_resize(event=None):
        # Only update if we have a document selected
        if current_doc_id:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT file_content, file_type FROM documents WHERE id = ?", (current_doc_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                file_content, file_type = result
                show_document_preview(file_content, file_type)
    
    preview_canvas.bind("<Configure>", on_resize)