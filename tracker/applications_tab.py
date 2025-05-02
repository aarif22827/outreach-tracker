import tkinter as tk
from tkinter import ttk, messagebox, font
import webbrowser
from datetime import datetime
from tracker.database import get_connection

def build_applications_tab(parent, status_options):
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

    columns = ("Title", "Company", "Application Link", "Status", "Last Updated", "Notes", "Delete")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings")
    for col in columns[:-1]:
        tree.heading(col, text=col, command=lambda c=col: toggle_sort(c))
        tree.column(col, width=150, anchor="w")
    tree.heading("Delete", text="Delete")
    tree.column("Delete", width=60, anchor="center")
    
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
        
        for col in columns[:-1]:
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
            
            tree.insert("", "end", iid=rid, values=(*display_values, "❌"))
        conn.close()

    def on_tree_click(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            reset_form()
            return
        
        column = tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1
        
        item_id_str = str(item_id)
        
        if column_index == 6:
            confirm = messagebox.askyesno("Delete", "Are you sure you want to delete this application?")
            if confirm:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM applications WHERE id = ?", (item_id,))
                conn.commit()
                conn.close()
                refresh_tree(search_var.get(), filter_status_var.get())
                reset_form()
        else:
            edit_application(item_id_str)
    
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
        
        item_id_str = str(item_id)
        
        if column_index == 2:
            values = tree.item(item_id, 'values')
            application_link = values[2]
            if application_link:
                webbrowser.open(application_link)
        elif column_index == 5:
            view_full_note(item_id_str)
    
    tree.bind("<Double-1>", on_double_click)
    
    def on_frame_click(event):
        if not tree.identify_row(event.y):
            reset_form()
    
    table_frame.bind("<Button-1>", on_frame_click)
    
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
        
        conn.commit()
        conn.close()
        
        reset_form()
        refresh_tree(search_var.get(), filter_status_var.get())

    button_frame = tk.Frame(parent)
    button_frame.pack(pady=5)
    
    add_button = tk.Button(button_frame, text="Add Application", command=add_or_update_application)
    add_button.pack(side="left", padx=5)
    
    cancel_button = tk.Button(button_frame, text="Cancel", command=reset_form)
    cancel_button.pack(side="left", padx=5)

    search_entry.bind("<Return>", lambda event: perform_search())

    refresh_tree()