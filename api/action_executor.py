import subprocess
import os
import json
import webbrowser

class ActionExecutor:
    def __init__(self):
        self.contacts_path = os.path.join(os.path.dirname(__file__), "contacts.json")
        self.load_contacts()
    
    def load_contacts(self):
        try:
            if os.path.exists(self.contacts_path):
                with open(self.contacts_path, 'r') as f:
                    self.contacts = json.load(f)
            else:
                self.contacts = {}
        except Exception:
            self.contacts = {}

    def execute_plan(self, ai_plan: dict):
        actions = ai_plan.get("actions", [])
        results = []
        
        # If the plan doesn't have a list of actions yet, create one from the legacy format
        if not actions:
            actions = [{"intent": ai_plan.get("intent"), "target": ai_plan.get("target"), "number": ai_plan.get("number")}]

        for action in actions:
            intent = action.get("intent")
            target = action.get("target", "").lower()
            number = action.get("number")
            
            if intent == "call":
                # Check if it's a number directly
                call_number = number or self.contacts.get(target)
                if not call_number and target.replace('+', '').isdigit():
                    call_number = target
                
                if call_number:
                    results.append(self.make_call(call_number))
                else:
                    results.append({"status": "failed", "message": f"Contact '{target}' not found"})
            
            elif intent == "open_app":
                results.append(self.open_app(target))
            
            elif intent == "brightness" or intent == "change_brightness":
                level = action.get("level")
                change = action.get("change") or action.get("value")
                results.append(self.set_brightness(level=level, change=change))
            
            elif intent == "volume" or intent == "change_volume":
                level = action.get("level")
                change = action.get("change") or action.get("value")
                results.append(self.set_volume(level=level, change=change))
                
        return {"status": "success", "results": results}
    
    def set_volume(self, level=None, change=None):
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            current_db = volume.GetMasterVolumeLevelScalar() # 0.0 to 1.0
            current_pct = int(round(current_db * 100))
            
            if level is not None:
                new_pct = int(level)
            elif change is not None:
                new_pct = current_pct + int(change)
            else:
                return {"status": "failed", "message": "No level or change specified for volume"}
            
            new_pct = max(0, min(100, new_pct))
            volume.SetMasterVolumeLevelScalar(new_pct / 100.0, None)
            return {"status": "success", "action": f"Volume set to {new_pct}%"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def set_brightness(self, level=None, change=None):
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            
            if level is not None:
                new_level = int(level)
            elif change is not None:
                new_level = current + int(change)
            else:
                return {"status": "failed", "message": "No level or change specified for brightness"}
            
            # Clamp value between 0 and 100
            new_level = max(0, min(100, new_level))
            sbc.set_brightness(new_level)
            return {"status": "success", "action": f"Brightness set to {new_level}%"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def make_call(self, number: str):
        # Using f-string for shell command
        cmd = f'start tel:{number}'
        subprocess.run(cmd, shell=True)
        return {"status": "success", "action": f"Calling {number}"}
    
    def open_app(self, app_name: str):
        apps = {
            "youtube": "https://youtube.com",
            "whatsapp": "https://web.whatsapp.com",
            "chrome": "https://google.com"
        }
        url = apps.get(app_name, f"https://google.com/search?q={app_name}")
        
        webbrowser.open(url)
        return {"status": "success", "action": f"Opened {app_name}"}

# Test it
if __name__ == "__main__":
    executor = ActionExecutor()
    plan = {"intent": "call", "target": "mom"}
    print(json.dumps(executor.execute_plan(plan), indent=2))
