# prompts.py


def get_history_prompt(history_components, builder_info):
    return {
        "key": "History",
        "prompt": (
            "You are an expert in writing detailed and vivid sword & sorcery fantasy lore. "
            f"The dungeon was originally built by a proud and distinct race of {builder_info['creature_type']} "
            f"known as {builder_info['builder_name']}. Their culture was defined their primary impulse, which was "
            f"to be {builder_info['impulse']}.They designed the location as a {history_components['modifier']} "
            f"{history_components['purpose']} with a specific purpose—perhaps to serve as a sacred temple, a fortress, "
            f"a wizards lab, a crypt, or something else of practical or spiritual value. Now, provide a detailed and "
            f"specific account of the dungeon's ancient history. Include concrete details such as the style of "
            f"architecture, religious or ceremonial practices, and at least one significant historical event that "
            f"influenced its creation. Do not be vague or repetitive. Limit your output to one paragraph."
        )
    }


def get_ruin_prompt(history_components, builder_info, history_text):
    return {
        "key": "Ruin",
        "prompt": (
            "Building on the history you just described, explain in specific detail how the original builders’ "
            "culture fell into ruin.Describe one or more concrete events—such as a catastrophic natural disaster, "
            f"a brutal invasion, or internal betrayal—that led to their collapse. Be sure to reference the factor "
            f"'{history_components['ruin']}' and explain exactly how it contributed to the downfall. Include vivid "
            f"details such as the crumbling of their architectural marvels, the collapse of their social order, "
            "or the loss of a key leader. Avoid generic or vague statements. Limit your output to one paragraph."
        )
    }


def get_present_prompt(components, builder_info):
    return {
        "key": "Present State",
        "prompt": (
            "Now, describe the current state of the dungeon in vivid, concrete detail. "
            f"Focus on the new occupant known as {builder_info['present_name']}. "
            f"Explain exactly how and why they have transformed or repurposed the ancient site into a {components['present']}. "
            "Include specifics such as the modern architectural changes, the new cultural or political practices in place, "
            "and any distinctive artifacts or symbols that mark the transformation. "
            "Make sure your description is imaginative and detailed rather than vague. Limit your output to one paragraph."
        )
    }



