import tkinter as tk
from tkinter import ttk, messagebox
from tracker.database import get_connection

# Template categories
TEMPLATE_CATEGORIES = ["Connection Request", "Follow-up", "Thank You", "Application", "Interview", "Other"]

def build_templates_tab(parent):
    # Use the same approach as in documents tab
    main_frame = tk.Frame(parent)
    main_frame.pack(fill="both", expand=True)
    
    paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
    paned_window.pack(fill="both", expand=True)
    
    # Left side - template list
    list_frame = ttk.Frame(paned_window)
    
    # Top actions bar
    actions_frame = ttk.Frame(list_frame)
    actions_frame.pack(fill="x", pady=5)
    
    # Filter by category
    ttk.Label(actions_frame, text="Filter:").pack(side="left")
    filter_var = tk.StringVar(value="All")
    filter_combo = ttk.Combobox(actions_frame, textvariable=filter_var, 
                             values=["All"] + TEMPLATE_CATEGORIES, 
                             state="readonly", width=15)
    filter_combo.pack(side="left", padx=5)
    
    # New template button
    new_button = ttk.Button(actions_frame, text="New Template",
                         command=lambda: create_new_template())
    new_button.pack(side="right", padx=5)
    
    # Search field
    search_var = tk.StringVar()
    search_entry = ttk.Entry(actions_frame, textvariable=search_var, width=20)
    search_entry.pack(side="right", padx=5)
    ttk.Label(actions_frame, text="Search:").pack(side="right")
    
    # Templates listbox with scrollbar
    list_container = ttk.Frame(list_frame)
    list_container.pack(fill="both", expand=True, pady=5)
    
    template_listbox = tk.Listbox(list_container, width=30)
    listbox_scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=template_listbox.yview)
    template_listbox.configure(yscrollcommand=listbox_scrollbar.set)
    
    template_listbox.pack(side="left", fill="both", expand=True)
    listbox_scrollbar.pack(side="right", fill="y")
    
    # Right side - Editor panel
    editor_frame = ttk.LabelFrame(paned_window, text="Template Editor")
    
    # Editor content
    editor_content = ttk.Frame(editor_frame)
    editor_content.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Template details
    ttk.Label(editor_content, text="Template Name:").pack(anchor="w")
    name_var = tk.StringVar()
    name_entry = ttk.Entry(editor_content, textvariable=name_var, width=40)
    name_entry.pack(fill="x", pady=(0, 10))
    
    ttk.Label(editor_content, text="Category:").pack(anchor="w")
    category_var = tk.StringVar(value=TEMPLATE_CATEGORIES[0])
    category_combo = ttk.Combobox(editor_content, textvariable=category_var, 
                               values=TEMPLATE_CATEGORIES,
                               state="readonly", width=20)
    category_combo.pack(anchor="w", pady=(0, 10))
    
    # Variables info
    variables_frame = ttk.LabelFrame(editor_content, text="Available Variables")
    variables_frame.pack(fill="x", pady=10)
    
    variables_text = "You can use these variables in your templates:\n"
    variables_text += "{name} - Contact's name\n"
    variables_text += "{company} - Company name\n"
    variables_text += "{title} - Job title\n"
    variables_text += "{my_name} - Your name"
    
    var_label = ttk.Label(variables_frame, text=variables_text, justify="left")
    var_label.pack(anchor="w", padx=5, pady=5)
    
    # Template content
    ttk.Label(editor_content, text="Template Content:").pack(anchor="w", pady=(10, 0))
    
    content_frame = ttk.Frame(editor_content)
    content_frame.pack(fill="both", expand=True, pady=(0, 10))
    
    template_text = tk.Text(content_frame, wrap="word", height=10)
    text_scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=template_text.yview)
    template_text.configure(yscrollcommand=text_scrollbar.set)
    
    template_text.pack(side="left", fill="both", expand=True)
    text_scrollbar.pack(side="right", fill="y")
    
    # Buttons
    button_frame = ttk.Frame(editor_content)
    button_frame.pack(fill="x")
    
    save_button = ttk.Button(button_frame, text="Save Template", 
                          command=lambda: save_template())
    save_button.pack(side="left", padx=5)
    
    delete_button = ttk.Button(button_frame, text="Delete Template",
                            command=lambda: delete_template(), state="disabled")
    delete_button.pack(side="left", padx=5)
    
    preview_button = ttk.Button(button_frame, text="Preview",
                             command=lambda: preview_template())
    preview_button.pack(side="left", padx=5)
    
    copy_button = ttk.Button(button_frame, text="Copy to Clipboard",
                          command=lambda: copy_to_clipboard())
    copy_button.pack(side="left", padx=5)
    
    # Add panes to paned window
    paned_window.add(list_frame)
    paned_window.add(editor_frame)
    
    # Set up the initial position of the sash to give more space to the editor
    def configure_sash(event=None):
        width = paned_window.winfo_width()
        if width > 1:
            paned_window.sashpos(0, width // 4)  # 1/4 for list, 3/4 for editor
    
    paned_window.bind("<Configure>", configure_sash)
    
    # Current template tracking
    current_template_id = None
    template_data = {}  # id -> (name, category)
    
    # Function to create a new template
    def create_new_template():
        nonlocal current_template_id
        current_template_id = None
        
        name_var.set("")
        category_var.set(TEMPLATE_CATEGORIES[0])
        template_text.delete("1.0", "end")
        
        delete_button.config(state="disabled")
        save_button.config(text="Save Template")
        
        name_entry.focus()
    
    # Refresh template list
    def refresh_templates():
        template_listbox.delete(0, "end")
        template_data.clear()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT id, name, category FROM message_templates"
        params = []
        
        if filter_var.get() != "All":
            query += " WHERE category = ?"
            params.append(filter_var.get())
        
        if search_var.get():
            if "WHERE" in query:
                query += " AND (name LIKE ? OR content LIKE ?)"
            else:
                query += " WHERE (name LIKE ? OR content LIKE ?)"
            
            search_param = f"%{search_var.get()}%"
            params.extend([search_param, search_param])
        
        query += " ORDER BY category, name"
        
        cursor.execute(query, params)
        
        for row in cursor.fetchall():
            template_id, name, category = row
            
            display_text = f"{name} [{category}]"
            template_listbox.insert("end", display_text)
            
            # Store ID at current index for later retrieval
            index = template_listbox.size() - 1
            template_data[index] = (template_id, name, category)
        
        conn.close()
    
    # Load template when selected
    def on_template_select(event):
        nonlocal current_template_id
        
        selected_indices = template_listbox.curselection()
        if not selected_indices:
            return
        
        index = selected_indices[0]
        if index not in template_data:
            return
        
        template_id, name, category = template_data[index]
        current_template_id = template_id
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT content FROM message_templates WHERE id = ?", (template_id,))
        content = cursor.fetchone()[0]
        conn.close()
        
        name_var.set(name)
        category_var.set(category)
        
        template_text.delete("1.0", "end")
        template_text.insert("1.0", content)
        
        delete_button.config(state="normal")
        save_button.config(text="Update Template")
    
    template_listbox.bind("<<ListboxSelect>>", on_template_select)
    
    # Save template function
    def save_template():
        name = name_var.get().strip()
        category = category_var.get()
        content = template_text.get("1.0", "end-1c").strip()
        
        if not name:
            messagebox.showwarning("Missing Information", "Please enter a template name.")
            return
        
        if not content:
            messagebox.showwarning("Missing Information", "Template content cannot be empty.")
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        
        if current_template_id:
            # Update existing template
            cursor.execute('''
                UPDATE message_templates
                SET name = ?, category = ?, content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, category, content, current_template_id))
            
            message = "Template updated successfully!"
        else:
            # Create new template
            cursor.execute('''
                INSERT INTO message_templates (name, category, content)
                VALUES (?, ?, ?)
            ''', (name, category, content))
            
            message = "Template created successfully!"
        
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Success", message)
        refresh_templates()
    
    # Delete template function
    def delete_template():
        if not current_template_id:
            return
        
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this template?")
        if not confirm:
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM message_templates WHERE id = ?", (current_template_id,))
        
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Success", "Template deleted successfully!")
        create_new_template()  # Reset form
        refresh_templates()
    
    # Preview template function
    def preview_template():
        content = template_text.get("1.0", "end-1c")
        
        # Sample data for preview
        sample_data = {
            "name": "John Smith",
            "company": "Example Corp",
            "title": "Software Engineer",
            "my_name": "Your Name"
        }
        
        # Replace variables
        try:
            preview_content = content.format(**sample_data)
            
            # Show preview in popup
            popup = tk.Toplevel()
            popup.title("Template Preview")
            popup.geometry("500x400")
            popup.transient(parent)
            
            ttk.Label(popup, text="Preview with sample data:", font=("Arial", 12, "bold")).pack(pady=10)
            
            preview_frame = ttk.Frame(popup)
            preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            preview_text = tk.Text(preview_frame, wrap="word")
            preview_scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=preview_text.yview)
            preview_text.configure(yscrollcommand=preview_scrollbar.set)
            
            preview_text.pack(side="left", fill="both", expand=True)
            preview_scrollbar.pack(side="right", fill="y")
            
            preview_text.insert("1.0", preview_content)
            preview_text.config(state="disabled")
            
            ttk.Button(popup, text="Close", command=popup.destroy).pack(pady=10)
            
        except KeyError as e:
            messagebox.showerror("Format Error", f"Invalid variable: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to preview template: {e}")
    
    # Copy to clipboard function
    def copy_to_clipboard():
        content = template_text.get("1.0", "end-1c")
        
        try:
            parent.clipboard_clear()
            parent.clipboard_append(content)
            messagebox.showinfo("Success", "Template copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy to clipboard: {e}")
    
    # Connect filter and search
    filter_combo.bind("<<ComboboxSelected>>", lambda e: refresh_templates())
    search_entry.bind("<Return>", lambda e: refresh_templates())
    
    # Initial load
    refresh_templates()