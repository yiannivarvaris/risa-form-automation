import fitz
import re

RACE_HEADER_RE = re.compile(r"\bRace\s+(\d+)\s*[-:]", re.IGNORECASE)
RUNNER_START_RE = re.compile(r"^(\d{1,2})e?\s+")


def extract_text_from_pdf(pdf_path):
    text = ""
    pdf = fitz.open(pdf_path)

    for page in pdf:
        text += page.get_text() + "\n"

    return text


def clean_name(name):
    name = re.sub(r"\s+", " ", name.strip())
    name = re.sub(r"\s+\(Blks\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+EM$", "", name, flags=re.IGNORECASE)
    return name.strip()


def _is_last10_token(token):
    # Examples: 20x, 824, 5x6969x2
    return bool(re.fullmatch(r"[0-9xX]+", token))


def _is_horse_token(token):
    t = token.replace("’", "'")
    if re.fullmatch(r"\([A-Z]{2,4}\)", t):
        return True
    return bool(re.fullmatch(r"[A-Z0-9'\-\.]+", t))


def _extract_name_tokens(fragment):
    parts = fragment.split()
    if not parts:
        return []

    if _is_last10_token(parts[0]):
        parts = parts[1:]

    name_tokens = []
    for token in parts:
        if _is_horse_token(token):
            name_tokens.append(token)
        else:
            break
    return name_tokens


def _should_skip_race(header_line):
    h = header_line.lower()
    return "trial" in h or "jump out" in h or "jump-out" in h


def extract_races(text):
    # Keep latest occurrence per race number to satisfy "latest race start".
    races_by_number = {}

    current_race_num = None
    current_race = None
    in_runner_table = False
    current_runner = None

    lines = text.splitlines()

    def finalize_runner():
        nonlocal current_runner, current_race
        if not current_race or not current_runner:
            current_runner = None
            return

        name = clean_name(" ".join(current_runner["name_tokens"]))
        if name:
            current_race["horses"].append({
                "number": current_runner["number"],
                "name": name,
            })
        current_runner = None

    def finalize_race():
        nonlocal current_race_num, current_race
        if not current_race_num or not current_race:
            return

        # Keep order and de-duplicate by runner number inside race.
        deduped = []
        seen = set()
        for horse in current_race["horses"]:
            key = horse["number"]
            if key in seen:
                continue
            seen.add(key)
            deduped.append(horse)
        current_race["horses"] = deduped

        if current_race["horses"]:
            races_by_number[current_race_num] = current_race

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        race_match = RACE_HEADER_RE.search(line)
        if race_match:
            finalize_runner()
            finalize_race()

            race_num = int(race_match.group(1))
            current_race_num = race_num

            if _should_skip_race(line):
                current_race = None
                in_runner_table = False
                continue

            current_race = {
                "race_name": f"Race {race_num}",
                "horses": [],
            }
            in_runner_table = False
            continue

        if not current_race:
            continue

        lower = line.lower()

        # Runner table header can vary slightly across PDFs.
        if ("no" in lower and "horse" in lower and "last" in lower) or lower.startswith("no horse"):
            in_runner_table = True
            finalize_runner()
            continue

        if not in_runner_table:
            continue

        # End of runners section.
        if lower.startswith("trainer:") or lower.startswith("track") or lower.startswith("stewards"):
            finalize_runner()
            in_runner_table = False
            continue

        m = RUNNER_START_RE.match(line)
        if m:
            finalize_runner()
            runner_number = m.group(1)
            after_num = line[m.end():]
            name_tokens = _extract_name_tokens(after_num)
            current_runner = {
                "number": runner_number,
                "name_tokens": name_tokens,
            }
            continue

        # Handle wrapped runner lines: append upper-case horse tokens only.
        if current_runner:
            continuation_tokens = _extract_name_tokens(line)
            if continuation_tokens:
                current_runner["name_tokens"].extend(continuation_tokens)

    finalize_runner()
    finalize_race()

    races = [races_by_number[k] for k in sorted(races_by_number.keys())]

    print("RACES FOUND")
    for race in races:
        print(race["race_name"], [horse["name"] for horse in race["horses"]])

    return races


def parse_races_from_text(text):
    return extract_races(text)
