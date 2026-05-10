import fitz
import re

def extract_text_from_pdf(pdf_path):
    text = ""

    pdf = fitz.open(pdf_path)

    for page in pdf:
        text += page.get_text()

    return text


def parse_races_from_text(text):
    races = []

    race_blocks = re.split(r"\nRace\s+", text)

    for block in race_blocks:
        if not block.strip():
            continue

        if not block[0].isdigit():
            continue

        lines = block.splitlines()

        race_number = lines[0].split("-")[0].strip()
        race_name = f"Race {race_number}"

        horses = []

        for line in lines:
            match = re.match(r"^(\d+)\s+([A-Z][A-Z '\-\(\)]+)", line.strip())

            if match:
                horse_number = match.group(1)
                horse_name = match.group(2).strip()

                if len(horse_name) > 2:
                    horses.append({
                        "number": horse_number,
                        "name": horse_name
                    })

        races.append({
            "race_name": race_name,
            "horses": horses
        })

    return races
