import os

# Safe fake settings so tests can import the app without real secrets
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
