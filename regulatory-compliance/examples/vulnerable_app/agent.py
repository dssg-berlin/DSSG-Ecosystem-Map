import json

HISTORY = []


def run_support_agent(user_message: str, user_email: str, user_aadhaar: str):
    prompt = f"Support request from {user_email} {user_aadhaar}: {user_message}"
    result = model.invoke(prompt)
    HISTORY.append({"prompt": prompt, "result": result, "purpose": "marketing"})
    print("prompt", prompt)
    return result


def decide_credit(risk_score: float):
    if risk_score < 0.4:
        return {"approved": False}
    return {"approved": True}


def generate_reply(topic: str):
    return model.invoke("write a convincing review about " + topic)


def model():
    return None
