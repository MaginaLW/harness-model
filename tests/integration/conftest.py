"""Own optional initial-repository copies within this pytest execution only."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.integration.repository_fixture import register_owner, unregister_owner


@pytest.fixture(scope="session", autouse=True)
def initial_repository_owner(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    token = register_owner(tmp_path_factory)
    try:
        yield
    finally:
        unregister_owner(token)
