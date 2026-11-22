from fastapi import FastAPI
from pydantic import BaseModel

from privacy import audit_log, consent_service, masking, retention, validate_input


app = FastAPI()


class LoanRequest(BaseModel):
    email: str
    aadhaar: str
    phone: str
    annual_income: float


@app.post("/loan/apply")
async def apply_for_loan(request: LoanRequest, consent_id: str):
    if not consent_service.is_valid(consent_id, purpose="loan_underwriting"):
        return {"error": "no lawful basis for this purpose"}
    validate_input(request)
    token = masking.tokenize(request.aadhaar)
    score_value = compute_score(token, request.annual_income)
    decision = approve_or_decline(score_value)
    audit_log(
        "underwriting_decision",
        purpose="loan_underwriting",
        explanation=decision["explanation"],
        human_review=decision["human_review"],
    )
    retention.schedule_purge(token, retention_days=90)
    return decision


@app.post("/chat")
async def chat(message: str, consent_id: str):
    if not consent_service.is_valid(consent_id, purpose="customer_support"):
        return {"error": "no lawful basis"}
    safe_message = masking.redact_text(message)
    answer = support_model.reply(safe_message)
    return {"answer": answer, "ai_disclosure": True}


@app.post("/content/generate")
async def create_image(topic: str):
    media = image_service.create(topic)
    return {"media": media, "ai_generated": True, "watermark": "synthetic"}


@app.post("/children/guardian-check")
async def guardian_check(guardian_token: str):
    verified = consent_service.verifiable_consent(guardian_token)
    return {"verifiable_consent": verified}


def compute_score(token: str, income: float) -> float:
    return min(income / 10000, 1.0)


def approve_or_decline(score_value: float) -> dict:
    explanation = build_reason_codes(score_value)
    review = score_value < 0.5
    return {
        "approved": not review,
        "explanation": explanation,
        "reason_codes": explanation,
        "human_review": review,
    }


def build_reason_codes(score_value: float) -> list[str]:
    return ["income_threshold", "verified_identity"] if score_value >= 0.5 else ["income_threshold"]


class support_model:
    @staticmethod
    def reply(safe_message: str) -> str:
        return "How can I help?"


class image_service:
    @staticmethod
    def create(topic: str) -> str:
        return "media:" + topic
