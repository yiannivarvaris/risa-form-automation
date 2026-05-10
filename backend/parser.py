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
    name = re.sub(r"\s+\(Blks\)", "", name)
    name = re.sub(r"\s+\(NZ\)", " (NZ)", name)
    name = re.sub(r"\s+EM$", "", name)
    return name.strip()


def extract_races(text):
    races = []

    race_blocks = re.split(r"(?=Race\s+\d+\s+-)", text)

    for block in race_blocks:
        race_match = re.search(r"Race\s+(\d+)\s+-", block)

        if not race_match:
            continue

        race_number = race_match.group(1)
        race_name = f"Race {race_number}"

        horses = []

        lines = block.splitlines()

        for line in lines:
            line = line.strip()

            match = re.match(r"^(\d{1,2})e?\s+(?:[0-9xX]+)?\s*([A-Z][A-Z '\-’\(\)]+)", line)

            if match:
                horse_number = match.group(1)
                horse_name = clean_horse_name(match.group(2))

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


def parse_races_from_text(text):
    return extract_races(text)
