from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PermissionSeed:
    code: str
    description: str
    group: str


@dataclass(frozen=True, slots=True)
class RoleSeed:
    name: str
    description: str


ROLE_SEEDS = (
    RoleSeed("super_admin", "Full platform access and administration."),
    RoleSeed("manager", "Operational management across the Kabisa platform."),
    RoleSeed("sales", "Sales, customer, order, and delivery operations."),
    RoleSeed("inventory", "Catalog, stock, batch, and import operations."),
    RoleSeed("accounts", "Payment, order, customer, and reporting access."),
)

PERMISSION_CODES_BY_GROUP: dict[str, tuple[str, ...]] = {
    "admin": (
        "admin_users.view",
        "admin_users.create",
        "admin_users.edit",
        "admin_users.delete",
        "roles.view",
        "roles.manage",
        "settings.view",
        "settings.manage",
        "audit.view",
    ),
    "catalog": (
        "categories.view",
        "categories.create",
        "categories.edit",
        "categories.delete",
        "brands.view",
        "brands.create",
        "brands.edit",
        "brands.delete",
        "products.view",
        "products.create",
        "products.edit",
        "products.delete",
        "products.verify",
        "product_prices.manage",
        "catalog.import",
        "catalog.export",
    ),
    "inventory": (
        "inventory.view",
        "inventory.adjust",
        "batches.create",
        "batches.edit",
    ),
    "customers": (
        "customers.view",
        "customers.create",
        "customers.edit",
        "customers.delete",
        "customers.verify",
        "customer_docs.review",
        "customer_feedback.view",
    ),
    "orders": (
        "orders.view",
        "orders.create",
        "orders.edit",
        "orders.approve",
        "orders.cancel",
        "orders.status",
        "payments.view",
        "payments.record",
        "deliveries.view",
        "deliveries.assign",
        "delivery_agents.view",
        "delivery_agents.create",
        "delivery_agents.edit",
        "delivery_agents.delete",
    ),
    "promotions": (
        "coupons.view",
        "coupons.create",
        "coupons.edit",
        "coupons.delete",
    ),
    "reports": (
        "reports.view",
        "reports.export",
    ),
}


def _permission_description(code: str) -> str:
    resource, action = code.split(".", maxsplit=1)
    readable_resource = resource.replace("_", " ")
    readable_action = action.replace("_", " ").capitalize()
    return f"{readable_action} {readable_resource}."


PERMISSION_SEEDS = tuple(
    PermissionSeed(
        code=code,
        description=_permission_description(code),
        group=group,
    )
    for group, codes in PERMISSION_CODES_BY_GROUP.items()
    for code in codes
)
ALL_PERMISSION_CODES = frozenset(permission.code for permission in PERMISSION_SEEDS)

ROLE_PERMISSION_CODES: dict[str, frozenset[str]] = {
    "super_admin": ALL_PERMISSION_CODES,
    "manager": ALL_PERMISSION_CODES
    - {
        "admin_users.view",
        "admin_users.create",
        "admin_users.edit",
        "admin_users.delete",
        "roles.manage",
        "settings.manage",
    },
    "sales": frozenset(
        {
            "products.view",
            "inventory.view",
            "customers.view",
            "customers.create",
            "customers.edit",
            "orders.view",
            "orders.create",
            "orders.edit",
            "payments.view",
            "deliveries.view",
            "reports.view",
        }
    ),
    "inventory": frozenset(
        {
            "products.view",
            "products.edit",
            "categories.view",
            "brands.view",
            "inventory.view",
            "inventory.adjust",
            "orders.view",
            "batches.create",
            "batches.edit",
            "catalog.import",
            "catalog.export",
            "reports.view",
        }
    ),
    "accounts": frozenset(
        {
            "orders.view",
            "payments.view",
            "payments.record",
            "customers.view",
            "reports.view",
            "reports.export",
            "products.view",
        }
    ),
}

EXPECTED_PERMISSION_COUNT = 56
EXPECTED_MAPPING_COUNTS = {
    "super_admin": 56,
    "manager": 50,
    "sales": 11,
    "inventory": 12,
    "accounts": 7,
}


def validate_catalogue() -> None:
    role_names = {role.name for role in ROLE_SEEDS}
    permission_codes = [permission.code for permission in PERMISSION_SEEDS]

    if len(permission_codes) != EXPECTED_PERMISSION_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_PERMISSION_COUNT} permissions; found {len(permission_codes)}."
        )
    if len(permission_codes) != len(set(permission_codes)):
        raise RuntimeError("Permission catalogue contains duplicate codes.")
    if set(ROLE_PERMISSION_CODES) != role_names:
        raise RuntimeError("Every seeded role must have an explicit permission mapping.")

    for role_name, codes in ROLE_PERMISSION_CODES.items():
        unknown_codes = codes - ALL_PERMISSION_CODES
        if unknown_codes:
            raise RuntimeError(
                f"Role {role_name!r} maps unknown permissions: {sorted(unknown_codes)}."
            )
        expected_count = EXPECTED_MAPPING_COUNTS[role_name]
        if len(codes) != expected_count:
            raise RuntimeError(
                f"Role {role_name!r} should have {expected_count} permissions; "
                f"found {len(codes)}."
            )
