"""Keep the static landing/play clue data in sync with the authored JSON."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
clues = json.loads((root / "clues/race-01.json").read_text())["clues"]
for name in ("play.html", "index.html"):
    fields = dict(t="title", q="riddle", u="source_url", f="answer_form")
    if name == "play.html":
        fields.update(p="answer_pattern", h="hint")
    data = [{key: clue[field] for key, field in fields.items()} for clue in clues]
    declaration = "const CLUES = " + json.dumps(data, ensure_ascii=False) + ";"
    target = root / "web" / name
    text = target.read_text()
    text, count = re.subn(r"^const CLUES = .*;$", lambda _: declaration, text, flags=re.M)
    if count != 1:
        raise ValueError(f"expected one CLUES declaration in {target}")
    target.write_text(text)
    print(f"Synced {name}: {len(data)} clues")
