import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from tkcalendar import DateEntry
from tracker.database import get_connection

def build_reminders_tab(parent, notebook):
    # Main frame
    main_frame = tk.Frame(parent)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Filter frame
    filter_frame = tk.Frame(main_frame)
    filter_frame.pack(fill="x", pady=5)
    
    # Filter by status
    tk.Label(filter_frame, text="Show:").pack(side="left")
    status_var = tk.StringVar(value="All")
    status_filter = ttk.Combobox(filter_frame, textvariable=status_var, 
                                values=["All", "Pending", "Completed", "Snoozed"], 
                                state="readonly", width=15)
    status_filter.pack(side="left", padx=5)
    
    # Filter by date range
    tk.Label(filter_frame, text="Date Range:").pack(side="left", padx=(20, 5))
    date_var = tk.StringVar(value="All")
    date_filter = ttk.Combobox(filter_frame, textvariable=date_var, 
                              values=["All", "Today", "This Week", "Next Week", "Custom"], 
                              state="readonly", width=15)
    date_filter.pack(side="left", padx=5)
    
    # Custom date range frame (initially hidden)
    custom_frame = tk.Frame(filter_frame)
    
    tk.Label(custom_frame, text="From:").pack(side="left")
    from_date = DateEntry(custom_frame, width=12, background='darkblue',
                        foreground='white', borderwidth=2, date_pattern='mm/dd/yyyy')
    from_date.pack(side="left", padx=5)
    
    tk.Label(custom_frame, text="To:").pack(side="left")
    to_date = DateEntry(custom_frame, width=12, background='darkblue',
                      foreground='white', borderwidth=2, date_pattern='mm/dd/yyyy')
    to_date.pack(side="left", padx=5)
    
    # Table of reminders
    table_frame = tk.Frame(main_frame)
    table_frame.pack(fill="both", expand=True, pady=10)
    
    columns = ("Title", "Related To", "Due Date", "Status", "Actions")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings")
    
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120, anchor="w")
    
    tree.column("Actions", width=100, anchor="center")
    
    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)
    
    # Store the full details of reminders
    reminder_details = {}
    
    def show_hide_custom_dates(event=None):
        if date_var.get() == "Custom":
            custom_frame.pack(side="left")
        else:
            custom_frame.pack_forget()
            refresh_reminders()
    
    date_filter.bind("<<ComboboxSelected>>", show_hide_custom_dates)
    
    def apply_custom_filter():
        if date_var.get() == "Custom":
            refresh_reminders()
    
    apply_button = tk.Button(filter_frame, text="Apply", command=apply_custom_filter)
    apply_button.pack(side="left", padx=10)
    
    status_filter.bind("<<ComboboxSelected>>", lambda e: refresh_reminders())
    
    def view_reminder_details(reminder_id):
        reminder = reminder_details[reminder_id]
        
        popup = tk.Toplevel()
        popup.title("Reminder Details")
        popup.geometry("500x400")
        popup.transient(parent)
        
        tk.Label(popup, text="Title:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        title_label = tk.Label(popup, text=reminder["title"], font=("Arial", 12, "bold"), anchor="w")
        title_label.pack(fill="x", padx=10)
        
        related_type = "Application" if reminder["related_type"] == "application" else "Contact"
        tk.Label(popup, text=f"Related to {related_type}:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        related_label = tk.Label(popup, text=reminder["related_name"], anchor="w")
        related_label.pack(fill="x", padx=10)
        
        tk.Label(popup, text="Due Date:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        date_label = tk.Label(popup, text=reminder["due_date"], anchor="w")
        date_label.pack(fill="x", padx=10)
        
        tk.Label(popup, text="Status:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        status_label = tk.Label(popup, text=reminder["status"].capitalize(), anchor="w")
        status_label.pack(fill="x", padx=10)
        
        tk.Label(popup, text="Description:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        
        desc_frame = tk.Frame(popup)
        desc_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        desc_text = tk.Text(desc_frame, wrap="word", height=5)
        desc_scrollbar = tk.Scrollbar(desc_frame, command=desc_text.yview)
        desc_text.configure(yscrollcommand=desc_scrollbar.set)
        
        desc_text.pack(side="left", fill="both", expand=True)
        desc_scrollbar.pack(side="right", fill="y")
        
        desc_text.insert("1.0", reminder["description"])
        desc_text.config(state="disabled")
        
        def mark_complete():
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (reminder_id,))
            conn.commit()
            conn.close()
            refresh_reminders()
            popup.destroy()
        
        def snooze_reminder():
            snooze_popup = tk.Toplevel(popup)
            snooze_popup.title("Snooze Reminder")
            snooze_popup.transient(popup)
            snooze_popup.geometry("300x150")
            
            tk.Label(snooze_popup, text="Snooze until:").pack(pady=(10, 5))
            
            snooze_date = DateEntry(snooze_popup, width=12, background='darkblue',
                                 foreground='white', borderwidth=2, date_pattern='mm/dd/yyyy')
            snooze_date.pack(pady=5)
            
            def perform_snooze(new_date):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE reminders SET due_date = ?, status = 'snoozed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                             (new_date, reminder_id))
                conn.commit()
                conn.close()
                refresh_reminders()
                snooze_popup.destroy()
                popup.destroy()
                
            snooze_button = tk.Button(snooze_popup, text="Snooze", 
                                   command=lambda: perform_snooze(snooze_date.get_date().strftime("%m/%d/%Y")))
            snooze_button.pack(pady=10)
        
        def goto_related():
            # Switch to the appropriate tab and select the related item
            if reminder["related_type"] == "contact":
                notebook.select(0)  # Contacts tab
            elif reminder["related_type"] == "application":
                notebook.select(1)  # Applications tab
            popup.destroy()
        
        button_frame = tk.Frame(popup)
        button_frame.pack(pady=10)
        
        complete_btn = tk.Button(button_frame, text="Mark Complete", command=mark_complete)
        complete_btn.pack(side="left", padx=5)
        
        snooze_btn = tk.Button(button_frame, text="Snooze", command=snooze_reminder)
        snooze_btn.pack(side="left", padx=5)
        
        goto_btn = tk.Button(button_frame, text="Go to Related Item", command=goto_related)
        goto_btn.pack(side="left", padx=5)
        
        close_btn = tk.Button(popup, text="Close", command=popup.destroy)
        close_btn.pack(pady=10)
    
    def on_tree_double_click(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
            
        view_reminder_details(item_id)
    
    tree.bind("<Double-1>", on_tree_double_click)
    
    def on_tree_click(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
        
        column = tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1
        
        if column_index == 4:  # Actions column
            # Create a popup menu with actions
            item_id_str = str(item_id)
            
            action_menu = tk.Menu(tree, tearoff=0)
            action_menu.add_command(label="View Details", 
                                 command=lambda: view_reminder_details(item_id_str))
            action_menu.add_command(label="Mark Complete", 
                                 command=lambda: update_reminder_status(item_id_str, "completed"))
            action_menu.add_command(label="Delete", 
                                 command=lambda: delete_reminder(item_id_str))
            
            action_menu.post(event.x_root, event.y_root)
    
    tree.bind("<ButtonRelease-1>", on_tree_click)
    
    def update_reminder_status(reminder_id, new_status):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE reminders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                     (new_status, reminder_id))
        conn.commit()
        conn.close()
        refresh_reminders()
    
    def delete_reminder(reminder_id):
        confirm = messagebox.askyesno("Delete Reminder", "Are you sure you want to delete this reminder?")
        if confirm:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()
            conn.close()
            refresh_reminders()
    
    def refresh_reminders():
        # Clear existing data
        for row in tree.get_children():
            tree.delete(row)
        reminder_details.clear()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Basic query
        query = """
            SELECT r.id, r.title, r.related_type, r.related_id, r.due_date, r.status, r.description,
                   CASE 
                       WHEN r.related_type = 'contact' THEN o.name
                       WHEN r.related_type = 'application' THEN a.title || ' at ' || a.name
                       ELSE 'Unknown'
                   END as related_name
            FROM reminders r
            LEFT JOIN outreaches o ON r.related_id = o.id AND r.related_type = 'contact'
            LEFT JOIN applications a ON r.related_id = a.id AND r.related_type = 'application'
            WHERE 1=1
        """
        params = []
        
        # Status filter
        if status_var.get() != "All":
            query += " AND r.status = ?"
            params.append(status_var.get().lower())
        
        # Date filter
        today = datetime.now().date()
        if date_var.get() == "Today":
            query += " AND date(r.due_date) = date(?)"
            params.append(today.strftime("%m/%d/%Y"))
        elif date_var.get() == "This Week":
            # Get the date for next 7 days
            next_week = today + timedelta(days=7)
            query += " AND date(r.due_date) BETWEEN date(?) AND date(?)"
            params.extend([today.strftime("%m/%d/%Y"), next_week.strftime("%m/%d/%Y")])
        elif date_var.get() == "Next Week":
            start_next_week = today + timedelta(days=7)
            end_next_week = today + timedelta(days=14)
            query += " AND date(r.due_date) BETWEEN date(?) AND date(?)"
            params.extend([start_next_week.strftime("%m/%d/%Y"), end_next_week.strftime("%m/%d/%Y")])
        elif date_var.get() == "Custom":
            start_date = from_date.get_date()
            end_date = to_date.get_date()
            query += " AND date(r.due_date) BETWEEN date(?) AND date(?)"
            params.extend([start_date.strftime("%m/%d/%Y"), end_date.strftime("%m/%d/%Y")])
        
        # Order by due date
        query += " ORDER BY date(r.due_date), r.status"
        
        cursor.execute(query, params)
        
        for row in cursor.fetchall():
            rid = str(row[0])
            title = row[1]
            related_type = row[2]
            related_id = row[3]
            due_date = row[4]
            status = row[5].capitalize()
            description = row[6]
            related_name = row[7]
            
            # Calculate if the reminder is overdue
            try:
                due_date_obj = datetime.strptime(due_date, "%m/%d/%Y").date()
                if due_date_obj < today and status.lower() != "completed":
                    display_status = "⚠️ Overdue"
                else:
                    display_status = status
            except:
                display_status = status
            
            # Store the full details
            reminder_details[rid] = {
                "id": rid,
                "title": title,
                "related_type": related_type,
                "related_id": related_id,
                "due_date": due_date,
                "status": status.lower(),
                "description": description,
                "related_name": related_name
            }
            
            tree.insert("", "end", iid=rid, values=(title, related_name, due_date, display_status, "⚙️"))
        
        conn.close()
    
    # Button to add a new reminder manually
    def add_new_reminder():
        popup = tk.Toplevel()
        popup.title("Add New Reminder")
        popup.geometry("500x400")
        popup.transient(parent)
        
        tk.Label(popup, text="Title:").pack(anchor="w", padx=10, pady=(10, 0))
        title_entry = tk.Entry(popup, width=50)
        title_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        tk.Label(popup, text="Related To:").pack(anchor="w", padx=10)
        related_frame = tk.Frame(popup)
        related_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        related_type_var = tk.StringVar(value="contact")
        tk.Radiobutton(related_frame, text="Contact", variable=related_type_var, value="contact").pack(side="left")
        tk.Radiobutton(related_frame, text="Application", variable=related_type_var, value="application").pack(side="left")
        
        # We need to create a system to select related items
        tk.Label(popup, text="Select Item:").pack(anchor="w", padx=10)
        
        related_items_var = tk.StringVar()
        related_items_dropdown = ttk.Combobox(popup, textvariable=related_items_var, width=48, state="readonly")
        related_items_dropdown.pack(fill="x", padx=10, pady=(0, 10))
        
        related_items_map = {}  # To store id -> name mapping
        
        def update_related_items(*args):
            related_type = related_type_var.get()
            
            conn = get_connection()
            cursor = conn.cursor()
            
            related_items_map.clear()
            
            if related_type == "contact":
                cursor.execute("SELECT id, name, company FROM outreaches ORDER BY name")
                items = [(str(r[0]), f"{r[1]} ({r[2]})") for r in cursor.fetchall()]
            else:
                cursor.execute("SELECT id, title, name FROM applications ORDER BY name")
                items = [(str(r[0]), f"{r[1]} at {r[2]}") for r in cursor.fetchall()]
            
            for item_id, item_name in items:
                related_items_map[item_name] = item_id
            
            related_items_dropdown['values'] = list(related_items_map.keys())
            if related_items_dropdown['values']:
                related_items_dropdown.current(0)
            
            conn.close()
        
        related_type_var.trace("w", update_related_items)
        update_related_items()
        
        tk.Label(popup, text="Due Date:").pack(anchor="w", padx=10)
        due_date = DateEntry(popup, width=20, background='darkblue',
                           foreground='white', borderwidth=2, date_pattern='mm/dd/yyyy')
        due_date.pack(anchor="w", padx=10, pady=(0, 10))
        
        tk.Label(popup, text="Description:").pack(anchor="w", padx=10)
        
        desc_frame = tk.Frame(popup)
        desc_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        desc_text = tk.Text(desc_frame, wrap="word", height=5)
        desc_scrollbar = tk.Scrollbar(desc_frame, command=desc_text.yview)
        desc_text.configure(yscrollcommand=desc_scrollbar.set)
        
        desc_text.pack(side="left", fill="both", expand=True)
        desc_scrollbar.pack(side="right", fill="y")
        
        def save_reminder():
            if not title_entry.get().strip():
                messagebox.showwarning("Missing Information", "Please enter a title for the reminder.")
                return
                
            if not related_items_var.get():
                messagebox.showwarning("Missing Information", "Please select a related item.")
                return
            
            related_id = related_items_map[related_items_var.get()]
            
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO reminders
                (title, related_type, related_id, due_date, description, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                title_entry.get().strip(),
                related_type_var.get(),
                related_id,
                due_date.get_date().strftime("%m/%d/%Y"),
                desc_text.get("1.0", "end-1c").strip(),
                "pending"
            ))
            
            conn.commit()
            conn.close()
            
            refresh_reminders()
            popup.destroy()
        
        button_frame = tk.Frame(popup)
        button_frame.pack(pady=10)
        
        save_button = tk.Button(button_frame, text="Save Reminder", command=save_reminder)
        save_button.pack(side="left", padx=5)
        
        cancel_button = tk.Button(button_frame, text="Cancel", command=popup.destroy)
        cancel_button.pack(side="left", padx=5)

    add_button = tk.Button(main_frame, text="+ Add New Reminder", command=add_new_reminder)
    add_button.pack(pady=10)
    
    # Check for upcoming reminders on tab selection
    def check_upcoming_reminders():
        conn = get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        next_day = today + timedelta(days=1)
        
        cursor.execute('''
            SELECT COUNT(*) FROM reminders
            WHERE status = 'pending'
            AND date(due_date) <= date(?)
        ''', (next_day.strftime("%m/%d/%Y"),))
        
        count = cursor.fetchone()[0]
        
        if count > 0:
            notebook.tab(2, text=f"🔔 Reminders ({count})")
        else:
            notebook.tab(2, text="🔔 Reminders")
        
        conn.close()
    
    # Initial load
    refresh_reminders()
    
    # Return the update function so it can be called from outside
    return check_upcoming_reminders