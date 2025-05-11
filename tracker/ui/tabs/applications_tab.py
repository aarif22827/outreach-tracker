import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from datetime import datetime
from tkcalendar import DateEntry
import os

from tracker.core.models import Application, Document, Reminder
from tracker.utils.ui_components import (create_search_frame, create_sortable_treeview, 
                                      truncate_text, format_date, resize_treeview_columns)
from tracker.utils.reminder_utils import create_reminder, set_reminder_for_item
from tracker.utils.document_utils import (manage_linked_documents, view_linked_documents,
                                      unlink_document, open_document, view_document_details)

def build_applications_tab(parent, status_options, check_reminders_callback=None):
    editing_id = None
    
    search_frame, search_var = create_search_frame(
        parent,
        search_callback=lambda: refresh_tree(search_var.get(), filter_status_var.get()),
        reset_callback=lambda: (search_var.set(""), filter_status_var.set("All"), refresh_tree())
    )
    
    tk.Label(search_frame, text="Filter by Status:").pack(side="left", padx=(20, 5))
    filter_status_var = tk.StringVar(value="All")
    status_options_list = ["All"] + status_options
    filter_status = ttk.Combobox(search_frame, textvariable=filter_status_var, 
                               values=status_options_list, width=20, state="readonly")
    filter_status.pack(side="left")
    
    filter_status.bind("<<ComboboxSelected>>", 
                     lambda e: refresh_tree(search_var.get(), filter_status_var.get()))
    
    sort_column = ""
    sort_direction = None
    
    def sort_callback(column):
        nonlocal sort_column, sort_direction
        
        if sort_column == column:
            if sort_direction == "asc":
                sort_direction = "desc"
            elif sort_direction == "desc":
                sort_direction = None
            else:
                sort_direction = "asc"
        else:
            sort_column = column
            sort_direction = "asc"
        
        for col in columns:
            tree.heading(col, text=col, command=lambda c=col: sort_callback(c))
        
        if sort_direction == "asc":
            tree.heading(sort_column, text=f"{sort_column} ↑")
        elif sort_direction == "desc":
            tree.heading(sort_column, text=f"{sort_column} ↓")
        
        refresh_tree(search_var.get(), filter_status_var.get())
    
    columns = ("Title", "Company", "Application Link", "Status", "Last Updated", "Notes")
    tree, table_frame = create_sortable_treeview(parent, columns, sort_callback)
    
    tree.column("Notes", width=200)
    
    full_notes = {}
    
    def view_full_note(item_id):
        """Display the full note text in a popup"""
        item_id_str = str(item_id)
        if item_id_str in full_notes and full_notes[item_id_str]:
            note_text = full_notes[item_id_str]
            popup = tk.Toplevel()
            popup.title("Full Note")
            popup.geometry("500x300")
            popup.transient(parent)
            
            note_frame = tk.Frame(popup)
            note_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            text_widget = tk.Text(note_frame, wrap="word")
            scrollbar = tk.Scrollbar(note_frame, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            text_widget.insert("1.0", note_text)
            text_widget.config(state="disabled")
            
            close_button = tk.Button(popup, text="Close", command=popup.destroy)
            close_button.pack(pady=10)

    def refresh_tree(search_text="", status_filter="All"):
        """Refresh the treeview with filtered data"""
        for row in tree.get_children():
            tree.delete(row)
        
        full_notes.clear()
        
        where_clause = []
        params = []
        
        if search_text:
            where_clause.append("""
                (title LIKE ? OR name LIKE ? OR application_link LIKE ? OR notes LIKE ?)
            """)
            search_param = f"%{search_text}%"
            params.extend([search_param, search_param, search_param, search_param])
        
        if status_filter != "All":
            where_clause.append("status = ?")
            params.append(status_filter)
        
        final_where = " AND ".join(where_clause) if where_clause else ""
        
        applications = Application.find_all(final_where, tuple(params))
        
        if sort_column and sort_direction:
            column_map = {
                "Title": "title",
                "Company": "name",
                "Application Link": "application_link", 
                "Status": "status",
                "Last Updated": "updated_at",
                "Notes": "notes"
            }
            
            attr = column_map.get(sort_column)
            if attr:
                reverse = sort_direction == "desc"
                applications = sorted(applications, 
                                    key=lambda a: getattr(a, attr, "") or "", 
                                    reverse=reverse)
        
        for app in applications:
            rid = str(app.id)
            note_text = app.notes or ""
            full_notes[rid] = note_text
            
            tree.insert("", "end", iid=rid, values=(
                app.title,
                app.name,
                app.application_link,
                app.status,
                app.updated_at or "",
                truncate_text(note_text)
            ))
    
    def show_context_menu(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
        
        tree.selection_set(item_id)
        
        context_menu = tk.Menu(tree, tearoff=0)
        
        values = tree.item(item_id, 'values')
        
        context_menu.add_command(label="Edit", command=lambda: edit_application(item_id))
        
        application_link = values[2] if len(values) > 2 else None
        if application_link and application_link.strip():
            context_menu.add_command(label="Open Link", 
                                  command=lambda: webbrowser.open(application_link))
        
        context_menu.add_command(label="Set Reminder", 
                              command=lambda: set_reminder_for_application(item_id))
        
        if item_id in full_notes and full_notes[item_id].strip():
            context_menu.add_command(label="View Full Notes", 
                                   command=lambda: view_full_note(item_id))
        
        context_menu.add_separator()
        context_menu.add_command(label="Link Documents", 
                              command=lambda: manage_linked_documents(item_id, 'application', parent))
        context_menu.add_command(label="View Linked Documents", 
                              command=lambda: view_linked_documents(item_id, 'application', parent))
        
        context_menu.add_separator()
        
        context_menu.add_command(label="Delete", 
                              command=lambda: delete_application(item_id))
        
        context_menu.tk_popup(event.x_root, event.y_root)
    
    tree.bind("<Button-3>", show_context_menu)
    
    def delete_application(item_id):
        confirm = messagebox.askyesno("Delete", "Are you sure you want to delete this application?")
        if confirm:
            application = Application.get_by_id(item_id)
            if application:
                application.delete()
                refresh_tree(search_var.get(), filter_status_var.get())
                reset_form()
    
    def on_tree_click(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            reset_form()
            return
        
        edit_application(item_id)
    
    tree.bind("<ButtonRelease-1>", on_tree_click)
    
    tree.bind("<ButtonPress-1>", lambda event: resize_treeview_columns(tree, event))
    
    def on_double_click(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
            
        column = tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1
        
        if column_index == 5:
            view_full_note(item_id)
    
    tree.bind("<Double-1>", on_double_click)
    
    def on_frame_click(event):
        if not tree.identify_row(event.y):
            reset_form()
    
    table_frame.bind("<Button-1>", on_frame_click)
    
    def set_reminder_for_application(app_id):
        """Set a reminder for the selected application"""
        set_reminder_for_item(app_id, 'application', parent, check_reminders_callback)
    
    form_frame = tk.Frame(parent)
    form_frame.pack(pady=10)

    tk.Label(form_frame, text="Job Title").grid(row=0, column=0)
    tk.Label(form_frame, text="Company").grid(row=0, column=2)
    
    tk.Label(form_frame, text="Application Link").grid(row=1, column=0)
    tk.Label(form_frame, text="Status").grid(row=1, column=2)
    
    tk.Label(form_frame, text="Notes").grid(row=2, column=0, sticky="n")

    entry_title = tk.Entry(form_frame, width=30)
    entry_company = tk.Entry(form_frame, width=30)
    entry_application_link = tk.Entry(form_frame, width=30)
    status_var = tk.StringVar(value=status_options[0])
    dropdown_status = ttk.Combobox(form_frame, textvariable=status_var, 
                                 values=status_options, state="readonly", width=28)
    
    notes_frame = tk.Frame(form_frame)
    entry_notes = tk.Text(notes_frame, width=60, height=4, wrap="word")
    notes_scrollbar = tk.Scrollbar(notes_frame, command=entry_notes.yview)
    entry_notes.configure(yscrollcommand=notes_scrollbar.set)
    entry_notes.pack(side="left", fill="both", expand=True)
    notes_scrollbar.pack(side="right", fill="y")

    entry_title.grid(row=0, column=1, padx=5)
    entry_company.grid(row=0, column=3, padx=5)
    entry_application_link.grid(row=1, column=1, padx=5)
    dropdown_status.grid(row=1, column=3, padx=5)
    notes_frame.grid(row=2, column=1, columnspan=3, pady=5, sticky="ew")

    def reset_form():
        nonlocal editing_id
        editing_id = None
        entry_title.delete(0, tk.END)
        entry_company.delete(0, tk.END)
        entry_application_link.delete(0, tk.END)
        entry_notes.delete("1.0", tk.END)
        status_var.set(status_options[0])
        add_button.config(text="Add Application")
        
        parent.focus_set()
        
        for selected_item in tree.selection():
            tree.selection_remove(selected_item)
    
    def add_or_update_application():
        nonlocal editing_id
        title = entry_title.get().strip()
        company = entry_company.get().strip()
        application_link = entry_application_link.get().strip()
        status = status_var.get()
        notes = entry_notes.get("1.0", "end-1c").strip()

        if not title or not company:
            messagebox.showerror("Error", "Job Title and Company are required.")
            return

        application = Application(
            id=editing_id,
            title=title,
            name=company,
            application_link=application_link,
            status=status,
            notes=notes
        )
        
        application.save()
        
        is_new = editing_id is None
        if is_new:
            editing_id = application.id
        
        messagebox.showinfo("Success", 
                          "Application updated successfully!" if not is_new else "Application added successfully!")
        
        if is_new and status in ["✅ Applied", "🔍 Under Review"]:
            if messagebox.askyesno("Create Reminder", "Would you like to set a follow-up reminder for this application?"):
                set_reminder_for_item(editing_id, 'application', parent, check_reminders_callback)
            
            if messagebox.askyesno("Link Documents", "Would you like to link documents to this application?"):
                manage_linked_documents(editing_id, 'application', parent)
        
        reset_form()
        refresh_tree(search_var.get(), filter_status_var.get())

    def edit_application(item_id):
        nonlocal editing_id
        editing_id = item_id
        
        application = Application.get_by_id(item_id)
        if not application:
            messagebox.showerror("Error", "Application not found")
            return
        
        entry_title.delete(0, tk.END)
        entry_title.insert(0, application.title)
        
        entry_company.delete(0, tk.END)
        entry_company.insert(0, application.name)
        
        entry_application_link.delete(0, tk.END)
        entry_application_link.insert(0, application.application_link or "")
        
        status_var.set(application.status)
        
        entry_notes.delete("1.0", tk.END)
        if application.notes:
            entry_notes.insert("1.0", application.notes)
        
        add_button.config(text="Update Application")
    
    def set_reminder():
        if not editing_id:
            messagebox.showinfo("Info", "Please select an application first or save the current application.")
            return
        
        set_reminder_for_item(editing_id, 'application', parent, check_reminders_callback)
    
    button_frame = tk.Frame(parent)
    button_frame.pack(pady=5)
    
    add_button = tk.Button(button_frame, text="Add Application", command=add_or_update_application)
    add_button.pack(side="left", padx=5)
    
    reminder_button = tk.Button(button_frame, text="Set Reminder", command=set_reminder)
    reminder_button.pack(side="left", padx=5)
    
    def add_documents():
        if not editing_id:
            messagebox.showinfo("Info", "Please select an application first or save the current application.")
            return
        
        manage_linked_documents(editing_id, 'application', parent)
    
    documents_button = tk.Button(button_frame, text="Manage Documents", command=add_documents)
    documents_button.pack(side="left", padx=5)
    
    cancel_button = tk.Button(button_frame, text="Cancel", command=reset_form)
    cancel_button.pack(side="left", padx=5)

    search_var.trace("w", lambda *args: refresh_tree(search_var.get(), filter_status_var.get()))

    refresh_tree()