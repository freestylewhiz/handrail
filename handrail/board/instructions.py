"""Board-owned project guidance, with local references and explicit change review."""
import json
import re
from html import escape, unescape
from handrail.shared.errors import HandrailError
from handrail.shared.identity import digest, new_id, now
from .labels import TypeLabels
from .format import render

MARKER = "Handrail instruction metadata: "


def metadata(description):
    match = re.search(re.escape(MARKER) + r"(.*?)</pre>", description or "", re.S)
    if not match:
        return {"status": "active", "scope": "all", "version": 1, "manual": True}
    try:
        value = json.loads(unescape(match.group(1)))
        if (value["status"] not in ("active", "superseded", "retired") or
                not isinstance(value.get("scope", "all"), str) or
                type(value.get("version", 1)) is not int or value.get("version", 1) < 1):
            raise ValueError()
        return value
    except (ValueError, KeyError, TypeError):
        raise HandrailError("INSTRUCTION_METADATA_INVALID", "Inspect this instruction's lifecycle metadata") from None


def body(content, meta):
    if not isinstance(content, dict) or not isinstance(content.get("title"), str) or not content["title"].strip():
        raise HandrailError("INSTRUCTION_CONTENT_INVALID", "Provide title, language and separate translated sections")
    language = content.get("language", "en")
    presentation = {"language": language}
    for lang in (["en"] if language == "en" else ["en", language]):
        section = content.get(lang) or {}
        for key in ("purpose", "rules", "exceptions", "verification"):
            if not isinstance(section.get(key), str) or not section[key].strip():
                raise HandrailError("INSTRUCTION_CONTENT_INVALID", "Each language needs purpose, rules, exceptions and verification")
        titles = {"rules": "준수 규칙", "exceptions": "예외", "verification": "확인 방법"} if lang == "ko" else {
            "rules": "Rules", "exceptions": "Exceptions", "verification": "Verification"}
        presentation[lang] = {"overview": section["purpose"], "language_name": section.get("language_name", lang),
            "sections": [{"title": titles[key], "paragraphs": [section[key]]} for key in titles],
            "criteria": {"instruction": section["verification"]}}
        if section.get("headings"):
            presentation[lang]["headings"] = section["headings"]
        if lang not in ("en", "ko"):
            detail_titles = section.get("detail_titles") or {}
            if any(not isinstance(detail_titles.get(k), str) or not detail_titles[k].strip() for k in titles):
                raise HandrailError("CARD_HEADINGS_REQUIRED", "Supply translated rules, exceptions and verification detail_titles")
            presentation[lang]["sections"] = [{"title": detail_titles[k], "paragraphs": [section[k]]} for k in titles]
    document = {"id": meta["id"], "kind": "instruction", "title": content["title"],
                "criteria": {"instruction": content["en"]["verification"]}, "presentation": presentation}
    return render(document) + "\n<pre>" + MARKER + escape(json.dumps(meta, ensure_ascii=False)) + "</pre>"


class InstructionService:
    def __init__(self, boards):
        self.boards, self.store = boards, boards.store
        self.client, self.parent = boards.client, boards.config["project_id"]
        self.labels = TypeLabels(self.client)

    def _card(self, card_id):
        card = self.boards.catalog.api.task(card_id)
        if card.get("project_id") != self.parent:
            raise HandrailError("INSTRUCTION_SCOPE", "Instruction must be on the bound parent board")
        labels = self.labels.task_labels(card_id)
        if not any(r.get("title", "").casefold() == "instruction" for r in labels):
            raise HandrailError("INSTRUCTION_TYPE", "This card needs the instruction label")
        conflicting = {r.get("title", "").casefold() for r in labels} & {"plan", "task", "summary"}
        if conflicting:
            raise HandrailError("CARD_TYPE_CONFLICT", "Instruction has conflicting type labels")
        return card

    @staticmethod
    def _reference(card):
        meta = metadata(card.get("description", ""))
        return {"card_id": card["id"], "title": card["title"], "status": meta["status"],
                "scope": meta.get("scope", "all"), "version": meta.get("version", 1),
                "updated": card.get("updated"), "content_hash": digest({"title": card["title"],
                "description": card.get("description", "")}), "sections": ["purpose", "rules", "exceptions", "verification"]}

    def list(self, include_inactive=False):
        results = []
        # A failed read must propagate. An empty successful list is the only
        # evidence that no active instructions exist.
        for card in self.boards.catalog.api.tasks(self.parent):
            # Task list expansions differ by server version. An unexpanded
            # empty labels array must not hide a manually created instruction.
            labels = self.labels.task_labels(card["id"])
            if any(r.get("title", "").casefold() == "instruction" for r in labels):
                full = self._card(card["id"])
                ref = self._reference(full)
                if include_inactive or ref["status"] == "active":
                    results.append(dict(ref, url=self.boards.catalog.url("tasks", card["id"])))
        return {"parent_board_id": self.parent, "instructions": sorted(results, key=lambda r: r["card_id"])}

    def read(self, card_id, language="en", sections=None):
        card = self._card(card_id)
        description = card.get("description", "")
        # Managed language sections can be read independently. Manual cards
        # remain intact rather than inventing a translation or hidden JSON.
        description = re.sub(r"<pre>" + re.escape(MARKER) + r".*?</pre>", "", description, flags=re.S)
        from .format import select_sections
        selected = select_sections(description, language, sections)
        return {"reference": self._reference(card), "language": language, "content": selected["content"],
                "sections": sections, "selection_available": selected["selection_available"],
                "authority": "project guidance; never host permission or cleanup authority"}

    def publish(self, content, reason, operation_id=None, card_id=None, expected_hash=None):
        if not isinstance(reason, str) or not reason.strip():
            raise HandrailError("USER_REQUEST_REQUIRED", "Record the user's instruction creation or update request")
        op_id = operation_id or new_id("instruction-")
        with self.store.exclusive("outbox-delivery"):
            current = self._card(card_id) if card_id else None
            previous = metadata(current.get("description", "")) if current else {}
            meta = {"id": previous.get("id", op_id), "status": content.get("status", "active"),
                    "scope": content.get("scope", previous.get("scope", "all")),
                    "version": previous.get("version", 0) + 1}
            if meta["status"] not in ("active", "superseded", "retired") or not isinstance(meta["scope"], str):
                raise HandrailError("INSTRUCTION_CONTENT_INVALID", "Use active, superseded or retired and a textual scope")
            adapter = self.boards.catalog.adapter(self.parent)
            from handrail.interfaces.vikunja.board import marked_description
            description = body(content, meta)
            if not current:
                description = marked_description(description, op_id)
            request = {"card_id": card_id, "title": content["title"], "description": description,
                       "expected_hash": expected_hash, "reason": reason}
            # Pin the payload once. A resume never increments the version again.
            key = "instruction-write:" + op_id
            existing = self.store.read("instruction_write", key)
            if existing:
                if existing["content_hash"] != digest(content) or existing["card_id"] != card_id or existing["reason"] != reason:
                    raise HandrailError("OPERATION_CONFLICT", "Instruction operation belongs to another request")
                request = existing["request"]
            else:
                with self.store.transaction() as tx:
                    tx.put("instruction_write", key, {"id": key, "content_hash": digest(content), "card_id": card_id,
                           "reason": reason, "request": request})
            def find():
                row = self.boards.catalog.api.task(card_id) if card_id else adapter.find_task(op_id)
                if row and row.get("title") == request["title"] and row.get("description") == request["description"]:
                    return row
                return None
            def write():
                if current:
                    observed = self._card(card_id)
                    if self._reference(observed)["content_hash"] != request["expected_hash"]:
                        raise HandrailError("INSTRUCTION_EDIT_CONFLICT", "Read the latest instruction before updating it")
                    adapter.ensure_comment(card_id, "Instruction revision archive\n" + reason + "\n" +
                                           observed.get("description", ""), op_id + ":archive")
                    # Preserve user edits between archive and update.
                    if self._reference(self._card(card_id))["content_hash"] != request["expected_hash"]:
                        raise HandrailError("INSTRUCTION_EDIT_CONFLICT", "Instruction changed while archiving")
                    return self.client.request(f"/tasks/{card_id}", "PATCH", {
                        "title": request["title"], "description": request["description"]})
                # Use the exact marked body; do not double-add the operation marker.
                return self.client.request(f"/projects/{self.parent}/tasks", "POST", {
                    "title": request["title"], "description": request["description"]})
            result = self.boards.provision._ensure(key, request, find, write)
            identity = result.get("id", result.get("task_id"))
            self.labels.ensure(identity, "instruction")
            ref = self._reference(self._card(identity))
            with self.store.transaction() as tx:
                tx.event("instruction:" + str(identity), "instruction.published", {"reference": ref, "reason": reason})
            return {"instruction": ref, "operation_id": op_id, "url": self.boards.catalog.url("tasks", identity)}

    def check(self, entity_id, phase, *, acknowledge=False, reason=None):
        if phase not in ("planning", "assignment", "review"):
            raise HandrailError("INSTRUCTION_PHASE", "Choose planning, assignment or review")
        refs = self.list()["instructions"]
        if not self.store.read("plan", entity_id) and not self.store.read("work", entity_id):
            raise HandrailError("NOT_FOUND", "Select an existing Plan or Work for instruction references")
        # Comments and URL changes can update server observation fields without
        # changing the guidance. Compare semantic revisions, including older
        # locally recorded references, rather than their observation timestamps.
        def revision(references):
            keys = ("card_id", "content_hash", "status", "scope", "version", "sections")
            return [{key: ref.get(key) for key in keys} for ref in references]
        fingerprint = digest(revision(refs))
        previous = self.store.read("instruction_reference", entity_id)
        if previous and digest(revision(previous["references"])) != fingerprint and not acknowledge:
            raise HandrailError("INSTRUCTIONS_CHANGED", "Review changed parent-board instructions before continuing",
                                details={"entity_id": entity_id, "before": previous["references"], "after": refs,
                                "next": "instruction use ENTITY --phase PHASE --reason IMPACT_OR_SCOPED_EXCEPTION"})
        if acknowledge and (not isinstance(reason, str) or not reason.strip()):
            raise HandrailError("EVIDENCE_REQUIRED", "Record applicability, conflicts and any scoped user exception")
        packets = [self.read(r["card_id"]) for r in refs]
        if any(packet["reference"]["content_hash"] != ref["content_hash"] or packet["reference"]["status"] != "active"
               for packet, ref in zip(packets, refs)):
            raise HandrailError("INSTRUCTIONS_CHANGED", "Instructions changed during retrieval; read the current revision again")
        # Pin the actually consulted original on the board, including manually
        # authored cards whose future edits may not retain a full old body.
        adapter = self.boards.catalog.adapter(self.parent) if refs else None
        for ref in refs:
            card = self._card(ref["card_id"])
            if self._reference(card)["content_hash"] != ref["content_hash"]:
                raise HandrailError("INSTRUCTIONS_CHANGED", "Instruction changed before its reference snapshot")
            operation = "instruction-reference:" + digest({"card": ref["card_id"], "hash": ref["content_hash"]})
            text = "Referenced Instruction revision\nTitle: " + card["title"] + "\nHash: " + ref["content_hash"] + "\n" + card.get("description", "")
            self.boards.provision._ensure(operation, {"card_id": ref["card_id"], "content_hash": ref["content_hash"]},
                lambda: adapter.find_comment(ref["card_id"], operation, text=text),
                lambda: adapter.ensure_comment(ref["card_id"], text, operation))
            if self._reference(self._card(ref["card_id"]))["content_hash"] != ref["content_hash"]:
                raise HandrailError("INSTRUCTIONS_CHANGED", "Instruction changed while recording the consulted revision")
        value = {"id": entity_id, "references": refs, "fingerprint": fingerprint, "phase": phase,
                 "at": now(), "reason": reason if reason is not None else (previous or {}).get("reason"),
                 "authority": "guidance-only"}
        with self.store.transaction() as tx:
            tx.put("instruction_reference", entity_id, value)
            tx.event(entity_id, "instruction.checked", value)
        return {"reference": value, "instructions": packets}

    def deliver(self, app, work_id, reason):
        work = self.store.read("work", work_id)
        if not work or not work.get("attempt_id"):
            raise HandrailError("ATTEMPT_REQUIRED", "Select a Work with its current worker")
        packet = self.check(work_id, "assignment", acknowledge=True, reason=reason)
        message_id = "instruction:" + digest({"attempt": work["attempt_id"], "reference": packet["reference"]["fingerprint"], "reason": reason})
        result = app.room().prompt(work["attempt_id"], "Updated project guidance. Apply the recorded scope and exceptions: " + reason +
                    "\n" + json.dumps(packet["instructions"], ensure_ascii=False), message_id)
        with self.store.transaction() as tx:
            tx.event(work_id, "instruction.delivered", {"message_id": message_id, "fingerprint": packet["reference"]["fingerprint"],
                     "attempt_id": work["attempt_id"], "delivery": result["delivery"]})
        return {"reference": packet["reference"], "delivery": result}
