import random


def get_combined_history_prompt(history_components, builder_info):
    # Randomly choose a demonym from the provided list.
    demonym = random.choice(["ians", "ites", "ters", "ans", "iers", "ers"])
    # Append the demonym to the builder's name.
    builder_name_with_demonym = f"{builder_info['builder_name']}{demonym}"

    return {
        "key": "CombinedHistory",
        "prompt": (
            f"You are a master storyteller specializing in sword & sorcery fantasy."
            f"You're going to write lore for a location that will be used in a tabletop roleplaying game."
            f"Dungeon ancient builders: {builder_info['creature_type']} known as {builder_name_with_demonym}.for "
            f"Dungeon builders motivation: {builder_info['impulse']}. "
            f"Dungeon's ancient purpose: {history_components['modifier']} {history_components['purpose']}.\n\n"
            f"Builders ancient culture fell to ruin because: {history_components['ruin']}.\n\n"
            f"Present occupants are: {builder_info['present_name']}."
            f"Present occupants use the dungeon as: {history_components['present']}.\n\n"
            "Using these details, write three paragraphs detailing the history from the ancient builders to the "
            "present day."
            "Required Sections:"
            "## Ancient History"
            "## Culture's Decline"
            "## Present Day"
        )
    }
