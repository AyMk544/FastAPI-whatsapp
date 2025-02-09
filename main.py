from fastapi import FastAPI, Request
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# WhatsApp API Credentials
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN") 

# Endpoint to verify webhook (GET Request)
@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    # Check if all required parameters are present
    if not all([hub_mode, hub_challenge, hub_verify_token]):
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    # Verify the mode and token
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        try:
            # Convert challenge to integer and return as plain text
            challenge_int = int(hub_challenge)
            return str(challenge_int)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hub.challenge value")
    
    # If verification fails, return 403 Forbidden
    raise HTTPException(status_code=403, detail="Verification failed")


# Function to send messages to WhatsApp
async def send_whatsapp_message(phone: str, message: str):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "text": {"body": message},
    }
    
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        return response.json()


# Endpoint to receive messages (POST Request)
@app.post("/webhook")
async def receive_whatsapp_message(request: Request):
    data = await request.json()
    
    try:
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("value", {}).get("messages"):
                        message = change["value"]["messages"][0]
                        user_phone = message.get("from")
                        message_type = message.get("type")
                        
                        if message_type == "text":
                            text = message["text"]["body"]
                            print(f"\nNew message from {user_phone}:")
                            print(f"Content: {text}")
                            await send_whatsapp_message(user_phone, f"Received: {text}")
                        else:
                            print(f"\nReceived {message_type} message from {user_phone}")
        return {"status": "success"}
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return {"status": "error", "message": str(e)}
