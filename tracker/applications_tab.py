import tkinter as tk
from tkinter import ttk, messagebox, font
import webbrowser
from datetime import datetime
from tkcalendar import DateEntry
from tracker.database import get_connection

def build_applications_tab(parent, status_options, check_reminders_callback=None):
    editing_id = None
    
    sort_column = ""
    sort_direction = None
    
    search_frame = tk.Frame(parent)
    search_frame.pack(fill="x", pady=5, padx=10)
    
    tk.Label(search_frame, text="Search:").pack(side="left")
    search_var = tk.StringVar()
    search_entry = tk.Entry(search_frame, textvariable=search_var, width=30)
    search_entry.pack(side="left", padx=5)
    
    tk.Label(search_frame, text="Filter by Status:").pack(side="left", padx=(20, 5))
    filter_status_var = tk.StringVar(value="All")
    status_options_list = ["All"] + status_options
    filter_status = ttk.Combobox(search_frame, textvariable=filter_status_var, values=status_options_list, width=20, state="readonly")
    filter_status.pack(side="left")
    
    def perform_search():
        refresh_tree(search_var.get(), filter_status_var.get())
    
    search_button = tk.Button(search_frame, text="Search", command=perform_search)
    search_button.pack(side="left", padx=10)
    
    def reset_search():
        search_var.set("")
        filter_status_var.set("All")
        refresh_tree()
    
    reset_button = tk.Button(search_frame, text="Reset", command=reset_search)
    reset_button.pack(side="left")
    
    table_frame = tk.Frame(parent)
    table_frame.pack(fill="both", expand=True)

    # Removed Delete column
    columns = ("Title", "Company", "Application Link", "Status", "Last Updated", "Notes")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col, command=lambda c=col: toggle_sort(c))
        tree.column(col, width=150, anchor="w")
    
    tree.column("Notes", width=200)
    
    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)
    
    full_notes = {}

    def truncate_text(text, max_length=50):
        if not text:
            return ""
        text = text.replace("\n", " ")
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text
    
    def view_full_note(item_id):
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

    def toggle_sort(column):
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
            tree.heading(col, text=col, command=lambda c=col: toggle_sort(c))
        
        if sort_direction == "asc":
            tree.heading(sort_column, text=f"{sort_column} ↑")
        elif sort_direction == "desc":
            tree.heading(sort_column, text=f"{sort_column} ↓")
        
        refresh_tree(search_var.get(), filter_status_var.get())

    def refresh_tree(search_text="", status_filter="All"):
        for row in tree.get_children():
            tree.delete(row)
        
        full_notes.clear()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, title, name, application_link, status, updated_at, notes 
            FROM applications
            WHERE 1=1
        """
        params = []
        
        if search_text:
            query += """
                AND (title LIKE ? OR name LIKE ? OR application_link LIKE ? OR notes LIKE ?)
            """
            search_param = f"%{search_text}%"
            params.extend([search_param, search_param, search_param, search_param])
        
        if status_filter != "All":
            query += " AND status = ?"
            params.append(status_filter)
        
        if sort_column and sort_direction:
            column_map = {
                "Title": "title",
                "Company": "name",
                "Application Link": "application_link",
                "Status": "status",
                "Last Updated": "updated_at",
                "Notes": "notes"
            }
            
            db_column = column_map.get(sort_column)
            if db_column:
                query += f" ORDER BY {db_column} {'ASC' if sort_direction == 'asc' else 'DESC'}"
        
        cursor.execute(query, params)
        
        for row in cursor.fetchall():
            rid = str(row[0])
            note_text = str(row[6]) if row[6] is not None else ""
            full_notes[rid] = note_text
            
            truncated_note = truncate_text(note_text)
            
            display_values = list(row[1:])
            display_values[5] = truncated_note
            
            # Removed the delete button
            tree.insert("", "end", iid=rid, values=display_values)
        conn.close()

    # Context menu implementation
    def show_context_menu(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
        
        # Select the row first
        tree.selection_set(item_id)
        
        # Create context menu
        context_menu = tk.Menu(tree, tearoff=0)
        
        # Get application details for context-sensitive options
        values = tree.item(item_id, 'values')
        
        # Always add Edit option
        context_menu.add_command(label="Edit", command=lambda: edit_application(item_id))
        
        # Add application link option only if it exists
        application_link = values[2] if len(values) > 2 else None
        if application_link and application_link.strip():
            context_menu.add_command(label="Open Link", 
                                  command=lambda: webbrowser.open(application_link))
        
        # Always add Reminder option
        context_menu.add_command(label="Set Reminder", 
                              command=lambda: set_reminder_for_selected())
        
        # Add View Notes option only if there are notes
        if item_id in full_notes and full_notes[item_id].strip():
            context_menu.add_command(label="View Full Notes", 
                                  command=lambda: view_full_note(item_id))
        
        context_menu.add_separator()
        
        # Always add Delete option
        context_menu.add_command(label="Delete", 
                              command=lambda: delete_application(item_id))
        
        # Display context menu
        context_menu.tk_popup(event.x_root, event.y_root)
        
    tree.bind("<Button-3>", show_context_menu)  # Right-click
    
    def delete_application(item_id):
        confirm = messagebox.askyesno("Delete", "Are you sure you want to delete this application?")
        if confirm:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM applications WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            refresh_tree(search_var.get(), filter_status_var.get())
            reset_form()

    # Modified on_tree_click to handle single click without delete column
    def on_tree_click(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            reset_form()
            return
        
        edit_application(item_id)
    
    tree.bind("<ButtonRelease-1>", on_tree_click)
    
    def resize_column(event):
        region = tree.identify_region(event.x, event.y)
        if region == "separator":
            column = tree.identify_column(event.x)
            column_index = int(column.replace('#', '')) - 1
            
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
    
    tree.bind("<ButtonPress-1>", resize_column)
    
    def on_double_click(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
            
        column = tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1
        
        # Only handle double click for notes column to view full notes
        if column_index == 5:  # Notes column
            view_full_note(item_id)
    
    tree.bind("<Double-1>", on_double_click)
    
    def on_frame_click(event):
        if not tree.identify_row(event.y):
            reset_form()
    
    table_frame.bind("<Button-1>", on_frame_click)
    
    # Add function to set reminder for currently selected application
    def set_reminder_for_selected():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select an application first.")
            return
        
        item_id = selected_items[0]
        
        # Get application details
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, name FROM applications WHERE id = ?", (item_id,))
        app = cursor.fetchone()
        conn.close()
        
        if app:
            title, company = app
            create_reminder(item_id, f"{title} at {company}")
    
    def edit_application(item_id):
        nonlocal editing_id
        editing_id = item_id
        values = tree.item(item_id, 'values')
        
        entry_title.delete(0, tk.END)
        entry_title.insert(0, values[0])
        
        entry_company.delete(0, tk.END)
        entry_company.insert(0, values[1])
        
        entry_application_link.delete(0, tk.END)
        entry_application_link.insert(0, values[2])
        
        status_var.set(values[3])
        
        entry_notes.delete("1.0", tk.END)
        
        item_id_str = str(item_id)
        if item_id_str in full_notes:
            entry_notes.insert("1.0", full_notes[item_id_str])
        
        add_button.config(text="Update Application")

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
    dropdown_status = ttk.Combobox(form_frame, textvariable=status_var, values=status_options, state="readonly", width=28)
    
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

        conn = get_connection()
        cursor = conn.cursor()
        
        if editing_id:
            cursor.execute('''
                UPDATE applications
                SET name = ?, title = ?, application_link = ?, status = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?''',
                (company, title, application_link, status, notes, editing_id))
            messagebox.showinfo("Success", "Application updated successfully!")
        else:
            cursor.execute('''
                INSERT INTO applications
                (name, title, application_link, status, notes)
                VALUES (?, ?, ?, ?, ?)''',
                (company, title, application_link, status, notes))
            
            # Get the id of the last inserted row
            if status in ["✅ Applied", "🔍 Under Review"]:
                cursor.execute("SELECT last_insert_rowid()")
                new_id = cursor.fetchone()[0]
                editing_id = new_id
                
                # Prompt to create a follow-up reminder
                if messagebox.askyesno("Create Reminder", "Would you like to set a follow-up reminder for this application?"):
                    create_reminder(editing_id, f"{title} at {company}")
        
        conn.commit()
        conn.close()
        
        reset_form()
        refresh_tree(search_var.get(), filter_status_var.get())
    
    def create_reminder(app_id, app_name):
        reminder_window = tk.Toplevel()
        reminder_window.title("Set Follow-up Reminder")
        reminder_window.geometry("400x300")
        reminder_window.transient(parent)
        
        tk.Label(reminder_window, text=f"Reminder for: {app_name}").pack(pady=10)
        
        tk.Label(reminder_window, text="Title:").pack(anchor="w", padx=20)
        title_var = tk.StringVar(value=f"Follow up on {app_name}")
        title_entry = tk.Entry(reminder_window, textvariable=title_var, width=40)
        title_entry.pack(padx=20, fill="x")
        
        tk.Label(reminder_window, text="Description:").pack(anchor="w", padx=20, pady=(10,0))
        desc_frame = tk.Frame(reminder_window)
        desc_frame.pack(padx=20, fill="both", expand=True)
        
        desc_text = tk.Text(desc_frame, height=4, wrap="word")
        desc_scrollbar = tk.Scrollbar(desc_frame, command=desc_text.yview)
        desc_text.configure(yscrollcommand=desc_scrollbar.set)
        desc_text.pack(side="left", fill="both", expand=True)
        desc_scrollbar.pack(side="right", fill="y")
        
        desc_text.insert("1.0", "Send a follow-up email to check on the status of the application.")
        
        tk.Label(reminder_window, text="Due Date:").pack(anchor="w", padx=20)
        # Default to 7 days from now
        due_date = DateEntry(reminder_window, width=20, background='darkblue',
                          foreground='white', borderwidth=2, date_pattern='mm/dd/yyyy')
        due_date.pack(anchor="w", padx=20)
        
        def save_reminder():
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reminders
                (related_type, related_id, title, description, due_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                "application",
                app_id,
                title_entry.get().strip(),
                desc_text.get("1.0", "end-1c").strip(),
                due_date.get_date().strftime("%m/%d/%Y"),
                "pending"
            ))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Reminder created successfully!")
            if check_reminders_callback:
                check_reminders_callback()
            reminder_window.destroy()
        
        button_frame = tk.Frame(reminder_window)
        button_frame.pack(pady=15)
        
        save_button = tk.Button(button_frame, text="Save Reminder", command=save_reminder)
        save_button.pack(side="left", padx=5)
        
        cancel_button = tk.Button(button_frame, text="Cancel", command=reminder_window.destroy)
        cancel_button.pack(side="left", padx=5)
    
    def set_reminder():
        if not editing_id:
            messagebox.showinfo("Info", "Please select an application first or save the current application.")
            return
        
        # Get application details
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, name FROM applications WHERE id = ?", (editing_id,))
        app = cursor.fetchone()
        conn.close()
        
        if app:
            title, company = app
            create_reminder(editing_id, f"{title} at {company}")

    button_frame = tk.Frame(parent)
    button_frame.pack(pady=5)
    
    add_button = tk.Button(button_frame, text="Add Application", command=add_or_update_application)
    add_button.pack(side="left", padx=5)
    
    reminder_button = tk.Button(button_frame, text="Set Reminder", command=set_reminder)
    reminder_button.pack(side="left", padx=5)
    
    cancel_button = tk.Button(button_frame, text="Cancel", command=reset_form)
    cancel_button.pack(side="left", padx=5)

    search_entry.bind("<Return>", lambda event: perform_search())

    refresh_tree()