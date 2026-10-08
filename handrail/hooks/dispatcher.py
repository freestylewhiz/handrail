"""Retryable hooks share the durable outbox; handler keys provide deduplication."""
from handrail.shared.errors import HandrailError


class HookDispatcher:
    def __init__(self, store):
        self.store = store
        self.handlers = {}

    def register(self, topic, handler):
        if topic in self.handlers:
            raise HandrailError("HOOK_DUPLICATE", f"Handler already registered: {topic}")
        self.handlers[topic] = handler

    def dispatch(self, topic=None):
        with self.store.exclusive("outbox-delivery"):
            return self._dispatch(topic)

    def _dispatch(self, topic):
        results = []
        for item in self.store.outbox(topic):
            if item["status"] == "complete" or item["topic"] not in self.handlers:
                continue
            # The handler must reconcile a previous unknown/sending delivery.
            with self.store.transaction() as tx:
                tx.delivery(item["key"], "sending")
            try:
                result = self.handlers[item["topic"]](item)
            except HandrailError as exc:
                status = "unknown" if exc.uncertain else "failed"
                result = exc.as_dict()
            except Exception as exc:
                status = "unknown"
                result = {"error": "HOOK_FAILED", "type": type(exc).__name__}
            else:
                status = "complete"
            with self.store.transaction() as tx:
                tx.delivery(item["key"], status, result)
            results.append({"key": item["key"], "status": status, "result": result})
            if status != "complete":
                break  # Preserve event order after an uncertain or failed write.
        return results
