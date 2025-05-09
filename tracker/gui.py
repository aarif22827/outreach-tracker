import tkinter as tk
from tkinter import ttk
from tracker.database import create_tables
from tracker.contacts_tab import build_contacts_tab
from tracker.applications_tab import build_applications_tab
from tracker.reminders_tab import build_reminders_tab
from tracker.resources_tab import build_resources_tab  # Add this import

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

APPLICATION_STATUS_OPTIONS = [
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
    root.geometry("1000x650")
    
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    
    contacts_tab = ttk.Frame(notebook)
    applications_tab = ttk.Frame(notebook)
    reminders_tab = ttk.Frame(notebook)
    resources_tab = ttk.Frame(notebook)  # Add this line
    
    notebook.add(contacts_tab, text="💬 Contacts")
    notebook.add(applications_tab, text="📑 Applications")
    notebook.add(reminders_tab, text="🔔 Reminders")
    notebook.add(resources_tab, text="📁 Resources")  # Add this line
    
    # Build the reminders tab first to get the check_reminders function
    check_reminders = build_reminders_tab(reminders_tab, notebook)
    
    # Pass the check_reminders function to the other tabs
    build_contacts_tab(contacts_tab, STATUS_OPTIONS, check_reminders)
    build_applications_tab(applications_tab, APPLICATION_STATUS_OPTIONS, check_reminders)
    build_resources_tab(resources_tab)  # Add this line
    
    # Check for reminders when the app starts
    check_reminders()
    
    root.mainloop()