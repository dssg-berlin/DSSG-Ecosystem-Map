from fastapi import FastAPI
from pydantic import BaseModel
import logging

app = FastAPI()
log = logging.getLogger(__name__)


class LoanRequest(BaseModel):
    email: str
    aadhaar: str
    phone: str
    annual_income: float


@app.post("/loan/apply")
async def apply_for_loan(request: LoanRequest):
    log.info("Loan application from %s aadhaar %s phone %s", request.email, request.aadhaar, request.phone)
    score = request.annual_income / 10000
    approved = score > 8
    return {"approved": approved}


@app.post("/chat")
async def chat(message: str):
    prompt = "You are a support bot. Customer email is in the message: " + message
    answer = call_model(prompt)
    return {"answer": answer}


@app.post("/content/generate")
async def generate_image(prompt: str):
    image = synthesize_image(prompt)
    return {"image": image}


@app.post("/children/profile")
async def profile_child(child_email: str, behavioural_events: list):
    target_ad = select_targeted_advertising(child_email, behavioural_events)
    return {"ad": target_ad}


def call_model(prompt):
    return external_llm(prompt)


def synthesize_image(prompt):
    return image_api.generate(prompt)
