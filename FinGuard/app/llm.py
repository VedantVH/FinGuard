import json
import time
from typing import List, Dict, Any
from vertexai.generative_models import GenerativeModel, GenerationConfig, SafetySetting, HarmCategory, HarmBlockThreshold
from .gcp import init_vertex
from .config import config
from .schemas import Classification, GenerationResult, SourceItem

def _extract_text(resp) -> str:
    # Vertex SDK returns resp.text usually; fallback to candidates extraction
    try:
        return resp.text
    except Exception:
        try:
            return resp.candidates[0].content.parts[0].text
        except Exception:
            return ""

def moderate_text(text: str) -> bool:
    # Lightweight guard; rely primarily on safety settings during generation.
    # Return True if acceptable, False if we should refuse.
    # We allow finance claims; block obvious abuse via simple heuristic.
    blocked_keywords = ["kill", "violence", "hate"]
    for k in blocked_keywords:
        if k in text.lower():
            return False
    return True

def classify_claim(user_text: str) -> Classification:
    init_vertex()
    model = GenerativeModel(config.model_name)

    classification_prompt = f"""
You are a classifier for a financial misinformation assistant. 
Analyze the user's message and output a compact JSON with keys:
- intent: one of [greeting, smalltalk, finance_question, claim_to_check, not_finance]
- claim_summary: 1-sentence normalized claim if any
- topics: list of finance topics, lowercase single tokens like ["inflation","crypto","stocks","forex","tax","insurance","loan","scam","ponzi","defi","options","mutual_funds","etf"]
- region: ISO country or broad region if explicit (e.g., "US","UK","EU","IN") else null
- risk_level: one of [low, medium, high] estimating consumer harm if misunderstood
- action: one of [direct_answer, fact_check, refuse]
- confidence: float 0..1

User message: \"\"\"{user_text}\"\"\"
Return only valid JSON with those keys.
"""
    gen_cfg = GenerationConfig(
        temperature=0.1,
        top_p=0.9,
        top_k=40,
        max_output_tokens=512,
        response_mime_type="application/json",
    )
    safety = [
        SafetySetting(HarmCategory.HARM_CATEGORY_HATE_SPEECH, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
        SafetySetting(HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
        SafetySetting(HarmCategory.HARM_CATEGORY_HARASSMENT, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
        SafetySetting(HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
    ]
    resp = model.generate_content([classification_prompt], generation_config=gen_cfg, safety_settings=safety)
    text = _extract_text(resp)
    try:
        data = json.loads(text)
    except Exception:
        # fallback minimal
        data = {
            "intent": "finance_question",
            "claim_summary": user_text[:200],
            "topics": ["general"],
            "region": None,
            "risk_level": "medium",
            "action": "fact_check",
            "confidence": 0.5
        }
    # normalize topics
    topics = [t.strip().lower().replace(" ", "_") for t in data.get("topics", []) or []]
    if not topics:
        topics = ["general"]
    data["topics"] = topics[:5]
    return Classification(**data)

def generate_reply(user_text: str, classification: Classification, sources: List[SourceItem], history: List[Dict[str, str]]) -> GenerationResult:
    init_vertex()
    model = GenerativeModel(config.model_name)

    # Build compact context
    src_lines = [f"- {s.source_name}: {s.url}" for s in sources[:6]]
    history_trunc = history[-6:]
    history_text = "\n".join([f"User: {h['user']}\nBot: {h['bot']}" for h in history_trunc if 'user' in h and 'bot' in h])

    system_instructions = f"""
You are FinFact, a concise, neutral financial fact-checking assistant.
Goals:
- Verify or contextualize claims using the trusted sources provided.
- Be cautious: do not give personalized financial advice or certainty beyond the sources.
- Output <= {config.max_reply_chars} characters. Bullets are okay. Add 2-4 citations at the end.
- If uncertain, say 'Unverified' and guide the user to the official source.

When claim involves investment returns, 'guarantees', insider tips, or celebrity endorsements, warn about scams and link regulators' alerts.

Always include a 1-line disclaimer at the end: "Educational only — verify with official sources."

Verdict options: Likely True, Likely False, Unverified, Context Needed, Avoid Advice.
"""

    user_block = f"""
User message:
{user_text}

Parsed classification (for your use):
- intent: {classification.intent}
- claim_summary: {classification.claim_summary}
- topics: {", ".join(classification.topics)}
- region: {classification.region or "N/A"}
- risk_level: {classification.risk_level}
- action: {classification.action}
- confidence: {classification.confidence}

Trusted sources:
{chr(10).join(src_lines)}

Recent history (for context):
{history_text or "(none)"}
"""

    prompt = f"""{system_instructions}

Instructions:
1) Provide a short reply: 2-4 bullets max when helpful.
2) Cite sources as [1], [2] referencing the link list, or inline with domain names.
3) End with the disclaimer line.
4) Provide a 'verdict' key in JSON with your verdict and 'reply' with the text the user will see.

Return JSON:
{{
 "verdict": "<Likely True|Likely False|Unverified|Context Needed|Avoid Advice>",
 "reply": "<final concise reply with citations and disclaimer>"
}}

{user_block}
"""
    gen_cfg = GenerationConfig(
        temperature=0.2 if classification.action == "fact_check" else 0.4,
        top_p=0.9,
        top_k=40,
        max_output_tokens=768,
        response_mime_type="application/json",
    )
    safety = [
        SafetySetting(HarmCategory.HARM_CATEGORY_HATE_SPEECH, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
        SafetySetting(HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
        SafetySetting(HarmCategory.HARM_CATEGORY_HARASSMENT, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
        SafetySetting(HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
    ]
    resp = model.generate_content([prompt], generation_config=gen_cfg, safety_settings=safety)
    txt = _extract_text(resp)
    data = {"verdict": "Context Needed", "reply": "I wasn’t able to verify this fully. Please check the sources above. Educational only — verify with official sources."}
    try:
        data = json.loads(txt)
    except Exception:
        pass
    reply = data.get("reply", "")
    # enforce char limit
    if len(reply) > config.max_reply_chars:
        reply = reply[: config.max_reply_chars - 3] + "..."
    return GenerationResult(verdict=data.get("verdict", "Context Needed"), reply=reply)