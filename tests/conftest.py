"""Test configuration.

Patches UserStore to use a temp file so tests never touch data/users.json,
and resets all module-level singletons before each test session.
"""

import pytest


@pytest.fixture(autouse=True, scope="session")
def isolated_user_store(tmp_path_factory):
    """Point UserStore at a temp file and reset all singletons for the session."""
    tmp = tmp_path_factory.mktemp("data") / "users.json"

    import app.services.user_store as us_mod
    us_mod.DATA_FILE = tmp

    import app.dependencies as dep_mod
    dep_mod._user_store = None
    dep_mod.get_ledger.cache_clear()
    dep_mod.get_router.cache_clear()

    yield

    dep_mod._user_store = None
    dep_mod.get_ledger.cache_clear()
    dep_mod.get_router.cache_clear()
