"""Brahma platform (U2): append-only audit, demo identities and the model gateway.

Decision support, not diagnosis. Synthetic data only. U2 depends on no other unit:
other units' identifiers (case, walk, pack version) are stored as plain text.

- ``brahma.platform.audit``: contract C2 (``AuditService``).
- ``brahma.platform.identity``: contract C3 (``IdentityService``).
- ``brahma.platform.models``: contract C4 (``ModelGateway``).
"""

# Every environment variable U2 reads (NFR5.2). scripts/check_env_example.py checks that
# `.env.example` lists each one with an empty value.
ENV_VARS = (
    "BRAHMA_MODEL_PROVIDER",
    "BRAHMA_MODEL_NAME",
    "META_API_KEY",
    "ANTHROPIC_API_KEY",
    "LLAMA_API_KEY",
    "BRAHMA_MODEL_BASE_URL",
    "BRAHMA_MODEL_RPM",
    "BRAHMA_MODEL_TIMEOUT_S",
    "BRAHMA_DB_PATH",
)

__all__ = ["ENV_VARS"]
