import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from tkcalendar import DateEntry
import webbrowser
import os

from tracker.core.models import Reminder, Contact, Application

def build_reminders_tab(parent, notebook):
    """
    Build the reminders tab
    
    Parameters:
    - parent: Parent frame
    - notebook: The main notebook widget to allow switching tabs
    
    Returns:
    - check_reminders: Function to check for upcoming reminders
    """
    controls_frame = tk.Frame(parent)
    controls_frame.pack(fill="x", padx=10, pady=5)
    
    filter_frame = tk.Frame(controls_frame)
    filter_frame.pack(side="left")
    
    tk.Label(filter_frame, text="Filter by status:").pack(side="left")
    status_var = tk.StringVar(value="pending")
    status_combo = ttk.Combobox(filter_frame, textvariable=status_var, 
                              values=["all", "pending", "completed", "snoozed"], 
                              width=10, state="readonly")
    status_combo.pack(side="left", padx=5)
    
    date_frame = tk.Frame(controls_frame)
    date_frame.pack(side="left", padx=20)
    
    tk.Label(date_frame, text="Due within:").pack(side="left")
    days_var = tk.StringVar(value="7")
    days_combo = ttk.Combobox(date_frame, textvariable=days_var, 
                            values=["1", "3", "7", "14", "30", "all"], 
                            width=5, state="readonly")
    days_combo.pack(side="left", padx=5)
    tk.Label(date_frame, text="days").pack(side="left")
    
    refresh_btn = ttk.Button(controls_frame, text="Refresh", 
                          command=lambda: refresh_reminders(status_var.get(), days_var.get()))
    refresh_btn.pack(side="right", padx=10)
    
    columns = ("Title", "Related To", "Description", "Due Date", "Status")
    tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
    
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    
    tree.column("Title", width=150)
    tree.column("Description", width=200)
    
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    tree.pack(side="left", fill="both", expand=True, padx=10, pady=5)
    scrollbar.pack(side="right", fill="y", pady=5)
    
    reminder_data = {}
    
    def refresh_reminders(status_filter="pending", days_filter="7"):
        """Refresh the reminders list based on filters"""
        for item in tree.get_children():
            tree.delete(item)
            
        reminder_data.clear()
        
        if days_filter == "all":
            reminders = []
            
            if status_filter == "all":
                reminders = Reminder.find_all()
            else:
                reminders = Reminder.find_all("status = ?", (status_filter,))
        else:
            days = int(days_filter)
            
            if status_filter == "all":
                today = datetime.now()
                future_date = today + timedelta(days=days)
                
                today_str = today.strftime("%m/%d/%Y")
                future_str = future_date.strftime("%m/%d/%Y")
                
                reminders = Reminder.find_all(
                    "julianday(due_date) >= julianday(?) AND julianday(due_date) <= julianday(?)",
                    (today_str, future_str)
                )
            elif status_filter == "pending":
                reminders = Reminder.find_upcoming(days)
            else:
                today = datetime.now()
                future_date = today + timedelta(days=days)
                
                today_str = today.strftime("%m/%d/%Y")
                future_str = future_date.strftime("%m/%d/%Y")
                
                reminders = Reminder.find_all(
                    "status = ? AND julianday(due_date) >= julianday(?) AND julianday(due_date) <= julianday(?)",
                    (status_filter, today_str, future_str)
                )
                
        for reminder in reminders:
            related_text = ""
            if hasattr(reminder, 'related_name'):
                related_text = reminder.related_name
            else:
                if reminder.related_type == "contact":
                    contact = Contact.get_by_id(reminder.related_id)
                    if contact:
                        related_text = f"{contact.name} at {contact.company}"
                elif reminder.related_type == "application":
                    application = Application.get_by_id(reminder.related_id)
                    if application:
                        related_text = f"{application.title} at {application.name}"
            
            tree.insert("", "end", iid=reminder.id, values=(
                reminder.title,
                related_text,
                reminder.description[:50] + "..." if len(reminder.description) > 50 else reminder.description,
                reminder.due_date,
                reminder.status
            ))
            
            reminder_data[str(reminder.id)] = reminder
            
        highlight_overdue_reminders()
    
    def highlight_overdue_reminders():
        """Highlight reminders that are overdue"""
        today = datetime.now()
        
        for item_id in tree.get_children():
            reminder_id = str(item_id)
            if reminder_id in reminder_data:
                reminder = reminder_data[reminder_id]
                if reminder.status == "pending":
                    try:
                        due_date = datetime.strptime(reminder.due_date, "%m/%d/%Y")
                        if due_date < today:
                            tree.item(item_id, tags=("overdue",))
                    except ValueError:
                        pass
        
        tree.tag_configure("overdue", foreground="red")
    
    def show_context_menu(event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
            
        tree.selection_set(item_id)
        reminder_id = str(item_id)
        
        if reminder_id in reminder_data:
            reminder = reminder_data[reminder_id]
            
            context_menu = tk.Menu(tree, tearoff=0)
            
            if reminder.related_type and reminder.related_id:
                context_menu.add_command(
                    label=f"View {reminder.related_type.capitalize()}", 
                    command=lambda: view_related_item(reminder.related_type, reminder.related_id)
                )
                context_menu.add_separator()
            
            if reminder.status == "pending":
                context_menu.add_command(
                    label="Mark Complete", 
                    command=lambda: mark_complete(reminder_id)
                )
                context_menu.add_command(
                    label="Snooze", 
                    command=lambda: snooze_reminder(reminder_id)
                )
            elif reminder.status == "snoozed":
                context_menu.add_command(
                    label="Mark Complete", 
                    command=lambda: mark_complete(reminder_id)
                )
                context_menu.add_command(
                    label="Mark Pending", 
                    command=lambda: mark_pending(reminder_id)
                )
            elif reminder.status == "completed":
                context_menu.add_command(
                    label="Mark Pending", 
                    command=lambda: mark_pending(reminder_id)
                )
                
            context_menu.add_separator()
            context_menu.add_command(
                label="Delete", 
                command=lambda: delete_reminder(reminder_id)
            )
            
            context_menu.tk_popup(event.x_root, event.y_root)
    
    tree.bind("<Button-3>", show_context_menu)
    
    def view_related_item(related_type, related_id):
        """Navigate to the related contact or application"""
        if related_type == "contact":
            notebook.select(0)
            parent.event_generate("<<SelectContact>>", data=related_id)
        elif related_type == "application":
            notebook.select(1)
            parent.event_generate("<<SelectApplication>>", data=related_id)
    
    def mark_complete(reminder_id):
        """Mark a reminder as complete"""
        reminder = Reminder.get_by_id(int(reminder_id))
        if reminder:
            reminder.mark_complete()
            refresh_reminders(status_var.get(), days_var.get())
    
    def mark_pending(reminder_id):
        """Mark a reminder as pending"""
        reminder = Reminder.get_by_id(int(reminder_id))
        if reminder:
            reminder.status = "pending"
            reminder.save()
            refresh_reminders(status_var.get(), days_var.get())
    
    def snooze_reminder(reminder_id):
        """Snooze a reminder to a later date"""
        reminder = Reminder.get_by_id(int(reminder_id))
        if not reminder:
            return
            
        snooze_dialog = tk.Toplevel()
        snooze_dialog.title("Snooze Reminder")
        snooze_dialog.geometry("300x150")
        snooze_dialog.transient(parent)
        snooze_dialog.grab_set()
        
        tk.Label(snooze_dialog, text="Snooze until:").pack(pady=(10, 5))
        
        date_picker = DateEntry(snooze_dialog, width=12, background='darkblue',
                             foreground='white', borderwidth=2, date_pattern='mm/dd/yyyy')
        date_picker.pack(pady=5)
        
        try:
            tomorrow = datetime.now() + timedelta(days=1)
            date_picker.set_date(tomorrow)
        except:
            pass
        
        def confirm_snooze():
            new_date = date_picker.get_date().strftime("%m/%d/%Y")
            reminder.snooze(new_date)
            refresh_reminders(status_var.get(), days_var.get())
            snooze_dialog.destroy()
        
        button_frame = tk.Frame(snooze_dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Snooze", command=confirm_snooze).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=snooze_dialog.destroy).pack(side="left", padx=5)
    
    def delete_reminder(reminder_id):
        """Delete a reminder"""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this reminder?"):
            reminder = Reminder.get_by_id(int(reminder_id))
            if reminder:
                reminder.delete()
                refresh_reminders(status_var.get(), days_var.get())
    
    def check_reminders():
        """Check for upcoming reminders and show notification if needed"""
        today = datetime.now().strftime("%m/%d/%Y")
        due_reminders = Reminder.find_all(
            "status = 'pending' AND julianday(due_date) <= julianday(?)", 
            (today,)
        )
        
        if due_reminders:
            refresh_reminders(status_var.get(), days_var.get())
            
            remind_window = tk.Toplevel()
            remind_window.title("Reminder Alert")
            remind_window.geometry("400x300")
            remind_window.transient(parent.master)
            
            tk.Label(
                remind_window, 
                text="You have reminders due today!", 
                font=("Arial", 14, "bold")
            ).pack(pady=10)
            
            list_frame = tk.Frame(remind_window)
            list_frame.pack(fill="both", expand=True, padx=10)
            
            remind_list = tk.Listbox(list_frame, height=10, width=50)
            remind_scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=remind_list.yview)
            remind_list.configure(yscrollcommand=remind_scrollbar.set)
            
            remind_list.pack(side="left", fill="both", expand=True)
            remind_scrollbar.pack(side="right", fill="y")
            
            for i, reminder in enumerate(due_reminders):
                related_text = ""
                if reminder.related_type == "contact":
                    contact = Contact.get_by_id(reminder.related_id)
                    if contact:
                        related_text = f"{contact.name}"
                elif reminder.related_type == "application":
                    application = Application.get_by_id(reminder.related_id)
                    if application:
                        related_text = f"{application.title}"
                
                if related_text:
                    remind_list.insert(tk.END, f"{reminder.title} ({related_text})")
                else:
                    remind_list.insert(tk.END, reminder.title)
                
                remind_list.itemconfig(i, {"reminder_id": reminder.id})
            
            button_frame = tk.Frame(remind_window)
            button_frame.pack(pady=10)
            
            def view_reminder_tab():
                notebook.select(2)
                remind_window.destroy()
                
            def snooze_all():
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
                for reminder in due_reminders:
                    reminder.snooze(tomorrow)
                refresh_reminders(status_var.get(), days_var.get())
                remind_window.destroy()
                
            tk.Button(button_frame, text="View Reminders", command=view_reminder_tab).pack(side="left", padx=5)
            tk.Button(button_frame, text="Snooze All to Tomorrow", command=snooze_all).pack(side="left", padx=5)
            tk.Button(button_frame, text="Dismiss", command=remind_window.destroy).pack(side="left", padx=5)
            
            return len(due_reminders)
        
        return 0
    
    status_combo.bind("<<ComboboxSelected>>", lambda e: refresh_reminders(status_var.get(), days_var.get()))
    days_combo.bind("<<ComboboxSelected>>", lambda e: refresh_reminders(status_var.get(), days_var.get()))
    
    refresh_reminders()
    
    return check_reminders