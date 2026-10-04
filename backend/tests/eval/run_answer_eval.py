"""Runs the real Gemini writer + checker on saved decisions and stores every answer, so each can be read
against the decision's own text (the pass mark is a human reading, not the model's opinion of itself).

    python -m tests.eval.run_answer_eval [decision.html ...]

Needs GEMINI_API_KEY in backend/.env. Costs a few cents per run. Results: tests/eval/results/answers-<prompt>.json
"""
import json
import sys
import time
from pathlib import Path

from caselens.application.ports.ai import AnswerRequest
from caselens.application.use_cases.answer_case_question import AnswerCaseQuestion, decision_sources
from caselens.domain.digest import SourcePassage
from caselens.domain.errors import AiUnavailableError
from caselens.domain.services.heading_sections import HeadingSections
from caselens.domain.services.ruling_locator import RulingLocator
from caselens.infrastructure.ai.gemini_answerer import PROMPT_VERSION, GeminiAnswerChecker, GeminiAnswerWriter, _GeminiCall
from caselens.infrastructure.config import get_settings
from tests.helpers import digest_paragraphs

TOPIC = "Explain the topic of this case accurately, in plain words."
WHY = "Why does this case matter? Say what the Court decided and what follows from it."

# The reviewer's own passage from the user's video (Part Nine, Legislative power, Section 1), for GR 180046 only.
REVIEWER_180046 = SourcePassage(
    "R1",
    "I. Legislative power Section 1: The legislative power shall be vested in the Congress of the Philippines which shall "
    "consist of a Senate and a House of Representatives, except to the extent reserved to the people by the provision on "
    "initiative and referendum. Plenary Nature: Legislative power is generally considered plenary or absolute. This means "
    "Congress has the broad authority to pass laws on any subject matter it deems necessary, provided it does not run afoul "
    "of the restrictions set by the Constitution.",
)

DEFAULT = [
    "gr_180046_2009.html", "gr_148263_2009.html", "gr_173931_2009.html", "gr_175483_2015.html",
    "gr_221664_2022.html", "gr_71681_1989.html", "gr_119935_1997.html", "gr_161811_2006.html",
]


def main(names: list[str]) -> None:
    settings = get_settings()
    call = _GeminiCall(settings)
    use_case = AnswerCaseQuestion(GeminiAnswerWriter(settings, call), GeminiAnswerChecker(settings, call))
    out: dict = {"prompt": PROMPT_VERSION, "writer": settings.gemini_writer_model, "checker": settings.gemini_checker_model, "cases": {}}

    for name in names:
        paragraphs = digest_paragraphs(name)
        start = HeadingSections().body_start(paragraphs)
        ruling = RulingLocator().locate(paragraphs)
        sources = decision_sources(paragraphs, start, ruling.last)
        extra: list[SourcePassage] = [REVIEWER_180046] if name == "gr_180046_2009.html" else []
        questions = [("topic", TOPIC), ("why_it_matters", WHY)]
        record = {}
        for key, question in questions:
            began = time.time()
            try:
                answer = use_case.answer(AnswerRequest(question, tuple(extra) + tuple(sources)))
            except AiUnavailableError as exc:
                record[key] = {"error": str(exc)}
                print(f"{name} {key}: ERROR {exc}", flush=True)
                continue
            record[key] = {
                "seconds": round(time.time() - began, 1),
                "sentences": [{"text": s.text, "cites": list(s.cites)} for s in answer.sentences],
                "dropped": [{"text": d.text, "reason": d.reason} for d in answer.dropped],
            }
            print(f"{name} {key}: kept {len(answer.sentences)}, dropped {len(answer.dropped)} ({record[key]['seconds']} s)", flush=True)
        out["cases"][name] = record

    target = Path(__file__).parent / "results" / f"answers-{PROMPT_VERSION}.json"
    target.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("saved", target)


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
