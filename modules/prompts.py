# prompts.py
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
    "main": """Based on this history:
{history_content}

And this faction information:
{faction_content}

Generate a complete low-fantasy sword-and-sandals dungeon exterior description.

Format your response with these Markdown sections:
## Environment
Describe the physical surroundings, terrain, weather, vegetation, and atmosphere.

## Path
Detail the approach path, its condition, obstacles, and notable features.

## Landmark
Describe any prominent landmarks and their visual characteristics.

## Main Entrance
Detail the primary entrance and its notable features.

## Secondary Entrance
Detail any alternative entrances, focusing on hidden features and access points.

Keep descriptions focused on physical appearance and current state.
Use evocative language suitable for a game master.
""",
    "CONSOLIDATED": """
Generate a complete low-fantasy sword-and-sandals dungeon exterior description using these components:
{components}

Historical context: {history}
Faction influences: {factions}

Format your response with these Markdown sections:
## Environment
Describe the physical surroundings using: {components[environment]}
Focus on terrain, weather, vegetation, and atmosphere.

## Path
Detail the approach path that contains this obstacle: {components[path]}
Include its condition, describe the obstacle, and notable features.

## Landmark
Describe any prominent landmarks using this sense: {components[landmark]}
Highlight its characteristics and purpose.

## Antechamber
Describe the exterior aspects of the entrance chamber using: {components[antechamber]}
Include any defensive features or symbolic elements.

## Secondary Entrance
Detail the alternative entrance to the dungeonusing: {components[secondary_entrance]}
Focus on its hidden features and access challenges.

Maintain consistent tone and physical descriptions throughout.
Avoid historical narratives or faction details unless directly visible.
Use concise, evocative language suitable for a game master.
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
        "The following is the context for the dungeon's factions:\n"
        "{faction_content}\n"
        "Summarize the faction information in bullet points. Focus on key groups and their motivations.\n"

    ),
    "room_description": (
        "You are a master of low-fantasy dungeon design for tabletop RPGs.\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. Magic is RARE, MYSTERIOUS, and TERRIFYING. If anything magical appears (limit to one element if any), treat it as dangerous and unknown.\n"
        "2. CREATE A ROOM THAT FOCUSES EXCLUSIVELY ON THIS ENCOUNTER: {encounter_type} ({encounter_desc})\n"
        "3. ADD THIS EXPERIENCE AS A TWIST: {experience_type} ({experience_desc})\n"
        "4. Include EVOCATIVE MUNDANE DETAILS that connect to the dungeon's history and factions\n\n"
        
        "Dungeon Context:\n"
        "- History: {history_summary}\n"
        "- Factions: {faction_summary}\n\n"
        
        "FOLLOW THIS EXACT FORMAT:\n"
        "{room_number}. ROOM NAME\n"
        "[One paragraph room description with evocative mundane details. No bullet points here.]\n\n"
        "• [Feature]: [Brief description]\n"
        "▶ [Detail]: [What happens upon inspection or interaction]\n"
        "▷ [Sub-detail]: [Additional consequence, if applicable]\n\n"
        
        "EXAMPLE:\n"
        "7. BURIAL HALL\n"
        "A burial hall full of alcoves. A stone coffin lies in each alcove. The lids are carved with life-sized warriors in helms and chainmail, arms crossed over their chests.\n\n"
        "• Coffins: Six total. The heavy lids pull off with a puff of dust.\n"
        "▶ Inside: A grinning skeleton in chainmail holding a greataxe and a shield. A gold coin covers each eye socket.\n"
        "▷ Coins: Removing coins animates skeleton. Returning coins puts it back to rest.\n"
        "• Secret Door: A hidden panel in the back of the northern alcove slides open.\n\n"
        
        "Now create {room_number} ({room_type}):"
    ),
    "room_quality_control": (
        "You are a strict editor enforcing low-fantasy dungeon design standards.\n\n"
        "REVIEW AND FIX THE FOLLOWING ROOM TO ENSURE:\n"
        "1. FOCUS SOLELY on this encounter: {encounter_type} ({encounter_desc})\n"
        "2. Include this experience as a twist: {experience_type} ({experience_desc})\n"
        "3. LOW FANTASY ONLY - magic must be rare or absent entirely. At most ONE magical element, treated as dangerous.\n"
        "4. EVOCATIVE MUNDANE DETAILS that connect to {history_content} and {faction_content}\n"
        "5. EXACT FORMAT:\n\n"
        
        "{room_number}. ROOM NAME\n"
        "[One paragraph room description with evocative mundane details]\n\n"
        "• [Feature]: [Brief description]\n"
        "▶ [Detail]: [What happens upon inspection/interaction]\n"
        "▷ [Sub-detail]: [Additional consequence if needed]\n\n"
        
        "FORMAT RULES:\n"
        "- First part must be ONE PARAGRAPH description, not bullet points\n"
        "- Maximum {max_features} main features using • symbol\n"
        "- Use ▶ for inspection/interaction details\n"
        "- Use ▷ for sub-details only when needed\n"
        "- No extraneous sections or headers\n"
        "- Be concise and focused on the encounter type\n"
        "- For treasure: specific values (0-25gp small, 25-100gp medium, 200-500gp large)\n"
        "- For DCs: only STR/DEX/CON/INT/WIS/CHA with values 9 (easy), 12 (normal), 15 (hard), 18 (impossible)\n\n"
        
        "Original Content:\n{original_content}\n\n"

    )
}


def get_prompt(template_name: str, context: Dict[str, Any]) -> str:
    """Retrieve and format prompt template with validation"""
    required_params = {
        "history_summary": ["history_content"],
        "faction_summary": ["faction_content"],
        "room_description": [
            "room_number", "room_type", "experience_type",
            "experience_desc", "encounter_type", "encounter_desc",
            "max_features", "history_summary", "faction_summary"
        ],
        "room_quality_control": [
            "original_content", "max_features",
            "experience_type", "encounter_type",
            "experience_desc", "encounter_desc"
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

    try:
        return PROMPT_TEMPLATES[template_name].format(**context)
    except KeyError as e:
        logger.error(f"Template formatting error for {template_name}: {e}")
        raise ValueError(f"Invalid template parameter: {e}")
