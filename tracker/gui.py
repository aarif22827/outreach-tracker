import tkinter as tk
from tkinter import ttk, messagebox, font
import webbrowser
from datetime import datetime
from tracker.database import get_connection, create_tables
from tkcalendar import DateEntry

STATUS_OPTIONS = [
    "🔵 Not Connected", 
    "✅ Connected", 
    "💬 Messaged", 
    "🔄 Followed Up",
    "📅 Interviewing", 
    "👻 Ghosted", 
    "❌ Rejected", 
    "🏆 Offer"
]

COMPANY_STATUS_OPTIONS = [
    "📝 Not Applied",
    "✅ Applied", 
    "🔍 Under Review",
    "📞 Phone Screen", 
    "📅 Interviewing",
    "🏃‍♂️ Final Rounds", 
    "⏳ Waiting for Decision",
    "👻 Ghosted", 
    "❌ Rejected",
    "🏆 Offer",
    "💼 Accepted"
]

def run_gui():
    create_tables()

    root = tk.Tk()
    root.title("Outreach And Application Tracker")
    root.geometry("1000x600")
    
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    
    outreach_tab = ttk.Frame(notebook)
    company_tab = ttk.Frame(notebook)
    
    notebook.add(outreach_tab, text="💬 Contacts")
    notebook.add(company_tab, text="🏢 Companies")
    
    build_outreach_tab(outreach_tab)
    build_company_tab(company_tab)
    
    root.mainloop()

def build_outreach_tab(parent):
    editing_id = None
    
    table_frame = tk.Frame(parent)
    table_frame.pack(fill="both", expand=True)

    columns = ("Name", "Company", "Title", "LinkedIn", "Status", "Last Contacted", "Notes", "Delete")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings")
    for col in columns[:-1]:
        tree.heading(col, text=col)
        tree.column(col, width=130, anchor="w")
    tree.heading("Delete", text="Delete")
    tree.column("Delete", width=60, anchor="center")
    
    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    def refresh_tree():
        for row in tree.get_children():
            tree.delete(row)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, company, title, linkedin_url, status, last_response, notes FROM outreaches")
        for row in cursor.fetchall():
            rid = row[0]
            tree.insert("", "end", iid=rid, values=(*row[1:], "❌"))
        conn.close()

    def on_tree_click(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            reset_form()
            return
        
        column = tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1
        
        if column_index == 7:
            confirm = messagebox.askyesno("Delete", "Are you sure you want to delete this entry?")
            if confirm:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM outreaches WHERE id = ?", (item_id,))
                conn.commit()
                conn.close()
                refresh_tree()
                reset_form()
        elif column_index == 3:
            values = tree.item(item_id, 'values')
            linkedin_url = values[3]
            if linkedin_url:
                webbrowser.open(linkedin_url)
        else:
            edit_outreach(item_id)
    
    tree.bind("<ButtonRelease-1>", on_tree_click)
    
    def on_frame_click(event):
        if not tree.identify_row(event.y):
            reset_form()
    
    table_frame.bind("<Button-1>", on_frame_click)
    
    def resize_column(event):
        region = tree.identify_region(event.x, event.y)
        if region == "separator":
            column = tree.identify_column(event.x)
            column_index = int(column.replace('#', '')) - 1
            
            if 0 <= column_index < len(columns):
                col_name = columns[column_index]
                header_width = font.Font().measure(col_name) + 20
                max_width = header_width
                
                for item in tree.get_children():
                    values = tree.item(item, 'values')
                    if column_index < len(values):
                        cell_value = str(values[column_index])
                        cell_width = font.Font().measure(cell_value) + 20
                        max_width = max(max_width, cell_width)
                
                tree.column(col_name, width=max(100, max_width))
    
    tree.bind("<Double-1>", resize_column)
    
    def edit_outreach(item_id):
        nonlocal editing_id
        editing_id = item_id
        values = tree.item(item_id, 'values')
        
        entry_name.delete(0, tk.END)
        entry_name.insert(0, values[0])
        
        entry_company.delete(0, tk.END)
        entry_company.insert(0, values[1])
        
        entry_title.delete(0, tk.END)
        entry_title.insert(0, values[2])
        
        entry_linkedin.delete(0, tk.END)
        entry_linkedin.insert(0, values[3])
        
        status_var.set(values[4])
        
        try:
            date_str = values[5]
            if date_str:
                date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                entry_last_response.set_date(date_obj)
            else:
                entry_last_response.set_date(datetime.now())
        except ValueError:
            entry_last_response.set_date(datetime.now())
        
        entry_notes.delete(0, tk.END)
        entry_notes.insert(0, values[6])
        
        add_button.config(text="Update Entry")

    form_frame = tk.Frame(parent)
    form_frame.pack(pady=10)

    tk.Label(form_frame, text="Name").grid(row=0, column=0)
    tk.Label(form_frame, text="Company").grid(row=0, column=2)
    tk.Label(form_frame, text="Title").grid(row=1, column=0)
    tk.Label(form_frame, text="LinkedIn").grid(row=1, column=2)
    tk.Label(form_frame, text="Status").grid(row=2, column=0)
    tk.Label(form_frame, text="Last Contacted").grid(row=2, column=2)
    tk.Label(form_frame, text="Notes").grid(row=3, column=0)

    entry_name = tk.Entry(form_frame)
    entry_company = tk.Entry(form_frame)
    entry_title = tk.Entry(form_frame)
    entry_linkedin = tk.Entry(form_frame)
    status_var = tk.StringVar(value=STATUS_OPTIONS[0])
    dropdown_status = ttk.Combobox(form_frame, textvariable=status_var, values=STATUS_OPTIONS, state="readonly")
    
    entry_last_response = DateEntry(form_frame, width=16, background='darkblue',
                                    foreground='white', borderwidth=2, date_pattern='mm/dd/yyyy')
    
    entry_notes = tk.Entry(form_frame, width=80)

    entry_name.grid(row=0, column=1, padx=5)
    entry_company.grid(row=0, column=3, padx=5)
    entry_title.grid(row=1, column=1, padx=5)
    entry_linkedin.grid(row=1, column=3, padx=5)
    dropdown_status.grid(row=2, column=1, padx=5)
    entry_last_response.grid(row=2, column=3, padx=5)
    entry_notes.grid(row=3, column=1, columnspan=3, pady=5)

    def reset_form():
        nonlocal editing_id
        editing_id = None
        entry_name.delete(0, tk.END)
        entry_company.delete(0, tk.END)
        entry_title.delete(0, tk.END)
        entry_linkedin.delete(0, tk.END)
        entry_last_response.set_date(datetime.now())
        entry_notes.delete(0, tk.END)
        dropdown_status.set(STATUS_OPTIONS[0])
        add_button.config(text="Add Entry")
        
        parent.focus_set()
        
        for selected_item in tree.selection():
            tree.selection_remove(selected_item)
    
    def add_or_update_outreach():
        nonlocal editing_id
        name = entry_name.get().strip()
        company = entry_company.get().strip()
        title = entry_title.get().strip()
        linkedin = entry_linkedin.get().strip()
        status = status_var.get()
        last_response = entry_last_response.get_date().strftime("%m/%d/%Y")
        notes = entry_notes.get().strip()

        if not name or not company:
            messagebox.showerror("Error", "Name and Company are required.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        
        if editing_id:
            cursor.execute('''
                UPDATE outreaches
                SET name = ?, company = ?, title = ?, linkedin_url = ?, 
                    status = ?, last_response = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?''',
                (name, company, title, linkedin, status, last_response, notes, editing_id))
            messagebox.showinfo("Success", "Entry updated successfully!")
        else:
            cursor.execute('''
                INSERT INTO outreaches
                (name, company, title, linkedin_url, status, last_response, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (name, company, title, linkedin, status, last_response, notes))
        
        conn.commit()
        conn.close()
        
        reset_form()
        refresh_tree()

    button_frame = tk.Frame(parent)
    button_frame.pack(pady=5)
    
    add_button = tk.Button(button_frame, text="Add Entry", command=add_or_update_outreach)
    add_button.pack(side="left", padx=5)
    
    cancel_button = tk.Button(button_frame, text="Cancel", command=reset_form)
    cancel_button.pack(side="left", padx=5)

    refresh_tree()

def build_company_tab(parent):
    editing_id = None
    
    table_frame = tk.Frame(parent)
    table_frame.pack(fill="both", expand=True)

    columns = ("Company", "Application Link", "Status", "Last Updated", "Notes", "Delete")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings")
    for col in columns[:-1]:
        tree.heading(col, text=col)
        tree.column(col, width=160, anchor="w")
    tree.heading("Delete", text="Delete")
    tree.column("Delete", width=60, anchor="center")
    
    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    def refresh_tree():
        for row in tree.get_children():
            tree.delete(row)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, application_link, status, updated_at, notes FROM companies")
        for row in cursor.fetchall():
            rid = row[0]
            tree.insert("", "end", iid=rid, values=(*row[1:], "❌"))
        conn.close()

    def on_tree_click(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            reset_form()
            return
        
        column = tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1
        
        if column_index == 5:
            confirm = messagebox.askyesno("Delete", "Are you sure you want to delete this entry?")
            if confirm:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM companies WHERE id = ?", (item_id,))
                conn.commit()
                conn.close()
                refresh_tree()
                reset_form()
        elif column_index == 1:
            values = tree.item(item_id, 'values')
            application_link = values[1]
            if application_link:
                webbrowser.open(application_link)
        else:
            edit_company(item_id)
    
    tree.bind("<ButtonRelease-1>", on_tree_click)
    
    def on_frame_click(event):
        if not tree.identify_row(event.y):
            reset_form()
    
    table_frame.bind("<Button-1>", on_frame_click)
    
    def resize_column(event):
        region = tree.identify_region(event.x, event.y)
        if region == "separator":
            column = tree.identify_column(event.x)
            column_index = int(column.replace('#', '')) - 1
            
            if 0 <= column_index < len(columns):
                col_name = columns[column_index]
                header_width = font.Font().measure(col_name) + 20
                max_width = header_width
                
                for item in tree.get_children():
                    values = tree.item(item, 'values')
                    if column_index < len(values):
                        cell_value = str(values[column_index])
                        cell_width = font.Font().measure(cell_value) + 20
                        max_width = max(max_width, cell_width)
                
                tree.column(col_name, width=max(100, max_width))
    
    tree.bind("<Double-1>", resize_column)
    
    def edit_company(item_id):
        nonlocal editing_id
        editing_id = item_id
        values = tree.item(item_id, 'values')
        
        entry_company.delete(0, tk.END)
        entry_company.insert(0, values[0])
        
        entry_application_link.delete(0, tk.END)
        entry_application_link.insert(0, values[1])
        
        status_var.set(values[2])
        
        entry_notes.delete(0, tk.END)
        entry_notes.insert(0, values[4])
        
        add_button.config(text="Update Entry")

    form_frame = tk.Frame(parent)
    form_frame.pack(pady=10)

    tk.Label(form_frame, text="Company").grid(row=0, column=0)
    tk.Label(form_frame, text="Application Link").grid(row=0, column=2)
    tk.Label(form_frame, text="Status").grid(row=1, column=0)
    tk.Label(form_frame, text="Notes").grid(row=1, column=2)

    entry_company = tk.Entry(form_frame, width=30)
    entry_application_link = tk.Entry(form_frame, width=30)
    status_var = tk.StringVar(value=COMPANY_STATUS_OPTIONS[0])
    dropdown_status = ttk.Combobox(form_frame, textvariable=status_var, values=COMPANY_STATUS_OPTIONS, state="readonly", width=28)
    entry_notes = tk.Entry(form_frame, width=80)

    entry_company.grid(row=0, column=1, padx=5)
    entry_application_link.grid(row=0, column=3, padx=5)
    dropdown_status.grid(row=1, column=1, padx=5)
    entry_notes.grid(row=2, column=0, columnspan=4, pady=5, sticky="ew")

    def reset_form():
        nonlocal editing_id
        editing_id = None
        entry_company.delete(0, tk.END)
        entry_application_link.delete(0, tk.END)
        entry_notes.delete(0, tk.END)
        status_var.set(COMPANY_STATUS_OPTIONS[0])
        add_button.config(text="Add Company")
        
        parent.focus_set()
        
        for selected_item in tree.selection():
            tree.selection_remove(selected_item)
    
    def add_or_update_company():
        nonlocal editing_id
        company = entry_company.get().strip()
        application_link = entry_application_link.get().strip()
        status = status_var.get()
        notes = entry_notes.get().strip()

        if not company:
            messagebox.showerror("Error", "Company name is required.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        
        if editing_id:
            cursor.execute('''
                UPDATE companies
                SET name = ?, application_link = ?, status = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?''',
                (company, application_link, status, notes, editing_id))
            messagebox.showinfo("Success", "Entry updated successfully!")
        else:
            cursor.execute('''
                INSERT INTO companies
                (name, application_link, status, notes)
                VALUES (?, ?, ?, ?)''',
                (company, application_link, status, notes))
        
        conn.commit()
        conn.close()
        
        reset_form()
        refresh_tree()

    button_frame = tk.Frame(parent)
    button_frame.pack(pady=5)
    
    add_button = tk.Button(button_frame, text="Add Entry", command=add_or_update_company)
    add_button.pack(side="left", padx=5)
    
    cancel_button = tk.Button(button_frame, text="Cancel", command=reset_form)
    cancel_button.pack(side="left", padx=5)

    refresh_tree()