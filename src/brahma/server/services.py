"""The shared services of one server process (scalability-design.md NFR4.1).

They are created once in ``create_app`` and shared by every request: one SQLite
connection for the ``pf_``, ``cs_`` and ``ag_`` tables (and ``up_`` when the knowledge
feature is mounted), one knowledge service, the model gateway and the walk engine.
Start-up loads each pack in ``content/`` that is not loaded yet, or whose file version is
newer than the live one (FR2.6; stored as a new version, so past sessions keep theirs),
and seeds the demo profiles.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from brahma.agent.db import ag_connect
from brahma.agent.engine import WalkEngine
from brahma.agent.logging import WalkLogger
from brahma.agent.repository import WalkRepository
from brahma.cases.service import CaseService
from brahma.knowledge.db import kg_connect
from brahma.knowledge.errors import KnowledgeError
from brahma.knowledge.models import parse_version
from brahma.knowledge.service import KnowledgeService
from brahma.platform.audit.service import AuditService
from brahma.platform.identity.service import IdentityService
from brahma.platform.models import ModelGateway
from brahma.platform.profiles import ProfileRepository
from brahma.server.config import ServerConfig
from brahma.updates.db import ensure_up_schema
from brahma.updates.service import UpdateService

logger = logging.getLogger("brahma.server")

GatewayFactory = Callable[[sqlite3.Connection], ModelGateway]


def load_initial_packs(knowledge: KnowledgeService, content_dir: Path) -> list[str]:
    """Load every ``content/*.yaml`` pack that is new, or newer than its live version.

    A newer file becomes the pack's new live version; earlier versions stay stored, so
    past sessions replay on the version they used. A file that is not newer is skipped.
    A file that cannot be read is skipped with a warning when its pack is already live
    (the server keeps running on the live version), and raises otherwise.
    """
    loaded: list[str] = []
    for path in sorted(content_dir.glob("*.yaml")):
        try:
            pack = knowledge.loader.read(path)
            live = knowledge.repo.live_version(pack.pack.code)
            if live is not None and parse_version(pack.version) <= parse_version(live.number):
                continue
            ref = knowledge.load_pack(path)
        except KnowledgeError as exc:
            if knowledge.repo.live_versions():
                logger.warning("pack file not loaded: %s (%s)", path.name, type(exc).__name__)
                continue
            raise
        loaded.append(f"{ref.pack} {ref.number}")
    return loaded


def _default_gateway(config: ServerConfig) -> GatewayFactory:
    """The gateway from the environment, replaying ``BRAHMA_RECORDED_DIR`` when it is set."""
    recorded_dir = config.recorded_dir
    if recorded_dir is None:
        return ModelGateway.from_env

    def build(conn: sqlite3.Connection) -> ModelGateway:
        return ModelGateway.from_env(conn, recorded_dir=recorded_dir)

    return build


@dataclass
class Services:
    """Everything the routes use."""

    config: ServerConfig
    conn: sqlite3.Connection
    knowledge: KnowledgeService
    cases: CaseService
    audit: AuditService
    identity: IdentityService
    gateway: ModelGateway
    engine: WalkEngine
    _updates: UpdateService | None = field(default=None, repr=False)
    _updates_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @classmethod
    def build(cls, config: ServerConfig, gateway_factory: GatewayFactory | None = None) -> Services:
        """Open the database, load packs if needed, seed profiles and wire the services."""
        conn = ag_connect(config.db_path)
        knowledge = KnowledgeService(kg_connect(config.db_path))
        loaded = load_initial_packs(knowledge, config.content_dir)
        if loaded:
            logger.info("loaded packs: %s", ", ".join(loaded))
        ProfileRepository(conn).seed()
        audit = AuditService(conn)
        cases = CaseService(conn, knowledge)
        gateway = (gateway_factory or _default_gateway(config))(conn)
        engine = WalkEngine(
            knowledge=knowledge,
            cases=cases,
            audit=audit,
            gateway=gateway,
            repo=WalkRepository(conn),
            logger=WalkLogger(config.log_path),
        )
        return cls(
            config=config,
            conn=conn,
            knowledge=knowledge,
            cases=cases,
            audit=audit,
            identity=IdentityService(conn),
            gateway=gateway,
            engine=engine,
        )

    def updates(self) -> UpdateService:
        """U5's service on the shared connection, built on first use (C7 mount)."""
        if self._updates is None:
            with self._updates_lock:
                if self._updates is None:
                    ensure_up_schema(self.conn)
                    self._updates = UpdateService(
                        self.conn, self.knowledge, self.identity, gateway=self.gateway
                    )
        return self._updates

    def close(self) -> None:
        """Close both database connections."""
        self.conn.close()
        self.knowledge.close()
