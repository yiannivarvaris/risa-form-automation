import fitz
import re

def extract_text_from_pdf(pdf_path):
    text = ""

    pdf = fitz.open(pdf_path)

    for page in pdf:
        text += page.get_text() + "\n"

    return text


def extract_races(text):
    races = {}

    current_race = None

    lines = text.splitlines()

    for line in lines:

        line = line.strip()

        # Detect race headers
        race_match = re.search(r"Race\s+(\d+)", line, re.IGNORECASE)

        if race_match:
            race_number = race_match.group(1)
            current_race = f"Race {race_number}"
            races[current_race] = []
            continue

        # Detect horse lines
        horse_match = re.match(r"^(\d+)\s+([A-Z][A-Z '\-]+)", line)

        if horse_match and current_race:

            horse_name = horse_match.group(2).strip()

            # Clean weird junk
            horse_name = re.sub(r"\s+", " ", horse_name)

            if len(horse_name) > 2:
                races[current_race].append(horse_name)

    print("RACES FOUND")

    for race, horses in races.items():
        print(race, horses)

    return races
