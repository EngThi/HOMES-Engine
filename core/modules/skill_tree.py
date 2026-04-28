import json
import os
import logging
from . import register
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
STATE_FILE = "output/skills_state.json"

def load_state():
    if not os.path.exists(STATE_FILE):
        os.makedirs("output", exist_ok=True)
        return {"skills": {"NestJS": {"xp": 0, "level": 1}, "Docker": {"xp": 0, "level": 1}, "Python DataEng": {"xp": 0, "level": 1}}}
    with open(STATE_FILE, "r") as f: return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f, indent=4)

from core.key_utils import get_gemini_keys

@register("skill_tree")
def run(args: list) -> dict:
    cmd = args[0] if args else "status"
    state = load_state()

    if cmd == "status":
        return {"module": "skill_tree", "state": state}

    elif cmd == "quest":
        # Gemini analisa seu nível atual e gera uma tarefa
        from dotenv import load_dotenv
        load_dotenv()
        keys = get_gemini_keys()
        client = genai.Client(api_key=keys[0])
        
        prompt = f"""
        Sou um estudante de Engenharia. Minha Skill Tree atual: {json.dumps(state)}.
        Gere uma micro-quest de 30 minutos para a skill com menos XP. 
        A tarefa deve ser prática e focada em Big Tech.
        """
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return {"quest_assigned": response.text}

    elif cmd == "complete":
        skill = args[1] if len(args) > 1 else "NestJS"
        xp_gain = int(args[2]) if len(args) > 2 else 50
        
        if skill in state["skills"]:
            state["skills"][skill]["xp"] += xp_gain
            new_level = (state["skills"][skill]["xp"] // 100) + 1
            leveled_up = new_level > state["skills"][skill]["level"]
            state["skills"][skill]["level"] = new_level
            save_state(state)
            return {"status": "success", "skill": skill, "xp_added": xp_gain, "level": new_level, "leveled_up": leveled_up}
    
    return {"status": "error", "message": "Comando desconhecido"}
