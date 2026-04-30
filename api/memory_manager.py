import json
import os
from datetime import datetime

class MemoryManager:
    def __init__(self, filepath="memory.json", profile_path="boss_profile.json"):
        self.filepath = filepath
        self.profile_path = profile_path
        self.memory = self.load_json(self.filepath, {"user_preferences": {}, "learned_facts": [], "corrections": []})
        self.profile = self.load_json(self.profile_path, {
            "boss_name": "Boss",
            "preferences": {"theme": "dark", "language": "Hinglish", "mood_history": []},
            "emotional_profile": {"temperament": "Respectful", "connection_level": 100, "last_interaction": ""}
        })

    def load_json(self, path, default):
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except:
                return default
        return default

    def save_all(self):
        with open(self.filepath, "w") as f:
            json.dump(self.memory, f, indent=4)
        with open(self.profile_path, "w") as f:
            json.dump(self.profile, f, indent=4)

    def add_learned_fact(self, fact):
        if fact not in self.memory["learned_facts"]:
            self.memory["learned_facts"].append(fact)
            self.save_all()

    def update_mood(self, mood):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.profile["preferences"]["mood_history"].append({"mood": mood, "time": timestamp})
        self.profile["preferences"]["mood_history"] = self.profile["preferences"]["mood_history"][-10:]
        self.profile["emotional_profile"]["last_interaction"] = timestamp
        self.save_all()

    def get_memory_string(self):
        mem_str = "JARVIS CORE MEMORY:\n"
        mem_str += f"Boss Name: {self.profile.get('boss_name', 'Boss')}\n"
        mem_str += f"Current Emotional Connection: {self.profile['emotional_profile']['connection_level']}%\n"
        
        recent_moods = [m['mood'] for m in self.profile["preferences"]["mood_history"]]
        if recent_moods:
            mem_str += f"Recent Mood History: {', '.join(recent_moods)}\n"
            
        if self.memory["learned_facts"]:
            mem_str += "Learned Facts:\n- " + "\n- ".join(self.memory["learned_facts"][-5:]) + "\n"
        return mem_str
