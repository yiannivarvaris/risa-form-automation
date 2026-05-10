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


def extract_races(text):
    races = []

    race_blocks = re.split(r"(?=Race\s+\d+\s+-)", text)

    for block in race_blocks:
        race_match = re.search(r"Race\s+(\d+)\s+-", block)
        if not race_match:
            continue

        race_number = race_match.group(1)
        race_name = f"Race {race_number}"

        if "No Last 10 Horse Trainer Jockey Barrier Weight" not in block:
            continue

        table_part = block.split("No Last 10 Horse Trainer Jockey Barrier Weight", 1)[1]

        if "Trainer:" in table_part:
            table_part = table_part.split("Trainer:", 1)[0]

        horses = []

        for line in table_part.splitlines():
            line = line.strip()

            match = re.match(r"^(\d{1,2})e?\s+(.*)", line)
            if not match:
                continue

            number = match.group(1)
            rest = match.group(2).strip()

            # remove form figures at start
            rest = re.sub(r"^[0-9xX]+\s+", "", rest)

            words = rest.split()
            name_words = []

            for word in words:
                if word.isupper() or word in ["(NZ)", "(GB)", "(IRE)", "(USA)"]:
                    name_words.append(word)
                else:
                    break

            if not name_words:
                continue

            horse_name = clean_name(" ".join(name_words))

            horses.append({
                "number": number,
                "name": horse_name
            })

        if horses:
            races.append({
                "race_name": race_name,
                "horses": horses
            })

    print("RACES FOUND")
    for race in races:
        print(race["race_name"], [h["name"] for h in race["horses"]])

    return races


def parse_races_from_text(text):
    return extract_races(text)
