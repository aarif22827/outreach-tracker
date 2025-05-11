import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from datetime import datetime
from tkcalendar import DateEntry
import os

from tracker.core.models import Contact, Document, Reminder
from tracker.utils.ui_components import (create_search_frame, create_sortable_treeview, 
                                      truncate_text, format_date, resize_treeview_columns)
from tracker.utils.reminder_utils import create_reminder, set_reminder_for_item
from tracker.utils.document_utils import (manage_linked_documents, view_linked_documents,
                                      unlink_document, open_document, view_document_details)

def build_contacts_tab(parent, status_options, check_reminders_callback=None):
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
    
    columns = ("Name", "Company", "Title", "Email", "LinkedIn", "Status", "Last Contacted", "Notes")
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
                (name LIKE ? OR company LIKE ? OR title LIKE ? OR email LIKE ? 
                OR linkedin_url LIKE ? OR notes LIKE ?)
            """)
            search_param = f"%{search_text}%"
            params.extend([search_param, search_param, search_param, search_param, search_param, search_param])
        
        if status_filter != "All":
            where_clause.append("status = ?")
            params.append(status_filter)
        
        final_where = " AND ".join(where_clause) if where_clause else ""
        
        contacts = Contact.find_all(final_where, tuple(params))
        
        if sort_column and sort_direction:
            column_map = {
                "Name": "name",
                "Company": "company",
                "Title": "title",
                "Email": "email",
                "LinkedIn": "linkedin_url",
                "Status": "status",
                "Last Contacted": "last_response",
                "Notes": "notes"
            }
            
            attr = column_map.get(sort_column)
            if attr:
                reverse = sort_direction == "desc"
                contacts = sorted(contacts, 
                                key=lambda c: getattr(c, attr, "") or "", 
                                reverse=reverse)
        
        for contact in contacts:
            rid = str(contact.id)
            note_text = contact.notes or ""
            full_notes[rid] = note_text
            
            tree.insert("", "end", iid=rid, values=(
                contact.name,
                contact.company,
                contact.title,
                contact.email,
                contact.linkedin_url,
                contact.status,
                contact.last_response,
                truncate_text(note_text)
            ))
    
    def show_context_menu(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
        
        tree.selection_set(item_id)
        
        context_menu = tk.Menu(tree, tearoff=0)
        
        values = tree.item(item_id, 'values')
        
        context_menu.add_command(label="Edit", command=lambda: edit_contact(item_id))
        
        email = values[3] if len(values) > 3 else None
        if email and email.strip():
            context_menu.add_command(label="Send Email", 
                                   command=lambda: webbrowser.open(f"mailto:{email}"))
        
        linkedin = values[4] if len(values) > 4 else None
        if linkedin and linkedin.strip():
            context_menu.add_command(label="Open LinkedIn", 
                                   command=lambda: webbrowser.open(linkedin))
        
        context_menu.add_command(label="Set Reminder", 
                               command=lambda: set_reminder_for_contact(item_id))
        
        if item_id in full_notes and full_notes[item_id].strip():
            context_menu.add_command(label="View Full Notes", 
                                   command=lambda: view_full_note(item_id))
        
        context_menu.add_separator()
        context_menu.add_command(label="Link Documents", 
                              command=lambda: manage_linked_documents(item_id, 'contact', parent))
        context_menu.add_command(label="View Linked Documents", 
                              command=lambda: view_linked_documents(item_id, 'contact', parent))
        
        context_menu.add_separator()
        
        context_menu.add_command(label="Delete", 
                               command=lambda: delete_contact(item_id))
        
        context_menu.tk_popup(event.x_root, event.y_root)
    
    tree.bind("<Button-3>", show_context_menu)
    
    def delete_contact(item_id):
        confirm = messagebox.askyesno("Delete", "Are you sure you want to delete this contact?")
        if confirm:
            contact = Contact.get_by_id(item_id)
            if contact:
                contact.delete()
                refresh_tree(search_var.get(), filter_status_var.get())
                reset_form()
    
    def on_tree_click(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            reset_form()
            return
        
        edit_contact(item_id)
    
    tree.bind("<ButtonRelease-1>", on_tree_click)
    
    tree.bind("<ButtonPress-1>", lambda event: resize_treeview_columns(tree, event))
    
    def on_double_click(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
            
        column = tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1
        
        if column_index == 7:
            view_full_note(item_id)
    
    tree.bind("<Double-1>", on_double_click)
    
    def on_frame_click(event):
        if not tree.identify_row(event.y):
            reset_form()
    
    table_frame.bind("<Button-1>", on_frame_click)
    
    def set_reminder_for_contact(contact_id):
        """Set a reminder for the selected contact"""
        set_reminder_for_item(contact_id, 'contact', parent, check_reminders_callback)
    
    form_frame = tk.Frame(parent)
    form_frame.pack(pady=10)

    tk.Label(form_frame, text="Name").grid(row=0, column=0)
    tk.Label(form_frame, text="Company").grid(row=0, column=2)
    
    tk.Label(form_frame, text="Title").grid(row=1, column=0)
    tk.Label(form_frame, text="Email").grid(row=1, column=2)
    
    tk.Label(form_frame, text="LinkedIn").grid(row=2, column=0)
    tk.Label(form_frame, text="Status").grid(row=2, column=2)
    
    tk.Label(form_frame, text="Last Contacted").grid(row=3, column=0)
    tk.Label(form_frame, text="Notes").grid(row=3, column=2, sticky="n")

    entry_name = tk.Entry(form_frame)
    entry_company = tk.Entry(form_frame)
    entry_title = tk.Entry(form_frame)
    entry_email = tk.Entry(form_frame)
    entry_linkedin = tk.Entry(form_frame)
    status_var = tk.StringVar(value=status_options[0])
    dropdown_status = ttk.Combobox(form_frame, textvariable=status_var, values=status_options, state="readonly")
    
    entry_last_response = DateEntry(form_frame, width=16, background='darkblue',
                                  foreground='white', borderwidth=2, date_pattern='mm/dd/yyyy')
    
    notes_frame = tk.Frame(form_frame)
    entry_notes = tk.Text(notes_frame, width=40, height=4, wrap="word")
    notes_scrollbar = tk.Scrollbar(notes_frame, command=entry_notes.yview)
    entry_notes.configure(yscrollcommand=notes_scrollbar.set)
    entry_notes.pack(side="left", fill="both", expand=True)
    notes_scrollbar.pack(side="right", fill="y")

    entry_name.grid(row=0, column=1, padx=5)
    entry_company.grid(row=0, column=3, padx=5)
    entry_title.grid(row=1, column=1, padx=5)
    entry_email.grid(row=1, column=3, padx=5)
    entry_linkedin.grid(row=2, column=1, padx=5)
    dropdown_status.grid(row=2, column=3, padx=5)
    entry_last_response.grid(row=3, column=1, padx=5)
    notes_frame.grid(row=3, column=3, padx=5, pady=5, sticky="ew")

    def reset_form():
        nonlocal editing_id
        editing_id = None
        entry_name.delete(0, tk.END)
        entry_company.delete(0, tk.END)
        entry_title.delete(0, tk.END)
        entry_email.delete(0, tk.END)
        entry_linkedin.delete(0, tk.END)
        entry_last_response.set_date(datetime.now())
        entry_notes.delete("1.0", tk.END)
        status_var.set(status_options[0])
        add_button.config(text="Add Contact")
        
        parent.focus_set()
        
        for selected_item in tree.selection():
            tree.selection_remove(selected_item)
    
    def set_reminder():
        if not editing_id:
            messagebox.showinfo("Info", "Please select a contact first or save the current contact.")
            return
        
        set_reminder_for_item(editing_id, 'contact', parent, check_reminders_callback)
    
    def add_or_update_contact():
        nonlocal editing_id
        name = entry_name.get().strip()
        company = entry_company.get().strip()
        title = entry_title.get().strip()
        email = entry_email.get().strip()
        linkedin = entry_linkedin.get().strip()
        status = status_var.get()
        last_response = entry_last_response.get_date().strftime("%m/%d/%Y")
        notes = entry_notes.get("1.0", "end-1c").strip()

        if not name or not company:
            messagebox.showerror("Error", "Name and Company are required.")
            return

        contact = Contact(
            id=editing_id,
            name=name,
            company=company,
            title=title,
            email=email,
            linkedin_url=linkedin,
            status=status,
            last_response=last_response,
            notes=notes
        )
        
        contact.save()
        
        is_new = editing_id is None
        if is_new:
            editing_id = contact.id
        
        messagebox.showinfo("Success", 
                          "Contact updated successfully!" if not is_new else "Contact added successfully!")
        
        if is_new and status in ["✅ Connected", "💬 Messaged"]:
            if messagebox.askyesno("Create Reminder", "Would you like to set a follow-up reminder for this contact?"):
                set_reminder_for_item(editing_id, 'contact', parent, check_reminders_callback)
            
            if messagebox.askyesno("Link Documents", "Would you like to link documents to this contact?"):
                manage_linked_documents(editing_id, 'contact', parent)
        
        reset_form()
        refresh_tree(search_var.get(), filter_status_var.get())

    def edit_contact(item_id):
        nonlocal editing_id
        editing_id = item_id
        
        contact = Contact.get_by_id(item_id)
        if not contact:
            messagebox.showerror("Error", "Contact not found")
            return
        
        entry_name.delete(0, tk.END)
        entry_name.insert(0, contact.name)
        
        entry_company.delete(0, tk.END)
        entry_company.insert(0, contact.company)
        
        entry_title.delete(0, tk.END)
        entry_title.insert(0, contact.title or "")
        
        entry_email.delete(0, tk.END)
        entry_email.insert(0, contact.email or "")
        
        entry_linkedin.delete(0, tk.END)
        entry_linkedin.insert(0, contact.linkedin_url or "")
        
        status_var.set(contact.status)
        
        try:
            date_str = contact.last_response
            if date_str:
                date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                entry_last_response.set_date(date_obj)
            else:
                entry_last_response.set_date(datetime.now())
        except ValueError:
            entry_last_response.set_date(datetime.now())
        
        entry_notes.delete("1.0", tk.END)
        if contact.notes:
            entry_notes.insert("1.0", contact.notes)
        
        add_button.config(text="Update Contact")

    button_frame = tk.Frame(parent)
    button_frame.pack(pady=5)
    
    add_button = tk.Button(button_frame, text="Add Contact", command=add_or_update_contact)
    add_button.pack(side="left", padx=5)
    
    reminder_button = tk.Button(button_frame, text="Set Reminder", command=set_reminder)
    reminder_button.pack(side="left", padx=5)
    
    def add_documents():
        if not editing_id:
            messagebox.showinfo("Info", "Please select a contact first or save the current contact.")
            return
        
        manage_linked_documents(editing_id, 'contact', parent)
    
    documents_button = tk.Button(button_frame, text="Manage Documents", command=add_documents)
    documents_button.pack(side="left", padx=5)
    
    cancel_button = tk.Button(button_frame, text="Cancel", command=reset_form)
    cancel_button.pack(side="left", padx=5)

    search_var.trace("w", lambda *args: refresh_tree(search_var.get(), filter_status_var.get()))

    refresh_tree()