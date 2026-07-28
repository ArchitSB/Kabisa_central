from app.seed.catalogue import (
    ALL_PERMISSION_CODES,
    EXPECTED_MAPPING_COUNTS,
    EXPECTED_PERMISSION_COUNT,
    PERMISSION_SEEDS,
    ROLE_PERMISSION_CODES,
    ROLE_SEEDS,
    validate_catalogue,
)


def test_permission_catalogue_and_role_mappings_are_complete() -> None:
    validate_catalogue()

    assert len(PERMISSION_SEEDS) == EXPECTED_PERMISSION_COUNT == 55
    assert len(ALL_PERMISSION_CODES) == EXPECTED_PERMISSION_COUNT
    assert {role.name for role in ROLE_SEEDS} == set(ROLE_PERMISSION_CODES)
    assert {
        role_name: len(codes) for role_name, codes in ROLE_PERMISSION_CODES.items()
    } == EXPECTED_MAPPING_COUNTS


def test_manager_exclusions_are_exact() -> None:
    assert ALL_PERMISSION_CODES - ROLE_PERMISSION_CODES["manager"] == {
        "admin_users.view",
        "admin_users.create",
        "admin_users.edit",
        "admin_users.delete",
        "roles.manage",
        "settings.manage",
    }
