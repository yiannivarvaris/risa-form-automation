import logging
import re
from typing import Any

import fitz

LOGGER = logging.getLogger(__name__)

RACE_HEADER_RE = re.compile(r"\bRace\s+(\d+)\b", re.IGNORECASE)
RUNNER_LINE_RE = re.compile(r"^(\d{1,2})e?\s+")
AGE_SEX_RE = re.compile(r"\b(\d{1,2})([FGCMR])\b")
RATING_RE = re.compile(r"\bRtg\s*(\d+)\b", re.IGNORECASE)
DECLARED_CD_RE = re.compile(r"(\d{1,2}(?:\.\d)?)kg\s*\(\s*cd\s*(\d{1,2}(?:\.\d)?)kg\s*\)", re.IGNORECASE)
CLASS_RE = re.compile(r"\b(BM\d+|CL\d+|MDN|\d+-\d+)\b", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")

TRIAL_MARKERS = ("trial", "jump-out", "jump out", "jumpout")


SEX_MAP = {"F": "filly", "G": "gelding", "C": "colt", "M": "mare", "R": "rig"}


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract full text from all PDF pages in reading order."""
    text = ""
    pdf = fitz.open(pdf_path)
    for page in pdf:
        text += page.get_text() + "\n"
    return text


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_age_sex(line: str) -> tuple[int | None, str | None]:
    match = AGE_SEX_RE.search(line)
    if not match:
        return None, None
    age = int(match.group(1))
    sex = SEX_MAP.get(match.group(2))
    return age, sex


def _extract_horse_name(line: str) -> str | None:
    parts = line.split()
    if len(parts) < 2:
        return None
    parts = parts[1:]
    if parts and re.match(r"^[0-9xX]+$", parts[0]):
        parts = parts[1:]

    name_parts: list[str] = []
    for word in parts:
        upper = word.replace("’", "'")
        if upper.isupper() or upper in {"(NZ)", "(GB)", "(IRE)", "(USA)"}:
            name_parts.append(word)
        else:
            break

    if not name_parts:
        return None
    return " ".join(name_parts).replace(" (Blks)", "").replace(" EM", "").strip()


def _extract_current_weights(line: str) -> tuple[float | None, float | None, float | None, float | None]:
    current_weight = _parse_float(re.search(r"\b(\d{1,2}(?:\.\d)?)kg\b", line).group(1)) if re.search(r"\b(\d{1,2}(?:\.\d)?)kg\b", line) else None
    claim_match = re.search(r"\(\s*a\s*/\s*(\d(?:\.\d)?)\s*\)", line, re.IGNORECASE)
    apprentice_claim = _parse_float(claim_match.group(1)) if claim_match else None
    min_match = re.search(r"min\s*(\d{1,2}(?:\.\d)?)kg", line, re.IGNORECASE)
    apprentice_min = _parse_float(min_match.group(1)) if min_match else None

    adjusted = current_weight
    if current_weight is not None and apprentice_claim is not None:
        adjusted = current_weight - apprentice_claim
        if apprentice_min is not None:
            adjusted = max(adjusted, apprentice_min)
    return current_weight, apprentice_claim, apprentice_min, adjusted


def _extract_latest_start(horse_block: str, sex: str | None) -> dict[str, Any]:
    """Heuristic extraction for most recent non-trial previous start.

    Assumption: the first non-trial previous-start line in the horse block is the latest real race.
    """
    latest_line = None
    for raw_line in horse_block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(marker in line.lower() for marker in TRIAL_MARKERS):
            continue
        if DATE_RE.search(line) and ("kg" in line or "Rtg" in line or "cd" in line):
            latest_line = line
            break

    latest: dict[str, Any] = {
        "date": None,
        "class": None,
        "rating": 29,
        "declared_weight": None,
        "actual_carried_weight": None,
        "beaten_margin": None,
        "track_record": None,
        "distance_record": None,
        "runs_since_first_up": None,
        "days_since_last_start": None,
    }

    if not latest_line:
        return latest

    date_match = DATE_RE.search(latest_line)
    class_match = CLASS_RE.search(latest_line)
    rating_match = RATING_RE.search(latest_line)
    weight_match = DECLARED_CD_RE.search(latest_line)
    margin_match = re.search(r"\b(\d+(?:\.\d+)?)L\b", latest_line, re.IGNORECASE)

    latest["date"] = date_match.group(1) if date_match else None
    latest["class"] = class_match.group(1).upper() if class_match else None
    latest["rating"] = int(rating_match.group(1)) if rating_match else 29

    if weight_match:
        declared = _parse_float(weight_match.group(1))
        carried = _parse_float(weight_match.group(2))
        if declared is not None and sex in {"filly", "mare"}:
            declared += 2.0
        latest["declared_weight"] = declared
        latest["actual_carried_weight"] = carried

    if "won" in latest_line.lower() or re.search(r"\b1st\b", latest_line.lower()):
        latest["beaten_margin"] = 0
    elif margin_match:
        latest["beaten_margin"] = _parse_float(margin_match.group(1))

    rfu_match = re.search(r"\bRFU\s*(\d+)\b", latest_line, re.IGNORECASE)
    dsl_match = re.search(r"\bDSL\s*(\d+)\b", latest_line, re.IGNORECASE)
    tr_match = re.search(r"\bTR\s*([^,;]+)", latest_line, re.IGNORECASE)
    dr_match = re.search(r"\bDR\s*([^,;]+)", latest_line, re.IGNORECASE)

    latest["runs_since_first_up"] = rfu_match.group(1) if rfu_match else None
    latest["days_since_last_start"] = dsl_match.group(1) if dsl_match else None
    latest["track_record"] = tr_match.group(1).strip() if tr_match else None
    latest["distance_record"] = dr_match.group(1).strip() if dr_match else None
    return latest


def parse_races_from_text(text: str) -> list[dict[str, Any]]:
    races: list[dict[str, Any]] = []
    chunks = re.split(r"(?=\bRace\s+\d+\b)", text, flags=re.IGNORECASE)

    for chunk in chunks:
        header = RACE_HEADER_RE.search(chunk)
        if not header:
            continue

        race_number = int(header.group(1))
        race = {"race_number": race_number, "race_name": f"Race {race_number}", "horses": []}

        runner_lines = [ln for ln in chunk.splitlines() if RUNNER_LINE_RE.match(ln.strip())]
        for idx, line in enumerate(runner_lines):
            number = int(RUNNER_LINE_RE.match(line.strip()).group(1))
            name = _extract_horse_name(line.strip())
            if not name:
                continue

            age, sex = _extract_age_sex(line)
            current_weight, claim, apprentice_min, adjusted = _extract_current_weights(line)

            block_start = chunk.find(line)
            block_end = chunk.find(runner_lines[idx + 1]) if idx + 1 < len(runner_lines) else len(chunk)
            horse_block = chunk[block_start:block_end]
            latest_start = _extract_latest_start(horse_block, sex)

            race["horses"].append(
                {
                    "number": number,
                    "name": name,
                    "current_weight": current_weight,
                    "apprentice_claim": claim,
                    "apprentice_min_weight": apprentice_min,
                    "adjusted_current_weight": adjusted,
                    "age": age,
                    "sex": sex,
                    "age_sex": f"{age}yo {sex}" if age and sex and age == 3 else None,
                    "latest_start": latest_start,
                }
            )

        race["horses"].sort(key=lambda h: h["number"])
        if race["horses"]:
            races.append(race)

    races.sort(key=lambda r: r["race_number"])
    horse_count = sum(len(r["horses"]) for r in races)
    LOGGER.info("Extracted %s races and %s horses from guide", len(races), horse_count)
    return races
