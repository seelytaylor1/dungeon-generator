import random
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_combined_history_prompt(history_components, builder_info):
    # Randomly choose a demonym from the provided list.
    demonym = random.choice(["ians", "ites", "ters", "ans", "iers", "ers"])
    # Append the demonym to the builder's name.
    builder_name_with_demonym = f"{builder_info['builder_name']}{demonym}"

    return {
        "key": "CombinedHistory",
        "prompt": (
            f"You are a master storyteller specializing in low-fantasy, sword-and-sandals fiction. "
            f"You're going to write lore for a location that will be used in a tabletop roleplaying game.\n\n"
            f"Dungeon ancient builders: {builder_info['creature_type']} known as {builder_name_with_demonym}.\n\n"
            f"Dungeon builders motivation: {builder_info['impulse']}.\n\n"
            f"Dungeon's ancient purpose: {history_components['modifier']} {history_components['purpose']}.\n\n"
            f"Builders ancient culture fell to ruin because: {history_components['ruin']}.\n\n"
            f"Present occupants are: {builder_info['present_name']}.\n\n"
            f"Present occupants use the dungeon as: {history_components['present']}.\n\n"
            "Using these details, write three paragraphs detailing the history from the ancient builders to the "
            "present day."
            "Required Sections:"
            "## Ancient History"
            "## Culture's Decline"
            "## Present Day"
        )
    }


# Template for generating a detailed description for the present-day faction.
FACTION_PRESENT_DAY_PROMPT = """Create detailed description for current dungeon occupants: {name}

Historical Context:\n
{history}

Key Attributes:
- Original Builders: {builders}\n
- Original Purpose: {original_purpose}\n
- Current Purpose: {current_state}\n
- Previous Collapse: {ruin_cause}\n

Include sections:
## Faction Description\n
[one paragraph]\n
## Faction Members\n
[one paragraph]\n
## Faction Leader/Goal\n
[one paragraph]\n
## Faction Challenges\n
[one paragraph]\n
"""

# Template for generating a background faction.
FACTION_BACKGROUND_PROMPT = """Create background faction that might interact with {name}
Connected to dungeon history: {history}
Faction Traits: {traits}
Add one paragraph under these required headings:
## Faction Description
[one paragraph]
## Faction Members
[one paragraph]
## Faction Leader/Goal
[one paragraph]
## Faction Challenges
[one paragraph]
"""

# Exterior prompts
EXTERIOR_PROMPTS = {
    "Environment": """
Describe the physical surroundings of a low-fantasy, sword-and-sandals dungeon using this 
physical detail: {component_value}.
Focus on the visible terrain, weather, vegetation, and atmosphere.
Exclude historical backstory or faction information.
Limit your output to one paragraph. Begin:
""",
    "Path": """
Detail the path leading to the low-fantasy, sword-and-sandals dungeon, characterized by: "{component_value}".
Emphasize its physical condition, terrain, weather, vegetation (if any), and any natural or man-made obstacles.
Avoid historical or faction details.
Limit your output to one paragraph. Begin:
""",
    "Landmark": """
Describe a prominent landmark near the low-fantasy, sword-and-sandals dungeon using this detail: {component_value}.
Focus on its visual and physical characteristics—its shape, texture, and surroundings—and explain what makes it 
stand out.
Limit your output to one paragraph. Begin
""",
    "Secondary Entrance": """
Describe a secondary entrance to the low-fantasy, sword-and-sandals dungeon defined by: {component_value}.
Highlight its any observable features.
Exclude any historical or faction-related information.
Limit your output to one paragraph.
""",
    "Antechamber": """
Describe the exterior aspect of the low-fantasy, sword-and-sandals dungeon's antechamber using the following feature: {component_value}.
Concentrate on tangible details and describe the pathway into the dungeon proper.
Avoid including historical narratives or faction details.
Limit your output to one paragraph.
"""
}

# dungeon content
PROMPT_TEMPLATES = {
    "history_summary": (
        "You are an expert gamemaster and game designer. "
        "The following is the context for the dungeon's history:\n"
        "{history_content}\n"
        "Summarize the history in bullet points. Focus on key events and factions.\n"
    ),
    "faction_summary": (
        "You are an expert gamemaster and game designer. "
        "The following is the context for the dungeon's history:\n"
        "{faction_content}\n"
        "Summarize the history in bullet points. Focus on key events and factions.\n"
    ),
    "room_description": (
        "You are an expert gamemaster and game designer. \n"
        "The following is context for the dungeon and factions:\n"
        "Dungeon History Summary: {history_content}\n"
        "Active Factions Summary: {faction_summary}\n\n"
        "Generate low-fantasy sword-and-sandals RPG room content. "
        "Content must focus on this encounter type: {encounter_type} ({encounter_desc})\n"
        "The content must contain this experience: {experience_type} ({experience_desc})\n"
        "Use this EXACT structure for your output:\n"
        "[NUMBER]. [LOCATION NAME IN CAPS]\n"
        "[Sensory Detail 1] [Sensory Detail 2] [Sensory Detail 3]\n"
        "• [Key Feature 1]: [Description] \n"
        "▶ [Detail 1]: [Detail on inspection/effects of interaction] ([Mechanics/DC/gp value])\n"
        "• [Optional: Key Feature 2]: [Description] ([Mechanics/DC/gp value])"
        "▶ [OptionaL: Interaction 2]: [Detail on inspection/effects of interaction] ([Mechanics/DC/gp value])"
        "• [Optional: Key Feature 3]: [Description] ([Mechanics/DC/gp value])"
        "▶ [OptionaL: Interaction 2]: [Detail on inspection/effects of interaction] ([Mechanics/DC/gp value])"
        "HARD REQUIREMENTS:\n"
        "1. First line MUST be 3 sensory details separated by periods. They should relate to the contents of the room.\n"
        "2. • bullets for key features/objects/NPCs/traps that address the {encounter_type} \n"
        "3. ▶ arrows for interactions with () values\n"
        "6. NO markdown, ONLY plain text\n\n"
        "EXAMPLE OUTPUT:\n"
        "17. STATUE ROOM\n"
        "Bronze fragments of bull statue. Sulfuric air. Cracked wall.\n"
        "• Carvings. Scenes of acrobats leaping over charging bulls and warriors fighting in ritualistic combat.\n"
        "• Bull Statue: Exploded by some violent force.\n"
        "• Body: Young man in splintered armor\n"
        "▶ Backpack: Silver locket with portrait (5 gp)\n\n"
        "Now create {room_number} ({room_type}):"
    ),
    "room_quality_control": (
        "Transform this content to match STRICT FORMAT:\n"
        "1. First line = 3 sensory details\n"
        "2. Content must focus on this encounter type: {encounter_type} ({encounter_desc})\n"
        "3. The content must contain this experience: {experience_type} ({experience_desc})\n"
        "4. Add creature names and tactics where needed\n"
        "5. Ensure EXACT gp values\n\n"
        "EXAMPLE CONVERSION:\n"
        "Before: A room with jars that might explode\n"
        "After:\n"
        "15. JAR STORAGE\n"
        "Terracotta clusters. Sulfuric smell. Jagged door.\n"
        "• Jars: 20 sealed vessels (black mush inside)\n"
        "▶ Explosive: DC 12 DEX save (1d4 damage)\n"
        "▶ Treasure: 1:20 chance of cockatrice egg inside instead (40 gp)\n\n"
        "Original Content:\n{original_content}\n\n"
        "Revised Version:"
    )
}


def get_prompt(template_name: str, context: Dict[str, Any]) -> str:
    """Retrieve and format prompt template with validation"""
    required_params = {
        "room_description": [
            "room_number", "room_type", "experience_type",
            "experience_desc", "encounter_type", "encounter_desc",
            "max_features", "history_content", "faction_summary"
        ],
        "room_quality_control": [
            "original_content", "max_features",
            "experience_type", "encounter_type"
        ]
    }

    if template_name not in PROMPT_TEMPLATES:
        logger.error(f"Invalid prompt template: {template_name}")
        raise ValueError(f"Unknown prompt template: {template_name}")

    missing = [p for p in required_params.get(template_name, [])
               if p not in context]
    if missing:
        logger.warning(f"Missing parameters for {template_name}: {missing}")
        raise ValueError(f"Missing required parameters: {missing}")

    return PROMPT_TEMPLATES[template_name].format(**context)
