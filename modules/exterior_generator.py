# modules/exterior_generator.py

import time
import requests
import random
from .shared import tables
from .shared.output_writer import sanitize_output, register_handler
import logging


def generate_exterior(model, history_content=None, faction_content=None):
    try:
        logging.info("🌲 Starting dungeon exterior generation...")

        # Generate random environment
        logging.info("🌍 Rolling for environment...")
        environment = random.choice(tables.EXTERIOR_TABLES["environment"])
        logging.info(f"🌍 Environment selected: {environment}")

        # Handle special cases for environment
        if environment == "Re-roll twice and combine":
            logging.info("🎲 Re-rolling environment twice and combining...")
            env1 = random.choice(tables.EXTERIOR_TABLES["environment"])
            env2 = random.choice(tables.EXTERIOR_TABLES["environment"])
            while env1 == "Re-roll twice and combine":
                env1 = random.choice(tables.EXTERIOR_TABLES["environment"])
            while env2 == "Re-roll twice and combine" or env2 == env1:
                env2 = random.choice(tables.EXTERIOR_TABLES["environment"])
            environment = f"{env1} and {env2}"
            logging.info(f"🌍 Combined environment: {environment}")

        # Generate random path to the dungeon
        logging.info("🛤️ Rolling for path to the dungeon...")
        path = random.choice(tables.EXTERIOR_TABLES["path"])
        logging.info(f"🛤️ Path selected: {path}")

        # Handle sub-options for path
        if path == "River":
            logging.info("🌊 Path is a river. Selecting river details...")
            path_detail = random.choice(tables.EXTERIOR_TABLES["river_details"])
            path = f"{path} ({path_detail})"
            logging.info(f"🌊 Path updated with details: {path}")

        # Generate random landmark
        logging.info("🗿 Rolling for landmark on the way...")
        landmark = random.choice(tables.EXTERIOR_TABLES["landmark"])
        logging.info(f"🗿 Landmark selected: {landmark}")

        # Generate random secondary entrance
        logging.info("🚪 Rolling for secondary entrance...")
        secondary_entrance_location = random.choice(tables.EXTERIOR_TABLES["secondary_entrance_location"])
        secondary_entrance_destination = random.choice(tables.EXTERIOR_TABLES["secondary_entrance_destination"])
        secondary_entrance = f"{secondary_entrance_location} leading to {secondary_entrance_destination}"
        logging.info(f"🚪 Secondary entrance: {secondary_entrance}")

        # Generate random dungeon antechamber
        logging.info("🏰 Rolling for dungeon antechamber...")
        antechamber = random.choice(tables.EXTERIOR_TABLES["antechamber"])
        logging.info(f"🏰 Antechamber selected: {antechamber}")

        # Initialize descriptions dictionary
        descriptions = {}

        # Function to generate description for each component with unique prompts
        def generate_component_description(component_name, component_value):
            logging.info(f"✏️ Generating description for {component_name}...")
            start_time = time.time()

            # Optionally summarize content if too long
            max_content_length = 1000  # Adjust as needed
            hc = history_content if len(history_content) <= max_content_length else history_content[:max_content_length] + "..."

            # Define unique prompts for each component
            prompts = {
                'Environment': f"""You are an expert fantasy game writer. Write a succinct one paragraph 
                description of the environment surrounding the dungeon in a dark fantasy sword and sorcery 
                tabletop RPG. Be specific and focus on concrete details. Write like Robert E. Howard.
                Use the following details:

- Environment: {component_value}
- Dungeon History: {hc}

Emphasize the atmosphere and how it sets the mood for the adventure.""",

                'Path': f"""You are an expert fantasy game writer.  Write a succinct one paragraph 
                description of the path to the dungeon in a dark fantasy sword and sorcery tabletop RPG. 
                Write like Robert E. Howard. Use the following details:

- Path: {component_value}
- Dungeon History: {hc}

Detail any challenges or notable features adventurers might encounter along the way.""",

                'Landmark': f"""You are an expert fantasy game writer. Write a succinct one paragraph 
                description of a significant landmark on the way to the dungeon in a dark fantasy sword and sorcery 
                tabletop RPG. Be specific and focus on concrete details. Use the following details for inspiration:

- Landmark: {component_value}
- Dungeon History: {hc}

Explain how the landmark relates to the dungeon and its history.""",

                'Secondary Entrance': f"""You are an expert fantasy game writer.  Write a succinct one paragraph 
                description about a secondary entrance to the dungeon in a dark fantasy sword and sorcery tabletop 
                RPG. Be specific and focus on concrete details. Write like Robert E. Howard. Use the following details 
                for inspiration:

- Secondary Entrance: {component_value}
- Dungeon History: {hc}

Describe the entrance and any secrets or challenges associated with it.""",

                'Antechamber': f"""You are an expert fantasy game writer.  Write a succinct one paragraph 
                description the dungeon's antechamber in a dark fantasy sword and sorcery tabletop RPG. 
                Be specific and focus on concrete details. Write like Robert E. Howard. Use the following details 
                for inspiration:

- Antechamber: {component_value}
- Dungeon History: {hc}

Set the scene for what adventurers will encounter as they enter the dungeon.""",
            }

            prompt = prompts.get(component_name, f"Provide a description for {component_name}: {component_value}")

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.85,
                        "top_p": 0.9,
                        "max_tokens": 300
                    }
                },
                timeout=180
            )
            response.raise_for_status()
            elapsed_time = time.time() - start_time
            logging.info(f"✅ Description for {component_name} generated in {elapsed_time:.2f} seconds.")
            return sanitize_output(response.json()["response"])

        # Generate descriptions for each component
        components = [
            ('Environment', environment),
            ('Path', path),
            ('Landmark', landmark),
            ('Secondary Entrance', secondary_entrance),
            ('Antechamber', antechamber),
        ]

        for component_name, component_value in components:
            descriptions[component_name] = generate_component_description(component_name, component_value)
            time.sleep(2)  # Sleep for 2 seconds between requests
            logging.info("⏳ Waiting for 2 seconds before the next component generation...")

        logging.info("🎉 Dungeon exterior generation complete!")

        return {
            "descriptions": descriptions,
            "metadata": {
                "Environment": environment,
                "Path to Dungeon": path,
                "Landmark": landmark,
                "Secondary Entrance": secondary_entrance,
                "Antechamber": antechamber
            }
        }

    except Exception as e:
        logging.exception("❌ Exterior generation failed")
        return {"error": str(e)}


# Register the handler for the Exterior section
def exterior_handler(data, f):
    f.write("## Dungeon Exterior\n\n")
    descriptions = data.get('descriptions', {})
    for component_name, description in descriptions.items():
        f.write(f"### {component_name}\n\n")
        f.write(f"{description}\n\n")
    if 'metadata' in data:
        f.write("### Key Aspects\n")
        for k, v in data['metadata'].items():
            f.write(f"- **{k}**: {v}\n")
        f.write("\n")


register_handler("Exterior", exterior_handler)
