import tkinter as tk
from tkinter import ttk, messagebox
from tracker.database import get_connection, create_tables

STATUS_OPTIONS = [
    "Not Connected", "Connected", "Messaged", "Followed Up",
    "Interviewing", "Ghosted", "Rejected", "Offer"
]

def run_gui():
    create_tables()

    root = tk.Tk()
    root.title("Recruiter Tracker")
    root.geometry("1000x550")

    table_frame = tk.Frame(root)
    table_frame.pack(fill="both", expand=True)

    columns = ("Name", "Company", "Title", "LinkedIn", "Status", "Last Contacted", "Notes", "Delete")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings")
    for col in columns[:-1]:
        tree.heading(col, text=col)
        tree.column(col, width=130, anchor="w")
    tree.heading("Delete", text="")
    tree.column("Delete", width=60)
    tree.pack(fill="both", expand=True)

    def refresh_tree():
        for row in tree.get_children():
            tree.delete(row)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, company, title, linkedin_url, status, last_response, notes FROM recruiters")
        for row in cursor.fetchall():
            rid = row[0]
            tree.insert("", "end", iid=rid, values=(*row[1:], "Delete"))
        conn.close()

    def delete_recruiter(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
        confirm = messagebox.askyesno("Delete", "Are you sure you want to delete this recruiter?")
        if confirm:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM recruiters WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            refresh_tree()

    tree.bind("<Button-1>", lambda event: (
        delete_recruiter(event) if tree.identify_column(event.x) == f"#{len(columns)}" else None
    ))

    form_frame = tk.Frame(root)
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
    entry_last_response = tk.Entry(form_frame)
    entry_notes = tk.Entry(form_frame, width=80)

    entry_name.grid(row=0, column=1, padx=5)
    entry_company.grid(row=0, column=3, padx=5)
    entry_title.grid(row=1, column=1, padx=5)
    entry_linkedin.grid(row=1, column=3, padx=5)
    dropdown_status.grid(row=2, column=1, padx=5)
    entry_last_response.grid(row=2, column=3, padx=5)
    entry_notes.grid(row=3, column=1, columnspan=3, pady=5)

    def add_recruiter():
        name = entry_name.get().strip()
        company = entry_company.get().strip()
        title = entry_title.get().strip()
        linkedin = entry_linkedin.get().strip()
        status = status_var.get()
        last_response = entry_last_response.get().strip()
        notes = entry_notes.get().strip()

        if not name or not company:
            messagebox.showerror("Error", "Name and Company are required.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO recruiters
            (name, company, title, linkedin_url, status, last_response, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (name, company, title, linkedin, status, last_response, notes))
        conn.commit()
        conn.close()

        entry_name.delete(0, tk.END)
        entry_company.delete(0, tk.END)
        entry_title.delete(0, tk.END)
        entry_linkedin.delete(0, tk.END)
        entry_last_response.delete(0, tk.END)
        entry_notes.delete(0, tk.END)
        dropdown_status.set(STATUS_OPTIONS[0])

        refresh_tree()

    tk.Button(root, text="Add Recruiter", command=add_recruiter).pack(pady=5)

    refresh_tree()
    root.mainloop()
