import random
from modules import tables


def generate_random_name():
    """
    Generate a random name based on one of the following formats:
      1. W
      2. WW
      3. WWW
      4. The Y of Z
      5. The X of Z
      6. W the Y of Z
      7. XY (Noun)(Verbs)

    Where:
      - W is a syllable.
      - Y is a noun.
      - X is a verb.
      - Z is a place name built from one of the W formats.
    """
    # Get the random name choices from tables.RANDOM_NAME.
    random_data = tables.RANDOM_NAME
    syllables = random_data.get("syllables", [])
    nouns = random_data.get("nouns", [])
    verbs = random_data.get("verbs", [])

    # Choose one of the seven formats at random.
    format_choice = random.choice([1, 2, 3, 4, 5, 6, 7])

    def make_w(n):
        """Generate a word composed of n syllables, capitalizing the first letter."""
        return ''.join(random.choice(syllables) for _ in range(n)).capitalize()

    if format_choice == 1:
        # Format 1: W
        name = make_w(1)
    elif format_choice == 2:
        # Format 2: WW
        name = make_w(2)
    elif format_choice == 3:
        # Format 3: WWW
        name = make_w(3)
    elif format_choice == 4:
        # Format 4: The Y of Z
        noun = random.choice(nouns)
        z = make_w(random.choice([1, 2, 3]))
        name = f"The {noun} of {z}"
    elif format_choice == 5:
        # Format 5: The X of Z
        verb = random.choice(verbs)
        z = make_w(random.choice([1, 2, 3]))
        name = f"The {verb} of {z}"
    elif format_choice == 6:
        # Format 6: W the Y of Z
        w = make_w(1)
        noun = random.choice(nouns)
        z = make_w(random.choice([1, 2, 3]))
        name = f"{w} the {noun} of {z}"
    elif format_choice == 7:
        # Format 7: XY (Noun)(Verbs)
        noun = random.choice(nouns)
        verb = random.choice(verbs)
        name = f"{noun}{verb} {random.choice(nouns)}"

    return name


# Example usage:
if __name__ == "__main__":
    print("Builder Name:", generate_random_name())
    print("Present Name:", generate_random_name())
