from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.parser import parse_races_from_text


def test_parse_only_official_runner_table():
    text = """
Race 1
No / Last 10 / Horse / Trainer / Jockey / Barrier / Weight / Hcp Rating
1 123 LAST DANDELION 3 56.0kg 62
2 45 TRUE HORSE 4 55.0kg 60

2 of 8
4 year old bay gelding Sire: TEST Dam: TEST
Trainer: X Jockey: Y
"""
    races = parse_races_from_text(text)
    assert len(races) == 1
    names = [h["name"] for h in races[0]["horses"]]
    assert names == ["LAST DANDELION", "TRUE HORSE"]


def test_skip_race_when_runner_table_missing():
    text = """
Race 1
1 of 8
4 year old bay gelding Sire: TEST Dam: TEST
"""
    try:
        parse_races_from_text(text)
        assert False, "Expected ValueError when no horses are extracted"
    except ValueError:
        assert True
