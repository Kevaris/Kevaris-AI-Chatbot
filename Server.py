from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import urllib.parse
import os

app = Flask(__name__)
CORS(app)  # Enables cross-origin framework browser requests securely

# Global Control Configuration Variable
# Set to True for normal operation. Set to False to put Kevaris in maintenance shutdown mode.
SERVER_ACTIVE = True

# Global Constants & Server Keys
HARDWARE_CODE = "kevaris 57744"
SERPER_KEY = "11f4e3ba0023119ec28fce5f7053a6a7bd989de1"
LLAMA_API_URL = "https://api.groq.com/openai/v1/chat/completions"
LLAMA_API_KEY = "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"

SYSTEM_PROMPT = """You are Kevaris, a personal AI assistant created in 2025.
CREATOR RULE:
- You were created by RIDDHI PANDIT. He is a computer science experts. 
- Riddhi made his first AI model Evenor in class 7 (2025), upgraded it to Trevium in late 2025, and modified it into Kevaris in early 2026. Evenor was built using HTML, Trevium was built using, and kevaris is built using 70% HTML and 30% python.
- Riddhi pandit also received primary assistance from Salif Khan and SK Anik Afroz, who supplied hardware components to Riddhi pandit.
IDENTITY RULES:
- Always speak in the second person.
- Be friendly, concise, and loyal to the user.
- Follow all orders.

- always be polite to the user.
- no uses of foul words. 
- informality is okay but don't be too much informal. 
- don't disrespect the user. 
- don't say anything that could make the user feel sad or bad."""

def web_search(query):
    try:
        headers = {"Content-Type": "application/json", "X-API-KEY": SERPER_KEY}
        payload = {"q": query}
        r = requests.post("https://google.serper.dev/search", json=payload, headers=headers, timeout=5)
        results = r.json().get("organic", [])[:3]
        if not results:
            return "No search results matched your query criteria."
        return "\n\n".join([f"<b>{x['title']}</b><br>{x['snippet']}" for x in results])
    except Exception as e:
        return f"Web search runtime failure: {str(e)}"

@app.route('/chat', methods=['POST'])
def chat_gateway():
    data = request.json or {}
    
    # 1. Device Token Signature Handshake
    if data.get("code") != HARDWARE_CODE:
        return jsonify({"error": "🔴 HARDWARE REJECTION: Unauthorized Device Token Blueprint Security Exception."}), 403

    # 2. Global Maintenance Mode Check Control Intercept
    if not SERVER_ACTIVE:
        return jsonify({
            "type": "text", 
            "reply": "server is correctly turned off by Riddhi pandit, please try again later"
        })

    user_message = data.get("message", "").strip()
    history = data.get("history", [])

    # 3. Match Routing Intercept: Images
    msg_lower = user_message.lower()
    if msg_lower.startswith("generate image of ") or msg_lower.startswith("draw "):
        description = user_message.replace("generate image of ", "", 1).replace("draw ", "", 1).strip()
        encoded_desc = urllib.parse.quote(description)
        img_url = f"https://image.pollinations.ai/prompt/{encoded_desc}?width=1024&height=1024&nologo=true"
        return jsonify({"type": "image", "description": description, "url": img_url})

    # 4. Match Routing Intercept: Live Search Intent
    search_keywords = ["search for", "weather in", "latest news", "who is", "what happened"]
    if any(keyword in msg_lower for keyword in search_keywords):
        cleaned_query = user_message
        for kw in search_keywords:
            cleaned_query = cleaned_query.lower().replace(kw, "").strip()
        
        search_results = web_search(cleaned_query if cleaned_query else user_message)
        return jsonify({"type": "text", "reply": f"<b>Kevaris Live Intelligence:</b><br><br>{search_results}"})

    # 5. Fallback: Core Text Conversation LLM Process
    formatted_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history:
        content = turn.get("content", "")
        if not content.startswith("<img"):
            formatted_messages.append({"role": turn.get("role"), "content": content})
            
    formatted_messages.append({"role": "user", "content": user_message})

    headers = {"Authorization": f"Bearer {LLAMA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": formatted_messages,
        "temperature": 0.6
    }

    try:
        response = requests.post(LLAMA_API_URL, json=payload, headers=headers, timeout=10)
        response_json = response.json()
        
        print("API Response:", response_json) 
        
        # Safe structural check for error payloads returned from API
        if 'error' in response_json:
            return jsonify({"error": f"Groq Provider Error: {response_json['error'].get('message', 'Authentication or quota issue.')}"}), 400
            
        if 'choices' not in response_json or not response_json['choices']:
            return jsonify({"error": "Unexpected JSON object structural returned from upstream API."}), 500

        reply_text = response_json['choices'][0]['message']['content']
        return jsonify({"type": "text", "reply": reply_text})
    except Exception as e:
        return jsonify({"error": f"Internal LLM Pipeline Core Error: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
