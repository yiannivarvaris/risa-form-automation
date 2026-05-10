import logging
import re
from typing import Any

import fitz

LOGGER = logging.getLogger(__name__)

RACE_HEADER_RE = re.compile(r"\bRace\s*(\d+)\b", re.IGNORECASE)
RUNNER_LINE_RE = re.compile(r"^\s*(\d{1,2})(?:[A-Za-z])?\s+")
RUNNER_TABLE_HEADER_RE = re.compile(r"\bNo\b.*\bHorse\b", re.IGNORECASE)
AGE_SEX_RE = re.compile(r"\b(\d{1,2})([FGCMR])\b")
RATING_RE = re.compile(r"\bRtg\s*(\d+)\b", re.IGNORECASE)
DECLARED_CD_RE = re.compile(r"(\d{1,2}(?:\.\d)?)kg\s*\(\s*cd\s*(\d{1,2}(?:\.\d)?)kg\s*\)", re.IGNORECASE)
CLASS_RE = re.compile(r"\b(BM\d+|CL\d+|MDN|\d+-\d+)\b", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")

TRIAL_MARKERS = ("trial", "jump-out", "jump out", "jumpout")

SUSPICIOUS_NAME_FRAGMENTS = (
    "year old", "sire:", "dam:", "trainer:", "jockey:", "record:",
    "breeder:", "owners:", "colours:", "1st", "2nd", "last race",
    "other information", "true odds", "actual odds",
)

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
    # Remove saddlecloth prefix and possible emergency marker.
    cleaned = re.sub(r"^\s*\d{1,2}[A-Za-z]?\s+", "", line).strip()
    if not cleaned:
        return None

    # Stop name before obvious metadata columns.
    tokens = cleaned.split()
    if tokens and re.fullmatch(r"[0-9xX\-/*]+", tokens[0]):
        tokens = tokens[1:]

    stop_patterns = (
        re.compile(r"^\d{1,2}[FGCMR]$", re.IGNORECASE),
        re.compile(r"^\d{1,2}(?:\.\d)?kg$", re.IGNORECASE),
        re.compile(r"^(?:Rtg|CD|RFU|DSL)$", re.IGNORECASE),
        re.compile(r"^\([A-Za-z]{2,4}\)$"),
        re.compile(r"^\d{1,2}$"),
    )

    name_parts: list[str] = []
    for tok in tokens:
        if any(pat.match(tok) for pat in stop_patterns):
            break
        if not re.fullmatch(r"[A-Z'\-.]+", tok):
            break
        name_parts.append(tok)

    if not name_parts:
        return None

    name = " ".join(name_parts)
    name = re.sub(r"\s+\(Blks\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+EM$", "", name, flags=re.IGNORECASE)
    name = name.strip(" -")
    if not name:
        return None
    if re.fullmatch(r"(?:OF|THE)\s+\d+", name, re.IGNORECASE):
        return None
    if re.search(r"\b(?:OF|YEAR|SIRE|DAM)\b", name, re.IGNORECASE) and len(name.split()) <= 3:
        return None
    return name


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
    latest_line = None
    for raw_line in horse_block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(marker in line.lower() for marker in TRIAL_MARKERS):
            continue
        if DATE_RE.search(line) and ("kg" in line or "Rtg" in line or "cd" in line.lower()):
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


def _is_runner_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if not RUNNER_LINE_RE.match(stripped):
        return False
    if RACE_HEADER_RE.search(stripped):
        return False
    if re.search(r"\b(?:m|Metres|Prize|Time|No\.|Barrier|Jockey|Trainer)\b", stripped, re.IGNORECASE):
        return False
    return True



def _looks_like_runner_table_header(line: str) -> bool:
    return bool(RUNNER_TABLE_HEADER_RE.search(line))


def _is_suspicious_line(line: str) -> bool:
    lowered = line.lower()
    if any(fragment in lowered for fragment in SUSPICIOUS_NAME_FRAGMENTS):
        return True
    if re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", line):
        return True
    return False


def _extract_runner_table_lines(race_lines: list[str], race_number: int) -> list[str]:
    header_idx = next((i for i, line in enumerate(race_lines[:120]) if _looks_like_runner_table_header(line)), None)
    if header_idx is None:
        # Handle split headers (e.g. "No" on one line and "Horse" on another).
        for i in range(min(120, len(race_lines) - 1)):
            merged = f"{race_lines[i].strip()} {race_lines[i + 1].strip()}".strip()
            if _looks_like_runner_table_header(merged) or ("no" in merged.lower() and "horse" in merged.lower()):
                header_idx = i
                break

    if header_idx is None:
        LOGGER.warning("race %s: official runner table header not found; attempting early-race scan", race_number)
        header_idx = 0

    runner_lines: list[str] = []
    started = False
    non_runner_streak = 0
    stop_markers = re.compile(
        r"\b(?:Last race|Other Information|True Odds|Actual Odds|Runner\s+RWF|RWFS|RBFS|Sire:|Dam:|Record:)\b",
        re.IGNORECASE,
    )

    for line in race_lines[header_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            if started:
                break
            continue
        if RACE_HEADER_RE.search(stripped):
            break
        if _looks_like_runner_table_header(stripped) or re.fullmatch(r"(No|Horse|Trainer|Jockey|Barrier|Weight|Rating|Last\s*10|Form|Wt)", stripped, re.IGNORECASE):
            continue
        if stop_markers.search(stripped):
            break
        if RUNNER_LINE_RE.match(stripped):
            runner_lines.append(stripped)
            started = True
            non_runner_streak = 0
            continue
        if started:
            non_runner_streak += 1
            if non_runner_streak >= 2:
                break
        if runner_lines and not started:
            break

    if not runner_lines:
        LOGGER.warning("race %s: runner table detected but no valid runner lines extracted", race_number)
    return runner_lines


def parse_races_from_text(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    race_headers: list[tuple[int, int]] = []

    for i, line in enumerate(lines):
        m = RACE_HEADER_RE.search(line)
        if m:
            race_no = int(m.group(1))
            race_headers.append((race_no, i))

    # Deduplicate repeated race headers (often in page headers/footers).
    deduped_headers: list[tuple[int, int]] = []
    last_seen_line_for_race: dict[int, int] = {}
    for race_no, idx in race_headers:
        prev = last_seen_line_for_race.get(race_no)
        if prev is None or idx - prev > 20:
            deduped_headers.append((race_no, idx))
            last_seen_line_for_race[race_no] = idx

    races: list[dict[str, Any]] = []
    LOGGER.info("total races detected: %s", len(deduped_headers))

    for h_idx, (race_number, start_idx) in enumerate(deduped_headers):
        end_idx = deduped_headers[h_idx + 1][1] if h_idx + 1 < len(deduped_headers) else len(lines)
        race_lines = lines[start_idx:end_idx]
        context = race_lines[:100]
        LOGGER.info("race %s detected at line %s", race_number, start_idx + 1)
        LOGGER.info("first 100 lines around race %s heading:\n%s", race_number, "\n".join(context))

        race = {"race_number": race_number, "race_name": f"Race {race_number}", "horses": []}

        table_lines = _extract_runner_table_lines(race_lines, race_number)
        LOGGER.info("race %s raw candidate runner lines:\n%s", race_number, "\n".join(table_lines) if table_lines else "(none)")

        runner_line_indexes = [i for i, ln in enumerate(race_lines) if ln.strip() in set(table_lines)]
        for idx_pos, local_line_idx in enumerate(runner_line_indexes):
            line = race_lines[local_line_idx].strip()

            number_match = RUNNER_LINE_RE.match(line)
            if not number_match:
                LOGGER.info("race %s rejected line: %s | reason=no saddlecloth match", race_number, line)
                continue

            number = int(number_match.group(1))
            name = _extract_horse_name(line)
            if not name:
                LOGGER.info("race %s rejected line: %s | reason=invalid parsed horse name", race_number, line)
                continue

            LOGGER.info("race %s accepted runner: %s %s", race_number, number, name)
            age, sex = _extract_age_sex(line)
            current_weight, claim, apprentice_min, adjusted = _extract_current_weights(line)

            block_start = local_line_idx
            block_end = runner_line_indexes[idx_pos + 1] if idx_pos + 1 < len(runner_line_indexes) else len(race_lines)
            horse_block = "\n".join(race_lines[block_start:block_end])
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
        LOGGER.info("race %s horses detected: %s", race_number, len(race["horses"]))
        if race["horses"]:
            pretty = "\n".join(f"{h['number']} {h['name']}" for h in race["horses"])
            LOGGER.info("Race %s extracted runners:\n%s", race_number, pretty)
            races.append(race)

    races.sort(key=lambda r: r["race_number"])
    LOGGER.info("sorted race numbers: %s", [r["race_number"] for r in races])
    horse_count = sum(len(r["horses"]) for r in races)
    LOGGER.info("Extracted %s races and %s horses from guide", len(races), horse_count)
    if not races or horse_count == 0:
        raise ValueError("Parser extracted no races or horses from the PDF text.")
    return races
