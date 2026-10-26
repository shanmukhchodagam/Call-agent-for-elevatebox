import os
from dotenv import load_dotenv

load_dotenv()

# OmniDimension Configuration
OMNIDIM_API_KEY = os.getenv("OMNIDIM_API_KEY")
OMNIDIM_AGENT_ID = os.getenv("OMNIDIM_AGENT_ID", "259394")

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Database & System Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "elevate_sales.db")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

# Candidate & Assignment Submission Configuration (Section 06)
CANDIDATE_MOBILE_NUMBER = os.getenv("CANDIDATE_MOBILE_NUMBER", "+919381758441")
ARCHITECTURE_IMAGE_URL = os.getenv("ARCHITECTURE_IMAGE_URL", "https://raw.githubusercontent.com/elevate_sales_agent/main/architecture.png")
EVALUATOR_PHONE_NUMBER = os.getenv("EVALUATOR_PHONE_NUMBER", "+918688664337")

# WhatsApp Action Configuration (Optional external provider)
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")