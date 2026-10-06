import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace

from caselens.application.ports.ai import AnswerChecker, DigestRequest, DigestWriter
from caselens.domain.digest import AnswerSentence, Verdict
from caselens.domain.digest_v2 import DigestBlock, DigestDraft, Section
from caselens.domain.services.answer_validator import AnswerValidator

logger = logging.getLogger(__name__)

_CHECK_BATCH = 25  # sentences judged per call: a short list is judged more carefully than a long one
_CHECKS_AT_ONCE = 6  # the groups do not depend on each other, so they are judged at the same time (one group's wait, not all of them)
# An honest "the decision does not say" has nothing to cite. It is allowed only if it makes no other claim.
_NOT_STATED = re.compile(
    r"\b(?:not|never) (?:stated|said|discussed|addressed|mentioned|given|specified|shown|explained)\b|\bdoes not (?:say|state|discuss|address|mention|specify)\b|"
    r"\bno (?:separate |dissenting )?opinions?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DroppedLine:
    section: Section
    text: str
    reason: str


@dataclass
class DigestResult:
    draft: DigestDraft
    dropped: list[DroppedLine] = field(default_factory=list)
    written: int = 0  # sentences the writer produced
    repaired: int = 0  # sentences rewritten in the repair pass

    @property
    def kept(self) -> int:
        return len(self.draft.sentences())


class WriteCaseDigest:
    """Writes the whole digest in the client's format, then lets nothing through that is not backed by the decision.

    The writer drafts every section in one call. Then, for every sentence: (1) the paragraphs it cites must exist, and any number or
    name in it must be in them (code); (2) a second model, shown only that sentence and its cited paragraphs, must say "supported".
    Whatever fails is dropped and recorded; a section left with nothing stays empty. Nothing is filled in to look complete.
    """

    def __init__(self, writer: DigestWriter, checker: AnswerChecker, validator: AnswerValidator | None = None, *, repair: bool = True) -> None:
        self._repair = repair
        self._writer = writer
        self._checker = checker
        self._validator = validator or AnswerValidator()

    def execute(self, request: DigestRequest) -> DigestResult:
        sources = {source.id: source for source in request.sources}
        draft = self._writer.write(request)
        result = DigestResult(DigestDraft(), written=len(draft.sentences()))

        # 1 and 2: the code checks, then the second model
        positions = [(section, b, i, sentence) for section, blocks in draft.sections.items() for b, block in enumerate(blocks) for i, sentence in enumerate(block.sentences)]
        verdicts: dict[tuple[Section, int, int], AnswerSentence] = {}
        failed: list[tuple[tuple[Section, int, int], AnswerSentence, str]] = []
        self._judge(positions, sources, verdicts, failed)

        # 3. one repair pass: the writer rewrites what failed so it says only what its paragraphs say; a rewrite faces the same checks
        if failed and self._repair:
            rewrites = self._writer.repair(request, [(key[0].value, sentence.text, reason) for key, sentence, reason in failed])
            again = [(key[0], key[1], key[2], replace(rewrites[n], key=sentence.key)) for n, (key, sentence, _) in enumerate(failed) if n in rewrites]
            self._judge(again, sources, verdicts, [])  # a rewrite that passes takes the place of the sentence it fixes; one that fails is ignored
            result.repaired = sum(1 for key, _, _ in failed if key in verdicts)
        for key, sentence, reason in failed:
            if key not in verdicts:
                result.dropped.append(DroppedLine(key[0], sentence.text, reason))

        # 4. rebuild what survived (the rewrite sits where the sentence it replaced was), in the writer's order
        for section, blocks in draft.sections.items():
            kept_blocks = []
            for b, block in enumerate(blocks):
                keep = tuple(verdicts[(section, b, i)] for i in range(len(block.sentences)) if (section, b, i) in verdicts)
                if keep:
                    kept_blocks.append(DigestBlock(keep, block.heading, block.as_list))
            if kept_blocks:
                result.draft.sections[section] = tuple(kept_blocks)
        for line in result.dropped:
            logger.info("digest: dropped %s (%s): %s", line.section.value, line.reason[:120], line.text[:160])
        return result

    def _judge(self, entries, sources, verdicts, failed) -> None:
        """Code check every sentence, then have the second model judge the ones that cite something. A sentence that passes goes
        into `verdicts`; one that does not goes into `failed` with the reason."""
        to_check = []
        for section, b, i, sentence in entries:
            problem = self._code_check(sentence, sources)
            if problem:
                failed.append(((section, b, i), sentence, problem))
            elif not sentence.cites:
                verdicts[(section, b, i)] = sentence  # an honest "not stated" has nothing to judge
            else:
                to_check.append((section, b, i, sentence))
        batches = [to_check[start : start + _CHECK_BATCH] for start in range(0, len(to_check), _CHECK_BATCH)]
        if len(batches) > 1:
            with ThreadPoolExecutor(max_workers=min(len(batches), _CHECKS_AT_ONCE), thread_name_prefix="digest-check") as pool:
                answers = list(pool.map(lambda batch: self._checker.check([e[3] for e in batch], sources), batches))
        else:
            answers = [self._checker.check([e[3] for e in batch], sources) for batch in batches]
        for batch, checks in zip(batches, answers, strict=True):  # in the original order, so the result is the same as one by one
            for (section, b, i, sentence), check in zip(batch, checks, strict=True):
                if check.verdict is Verdict.SUPPORTED:
                    verdicts[(section, b, i)] = sentence
                else:
                    failed.append(((section, b, i), sentence, f"checker: {check.verdict.value} ({check.reason[:200]})"))

    def _code_check(self, sentence: AnswerSentence, sources: dict) -> str | None:
        if not sentence.cites:
            if _NOT_STATED.search(sentence.text) and not re.search(r"\d", sentence.text):
                return None  # "The decision does not say ..." makes no claim to back
            return "no source cited"
        return self._validator.check(sentence, sources, "", numbers_anywhere=True)
