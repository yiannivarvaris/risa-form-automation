import logging
import re
from typing import Any

import fitz

LOGGER = logging.getLogger(__name__)

RACE_HEADER_RE = re.compile(r"\bRace\s*(\d+)\b", re.IGNORECASE)
RUNNER_LINE_RE = re.compile(r"^\s*(\d{1,2})(?:[A-Za-z])?\s+(.+)$")

REJECT_MARKERS = (
    "sire:",
    "dam:",
    "track:",
    "dist:",
    "prize money",
    "breeder",
    "3 year old",
    "4 year old",
    "5 year old",
    "6 year old",
    "7 year old",
    "8 year old",
    "trainer",
)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text using layout-preserving blocks and save debug output."""
    all_lines: list[str] = []
    race_matches: list[str] = []

    with fitz.open(pdf_path) as pdf:
        total_pages = len(pdf)
        for page in pdf:
            blocks = page.get_text("blocks")
            blocks = sorted(blocks, key=lambda b: (round(b[1], 1), round(b[0], 1)))
            for block in blocks:
                block_text = block[4] if len(block) > 4 else ""
                if not block_text:
                    continue
                for ln in block_text.splitlines():
                    line = ln.rstrip()
                    if line:
                        all_lines.append(line)
                        m = RACE_HEADER_RE.search(line)
                        if m:
                            race_matches.append(m.group(0))

    text = "\n".join(all_lines)
    with open("debug_output.txt", "w", encoding="utf-8") as f:
        f.write(text)

    print(f"TOTAL PAGES: {total_pages}")
    print(f"TOTAL CHARACTERS: {len(text)}")
    print(f"ALL detected 'Race X' matches: {race_matches}")
    print("FIRST 500 lines of extracted text:")
    for idx, line in enumerate(all_lines[:500], start=1):
        print(f"{idx:04d}: {line}")

    return text


def _extract_horse_name_from_runner_line(line: str) -> str | None:
    m = RUNNER_LINE_RE.match(line.strip())
    if not m:
        return None
    remainder = m.group(2).strip()
    if not remainder:
        return None

    tokens = remainder.split()
    if tokens and re.fullmatch(r"[0-9Xx*/-]+", tokens[0]):
        tokens = tokens[1:]
    name_parts: list[str] = []
    for tok in tokens:
        if re.fullmatch(r"[A-Z][A-Z'\-.]*", tok):
            name_parts.append(tok)
            continue
        break

    if not name_parts:
        return None
    return " ".join(name_parts).strip()


def _is_runner_line(line: str) -> tuple[bool, str]:
    stripped = line.strip()
    if not stripped:
        return False, "blank line"
    if not RUNNER_LINE_RE.match(stripped):
        return False, "does not start with runner number"

    lowered = stripped.lower()
    for marker in REJECT_MARKERS:
        if marker in lowered:
            return False, f"contains blocked marker: {marker}"

    name = _extract_horse_name_from_runner_line(stripped)
    if not name:
        return False, "could not parse uppercase horse name"
    return True, "ok"


def parse_races_from_text(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    race_headers: list[tuple[int, int]] = []

    for i, line in enumerate(lines):
        m = RACE_HEADER_RE.search(line)
        if m:
            race_headers.append((int(m.group(1)), i))

    print(f"ALL detected 'Race X' matches in parse: {[f'Race {n}' for n, _ in race_headers]}")

    # Deduplicate repeated race headers
    deduped_headers: list[tuple[int, int]] = []
    last_seen_line_for_race: dict[int, int] = {}
    for race_no, idx in race_headers:
        prev = last_seen_line_for_race.get(race_no)
        if prev is None or idx - prev > 20:
            deduped_headers.append((race_no, idx))
            last_seen_line_for_race[race_no] = idx

    races: list[dict[str, Any]] = []
    for h_idx, (race_number, start_idx) in enumerate(deduped_headers):
        end_idx = deduped_headers[h_idx + 1][1] if h_idx + 1 < len(deduped_headers) else len(lines)
        race_lines = lines[start_idx:end_idx]

        race = {"race_number": race_number, "race_name": f"Race {race_number}", "horses": []}
        print(f"\n[Race {race_number}] scanning lines {start_idx + 1}..{end_idx}")

        for line in race_lines:
            ok, reason = _is_runner_line(line)
            if not RUNNER_LINE_RE.match(line.strip()):
                continue
            print(f"CANDIDATE RUNNER LINE: {line.strip()}")
            if not ok:
                print(f"REJECTED: {reason}")
                continue

            number = int(RUNNER_LINE_RE.match(line.strip()).group(1))
            name = _extract_horse_name_from_runner_line(line)
            if not name:
                print("REJECTED: name parse returned empty")
                continue
            print(f"ACCEPTED: {number} {name}")
            race["horses"].append({"number": number, "name": name})

        race["horses"].sort(key=lambda h: h["number"])
        if race["horses"]:
            races.append(race)

    if not races:
        first_100 = "\n".join(f"{i+1:04d}: {ln}" for i, ln in enumerate(lines[:100]))
        match_labels = [f"Race {n} @ line {idx+1}" for n, idx in deduped_headers]
        raise ValueError(
            "No races extracted from PDF. "
            f"race matches found={match_labels or '[]'}\n"
            f"first 100 lines:\n{first_100}"
        )

    return races
