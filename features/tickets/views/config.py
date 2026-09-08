import os

AUTO_CLOSE_HOURS = float(os.environ.get("TICKET_AUTO_CLOSE_HOURS", "24"))
WARN_BEFORE_MINUTES = float(os.environ.get("TICKET_WARN_BEFORE_MINUTES", "30"))
STAFF_ROLE_NAME = os.environ.get("TICKET_STAFF_ROLE", "Staff")
MAX_TICKETS_PER_USER = int(os.environ.get("TICKET_MAX_PER_USER", "2"))
