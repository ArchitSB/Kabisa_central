"""Generate the implementation reference without accessing the database or secrets."""

import inspect
import json
import re
from pathlib import Path

from app.api.v1.routes import storefront
from app.api.v1.store import account, auth, catalog, commerce
from app.main import app
from app.models import store
from app.services.store_content_service import COMPANY_KEYS, STORE_DEFAULTS


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def main():
    output = [
        "# Storefront implementation reference",
        "",
        (
            "Generated from the installed application source. Regenerate with "
            "`python scripts/export_storefront_reference.py` after activating the API environment."
        ),
        "",
        "## New tables",
        "",
        (
            "These extend the existing customer, address, document, product, order, payment and "
            "settings records. Database columns are **not** public response contracts. "
            "Customer responses use explicit safe projections; private hashes, storage paths, "
            "internal stock and other customers' prices never belong in public DTOs."
        ),
    ]
    tables = sorted(
        [
            value.__table__
            for value in vars(store).values()
            if inspect.isclass(value)
            and value.__module__ == store.__name__
            and hasattr(value, "__table__")
        ],
        key=lambda table: table.name,
    )
    for table in tables:
        output += [
            "",
            f"### `{table.name}`",
            "",
            "| Column | Type | Nullable | Key / relation |",
            "| --- | --- | --- | --- |",
        ]
        for col in table.columns:
            keys = ["Primary key"] if col.primary_key else []
            keys += [f"→ {foreign.target_fullname}" for foreign in col.foreign_keys]
            if col.unique:
                keys.append("Unique")
            output.append(
                f"| `{col.name}` | {cell(col.type)} | "
                f"{'Yes' if col.nullable else 'No'} | {cell(', '.join(keys))} |"
            )
    output += [
        "",
        "## HTTP endpoints",
        "",
        (
            "Every authenticated customer route resolves an active customer session and "
            "checks business ownership. File IDs and order IDs never grant access by themselves. "
            "Admin endpoints require a separate admin token and the permission below. "
            "OTP endpoints are throttled and proofs expire, are attempt-limited and single-use. "
            "Checkout additionally enforces configured verification, stock, minimum, "
            "address ownership, POM upload and server pricing rules."
        ),
        "",
        "| Method | Path | Access | Purpose |",
        "| --- | --- | --- | --- |",
    ]
    endpoints = {
        value.__name__: value
        for module in [account, auth, catalog, commerce, storefront]
        for value in vars(module).values()
        if inspect.isfunction(value) and value.__module__ == module.__name__
    }
    routes = [
        (path, method, operation)
        for path, path_item in app.openapi()["paths"].items()
        if path.startswith(("/api/v1/store/", "/api/v1/storefront/"))
        for method, operation in path_item.items()
        if method in {"get", "post", "patch", "delete", "put"}
    ]
    for path, method, operation in sorted(routes, key=lambda route: route[:2]):
        name = next(
            name
            for name in sorted(endpoints, key=len, reverse=True)
            if operation["operationId"].startswith(name + "_")
        )
        source = inspect.getsource(endpoints[name])
        admin = re.search(r"user: (Viewer|Editor|Deleter|Exporter)", source)
        if admin:
            access = {
                "Viewer": "storefront.view",
                "Editor": "storefront.manage",
                "Deleter": "storefront.delete",
                "Exporter": "storefront.export",
            }[admin[1]]
            if path.endswith("/bulk"):
                access += "; DELETE action also requires storefront.delete"
        elif "user: CurrentCustomer" in source:
            access = "Customer session + ownership"
        elif "user: OptionalCustomer" in source:
            access = "Public; optional customer tier"
        elif path.endswith("/payments/callback"):
            access = "Dormant provider callback (503)"
        else:
            access = "Public / authentication proof as applicable"
        title = operation.get("summary", name.replace("_", " ").capitalize())
        output.append(
            f"| {method.upper()} | `{path}` | " f"{cell(access)} | {cell(title)} |"
        )
    output += [
        "",
        "Content `{kind}` values: "
        + ", ".join(f"`{key}`" for key in store.CONTENT_MODELS)
        + ". CRUD is soft deletion, active/draft plus UTC scheduling. Slugs are unique. "
        "Collection modes are MANUAL and RULES. Rule fields: category, brand, product_type, "
        "sort (featured/newest/name). Exports use XLSX.",
        "",
        "## Runtime settings",
        "",
        (
            "Stored in `settings` with the `storefront.` prefix. This lists installation "
            "defaults; the seed may fill editable home/support content. Updates validate types, "
            "bounds, links and nested delivery/message structures. Blank contact or claim "
            "settings are omitted in the interface."
        ),
        "",
        "| Setting | Default (JSON) |",
        "| --- | --- |",
    ]
    for key, value in STORE_DEFAULTS.items():
        output.append(f"| `{key}` | `{cell(json.dumps(value, ensure_ascii=False))}` |")
    output += [
        "",
        (
            "Delivery modes: flat, zone, free. Zone values provide fee and ETA; "
            "free_delivery_threshold overrides the fee when a positive threshold is reached. "
            "Visibility values: visible, hidden, login_to_see. "
            "Tax is a percentage; monetary settings use the company's configured currency. "
            "Reviews and remote push are reserved integration seams, not active services."
        ),
        "",
        "### Public company aliases",
        "",
        "| Public field | Existing setting |",
        "| --- | --- |",
    ]
    for alias, key in COMPANY_KEYS.items():
        output.append(f"| `{alias}` | `{key}` |")
    output += [
        "",
        "## Permission additions",
        "",
        (
            "`storefront.view`, `storefront.manage`, `storefront.delete`, "
            "`storefront.export`: granted to super_admin and manager. Other operational "
            "roles retain their previous assignments. Creation, editing, settings, upload "
            "and prescription review use manage; all deletion paths use delete."
        ),
        "",
        (
            f"Inventory: **{len(tables)} new tables, {len(routes)} "
            f"HTTP operations, {len(STORE_DEFAULTS)} runtime settings, 4 permissions**."
        ),
        "",
    ]
    Path("docs/STOREFRONT_REFERENCE.md").write_text("\n".join(output))
    print(
        f"Generated {len(tables)} tables, {len(routes)} routes and {len(STORE_DEFAULTS)} settings."
    )


if __name__ == "__main__":
    main()
