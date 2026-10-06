import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace

from caselens.application.ports.ai import AnswerChecker, DigestRequest, DigestWriter
from caselens.domain.digest import AnswerSentence, SourcePassage, Verdict
from caselens.domain.digest_v2 import DigestBlock, DigestDraft, Section
from caselens.domain.services.claim_validator import ClaimStatus, ClaimValidator

logger = logging.getLogger(__name__)

CHECK_RISKY_AND_KEY = "risky_and_key"  # the second model judges only what code flags, plus the bold key sentences
CHECK_ALL = "all"  # the second model judges every cited sentence (the way it was before; a switch to go back to)
# A digest without these cannot be trusted as a digest: if the checks leave one empty, it is marked failed, never shown as finished.
CORE_SECTIONS = (Section.DOCTRINE, Section.FACTS, Section.ISSUE, Section.RULING)
# Sections where a sentence can sound right in the paragraph's own words yet teach more than the decision says: the second model always
# judges them, even when code finds nothing wrong (like the bold key sentences).
_ALWAYS_CHECKED = frozenset({Section.TOPIC})
_CHECK_BATCH = 40  # sentences judged per call; only flagged sentences are sent, so most digests need one call
_CHECKS_AT_ONCE = 6  # the groups do not depend on each other, so they are judged at the same time
_EVIDENCE_REACH = 2  # a rewrite may also use the paragraphs this close to the ones the failed sentence cited
_OPINION_ID = re.compile(r"^O(\d+)\.(\d+)$")


@dataclass(frozen=True)
class DroppedLine:
    section: Section
    text: str
    reason: str


@dataclass
class CallCounts:
    writer: int = 0
    checker: int = 0
    repair: int = 0

    @property
    def total(self) -> int:
        return self.writer + self.checker + self.repair


@dataclass
class DigestResult:
    draft: DigestDraft
    dropped: list[DroppedLine] = field(default_factory=list)
    written: int = 0  # sentences the writer produced
    repaired: int = 0  # sentences rewritten in the repair pass
    checked: int = 0  # sentences the second model was asked about (first pass and rewrites)
    calls: CallCounts = field(default_factory=CallCounts)

    @property
    def kept(self) -> int:
        return len(self.draft.sentences())

    @property
    def missing_core(self) -> list[Section]:
        """The core sections (Doctrine, Facts, Issue, Ruling) that have nothing left after the checks."""
        return [s for s in CORE_SECTIONS if s not in self.draft.sections]


class WriteCaseDigest:
    """Writes the whole digest in the client's format, then lets nothing through that is not backed by the decision.

    The writer drafts every section in one call. Code then sorts each sentence (`ClaimValidator`): INVALID ones (a paragraph that does
    not exist, a number or name the decision never mentions) fail at once; SUSPICIOUS ones, and the bold key sentences, go to a second
    model that sees only each sentence and its cited paragraphs and must say "supported"; the rest are shown as written. What fails is
    rewritten once from its own paragraphs (not the whole decision), and a rewrite faces the same sorting. What still fails is dropped
    and recorded; a section left with nothing stays empty. Nothing is filled in to look complete.
    """

    def __init__(
        self,
        writer: DigestWriter,
        checker: AnswerChecker,
        claims: ClaimValidator | None = None,
        *,
        repair: bool = True,
        check_mode: str = CHECK_RISKY_AND_KEY,
    ) -> None:
        self._repair = repair
        self._writer = writer
        self._checker = checker
        self._claims = claims or ClaimValidator()
        self._check_all = check_mode == CHECK_ALL

    def execute(self, request: DigestRequest) -> DigestResult:
        sources = {source.id: source for source in request.sources}
        draft = self._writer.write(request)
        result = DigestResult(DigestDraft(), written=len(draft.sentences()))
        result.calls.writer += 1

        # 1. code sorts every sentence; 2. the second model judges only the ones code cannot settle
        positions = [(section, b, i, sentence) for section, blocks in draft.sections.items() for b, block in enumerate(blocks) for i, sentence in enumerate(block.sentences)]
        verdicts: dict[tuple[Section, int, int], AnswerSentence] = {}
        failed: list[tuple[tuple[Section, int, int], AnswerSentence, str]] = []
        self._judge(positions, sources, verdicts, failed, result)

        # 3. one repair pass, for the failed sentences only, from their own paragraphs; a rewrite faces the same sorting and checks
        if failed and self._repair:
            evidence = self._evidence(request, draft, failed)
            rewrites = self._writer.repair(
                replace(request, sources=evidence), [(key[0].value, sentence.text, reason, sentence.cites) for key, sentence, reason in failed]
            )
            result.calls.repair += 1
            again = [(key[0], key[1], key[2], replace(rewrites[n], key=sentence.key)) for n, (key, sentence, _) in enumerate(failed) if n in rewrites]
            self._judge(again, sources, verdicts, [], result)  # a rewrite that passes takes the place of the sentence it fixes; one that fails is ignored
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

    def _judge(self, entries, sources, verdicts, failed, result: DigestResult) -> None:
        """Sort every sentence by code; send to the second model only those code cannot settle. A sentence that passes goes into
        `verdicts`; one that does not goes into `failed` with the reason."""
        to_check = []
        for section, b, i, sentence in entries:
            claim = self._claims.classify(sentence, sources, section)
            if claim.status is ClaimStatus.INVALID:
                failed.append(((section, b, i), sentence, claim.reason))
            elif not sentence.cites or (claim.status is ClaimStatus.PASS and not sentence.key and section not in _ALWAYS_CHECKED and not self._check_all):
                verdicts[(section, b, i)] = sentence  # an honest "not stated", or a plain sentence code found nothing wrong with
            else:
                to_check.append((section, b, i, sentence))
        if not to_check:
            return
        batches = [to_check[start : start + _CHECK_BATCH] for start in range(0, len(to_check), _CHECK_BATCH)]
        result.calls.checker += len(batches)
        result.checked += len(to_check)
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

    @staticmethod
    def _evidence(request: DigestRequest, draft: DigestDraft, failed) -> tuple[SourcePassage, ...]:
        """What the repair may use: the case record and, for each failed sentence, its own cited paragraphs and the ones next to them
        (a sentence that cited nothing usable takes the paragraphs its block's other sentences cite). Never the whole decision."""
        known = {s.id for s in request.sources}
        wanted = {"C1"}
        for (section, b, _), sentence, _ in failed:
            cites = [c for c in sentence.cites if c in known]
            if not cites:
                cites = [c for s in draft.sections[section][b].sentences for c in s.cites if c in known]
            for cite in cites:
                wanted.update(_near(cite))
        return tuple(s for s in request.sources if s.id in wanted)


def _near(cite: str) -> list[str]:
    """The passage and its neighbours: P12 -> P10..P14, O2.5 -> O2.3..O2.7."""
    if cite.startswith("P") and cite[1:].isdigit():
        n = int(cite[1:])
        return [f"P{k}" for k in range(n - _EVIDENCE_REACH, n + _EVIDENCE_REACH + 1)]
    opinion = _OPINION_ID.match(cite)
    if opinion:
        o, n = int(opinion.group(1)), int(opinion.group(2))
        return [f"O{o}.{k}" for k in range(n - _EVIDENCE_REACH, n + _EVIDENCE_REACH + 1)]
    return [cite]
