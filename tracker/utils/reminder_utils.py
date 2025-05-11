import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry
from tracker.core.models import Reminder, Contact, Application

def create_reminder(item_id, item_name, item_type, parent, callback=None):
    """
    Create a reminder for a contact or application
    
    Parameters:
    - item_id: The ID of the contact or application
    - item_name: Name to display in the reminder
    - item_type: Either "contact" or "application"
    - parent: The parent window
    - callback: Optional function to call after reminder is created
    """
    reminder_window = tk.Toplevel()
    reminder_window.title("Set Follow-up Reminder")
    reminder_window.geometry("400x300")
    reminder_window.transient(parent)
    
    tk.Label(reminder_window, text=f"Reminder for: {item_name}").pack(pady=10)
    
    tk.Label(reminder_window, text="Title:").pack(anchor="w", padx=20)
    title_var = tk.StringVar(value=f"Follow up with {item_name}")
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
    
    desc_text.insert("1.0", f"Send a follow-up email to continue the conversation." if item_type == "contact" 
                   else f"Follow up on application status.")
    
    tk.Label(reminder_window, text="Due Date:").pack(anchor="w", padx=20)
    # Default to 7 days from now
    due_date = DateEntry(reminder_window, width=20, background='darkblue',
                      foreground='white', borderwidth=2, date_pattern='mm/dd/yyyy')
    due_date.pack(anchor="w", padx=20)
    
    def save_reminder():
        reminder = Reminder(
            related_type=item_type,
            related_id=item_id,
            title=title_entry.get().strip(),
            description=desc_text.get("1.0", "end-1c").strip(),
            due_date=due_date.get_date().strftime("%m/%d/%Y"),
            status="pending"
        )
        reminder.save()
        
        messagebox.showinfo("Success", "Reminder created successfully!")
        if callback:
            callback()
        reminder_window.destroy()
    
    button_frame = tk.Frame(reminder_window)
    button_frame.pack(pady=15)
    
    save_button = tk.Button(button_frame, text="Save Reminder", command=save_reminder)
    save_button.pack(side="left", padx=5)
    
    cancel_button = tk.Button(button_frame, text="Cancel", command=reminder_window.destroy)
    cancel_button.pack(side="left", padx=5)

def set_reminder_for_item(item_id, item_type, parent, callback=None):
    """
    Set a reminder for a contact or application after retrieving its details
    
    Parameters:
    - item_id: The ID of the contact or application
    - item_type: Either "contact" or "application" 
    - parent: The parent window
    - callback: Optional function to call after reminder is created
    """
    if item_type == "contact":
        contact = Contact.get_by_id(item_id)
        if contact:
            create_reminder(item_id, contact.name, item_type, parent, callback)
        else:
            messagebox.showerror("Error", "Contact not found.")
    else:
        application = Application.get_by_id(item_id)
        if application:
            name = f"{application.title} at {application.name}"
            create_reminder(item_id, name, item_type, parent, callback)
        else:
            messagebox.showerror("Error", "Application not found.")