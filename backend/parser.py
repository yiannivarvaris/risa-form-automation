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
    name = re.sub(r"\s+EM$", "", name)
    return name.strip()


def get_name_from_runner_line(line):
    parts = line.strip().split()

    if not parts:
        return None

    # Remove runner number, e.g. 1, 15e
    parts = parts[1:]

    # Remove last-10-form column if present, e.g. 20x, 5x6969x2
    if parts and re.match(r"^[0-9xX]+$", parts[0]):
        parts = parts[1:]

    name_parts = []

    for part in parts:
        clean = part.replace("’", "'")

        # Horse names are uppercase in the runner table
        if clean.isupper() or clean in ["(NZ)", "(GB)", "(IRE)", "(USA)"]:
            name_parts.append(part)
        else:
            break

    if not name_parts:
        return None

    return clean_horse_name(" ".join(name_parts))


def extract_races(text):
    races = []

    race_blocks = re.split(r"(?=Race\s+\d+\s+-)", text)

    for block in race_blocks:
        race_match = re.search(r"Race\s+(\d+)\s+-", block)

        if not race_match:
            continue

        race_number = race_match.group(1)
        race_name = f"Race {race_number}"

        header = "No Last 10 Horse Trainer Jockey Barrier Weight"
        header_index = block.find(header)

        if header_index == -1:
            continue

        table_text = block[header_index + len(header):]

        trainer_index = table_text.find("Trainer:")
        if trainer_index != -1:
            table_text = table_text[:trainer_index]

        horses = []

        for line in table_text.splitlines():
            line = line.strip()

            if not re.match(r"^\d{1,2}e?\s+", line):
                continue

            horse_number_match = re.match(r"^(\d{1,2})e?", line)
            horse_number = horse_number_match.group(1)

            horse_name = get_name_from_runner_line(line)

            if horse_name:
                horses.append({
                    "number": horse_number,
                    "name": horse_name
                })

        if horses:
            races.append({
                "race_name": race_name,
                "horses": horses
            })

    return races


def parse_races_from_text(text):
    return extract_races(text)
