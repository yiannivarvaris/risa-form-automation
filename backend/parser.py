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

    # Remove gear/emergency notes from name
    name = re.sub(r"\s+\(.*?\)", "", name)
    name = re.sub(r"\s+EM$", "", name)

    return name.strip()


def extract_races(text):
    races = []

    # Split each race from the race heading
    race_blocks = re.split(r"(?=Race\s+\d+\s+-)", text)

    for block in race_blocks:
        race_match = re.search(r"Race\s+(\d+)\s+-", block)

        if not race_match:
            continue

        race_number = race_match.group(1)
        race_name = f"Race {race_number}"

        # Find official runner table
        table_match = re.search(
            r"No\s+Last\s+10\s+Horse\s+Trainer\s+Jockey\s+Barrier\s+Weight.*?\n(.*?)(?=\nTrainer:|\n\d+\s+[A-Z][A-Z '\-\(\)]+|\nRace\s+\d+\s+-)",
            block,
            re.DOTALL
        )

        if not table_match:
            continue

        table_text = table_match.group(1)
        lines = table_text.splitlines()

        horses = []

        for line in lines:
            line = line.strip()

            # Match runner rows:
            # 1 20x BRAZEN WARRIOR Patrick Payne Billy Egan 16 59.5kg
            # 15e 5x6969x2 ROUGHNUT Jane Duncan ...
            match = re.match(
                r"^(\d{1,2})e?\s+(?:[0-9xX]+)?\s*([A-Z][A-Z '\-\(\)]+?)\s+(?=[A-Z][a-z])",
                line
            )

            if not match:
                continue

            horse_number = match.group(1)
            horse_name = clean_horse_name(match.group(2))

            if len(horse_name) < 2:
                continue

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
