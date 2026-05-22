import os
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from graph import get_answer

load_dotenv(dotenv_path=r"D:\whatsapp_rag_agent\.env", override=True)

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok"}

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# ─── DEBUG (baad mein hata dena) ──────────────────────────────────────────────
print(f"✅ VERIFY_TOKEN loaded: {repr(VERIFY_TOKEN)}")
print(f"✅ PHONE_NUMBER_ID loaded: {repr(PHONE_NUMBER_ID)}")

# ─── Webhook Verification ─────────────────────────────────────────────────────
@app.get("/webhook")
async def verify(request: Request):
    params    = dict(request.query_params)
    mode      = params.get("hub.mode") or params.get("hub_mode")
    token     = params.get("hub.verify_token") or params.get("hub_verify_token")
    challenge = params.get("hub.challenge") or params.get("hub_challenge")

    print(f"🔍 mode={mode} | token={token} | expected={VERIFY_TOKEN}")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Verification failed")

# ─── Incoming Messages ────────────────────────────────────────────────────────
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    try:
        entry   = data["entry"][0]
        changes = entry["changes"][0]["value"]
        msg     = changes["messages"][0]

        if msg["type"] != "text":
            return {"status": "ignored"}

        user_number = msg["from"]
        user_text   = msg["text"]["body"]

        print(f"📩 Message from {user_number}: {user_text}")

        answer = get_answer(user_text)
        send_message(user_number, answer)

    except (KeyError, IndexError):
        pass

    return {"status": "ok"}

# ─── Send Message ─────────────────────────────────────────────────────────────
def send_message(to: str, text: str):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    r = requests.post(url, headers=headers, json=payload)
    print(f"📤 Reply sent | Status: {r.status_code}")
