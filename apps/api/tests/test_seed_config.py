import pytest
from app.core.config import settings
from app.seed.auth import SeedConfigurationError, _validated_super_admin_config


def test_seed_refuses_placeholder_password_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "super_admin_password", "replace-before-seeding")

    with pytest.raises(SeedConfigurationError, match="Refusing to seed"):
        _validated_super_admin_config()
