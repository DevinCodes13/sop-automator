import os

DATABASE_URL = os.environ["DATABASE_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_MINUTES = int(os.getenv("JWT_MINUTES", "60"))
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"].lower()
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")
FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "https://hapi.fhir.org/baseR4")
SCHOOL_TZ = os.getenv("SCHOOL_TZ", "America/Chicago")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
