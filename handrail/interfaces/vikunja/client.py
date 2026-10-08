"""Vikunja v2 HTTP client. Authenticated calls never follow redirects or retry writes."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from handrail.shared.errors import HandrailError

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class VikunjaClient:
    def __init__(self, base_url, token, allow_insecure_http=False, timeout=30):
        if not isinstance(base_url, str) or not base_url.strip():
            raise HandrailError("VIKUNJA_URL_INVALID", "base_url is required")
        parsed = urllib.parse.urlsplit(base_url.strip())
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise HandrailError("VIKUNJA_URL_INVALID", "base_url must not carry credentials, a query, or a fragment")
        if parsed.scheme == "http":
            if not allow_insecure_http:
                raise HandrailError("VIKUNJA_INSECURE_HTTP", "HTTP requires allow_insecure_http=True")
        elif parsed.scheme != "https":
            raise HandrailError("VIKUNJA_URL_INVALID", "base_url must be http or https")
        if not parsed.netloc:
            raise HandrailError("VIKUNJA_URL_INVALID", "base_url host is missing")
        if not isinstance(token, str) or not token:
            raise HandrailError("VIKUNJA_TOKEN_INVALID", "API token is required")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise HandrailError("VIKUNJA_TIMEOUT_INVALID", "timeout must be a positive number of seconds")
        self.url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
        self._token = token
        self.timeout = timeout
        self._opener = urllib.request.build_opener(_NoRedirect())

    def _fail(self, code, message, method, *, status=None, retryable=False, uncertain=None):
        writing = method in _WRITE_METHODS
        if uncertain is None:
            uncertain = bool(writing and (status is None or status >= 500 or status in {408, 429} or 300 <= status < 400))
        details = {"method": method}
        if status is not None:
            details["status"] = status
        error = HandrailError(code, message, details=details, retryable=retryable, uncertain=uncertain)
        error.__suppress_context__ = True
        raise error

    def request(self, path, method="GET", body=None):
        method = str(method or "GET").upper()
        parsed = urllib.parse.urlsplit(path if isinstance(path, str) else "")
        decoded = urllib.parse.unquote(parsed.path)
        if (not isinstance(path, str) or not parsed.path.startswith("/") or parsed.path.startswith("//")
                or parsed.scheme or parsed.netloc or ".." in decoded.split("/")):
            raise HandrailError("VIKUNJA_PATH_INVALID", "path must be API-relative", uncertain=False)
        headers = {"Accept": "application/json", "Authorization": "Bearer " + self._token}
        payload = body
        if body is not None and not isinstance(body, bytes):
            try:
                payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            except (TypeError, ValueError):
                self._fail("VIKUNJA_BODY_INVALID", "request body must be JSON", method, uncertain=False)
            headers["Content-Type"] = "application/merge-patch+json" if method == "PATCH" else "application/json"
        target = self.url + "/api/v2" + path
        request = urllib.request.Request(target, data=payload, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
                if not raw:
                    return None
                try:
                    return json.loads(raw.decode("utf-8"))
                except (UnicodeError, ValueError):
                    writing = method in _WRITE_METHODS
                    raise HandrailError(
                        "VIKUNJA_INVALID_RESPONSE",
                        "Vikunja response was not JSON",
                        details={"method": method},
                        retryable=not writing,
                        uncertain=writing,
                    ) from None
        except HandrailError:
            raise
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            exc.close()
            definite = 400 <= status < 500 and status not in {408, 429}
            self._fail(
                "VIKUNJA_HTTP_" + str(status),
                "Vikunja " + method + " failed with HTTP " + str(status),
                method,
                status=status,
                retryable=False,
                uncertain=False if definite else None,
            )
        except (TimeoutError, urllib.error.URLError, OSError):
            writing = method in _WRITE_METHODS
            self._fail(
                "VIKUNJA_CONNECTION_FAILED",
                "Vikunja " + method + " did not complete",
                method,
                retryable=not writing,
                uncertain=writing,
            )

    def pages(self, path):
        rows = []
        for page in range(1, 10001):
            separator = "&" if "?" in path else "?"
            envelope = self.request(path + separator + "page=" + str(page) + "&per_page=50")
            if not isinstance(envelope, dict):
                raise HandrailError("VIKUNJA_INVALID_RESPONSE", "expected a paginated collection", retryable=True)
            items = envelope.get("items")
            if items is None:
                items = []
            if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                raise HandrailError("VIKUNJA_INVALID_RESPONSE", "collection items must be objects", retryable=True)
            if "total_pages" not in envelope:
                raise HandrailError("VIKUNJA_INVALID_RESPONSE", "invalid pagination metadata", retryable=True)
            try:
                total_pages = int(envelope["total_pages"])
            except (TypeError, ValueError):
                raise HandrailError("VIKUNJA_INVALID_RESPONSE", "invalid pagination metadata", retryable=True) from None
            if total_pages < 0:
                raise HandrailError("VIKUNJA_INVALID_RESPONSE", "invalid pagination metadata", retryable=True)
            rows.extend(items)
            if total_pages == 0 or page >= total_pages:
                return rows
        raise HandrailError("VIKUNJA_PAGINATION_LIMIT", "pagination exceeded the page cap", retryable=False)
