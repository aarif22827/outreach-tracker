from dataclasses import dataclass

@dataclass
class Outreach:
    name: str
    company: str
    title: str
    linkedin_url: str
    status: str = "🔵 Not Connected"
    last_response: str = ""
    notes: str = ""

@dataclass
class Company:
    name: str
    application_link: str = ""
    status: str = "📝 Not Applied"
    notes: str = ""