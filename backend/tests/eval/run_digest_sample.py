"""M0: runs the whole new digest pipeline (the client's prompt, one writer call, code checks, a second model) on one saved
decision and writes the Word file, so a person can read it against the decision and against the client's own sample.

    python -m tests.eval.run_digest_sample gr_88211_1989.html "Constitutional Law" [level]

Needs GEMINI_API_KEY in backend/.env. Costs a few cents. Output: tests/eval/results/digest-<name>.json and .docx
"""
import json
import sys
import time
from pathlib import Path

from caselens.application.use_cases.build_digest_request import OpinionText, build_digest_request
from caselens.application.use_cases.write_case_digest import WriteCaseDigest
from caselens.domain.digest_v2 import Level
from caselens.domain.services.case_names import division_name, justice_name, short_case_name, surname_only
from caselens.domain.services.heading_sections import HeadingSections
from caselens.infrastructure.ai.gemini_answerer import GeminiAnswerChecker, _GeminiCall
from caselens.infrastructure.ai.gemini_digest import DIGEST_PROMPT_VERSION, GeminiDigestWriter
from caselens.infrastructure.config import get_settings
from caselens.infrastructure.docx_digest_export import DigestHeader, DocxCaseDigestExporter
from caselens.infrastructure.lawphil.html_decoding import decode_html
from caselens.infrastructure.lawphil.html_parser import LawphilCaseParser
from caselens.infrastructure.lawphil.separate_opinions import parse_separate_opinions
from tests.helpers import FIXTURES

MAX_PARAGRAPH_CHARS = 2500


def main(name: str, subject: str, level: Level) -> None:
    settings = get_settings()
    html = decode_html((FIXTURES / "digest" / name).read_bytes(), "text/html")
    case = LawphilCaseParser().parse(html, f"https://lawphil.net/x/{name}")
    opinions = [OpinionText(o.author, o.kind, o.paragraphs) for o in parse_separate_opinions(html)]
    request = build_digest_request(case, opinions, subject)
    chars = sum(len(p.text) for p in request.sources)
    print(f"{len(request.sources)} passages, {chars:,} characters, {len(opinions)} separate opinions")
    print("case line:", request.case_line)

    call = _GeminiCall(settings)
    use_case = WriteCaseDigest(GeminiDigestWriter(settings, call), GeminiAnswerChecker(settings, call))
    started = time.time()
    result = use_case.execute(request)
    seconds = time.time() - started
    usage = getattr(call, "usage", {})
    print(f"written {result.written}, repaired {result.repaired}, kept {result.kept}, dropped {len(result.dropped)}, {seconds:.0f} s, tokens {usage}")

    short = name.removesuffix(".html")
    out = Path(__file__).resolve().parent / "results"
    paragraphs = case.full_text.split("\n")
    start = HeadingSections.body_start(paragraphs) or 0
    ponente = justice_name(paragraphs[start - 1].strip().rstrip(":")) if start else None
    header = DigestHeader(surname_only(short_case_name(case.title)), f"G.R. No. {case.gr_no}, {case.decision_date:%B %d, %Y} ({division_name(case.division)})", subject, ponente)
    (out / f"digest-{short}.docx").write_bytes(DocxCaseDigestExporter().export(header, result.draft, level))
    (out / f"digest-{short}.json").write_text(json.dumps({
        "prompt": DIGEST_PROMPT_VERSION, "writer": settings.gemini_writer_model, "checker": settings.gemini_checker_model,
        "seconds": round(seconds), "usage": usage, "written": result.written, "repaired": result.repaired, "kept": result.kept,
        "sections": {s.value: [{"heading": b.heading, "list": b.as_list, "sentences": [{"text": x.text, "cites": list(x.cites)} for x in b.sentences]} for b in blocks] for s, blocks in result.draft.sections.items()},
        "dropped": [{"section": d.section.value, "text": d.text, "reason": d.reason} for d in result.dropped],
    }, indent=1, ensure_ascii=False))
    print("saved", out / f"digest-{short}.docx")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], Level(sys.argv[3]) if len(sys.argv) > 3 else Level.FULL)
