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


def get_horse_name_from_runner_line(line):
    parts = line.split()

    if len(parts) < 2:
        return None

    # remove runner number, e.g. 1 or 15e
    parts = parts[1:]

    # remove last-10 form, e.g. 20x, 824, 5x6969x2
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
    current_race = None
    in_runner_table = False

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        race_match = re.search(r"Race\s+(\d+)\s+-", line)
        if race_match:
            if current_race and current_race["horses"]:
                races.append(current_race)

            current_race = {
                "race_name": f"Race {race_match.group(1)}",
                "horses": []
            }
            in_runner_table = False
            continue

        if current_race and line.startswith("No Last 10 Horse"):
            in_runner_table = True
            continue

        if current_race and in_runner_table and line.startswith("Trainer:"):
            in_runner_table = False
            continue

        if not current_race or not in_runner_table:
            continue

        if not re.match(r"^\d{1,2}e?\s+", line):
            continue

        number = re.match(r"^(\d{1,2})e?", line).group(1)
        horse_name = get_horse_name_from_runner_line(line)

        if horse_name:
            current_race["horses"].append({
                "number": number,
                "name": horse_name
            })

    if current_race and current_race["horses"]:
        races.append(current_race)

    print("RACES FOUND")
    for race in races:
        print(race["race_name"], [horse["name"] for horse in race["horses"]])

    return races


def parse_races_from_text(text):
    return extract_races(text)
