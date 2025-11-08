import os
from pydantic import BaseModel, Field

class Config(BaseModel):
    # ---- GCP / Vertex AI ----
    project_id: str = Field(default_factory=lambda: os.environ.get("GOOGLE_CLOUD_PROJECT", "finguard-472115"))
    vertex_location: str = Field(default_factory=lambda: os.environ.get("VERTEX_LOCATION", "asia-south1"))  # India region
    model_name: str = Field(default_factory=lambda: os.environ.get("VERTEX_MODEL", "gemini-1.5-flash-001"))

    # ---- BigQuery ----
    bigquery_dataset: str = Field(default_factory=lambda: os.environ.get("BIGQUERY_DATASET", "finfact"))
    bq_table_logs: str = Field(default_factory=lambda: os.environ.get("BIGQUERY_LOGS_TABLE", "messages"))
    bq_table_sources: str = Field(default_factory=lambda: os.environ.get("BIGQUERY_SOURCES_TABLE", "trusted_sources"))

    # ---- Firestore ----
    firestore_collection_users: str = Field(default_factory=lambda: os.environ.get("FIRESTORE_USERS_COLLECTION", "users"))
    firestore_collection_sessions: str = Field(default_factory=lambda: os.environ.get("FIRESTORE_SESSIONS_COLLECTION", "sessions"))

    # ---- Twilio ----
    twilio_account_sid: str = Field(default_factory=lambda: os.environ.get("TWILIO_ACCOUNT_SID", ""))
    twilio_auth_token: str = Field(default_factory=lambda: os.environ.get("TWILIO_AUTH_TOKEN", ""))
    twilio_whatsapp_number: str = Field(default_factory=lambda: os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886"))
    require_twilio_signature: bool = Field(default_factory=lambda: os.environ.get("REQUIRE_TWILIO_SIGNATURE", "false").lower() == "true")

    # ---- App settings ----
    max_history_messages: int = Field(default_factory=lambda: int(os.environ.get("MAX_HISTORY_MESSAGES", "10")))
    min_reply_chars: int = 300
    max_reply_chars: int = 1100  # keep under WhatsApp 1600 char limit incl links

# Single config instance
config = Config()
