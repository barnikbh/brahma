"""Safe source fetching (BR2.1, BR2.2; security-design.md NFR8.1).

``SafeFetcher.fetch`` allows only http and https, refuses any host that resolves to a
non-public address (loopback, private, link-local, multicast, reserved, unspecified),
follows at most 3 redirects by hand and re-checks each hop, and streams the body with a
10 MB cap and a 20 s total budget. HTML is reduced to plain text with the standard
library's ``html.parser``. The resolver, the HTTP client and the clock are injectable,
so tests run with no network.

Known limit: the address check runs before httpx connects and httpx resolves the name
again, so a DNS answer that changes between the two (rebinding) is not caught. This is a
local-only demo with a reviewer in the loop; a hosted deployment should pin the address.
"""

from __future__ import annotations

import hashlib
import ipaddress
import socket
import time
from collections.abc import Callable
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from brahma.updates.errors import SourceFetchError
from brahma.updates.models import MAX_URL_LENGTH, FetchedSource

MAX_BYTES = 10 * 1024 * 1024
TIMEOUT_S = 20.0
MAX_REDIRECTS = 3
ALLOWED_SCHEMES = ("http", "https")
REDIRECT_STATUSES = (301, 302, 303, 307, 308)
USER_AGENT = "Brahma-source-check/0.1 (decision support, not diagnosis)"

Resolver = Callable[[str, int], list[str]]

_BLOCK_TAGS = frozenset(
    {
        *("p", "div", "br", "li", "ul", "ol", "tr", "td", "th", "table", "section"),
        *("article", "h1", "h2", "h3", "h4", "h5", "h6", "header", "footer"),
        *("blockquote", "pre", "dt", "dd"),
    }
)
_SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "head"}


def system_resolver(host: str, port: int) -> list[str]:
    """Every address ``host`` resolves to, using the operating system's resolver."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as exc:
        raise SourceFetchError(f"the host {host} could not be resolved") from exc
    return [str(info[4][0]) for info in infos]


def is_public_address(address: str) -> bool:
    """True only for a globally routable unicast address (IPv4-mapped IPv6 unwrapped)."""
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


class _TextExtractor(HTMLParser):
    """Collects visible text, a line per block element, and the page title."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        elif tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif not self._skip_depth:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    """Reduce HTML to ``(title, text)``: one line per block, whitespace collapsed."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    text = "\n".join(line for line in lines if line)
    return " ".join(parser.title.split()), text


def check_url(url: str, resolver: Resolver) -> None:
    """Raise SourceFetchError(refused=True) unless the URL may be fetched (BR2.1)."""
    if len(url) > MAX_URL_LENGTH:
        raise SourceFetchError("the URL is too long", refused=True)
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise SourceFetchError("the URL is not valid", refused=True) from exc
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise SourceFetchError("only http and https URLs can be fetched", refused=True)
    host = parts.hostname
    if not host:
        raise SourceFetchError("the URL has no host", refused=True)
    if parts.username or parts.password:
        raise SourceFetchError("URLs with a user name or password are refused", refused=True)
    default_port = 443 if parts.scheme.lower() == "https" else 80
    addresses = [host] if _is_ip_literal(host) else resolver(host, port or default_port)
    if not addresses:
        raise SourceFetchError(f"the host {host} could not be resolved")
    if not all(is_public_address(a) for a in addresses):
        raise SourceFetchError("the URL points to a local or private network address", refused=True)


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return False
    return True


class SafeFetcher:
    """Fetches one source page under the BR2 rules; see the module docstring."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        resolver: Resolver = system_resolver,
        *,
        max_bytes: int = MAX_BYTES,
        timeout_s: float = TIMEOUT_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client or httpx.Client(follow_redirects=False)
        self._resolver = resolver
        self._max_bytes = max_bytes
        self._timeout_s = timeout_s
        self._clock = clock

    def fetch(self, url: str) -> FetchedSource:
        """Fetch ``url`` and return its plain text. Raises SourceFetchError with a reason."""
        deadline = self._clock() + self._timeout_s
        current = url.strip()
        for _hop in range(MAX_REDIRECTS + 1):
            check_url(current, self._resolver)
            location, body, content_type = self._get(current, deadline)
            if location is None:
                return self._to_source(current, body, content_type)
            current = urljoin(current, location)
        raise SourceFetchError(f"more than {MAX_REDIRECTS} redirects")

    def _get(self, url: str, deadline: float) -> tuple[str | None, bytes, str]:
        remaining = max(0.1, deadline - self._clock())
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html, text/plain"}
        try:
            with self._client.stream(
                "GET", url, headers=headers, timeout=remaining, follow_redirects=False
            ) as response:
                if response.status_code in REDIRECT_STATUSES:
                    location = response.headers.get("location")
                    if not location:
                        raise SourceFetchError("a redirect had no target")
                    return location, b"", ""
                if response.status_code >= 400:
                    raise SourceFetchError(f"the server answered HTTP {response.status_code}")
                body = self._read_capped(response, deadline)
                return None, body, response.headers.get("content-type", "")
        except httpx.TimeoutException as exc:
            raise SourceFetchError(f"no answer within {self._timeout_s:.0f} s") from exc
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"connection failed ({type(exc).__name__})") from exc

    def _read_capped(self, response: httpx.Response, deadline: float) -> bytes:
        declared = response.headers.get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > self._max_bytes:
            raise SourceFetchError(self._too_big())
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > self._max_bytes:
                raise SourceFetchError(self._too_big())
            if self._clock() > deadline:
                raise SourceFetchError(f"no answer within {self._timeout_s:.0f} s")
            chunks.append(chunk)
        return b"".join(chunks)

    def _too_big(self) -> str:
        return f"the page is larger than {self._max_bytes // (1024 * 1024)} MB"

    @staticmethod
    def _to_source(url: str, body: bytes, content_type: str) -> FetchedSource:
        kind = content_type.split(";", 1)[0].strip().lower()
        if kind not in ("", "text/html", "application/xhtml+xml", "text/plain"):
            raise SourceFetchError(f"unsupported content type {kind}")
        decoded = body.decode(_charset(content_type), errors="replace")
        if kind == "text/plain":
            title, text = "", "\n".join(" ".join(ln.split()) for ln in decoded.splitlines())
        else:
            title, text = html_to_text(decoded)
        text = text.strip()
        if not text:
            raise SourceFetchError("the page has no readable text")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return FetchedSource(
            url=url,
            title=(title or urlsplit(url).hostname or url)[:200],
            text=text,
            content_hash=digest,
            bytes=len(body),
        )


def _charset(content_type: str) -> str:
    for part in content_type.split(";")[1:]:
        name, _, value = part.strip().partition("=")
        if name.lower() == "charset" and value:
            candidate = value.strip("\"' ")
            try:
                "".encode(candidate)
            except LookupError:
                return "utf-8"
            return candidate
    return "utf-8"
