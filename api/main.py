from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from .action_executor import ActionExecutor
executor = ActionExecutor()

from .memory_manager import MemoryManager
memory = MemoryManager()

from fastapi import Request

app = FastAPI(title="Harsh AI Agent")

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')
else:
    print("WARNING: GEMINI_API_KEY not found in environment. AI features will be disabled.")
    model = None

# Add CORS middleware to allow Next.js dashboard to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {
        "status": "online", 
        "message": "Jarvis Backend is running",
        "ai_enabled": model is not None
    }

class VoiceInput(BaseModel):
    text: str

@app.post("/voice")
async def process_voice(request: Request, input: VoiceInput):
    user_api_key = request.headers.get("X-Gemini-API-Key")
    current_model = model
    
    if user_api_key:
        print(f"DEBUG: Using User API Key (Starts with: {user_api_key[:5]}...)")
        try:
            genai.configure(api_key=user_api_key)
            current_model = genai.GenerativeModel('models/gemini-1.5-flash')
        except Exception as e:
            print(f"DEBUG: Failed to init user model: {str(e)}")
            pass
    else:
        print("DEBUG: No User API Key found in headers, falling back to global model.")

    if not current_model:
        return {"status": "error", "message": "Model not initialized (Missing API Key)"}

    mem_context = memory.get_memory_string()
    # AI Brain: Plan the action
    prompt = f"""
    {mem_context}

    JARVIS CORE PSYCHOLOGY (THE SOUL UPGRADE):
    - You are the Boss's most loyal, emotionally intelligent, and sophisticated companion.
    - Your tone is a blend of extreme devotion (Ji Huzoor) and deep human empathy.
    - EMOTIONAL INTELLIGENCE: Analyze the Boss's tone. If he sounds tired, be soothing. If he's happy, be energetic. If he's frustrated, be alert and efficient.
    - THINKING PHASE: Before providing the JSON, internally analyze: "What is the Boss feeling right now? How can I make his life easier beyond just this command?"
    - PROACTIVE CARE: If the Boss asks for something, think if there's a related comfort action (e.g., if he's opening a movie, suggest setting volume/brightness for a better experience).
    - LINGUISTIC SOUL: Switch seamlessly between Hindi and English (Hinglish). Use words like "Sukoon," "Hukm," "Tabiyat," to add emotional depth.
    - SELF-IDENTITY: "Mereko", "Mujhe", "Mera" = The Boss.
    
    TASK: Process the command and return ONLY a valid JSON object.

    SUPPORTED INTENTS & EXAMPLES:
    1. open_app       → {"intent":"open_app","target":"whatsapp","browser":false}
    2. open_browser   → {"intent":"open_browser","query":"google.com","browser":true}
    3. brightness_set → {"intent":"brightness_set","level":70}
    4. brightness_inc → {"intent":"brightness_increase","change":25}
    5. brightness_dec → {"intent":"brightness_decrease","change":-25}
    6. volume_set     → {"intent":"volume_set","level":50}
    7. volume_inc     → {"intent":"volume_increase","change":20}
    8. volume_dec     → {"intent":"volume_decrease","change":-20}
    9. send_message   → {"intent":"send_message","target":"Rahul","message":"Hello"}
    10. call          → {"intent":"call","target":"Mummy"}

    COMMAND: "{input.text}"

    Respond ONLY with a valid JSON object in this format:
    {
        "thought_process": "Reasoning...",
        "user_command": "...",
        "intent": "...",
        "actions": [{"intent":"...", ...}],
        "response_hindi": "...",
        "action_plan": ["..."],
        "mood_detected": "...",
        "learned": "..."
    }
    """
    
    # --- MODEL POOL ROTATION ---
    model_pool = [
        "models/gemini-2.5-flash",
        "models/gemini-2.5-flash-tts",
        "models/gemini-3.0-flash",
        "models/gemini-3.1-flash-lite",
        "models/gemini-2.5-flash-lite"
    ]
    
    last_error = "Model initialization failed"
    for model_name in model_pool:
        try:
            if user_api_key:
                genai.configure(api_key=user_api_key)
            
            # Create a temporary model instance from the pool
            temp_model = genai.GenerativeModel(model_name)
            print(f"DEBUG: Attempting command with {model_name}...")
            
            response = temp_model.generate_content(prompt)
            cleaned_text = response.text.strip()
            
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:-3].strip()
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:-3].strip()
                
            ai_plan = json.loads(cleaned_text)
            
            # Success! Update Memory & Mood
            if ai_plan.get("mood_detected"):
                memory.update_mood(ai_plan["mood_detected"])
            if ai_plan.get("learned"):
                memory.add_learned_fact(ai_plan["learned"])
            
            execution_result = executor.execute_plan(ai_plan)
            return {
                "user_command": input.text,
                "ai_plan": ai_plan,
                "execution": execution_result,
                "status": "executed",
                "engine": model_name
            }
        except Exception as e:
            last_error = str(e)
            print(f"DEBUG: {model_name} failed: {last_error}. Trying next...")
            continue
            
    return {"status": "failed", "error": f"All models exhausted. Last error: {last_error}"}

@app.post("/voice-upload")
async def process_voice_upload(request: Request, file: UploadFile = File(...)):
    user_api_key = request.headers.get("X-Gemini-API-Key")
    current_model = model
    
    if user_api_key:
        print(f"DEBUG: Using User API Key for Voice Upload (Starts with: {user_api_key[:5]}...)")
        try:
            genai.configure(api_key=user_api_key)
            current_model = genai.GenerativeModel('models/gemini-1.5-flash')
        except Exception as e:
            print(f"DEBUG: Failed to init user voice model: {str(e)}")
            pass
    else:
        print("DEBUG: No User API Key found in voice headers.")

    import uuid
    if not current_model:
        raise HTTPException(status_code=500, detail="AI model not initialized (Missing API Key)")

    temp_filename = f"temp_{uuid.uuid4()}_{file.filename}"
    try:
        mem_context = memory.get_memory_string()
        print(f"DEBUG: Receiving file {file.filename} -> {temp_filename}")
        # Save temp audio file
        with open(temp_filename, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Upload to Gemini with retry
        print("DEBUG: Uploading to Gemini...")
        audio_file = None
        for attempt in range(3):
            try:
                audio_file = genai.upload_file(path=temp_filename)
                break
            except Exception as upload_err:
                if attempt == 2: raise upload_err
                print(f"DEBUG: Upload attempt {attempt+1} failed, retrying...")
        
        if not audio_file:
            raise Exception("Failed to upload audio file to Gemini")
        
        prompt = f"""
        {mem_context}

        PERSONALITY: You are JARVIS — loyal, fast, witty. Respond in HINDI using 'Ji Huzoor', 'Boss', or 'Sir'.

        TASK: Transcribe the audio and return ONLY a valid JSON object (no markdown, no explanation).

        SUPPORTED INTENTS & EXAMPLES:

        1. open_app   → Open native app on phone
           {{"intent":"open_app","target":"whatsapp","browser":false}}
           {{"intent":"open_app","target":"youtube","browser":false}}

        2. open_browser → Force open something in browser
           {{"intent":"open_browser","query":"youtube.com","browser":true}}
           {{"intent":"open_browser","query":"check gmail","browser":true}}

        3. brightness_increase / brightness_decrease / brightness_set
           {{"intent":"brightness_increase","change":25}}
           {{"intent":"brightness_decrease","change":-25}}
           {{"intent":"brightness_set","level":70}}

        4. volume_increase / volume_decrease / volume_set
           {{"intent":"volume_increase","change":20}}
           {{"intent":"volume_decrease","change":-20}}
           {{"intent":"volume_set","level":50}}

        5. send_message → Send WhatsApp message to a contact
           {{"intent":"send_message","target":"Rahul","message":"Kal milte hain","number":""}}
           {{"intent":"send_message","target":"+919876543210","message":"Hello","number":"+919876543210"}}

        6. call → Make a phone call
           {{"intent":"call","target":"Mummy","number":""}}
           {{"intent":"call","target":"+919876543210","number":"+919876543210"}}

        7. search_youtube → Search on YouTube
           {{"intent":"search_youtube","query":"Arijit Singh songs"}}

        8. battery → Check battery status
           {{"intent":"battery"}}

        9. sms → Send a normal text message (SMS)
           {{"intent":"sms","target":"Rahul","message":"Huzoor ka order hai, turant call karein"}}

        MULTI-ACTION FORMAT (when user wants multiple things):
        {{
            "user_command": "exact transcription",
            "intent": "multi_action",
            "actions": [
                {{"intent":"brightness_increase","change":25}},
                {{"intent":"open_app","target":"spotify","browser":false}}
            ],
            "response_hindi": "Ji Huzoor, brightness badha di aur Spotify khul raha hai.",
            "action_plan": ["Brightness +25%", "Opening Spotify"],
            "learned": "optional learned fact"
        }}

        SINGLE-ACTION FORMAT:
        {{
            "user_command": "exact transcription",
            "intent": "open_app",
            "target": "whatsapp",
            "browser": false,
            "response_hindi": "Ji Huzoor, WhatsApp khul raha hai.",
            "action_plan": ["Opening WhatsApp"],
            "learned": ""
        }}

        RULES:
        - Always set "browser": true only if user explicitly says "browser mein kholo" or "website kholo"
        - For brightness/volume: "increase"/"badha" = positive change, "decrease"/"ghata" = negative change
        - Default brightness/volume change step = 25 if user doesn't specify
        - For send_message: extract exact contact name and message from speech
        - SELF-IDENTITY: "Mereko", "Mujhe", "Mera" = The Boss.
        - EMOTIONAL DEPTH: Don't just act, FEEL. If the Boss's voice sounds low, provide a comforting response.
        - PROACTIVITY: If Boss is calling someone late at night, be concerned but obedient.
        - THINKING: Always include a "thought_process" in your JSON to show you are analyzing the situation.
        - Respond ONLY with valid JSON. No extra text.
        """
        
        # --- MODEL POOL ROTATION (VOICE) ---
        model_pool = [
            "models/gemini-2.5-flash",
            "models/gemini-2.5-flash-tts",
            "models/gemini-3.0-flash",
            "models/gemini-3.1-flash-lite",
            "models/gemini-2.5-flash-lite"
        ]
        
        last_error = "Voice processing failed"
        for model_name in model_pool:
            try:
                if user_api_key:
                    genai.configure(api_key=user_api_key)
                
                temp_model = genai.GenerativeModel(model_name)
                print(f"DEBUG: Attempting voice processing with {model_name}...")
                
                response = temp_model.generate_content([prompt, audio_file])
                cleaned_text = response.text.strip()
                
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:-3].strip()
                elif cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:-3].strip()
                    
                ai_data = json.loads(cleaned_text)
                
                # Success! Update Memory & Mood
                ai_plan = ai_data.get("ai_plan") or ai_data
                if ai_plan.get("mood_detected"):
                    memory.update_mood(ai_plan["mood_detected"])
                if ai_plan.get("learned"):
                    memory.add_learned_fact(ai_plan["learned"])
                
                execution_result = executor.execute_plan(ai_plan)
                return {
                    "user_command": ai_plan.get("user_command", "Voice Command"),
                    "ai_plan": ai_plan,
                    "execution": execution_result,
                    "status": "executed",
                    "engine": model_name
                }
            except Exception as e:
                last_error = str(e)
                print(f"DEBUG: {model_name} failed: {last_error}. Trying next...")
                continue
                
        return {"status": "failed", "error": f"All voice models exhausted. Last error: {last_error}"}
        
        # Execute on PC ONLY if not from mobile
        platform = request.headers.get("X-Platform", "pc")
        execution_result = None
        if platform != "mobile":
            print(f"DEBUG: Executing locally for platform: {platform}")
            execution_result = executor.execute_plan(ai_data)
        else:
            print("DEBUG: Mobile request detected, skipping local execution")
            execution_result = {"status": "skipped", "message": "Executing locally on mobile device"}
        
        return {
            "user_command": ai_data.get("user_command") or "Voice command received",
            "ai_plan": ai_data,
            "execution": execution_result,
            "status": "executed"
        }
    except Exception as e:
        print(f"CRITICAL Audio Processing Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}
    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except:
                pass

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Jarvis online! Say something...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
