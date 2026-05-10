import fitz
import re


def extract_text_from_pdf(pdf_path):
    text = ""
    pdf = fitz.open(pdf_path)

    for page in pdf:
        text += page.get_text() + "\n"

    return text


def clean_name(name):
    name = name.strip()
    name = re.sub(r"\s+\(Blks\)", "", name)
    name = re.sub(r"\s+EM$", "", name)
    return name.strip()


def extract_horse_name(line):
    parts = line.split()

    # Remove runner number
    parts = parts[1:]

    # Remove last-10 form if present
    if parts and re.match(r"^[0-9xX]+$", parts[0]):
        parts = parts[1:]

    name_parts = []

    for word in parts:
        clean_word = word.replace("’", "'")

        if clean_word.isupper() or clean_word in ["(NZ)", "(GB)", "(IRE)", "(USA)", "(Blks)", "EM"]:
            name_parts.append(word)
        else:
            break

    if not name_parts:
        return None

    return clean_name(" ".join(name_parts))


def extract_races(text):
    races = []

    race_blocks = re.split(r"(?=Race\s+\d+\s+-)", text)

    for block in race_blocks:
        race_match = re.search(r"Race\s+(\d+)\s+-", block)

        if not race_match:
            continue

        race_number = race_match.group(1)
        race_name = f"Race {race_number}"

        header_match = re.search(
            r"No\s+Last\s+10\s+Horse\s+Trainer\s+Jockey\s+Barrier\s+Weight.*?Hcp\s+Rating",
            block,
            re.DOTALL
        )

        if not header_match:
            continue

        table_start = header_match.end()
        table_text = block[table_start:]

        if "Trainer:" in table_text:
            table_text = table_text.split("Trainer:", 1)[0]

        horses = []

        for line in table_text.splitlines():
            line = line.strip()

            if not re.match(r"^\d{1,2}e?\s+", line):
                continue

            number_match = re.match(r"^(\d{1,2})e?", line)
            number = number_match.group(1)

            horse_name = extract_horse_name(line)

            if horse_name:
                horses.append({
                    "number": number,
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
