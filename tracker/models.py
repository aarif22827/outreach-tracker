from dataclasses import dataclass

@dataclass
class Recruiter:
    name: str
    company: str
    title: str
    linkedin_url: str
    connection_sent: bool = False
    message_sent: bool = False
    followup_sent: bool = False
    status: str = "Not Contacted"
    last_response: str = ""
    notes: str = ""

@dataclass
class Company:
    name: str
    industry: str
    website: str
    applied: bool = False
    status: str = "Not Applied"
    notes: str = ""