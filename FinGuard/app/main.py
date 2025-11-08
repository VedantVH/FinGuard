import time
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from google.cloud import firestore, bigquery
import vertexai
from vertexai.generative_models import GenerativeModel

from app.config import config
from app.gcp import get_firestore, get_bigquery


import time
from typing import Dict, Any, List

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

from google.cloud import firestore, bigquery
import vertexai
from vertexai.generative_models import GenerativeModel

from .config import config
from .gcp import get_firestore, get_bigquery
from .schemas import Classification


# ---- Init FastAPI ----
app = FastAPI(title="FinFact WhatsApp Bot")

# ---- Init Vertex AI ----
vertexai.init(project=config.project_id, location=config.vertex_location)
gemini_model = GenerativeModel("gemini-2.0-flash-001")

# ---- BigQuery client ----
bq_client = bigquery.Client(project=config.project_id)

# ---- Health endpoint ----
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# -------- Utility Functions --------
def verify_twilio(request: Request, body: dict) -> bool:
    if not config.require_twilio_signature:
        return True
    validator = RequestValidator(config.twilio_auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    return validator.validate(url, body, signature)

def get_user_id(params: dict) -> str:
    return params.get("WaId") or params.get("From", "")

def save_history(fs, user_id: str, user_text: str, bot_text: str):
    sess_ref = fs.collection(config.firestore_collection_sessions).document(user_id)
    doc = sess_ref.get()
    data = doc.to_dict() if doc.exists else {}
    history = data.get("history", [])
    history.append({"user": user_text, "bot": bot_text, "ts": time.time()})
    history = history[-config.max_history_messages:]
    sess_ref.set({"history": history}, merge=True)

def upsert_user(fs, user_id: str, phone: str, profile_name: str):
    uref = fs.collection(config.firestore_collection_users).document(user_id)
    uref.set({
        "user_id": user_id,
        "phone": phone,
        "profile_name": profile_name,
        "last_seen": time.time(),
        "created_at": firestore.SERVER_TIMESTAMP,
    }, merge=True)

def log_to_bigquery(bq, payload: dict):
    table = f"{config.project_id}.{config.bigquery_dataset}.{config.bq_table_logs}"
    errors = bq.insert_rows_json(table, [payload])
    if errors:
        print("BQ insert errors:", errors)


# -------- Trusted Sources & Vertex AI --------
def check_trusted_sources(user_message: str, region: str = "IN") -> List[Dict[str, str]]:
    """
    Fetch top 3 relevant trusted sources based on topic keywords in user_message.
    """
    topic = "scam" if "guarantee" in user_message.lower() else "general"

    query = f"""
        SELECT topic, region, source_name, url, source_type, credibility_score
        FROM `{config.project_id}.{config.bigquery_dataset}.{config.bq_table_sources}`
        WHERE topic = @topic
        AND (region = @region OR region IS NULL OR region = '')
        ORDER BY credibility_score DESC
        LIMIT 3
    """

    job = bq_client.query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("topic", "STRING", topic),
                bigquery.ScalarQueryParameter("region", "STRING", region),
            ]
        ),
    )
    return [dict(row) for row in job.result()]

def vertex_ai_analyze(user_message: str, region: str = "IN") -> dict:
    sources = check_trusted_sources(user_message, region)
    sources_text = "\n".join([f"*{s['source_name']}*: {s['url']}" for s in sources]) if sources else "None found"

    prompt = f"""
    You are FinGuard AI, a financial misinformation assistant for Indian markets.

    User message: "{user_message}"

    Task:
    1. Classify this as: Safe ✅, Warning ⚠️, or Scam 🚨.
    2. Explain why (2–3 sentences).
    3. Trusted sources evidence:
    {sources_text}
    """

    response = gemini_model.generate_content([prompt])
    explanation = response.text.strip() if response and response.text else "No response from AI."
    verdict = "Scam 🚨" if "guarantee" in user_message.lower() else "Check Needed ⚠️"
    return {
        "verdict": verdict,
        "explanation": explanation,
        "sources": sources
    }


# -------- WhatsApp Webhook (/webhook) --------
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    params = dict(form)

    if not verify_twilio(request, params):
        return PlainTextResponse("Signature verification failed", status_code=status.HTTP_403_FORBIDDEN)

    user_text = params.get("Body", "").strip()
    from_number = params.get("From", "")
    profile_name = params.get("ProfileName", "") or "WhatsApp User"
    user_id = get_user_id(params)

    fs = get_firestore()
    upsert_user(fs, user_id, from_number, profile_name)
    resp = MessagingResponse()

    if not user_text:
        resp.message("Hi! Send me a financial claim and I will fact-check it.")
        return Response(content=str(resp), media_type="application/xml")

    try:
        t0 = time.time()
        analysis = vertex_ai_analyze(user_text)
        reply_text = analysis["explanation"]

        save_history(fs, user_id, user_text, reply_text)

        # Log structured data in BigQuery
        bq = get_bigquery()
        latency_ms = int((time.time() - t0) * 1000)
        log_to_bigquery(bq, {
            "ts": time.time(),
            "user_id": user_id,
            "phone": from_number,
            "message": user_text,
            "response": reply_text,  # must be string
            "latency_ms": latency_ms,
            "model": "gemini-2.0-flash-001",
            "region": "IN",
        })

        #resp.message(reply_text)
        analysis = vertex_ai_analyze(user_text)

        # Construct WhatsApp message
        msg_lines = [
            f"Classification: {analysis['verdict']}",
            f"Explanation: {analysis['explanation']}",
        ]

        if analysis['sources']:
            msg_lines.append("Trusted Sources:")
            for s in analysis['sources']:
                msg_lines.append(f"*{s['source_name']}*: {s['url']}")

        resp.message("\n".join(msg_lines))

        return Response(content=str(resp), media_type="application/xml")

    except Exception as e:
        print("Error handling message:", e)
        resp.message("Sorry, I hit a snag. Please try again later.")
        return Response(content=str(resp), media_type="application/xml")
