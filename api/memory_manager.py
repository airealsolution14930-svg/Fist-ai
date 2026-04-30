import json
import os

class MemoryManager:
    def __init__(self, filepath="memory.json"):
        self.filepath = filepath
        self.memory = self.load_memory()

    def load_memory(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    return json.load(f)
            except:
                return {"user_preferences": {}, "learned_facts": [], "corrections": []}
        return {"user_preferences": {}, "learned_facts": [], "corrections": []}

    def save_memory(self):
        with open(self.filepath, "w") as f:
            json.dump(self.memory, f, indent=4)

    def add_learned_fact(self, fact):
        if fact not in self.memory["learned_facts"]:
            self.memory["learned_facts"].append(fact)
            self.save_memory()

    def add_correction(self, correction):
        self.memory["corrections"].append(correction)
        self.save_memory()

    def update_preference(self, key, value):
        self.memory["user_preferences"][key] = value
        self.save_memory()

    def get_memory_string(self):
        mem_str = "JARVIS MEMORY (Use this to understand the user better):\n"
        if self.memory["user_preferences"]:
            mem_str += f"Preferences: {json.dumps(self.memory['user_preferences'])}\n"
        if self.memory["learned_facts"]:
            mem_str += "Learned Facts:\n- " + "\n- ".join(self.memory["learned_facts"][-10:]) + "\n"
        if self.memory["corrections"]:
            mem_str += "Recent Corrections:\n- " + "\n- ".join(self.memory["corrections"][-5:]) + "\n"
        return mem_str
