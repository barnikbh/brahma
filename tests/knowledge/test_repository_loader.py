"""Repository and loader (Step 6): round trip, version order, atomicity, safe parsing, comments."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from brahma.knowledge.errors import (
    BaseNotLive,
    CommentInvalid,
    NodeNotFound,
    PackBusy,
    PackLoadError,
    VersionNotIncreasing,
)
from brahma.knowledge.loader import MAX_PACK_BYTES, PackLoader
from brahma.knowledge.models import PackFile
from brahma.knowledge.repository import KnowledgeRepository, VersionContent


def _content(pack: PackFile) -> VersionContent:
    return VersionContent(pack.sources, pack.nodes, pack.edges, pack.change_summary)


def _publish(repo: KnowledgeRepository, pack: PackFile, number: str) -> str:
    return repo.publish(pack.pack, _content(pack), "system", number=number).number


Connect = Callable[..., sqlite3.Connection]


@pytest.fixture
def repo(connect: Connect) -> KnowledgeRepository:
    return KnowledgeRepository(connect())


@pytest.fixture
def pack(minimal_pack_path: Path) -> PackFile:
    return PackLoader().read(minimal_pack_path)


def test_small_pack_round_trips(repo: KnowledgeRepository, pack: PackFile) -> None:
    stored = repo.publish(pack.pack, _content(pack), "system", number=pack.version)
    assert (stored.number, stored.status, stored.change_summary) == (
        "1.0",
        "live",
        pack.change_summary,
    )
    assert repo.read_nodes(stored.pack_version_id) == sorted(pack.nodes, key=lambda n: n.node_id)
    assert repo.read_edges(stored.pack_version_id) == sorted(pack.edges, key=lambda e: e.edge_id)
    assert repo.read_sources("TST") == pack.sources
    stored_pack = repo.get_pack("TST")
    assert stored_pack is not None and stored_pack.live_version_number == "1.0"


def test_versions_listed_newest_first(repo: KnowledgeRepository, pack: PackFile) -> None:
    for number in ("1.0", "1.2", "1.10"):
        _publish(repo, pack, number)
    versions = repo.list_versions("TST")
    assert [v.number for v in versions] == ["1.10", "1.2", "1.0"]
    assert [v.status for v in versions] == ["live", "superseded", "superseded"]
    assert versions[0].based_on == "TST@1.2"
    with pytest.raises(VersionNotIncreasing):
        _publish(repo, pack, "1.9")
    with pytest.raises(VersionNotIncreasing):
        _publish(repo, pack, "1.10")


def test_concurrent_create_version_never_leaves_two_live(connect: Connect, pack: PackFile) -> None:
    KnowledgeRepository(connect()).publish(pack.pack, _content(pack), "system", number="1.0")
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def worker() -> None:
        repo = KnowledgeRepository(connect())
        barrier.wait()
        try:
            outcomes.append(repo.publish(pack.pack, _content(pack), "u5", base_number="1.0").number)
        except (BaseNotLive, PackBusy) as exc:
            outcomes.append(type(exc).__name__)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes.count("1.1") == 1
    assert len(outcomes) == 2
    live = connect().execute("SELECT number FROM kg_pack_version WHERE status='live'").fetchall()
    assert [row[0] for row in live] == ["1.1"]


def test_interrupted_write_leaves_previous_version_intact(
    repo: KnowledgeRepository, pack: PackFile, monkeypatch: pytest.MonkeyPatch
) -> None:
    _publish(repo, pack, "1.0")

    def crash(*_args: Any) -> None:
        raise RuntimeError("power cut")

    monkeypatch.setattr(repo, "insert_edges", crash)
    with pytest.raises(RuntimeError, match="power cut"):
        _publish(repo, pack, "2.0")
    assert [(v.number, v.status) for v in repo.list_versions("TST")] == [("1.0", "live")]
    assert repo.read_nodes("TST@2.0") == []


def test_busy_database_raises_pack_busy(connect: Connect, pack: PackFile) -> None:
    holder = connect()
    holder.execute("BEGIN IMMEDIATE")
    try:
        repo = KnowledgeRepository(connect(busy_timeout_ms=50))
        with pytest.raises(PackBusy):
            _publish(repo, pack, "1.0")
    finally:
        holder.execute("ROLLBACK")


def _write_big(tmp_path: Path) -> Path:
    path = tmp_path / "big.yaml"
    path.write_text("# " + "x" * (6 * 1024 * 1024) + "\n", encoding="utf-8")
    assert path.stat().st_size > MAX_PACK_BYTES
    return path


def _write_json(tmp_path: Path) -> Path:
    path = tmp_path / "pack.json"
    path.write_text("{}", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("make_path", "message"),
    [
        (lambda tmp, fx: fx / "alias.yaml", "aliases are not allowed"),
        (lambda tmp, fx: fx / "unsafe_tag.yaml", "unsafe YAML"),
        (lambda tmp, fx: _write_big(tmp), "limit is 5 MB"),
        (lambda tmp, fx: _write_json(tmp), ".yaml or .yml"),
        (lambda tmp, fx: tmp / "missing.yaml", "cannot read"),
    ],
)
def test_refused_pack_inputs(
    tmp_path: Path,
    fixtures_dir: Path,
    make_path: Callable[[Path, Path], Path],
    message: str,
) -> None:
    with pytest.raises(PackLoadError, match=message):
        PackLoader().read(make_path(tmp_path, fixtures_dir))


def test_model_errors_name_the_node(
    minimal_pack: dict[str, Any], write_pack: Callable[..., Path]
) -> None:
    minimal_pack["nodes"][2]["sourceIds"] = []
    with pytest.raises(PackLoadError) as caught:
        PackLoader().read(write_pack(minimal_pack))
    assert caught.value.item_id == "TST-N3"
    with pytest.raises(PackLoadError, match="mapping"):
        PackLoader().parse("- just\n- a list\n")


def test_changed_source_with_same_id_refused(repo: KnowledgeRepository, pack: PackFile) -> None:
    _publish(repo, pack, "1.0")
    changed = pack.model_copy(
        update={"sources": [pack.sources[0].model_copy(update={"title": "Renamed"})]}
    )
    with pytest.raises(PackLoadError) as caught:
        _publish(repo, changed, "1.1")
    assert caught.value.item_id == "TST-S1"
    assert repo.live_version("TST") is not None
    assert repo.live_version("TST").number == "1.0"  # type: ignore[union-attr]


def test_comments(repo: KnowledgeRepository, pack: PackFile) -> None:
    _publish(repo, pack, "1.0")
    markup = "<b>Check</b> the dose & <script>x</script>\nsecond line"
    first = repo.add_comment("TST-N8", "doctor-1", markup)
    second = repo.add_comment("TST-N8", "doctor-2", "Later\x07 comment")
    comments = repo.list_comments("TST-N8")
    assert [c.comment_id for c in comments] == [second, first]
    assert comments[1].text == markup
    assert comments[0].text == "Later comment"
    with pytest.raises(CommentInvalid, match="blank"):
        repo.add_comment("TST-N8", "doctor-1", "  \x00\t ")
    with pytest.raises(CommentInvalid, match="1001"):
        repo.add_comment("TST-N8", "doctor-1", "x" * 1001)
    with pytest.raises(NodeNotFound):
        repo.add_comment("URO-N1", "doctor-1", "Hello")
    assert repo.list_comments("URO-N1") == []


def test_rollback_on_sqlite_error(repo: KnowledgeRepository) -> None:
    with pytest.raises(sqlite3.IntegrityError), repo.transaction():
        repo.conn.execute("INSERT INTO kg_pack VALUES ('A', 'A', 'n', 's')")
        repo.conn.execute("INSERT INTO kg_pack VALUES ('A', 'A', 'n', 's')")
    assert repo.get_pack("A") is None
