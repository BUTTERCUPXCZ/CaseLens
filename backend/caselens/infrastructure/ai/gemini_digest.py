"""Gemini as the digest writer: the client's prompt, one call, every section as cited sentences."""
from caselens.application.ports.ai import DigestRequest, DigestWriter
from caselens.domain.digest import AnswerSentence
from caselens.domain.digest_v2 import DigestBlock, DigestDraft, Section
from caselens.infrastructure.ai.calls import CHECKER, REPAIR, WRITER
from caselens.infrastructure.ai.gemini_answerer import _GeminiCall, strip_inline_citations
from caselens.infrastructure.ai.prompts.digest_v1 import CLIENT_PROMPT, DIGEST_PROMPT_VERSION, DIGEST_VERSION, SYSTEM_RULES
from caselens.infrastructure.config import Settings

# Short field names: a digest has 100 to 180 sentences, and the names are repeated in every one of them (output tokens are what a
# digest costs). t = text, c = cites, k = key (bold); a block: h = heading, l = a bullet list, s = its sentences. `_field` below still
# reads the long names, so an answer in the older shape is not lost.
_SENTENCE = {
    "type": "object",
    "properties": {"t": {"type": "string"}, "c": {"type": "array", "items": {"type": "string"}}, "k": {"type": "boolean"}},
    "required": ["t", "c"],
}
_BLOCK = {
    "type": "object",
    "properties": {
        "h": {"type": "string", "nullable": True},
        "l": {"type": "boolean"},
        "s": {"type": "array", "items": _SENTENCE},
    },
    "required": ["s"],
}
_SCHEMA = {
    "type": "object",
    "properties": {section.value: {"type": "array", "items": _BLOCK} for section in Section},
}
_SYSTEM = f"{SYSTEM_RULES}\n\n--- THE STUDENT'S OWN INSTRUCTIONS (follow them within the rules above) ---\n{CLIENT_PROMPT}"


def _render(request: DigestRequest) -> str:
    lines = [f"CASE: {request.case_line}"]
    if request.subject:
        lines.append(f"Topic: {request.subject}")
    if request.scope:
        lines.append(
            f"TOPIC SCOPE (the student asked for this): {request.scope}\n"
            "Focus the Doctrine, the Issue, the Ratio Decidendi and the Topic Explained on this topic, as the decision deals with it. "
            "Keep the Facts and the Ruling complete. If the decision does not deal with this topic, say so plainly in the Doctrine "
            "and do not stretch the passages to fit it. Every rule above still applies."
        )
    if request.opinions:
        lines.append("SEPARATE OPINIONS GIVEN BELOW: " + "; ".join(request.opinions))
    passages = "\n\n".join(f"[{p.id}] {p.text}" for p in request.sources)
    return "\n".join(lines) + "\n\nPASSAGES (the whole decision):\n" + passages


_REPAIR_RULES = """You are fixing sentences of a case digest that a checker rejected. You are given the decision's numbered passages (the only truth)
and the rejected sentences, each with its section and the checker's reason. For each rejected sentence (they are numbered) write ONE replacement, giving its number in "number", that says
only what the passages say (drop the part the checker said is not supported; keep what is supported; use the Court's own terms for legal
concepts), with the ids of the passages it rests on in "cites". Cite only passages given above. If the passages do not support any version of it, leave it out.
Never write an id inside the text. Keep the plain, simple language."""
_REPAIR_SCHEMA = {
    "type": "object",
    "properties": {
        "sentences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"number": {"type": "integer"}, "text": {"type": "string"}, "cites": {"type": "array", "items": {"type": "string"}}},
                "required": ["number", "text", "cites"],
            },
        }
    },
    "required": ["sentences"],
}


class _Repair:
    def repair(self, request: DigestRequest, failed: list[tuple[str, str, str, tuple[str, ...]]]) -> dict[int, AnswerSentence]:
        """`request.sources` holds only the passages near the failed sentences (see `WriteCaseDigest._evidence`), not the decision."""
        rejected = "\n".join(
            f"{n}. [{section}] {text}\n   it cited: {', '.join(cites) or 'nothing'}\n   reason it was rejected: {reason}"
            for n, (section, text, reason, cites) in enumerate(failed)
        )
        passages = "\n\n".join(f"[{p.id}] {p.text}" for p in request.sources)
        prompt = f"CASE: {request.case_line}\n\nPASSAGES (the parts of the decision these sentences rely on):\n{passages}\n\nREJECTED SENTENCES TO FIX:\n{rejected}"
        data = self._call.json(REPAIR, _REPAIR_RULES, prompt, _REPAIR_SCHEMA)  # the repair role: the writer's model, no thinking first
        fixed: dict[int, AnswerSentence] = {}
        for item in data.get("sentences", []):
            text, inline = strip_inline_citations(item["text"])
            cites = tuple(dict.fromkeys([*item.get("cites", []), *inline]))
            if text.strip() and isinstance(item.get("number"), int) and 0 <= item["number"] < len(failed):
                fixed[item["number"]] = AnswerSentence(text=text, cites=cites)
        return fixed



def _field(item: dict, short: str, long: str):
    """A field by its short name, or by the long name an older answer used."""
    return item[short] if short in item else item.get(long)


class GeminiDigestWriter(_Repair, DigestWriter):
    def __init__(self, settings: Settings, call: _GeminiCall | None = None) -> None:
        self._call = call or _GeminiCall(settings)
        self._model = WRITER  # each provider picks its own writing model
        budget = settings.case_digest_thinking_budget
        self._thinking = None if budget < 0 else budget

    def write(self, request: DigestRequest) -> DigestDraft:
        data = self._call.json(self._model, _SYSTEM, _render(request), _SCHEMA, thinking_budget=self._thinking)
        draft = DigestDraft()
        for section in Section:
            blocks = []
            for item in data.get(section.value) or []:
                sentences = []
                for raw in _field(item, "s", "sentences") or []:
                    text, inline = strip_inline_citations(_field(raw, "t", "text") or "")
                    cites = tuple(dict.fromkeys([*(_field(raw, "c", "cites") or []), *inline]))
                    if text.strip():
                        sentences.append(AnswerSentence(text=text, cites=cites, key=bool(_field(raw, "k", "key"))))
                if sentences:
                    as_list = bool(item.get("l")) or item.get("kind") == "list"
                    blocks.append(DigestBlock(tuple(sentences), (_field(item, "h", "heading") or None), as_list))
            if blocks:
                draft.sections[section] = tuple(blocks)
        return draft


__all__ = ["GeminiDigestWriter", "DIGEST_PROMPT_VERSION", "DIGEST_VERSION"]
