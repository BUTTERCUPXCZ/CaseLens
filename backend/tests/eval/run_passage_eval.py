"""Runs the real Gemini passage picker + checker on the hand-marked decisions and compares its picks with the hand-marked
Facts and Issue (`tests/fixtures/digest/gold.json`). The AI only points at paragraph numbers; what is measured is whether
the paragraphs it points at are where the Court really states the part.

    python -m tests.eval.run_passage_eval [decision.html ...]

Needs GEMINI_API_KEY in backend/.env. Costs a few cents. Results: tests/eval/results/passages-<prompt>.json
Facts: "right" = the paragraphs the box SHOWS (the first four of the pick) are all inside the hand-marked Facts; `all_inside_gold` also says whether the whole range is. Issue: "overlap" = it includes a hand-marked issue
paragraph. "wrong" = a pick that is not inside / does not overlap, or any pick where the Court states no issue.
Doctrine has no hand-marked answer: its picks are stored and read by a person.
"""
import json
import sys
import time
from pathlib import Path

from caselens.application.use_cases.suggest_court_passages import SuggestCourtPassages
from caselens.domain.errors import AiUnavailableError
from caselens.domain.digest import SectionKind
from caselens.domain.services.heading_sections import HeadingSections
from caselens.domain.services.passage_suggester import IssueFinder
from caselens.domain.services.ruling_locator import RulingLocator
from caselens.infrastructure.ai.gemini_answerer import _GeminiCall
from caselens.infrastructure.ai.gemini_passages import PASSAGE_PROMPT_VERSION, GeminiPassageChecker, GeminiPassagePicker
from caselens.infrastructure.config import get_settings
from tests.helpers import digest_paragraphs

GOLD = json.loads((Path(__file__).resolve().parent.parent / "fixtures" / "digest" / "gold.json").read_text())


def span(ranges):
    return {i for first, last in (ranges or []) for i in range(first, last + 1)}


def main(names: list[str]) -> None:
    settings = get_settings()
    call = _GeminiCall(settings)
    use_case = SuggestCourtPassages(GeminiPassagePicker(settings, call), GeminiPassageChecker(settings, call))
    out: dict = {"prompt": PASSAGE_PROMPT_VERSION, "picker": settings.gemini_writer_model, "checker": settings.gemini_checker_model, "cases": {}}
    tally = {"facts": [0, 0, 0], "issues": [0, 0, 0]}  # right, wrong, abstained

    for name in names:
        paragraphs = digest_paragraphs(name)
        start, ruling = HeadingSections.body_start(paragraphs), RulingLocator().locate(paragraphs)
        # Only what production would ask the AI: a part the Court labelled, or the rules found, is never asked.
        labelled = HeadingSections().find(paragraphs)
        settled = {"facts": SectionKind.FACTS in labelled, "issues": SectionKind.ISSUES in labelled or IssueFinder().find(paragraphs, start, ruling.first if ruling else None) is not None}
        wanted = [key for key in ("facts", "issues", "doctrine") if not settled.get(key, False)]
        try:
            result = use_case.execute(wanted, paragraphs, start, ruling)
        except AiUnavailableError as exc:
            print(f"{name}: AI unavailable ({exc})")
            continue
        gold = GOLD[name]
        row = {}
        for key in ("facts", "issues"):
            found = result.found.get(key)
            if key not in wanted:
                row[key] = {"verdict": "not asked (the Court's heading or a rule found it)"}
                continue
            if found is None:
                tally[key][2] += 1
                row[key] = {"verdict": "abstained", "why": result.not_found.get(key)}
                continue
            picked = set(found.range.indexes())
            truth = span(gold[key])
            shown = set(list(found.range.indexes())[:4])  # the box shows the first four paragraphs of a long pick
            right = bool(truth) and (shown <= truth if key == "facts" else bool(picked & truth))
            tally[key][0 if right else 1] += 1
            row[key] = {"verdict": "right" if right else "WRONG", "picked": [found.range.first, found.range.last], "gold": gold[key], "all_inside_gold": picked <= truth if key == "facts" else None,
                        "starts": paragraphs[found.range.first][:140]}
        d = result.found.get("doctrine")
        row["doctrine"] = {"picked": [d.range.first, d.range.last], "text": " ".join(paragraphs[i] for i in d.range.indexes())[:700]} if d else {"abstained": result.not_found.get("doctrine")}
        out["cases"][name] = row
        print(f"{name:22} facts={row['facts']['verdict'][:9]:9} issues={row['issues']['verdict'][:9]:9} doctrine={'picked' if d else ('none' if 'doctrine' in wanted else '-')}", flush=True)
        time.sleep(1)

    out["tally_right_wrong_abstained"] = tally
    path = Path(__file__).resolve().parent / "results" / f"passages-{PASSAGE_PROMPT_VERSION}.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("\nright / wrong / abstained:", tally, "\nsaved", path)


if __name__ == "__main__":
    main(sys.argv[1:] or [k for k in GOLD if not k.startswith("_")])
