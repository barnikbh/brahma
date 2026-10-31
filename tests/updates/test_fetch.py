"""SafeFetcher (plan Step 11; BR2.1, BR2.2, AC8.1.3, NFR8.1). No network: respx + fake DNS."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterator

import httpx
import pytest
import respx

from brahma.updates.errors import SourceFetchError
from brahma.updates.fetch import MAX_BYTES, SafeFetcher, html_to_text, is_public_address
from tests.updates.conftest import SOURCE_URL, FakeResolver

NON_PUBLIC = (
    "10.1.2.3",
    "172.16.0.1",
    "192.168.0.1",
    "127.0.0.1",
    "0.0.0.0",
    "224.0.0.1",
    "::ffff:127.0.0.1",
    "fe80::1",
    "not-an-ip",
)


def _refused(fetcher: SafeFetcher, url: str) -> SourceFetchError:
    with pytest.raises(SourceFetchError) as caught:
        fetcher.fetch(url)
    return caught.value


@pytest.mark.parametrize(
    "url",
    ["ftp://guidelines.example.org/file.txt", "file:///etc/passwd", "javascript:alert(1)"],
)
def test_only_http_and_https_are_fetched(
    fetcher: SafeFetcher, http: respx.MockRouter, url: str
) -> None:
    error = _refused(fetcher, url)
    assert error.refused
    assert "http" in error.reason
    assert not http.calls


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1/", "http://[::1]:8080/x", "http://169.254.169.254/latest/meta-data"],
)
def test_loopback_and_link_local_literals_are_refused(
    fetcher: SafeFetcher, http: respx.MockRouter, url: str
) -> None:
    assert _refused(fetcher, url).refused
    assert not http.calls


def test_a_host_that_resolves_to_a_private_address_is_refused(
    fetcher: SafeFetcher, resolver: FakeResolver, http: respx.MockRouter
) -> None:
    resolver.hosts["intranet.example.org"] = ["93.184.216.34", "10.0.0.5"]
    error = _refused(fetcher, "https://intranet.example.org/page")
    assert error.refused
    assert "private" in error.reason
    assert resolver.calls == ["intranet.example.org"]
    assert not http.calls


def test_each_redirect_target_is_checked_and_at_most_three_are_followed(
    fetcher: SafeFetcher, resolver: FakeResolver, http: respx.MockRouter
) -> None:
    resolver.hosts["internal.example.org"] = ["192.168.1.10"]
    http.get(SOURCE_URL).mock(
        return_value=httpx.Response(302, headers={"location": "http://internal.example.org/"})
    )
    assert _refused(fetcher, SOURCE_URL).refused
    assert not any(c.request.url.host == "internal.example.org" for c in http.calls)

    loop = "https://loop.example.org/"
    http.get(url__startswith=loop).mock(
        return_value=httpx.Response(301, headers={"location": "/again"})
    )
    error = _refused(fetcher, loop)
    assert not error.refused
    assert "redirects" in error.reason


def test_a_body_over_10_mb_is_refused(fetcher: SafeFetcher, http: respx.MockRouter) -> None:
    http.get(SOURCE_URL).mock(
        return_value=httpx.Response(
            200, content=b"a" * (MAX_BYTES + 1), headers={"content-type": "text/plain"}
        )
    )
    error = _refused(fetcher, SOURCE_URL)
    assert not error.refused
    assert "10 MB" in error.reason


def test_a_streamed_body_without_a_length_is_capped(
    resolver: FakeResolver, http: respx.MockRouter
) -> None:
    def chunks() -> Iterator[bytes]:
        for _ in range(10):
            yield b"x" * 1024

    http.get(SOURCE_URL).mock(
        return_value=httpx.Response(200, content=chunks(), headers={"content-type": "text/plain"})
    )
    small = SafeFetcher(httpx.Client(), resolver, max_bytes=4096)
    assert "larger than" in _refused(small, SOURCE_URL).reason


def test_a_timeout_and_an_http_error_are_reported(
    fetcher: SafeFetcher, http: respx.MockRouter
) -> None:
    http.get(SOURCE_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    timed_out = _refused(fetcher, SOURCE_URL)
    assert not timed_out.refused
    assert "20 s" in timed_out.reason

    missing = "https://guidelines.example.org/missing"
    http.get(missing).mock(return_value=httpx.Response(404))
    assert "HTTP 404" in _refused(fetcher, missing).reason

    pdf = "https://guidelines.example.org/file.pdf"
    http.get(pdf).mock(
        return_value=httpx.Response(
            200, content=b"%PDF", headers={"content-type": "application/pdf"}
        )
    )
    assert "content type" in _refused(fetcher, pdf).reason


def test_the_total_time_budget_covers_a_slow_body(
    resolver: FakeResolver, http: respx.MockRouter
) -> None:
    ticks = iter([0.0, 0.0, 5.0, 25.0, 30.0, 35.0])
    clock: Callable[[], float] = lambda: next(ticks)  # noqa: E731
    http.get(SOURCE_URL).mock(
        return_value=httpx.Response(
            200, content=iter([b"part one ", b"part two"]), headers={"content-type": "text/plain"}
        )
    )
    slow = SafeFetcher(httpx.Client(), resolver, clock=clock)
    assert "20 s" in _refused(slow, SOURCE_URL).reason


def test_html_is_reduced_to_text_with_title_and_hash(
    fetcher: SafeFetcher, page: Callable[..., respx.Route]
) -> None:
    page()
    fetched = fetcher.fetch(SOURCE_URL)
    assert fetched.title == "Synthetic colitis note"
    assert fetched.text.splitlines()[0] == "Synthetic review note"
    assert "alert" not in fetched.text
    assert "color" not in fetched.text
    assert "sparing the small bowel" in fetched.text
    assert fetched.content_hash == hashlib.sha256(fetched.text.encode()).hexdigest()
    assert fetched.bytes > 0


def test_a_redirect_to_a_public_page_is_followed(
    fetcher: SafeFetcher, http: respx.MockRouter, page: Callable[..., respx.Route]
) -> None:
    old = "https://old.example.org/moved"
    http.get(old).mock(return_value=httpx.Response(308, headers={"location": SOURCE_URL}))
    page()
    assert fetcher.fetch(old).url == SOURCE_URL


def test_address_classification_and_html_helper() -> None:
    assert is_public_address("93.184.216.34")
    for address in NON_PUBLIC:
        assert not is_public_address(address), address
    title, text = html_to_text("<p>One &amp; two</p><div>  three   four </div>")
    assert (title, text) == ("", "One & two\nthree four")
