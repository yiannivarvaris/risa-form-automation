import fitz
import re

def extract_text_from_pdf(pdf_path):
    text = ""

    pdf = fitz.open(pdf_path)

    for page in pdf:
        text += page.get_text() + "\n"

    return text


def clean_horse_name(name):
    name = name.strip()

    # Remove common junk at end
    junk_words = [
        "M", "G", "K", "J", "C", "A", "B", "D",
        "Rtg", "Rating", "Trainer", "Jockey"
    ]

    parts = name.split()

    while parts and parts[-1] in junk_words:
        parts.pop()

    return " ".join(parts).strip()


def parse_races_from_text(text):
    races = []

    race_blocks = re.split(r"(?=\bRace\s+\d+\b)", text)

    for block in race_blocks:
        race_match = re.search(r"\bRace\s+(\d+)\b", block)

        if not race_match:
            continue

        race_number = race_match.group(1)
        race_name = f"Race {race_number}"

        horses = []
        seen_numbers = set()

        lines = block.splitlines()

        for line in lines:
            line = line.strip()

            # Match runner number then horse name
            match = re.match(r"^(\d{1,2})\s+([A-Z][A-Z '\-]+)", line)

            if not match:
                continue

            horse_number = match.group(1)

            if horse_number in seen_numbers:
                continue

            horse_name = clean_horse_name(match.group(2))

            if len(horse_name) < 3:
                continue

            # Ignore obvious non-horse lines
            bad_words = [
                "RACE", "TRACK", "DISTANCE", "TRAINER",
                "JOCKEY", "PRIZE", "TOTAL", "FIELD"
            ]

            if horse_name.upper() in bad_words:
                continue

            horses.append({
                "number": horse_number,
                "name": horse_name
            })

            seen_numbers.add(horse_number)

        horses.sort(key=lambda h: int(h["number"]))

        races.append({
            "race_name": race_name,
            "horses": horses
        })

    return races


# This keeps main.py working if it uses extract_races
def extract_races(text):
    return parse_races_from_text(text)
