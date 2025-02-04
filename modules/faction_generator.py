# faction_generator.py
import requests
import random
from .shared import tables
from .shared.output_writer import sanitize_output, register_handler
import logging

def generate_factions(model, history_content):
    num_factions = random.randint(1, 3)
    factions = []

    for _ in range(num_factions):
        faction_goal = random.choice(tables.FACTION_TABLES["goal"])
        faction_obstacle = random.choice(tables.FACTION_TABLES["obstacle"])
        faction_impulse = random.choice(tables.FACTION_TABLES["impulse"])
        faction_size = random.choice(tables.FACTION_TABLES["size"])
        faction_creature_type = random.choice(tables.FACTION_TABLES["creature_type"])

        faction_prompt = f"""You are an expert fantasy game writer. Write a short paragraph about a faction 
in a dark fantasy sword and sorcery tabletop RPG dungeon. The faction's history has been influenced by the following 
details:

- Faction Goal: {faction_goal}
- Faction Obstacle: {faction_obstacle}
- Faction Impulse: {faction_impulse}
- Faction Size: {faction_size}
- Faction Creature Type: {faction_creature_type}
- Dungeon History: {history_content}

Name the faction and describe the faction's goals, obstacles, behavior, size, and creature type. 
Include a brief introduction to their leader(s)."""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": faction_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "max_tokens": 300
                }
            },
            timeout=60
        )
        response.raise_for_status()

        faction_content = sanitize_output(response.json()["response"])
        factions.append({
            "goal": faction_goal,
            "obstacle": faction_obstacle,
            "impulse": faction_impulse,
            "size": faction_size,
            "creature_type": faction_creature_type,
            "content": faction_content
        })

    return {
        "num_factions": num_factions,
        "factions": factions
    }

# Register the handler for the Factions section
def factions_handler(data, f):
    f.write("## Factions\n\n")
    f.write(f"Number of Factions: {data['num_factions']}\n\n")
    for faction in data['factions']:
        f.write(f"### Faction\n\n")
        f.write(f"- **Goal**: {faction['goal']}\n")
        f.write(f"- **Obstacle**: {faction['obstacle']}\n")
        f.write(f"- **Impulse**: {faction['impulse']}\n")
        f.write(f"- **Size**: {faction['size']}\n")
        f.write(f"- **Creature Type**: {faction['creature_type']}\n\n")
        f.write(f"{faction['content']}\n\n")


register_handler("Faction", factions_handler)
