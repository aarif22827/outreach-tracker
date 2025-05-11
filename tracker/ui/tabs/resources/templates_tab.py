import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from tracker.core.models import MessageTemplate

def build_templates_tab(parent):
    """Build the message templates tab"""
    control_frame = tk.Frame(parent)
    control_frame.pack(fill="x", padx=10, pady=5)
    
    search_frame = tk.Frame(control_frame)
    search_frame.pack(side="left")
    
    tk.Label(search_frame, text="Search:").pack(side="left")
    search_var = tk.StringVar()
    search_entry = tk.Entry(search_frame, textvariable=search_var, width=25)
    search_entry.pack(side="left", padx=5)
    
    filter_frame = tk.Frame(control_frame)
    filter_frame.pack(side="left", padx=20)
    
    tk.Label(filter_frame, text="Category:").pack(side="left")
    category_var = tk.StringVar(value="All")
    category_combo = ttk.Combobox(filter_frame, textvariable=category_var, 
                                values=["All", "Introduction", "Follow-up", "Thank You", "Other"], 
                                width=15, state="readonly")
    category_combo.pack(side="left", padx=5)
    
    button_frame = tk.Frame(control_frame)
    button_frame.pack(side="right")
    
    refresh_btn = ttk.Button(button_frame, text="Refresh", 
                           command=lambda: refresh_templates(search_var.get(), category_var.get()))
    refresh_btn.pack(side="right", padx=5)
    
    add_btn = ttk.Button(button_frame, text="Add New", 
                       command=lambda: edit_template())
    add_btn.pack(side="right", padx=5)
    
    split_frame = tk.Frame(parent)
    split_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    list_frame = tk.Frame(split_frame)
    list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
    
    columns = ("Name", "Category", "Last Updated")
    tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
    
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    
    tree.column("Name", width=150)
    
    list_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=list_scrollbar.set)
    
    tree.pack(side="left", fill="both", expand=True)
    list_scrollbar.pack(side="right", fill="y")
    
    content_frame = tk.LabelFrame(split_frame, text="Template Content")
    content_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
    
    content_text = tk.Text(content_frame, wrap="word")
    content_scrollbar = tk.Scrollbar(content_frame, orient="vertical", command=content_text.yview)
    content_text.configure(yscrollcommand=content_scrollbar.set)
    
    content_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    content_scrollbar.pack(side="right", fill="y", pady=5)
    
    content_text.config(state="disabled")
    
    def refresh_templates(search_text="", category_filter="All"):
        """Refresh the templates list based on filters"""
        for item in tree.get_children():
            tree.delete(item)
            
        where_clause = []
        params = []
        
        if search_text:
            where_clause.append("(name LIKE ? OR content LIKE ?)")
            search_param = f"%{search_text}%"
            params.extend([search_param, search_param])
        
        if category_filter != "All":
            where_clause.append("category = ?")
            params.append(category_filter)
        
        final_where = " AND ".join(where_clause) if where_clause else ""
        
        templates = MessageTemplate.find_all(final_where, tuple(params))
        
        templates.sort(key=lambda t: t.name or "")
        
        for template in templates:
            date_display = ""
            date_value = template.updated_at or template.created_at or ""
            if date_value:
                try:
                    date_obj = datetime.strptime(date_value, "%Y-%m-%d %H:%M:%S")
                    date_display = date_obj.strftime("%m/%d/%Y")
                except ValueError:
                    date_display = date_value
            
            tree.insert("", "end", iid=template.id, values=(
                template.name,
                template.category,
                date_display
            ))
    
    def show_template_content(event=None):
        """Show the selected template content"""
        selected_items = tree.selection()
        if not selected_items:
            content_text.config(state="normal")
            content_text.delete(1.0, tk.END)
            content_text.config(state="disabled")
            return
            
        template_id = selected_items[0]
        template = MessageTemplate.get_by_id(int(template_id))
        
        if template:
            content_text.config(state="normal")
            content_text.delete(1.0, tk.END)
            content_text.insert(tk.END, template.content)
            content_text.config(state="disabled")
    
    tree.bind("<<TreeviewSelect>>", show_template_content)
    
    def show_context_menu(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
            
        tree.selection_set(item_id)
        
        context_menu = tk.Menu(tree, tearoff=0)
        context_menu.add_command(
            label="Edit Template", 
            command=lambda: edit_template(int(item_id))
        )
        context_menu.add_command(
            label="Copy to Clipboard", 
            command=lambda: copy_to_clipboard(int(item_id))
        )
        context_menu.add_separator()
        context_menu.add_command(
            label="Delete Template", 
            command=lambda: delete_template(int(item_id))
        )
        
        context_menu.tk_popup(event.x_root, event.y_root)
    
    tree.bind("<Button-3>", show_context_menu)
    
    def edit_template(template_id=None):
        """Edit or create a template"""
        template = None
        if template_id:
            template = MessageTemplate.get_by_id(template_id)
            if not template:
                return
                
        dialog = tk.Toplevel(parent)
        dialog.title("Edit Template" if template else "New Template")
        dialog.geometry("600x400")
        dialog.transient(parent)
        dialog.grab_set()
        
        form_frame = tk.Frame(dialog)
        form_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky="w")
        name_var = tk.StringVar(value=template.name if template else "")
        name_entry = tk.Entry(form_frame, textvariable=name_var, width=30)
        name_entry.grid(row=0, column=1, sticky="w", padx=5)
        
        tk.Label(form_frame, text="Category:").grid(row=0, column=2, sticky="w")
        category_options = ["Introduction", "Follow-up", "Thank You", "Other"]
        template_category = tk.StringVar(value=template.category if template else category_options[0])
        category_dropdown = ttk.Combobox(form_frame, textvariable=template_category, 
                                       values=category_options, width=15, state="readonly")
        category_dropdown.grid(row=0, column=3, sticky="w", padx=5)
        
        tk.Label(form_frame, text="Content:").grid(row=1, column=0, sticky="nw", pady=5)
        
        editor_frame = tk.Frame(dialog)
        editor_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        content_editor = tk.Text(editor_frame, wrap="word")
        editor_scrollbar = tk.Scrollbar(editor_frame, orient="vertical", command=content_editor.yview)
        content_editor.configure(yscrollcommand=editor_scrollbar.set)
        
        content_editor.pack(side="left", fill="both", expand=True)
        editor_scrollbar.pack(side="right", fill="y")
        
        if template and template.content:
            content_editor.insert(tk.END, template.content)
            
        help_frame = tk.Frame(dialog)
        help_frame.pack(fill="x", padx=10)
        
        help_text = """
        Available Variables:
        {name} - Contact name
        {company} - Company name
        {title} - Job title
        {date} - Current date
        """
        
        tk.Label(help_frame, text=help_text, justify="left").pack(anchor="w")
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        def save_template():
            name = name_var.get().strip()
            category = template_category.get()
            content = content_editor.get(1.0, tk.END).strip()
            
            if not name or not content:
                messagebox.showerror("Error", "Name and Content are required.")
                return
                
            if template:
                template.name = name
                template.category = category
                template.content = content
                template.save()
                messagebox.showinfo("Success", "Template updated successfully!")
            else:
                new_template = MessageTemplate(
                    name=name,
                    category=category,
                    content=content
                )
                new_template.save()
                messagebox.showinfo("Success", "Template created successfully!")
                
            refresh_templates(search_var.get(), category_var.get())
            dialog.destroy()
        
        save_btn = ttk.Button(button_frame, text="Save", command=save_template)
        save_btn.pack(side="right", padx=5)
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side="right", padx=5)
    
    def copy_to_clipboard(template_id):
        """Copy template content to clipboard"""
        template = MessageTemplate.get_by_id(template_id)
        if template:
            parent.clipboard_clear()
            parent.clipboard_append(template.content)
            messagebox.showinfo("Success", "Template copied to clipboard!")
    
    def delete_template(template_id):
        """Delete a template"""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this template?"):
            template = MessageTemplate.get_by_id(template_id)
            if template:
                template.delete()
                refresh_templates(search_var.get(), category_var.get())
                
                content_text.config(state="normal")
                content_text.delete(1.0, tk.END)
                content_text.config(state="disabled")
    
    search_var.trace("w", lambda *args: refresh_templates(search_var.get(), category_var.get()))
    category_combo.bind("<<ComboboxSelected>>", lambda e: refresh_templates(search_var.get(), category_var.get()))
    
    refresh_templates()