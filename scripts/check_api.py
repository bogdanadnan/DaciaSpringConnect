#!/usr/bin/env python3
"""
Standalone debug script — tests real Renault API connectivity.

Usage:
    python scripts/check_api.py

The script will prompt for credentials interactively (never stored on disk).
Set env vars to skip prompts:
    RENAULT_EMAIL, RENAULT_PASSWORD, RENAULT_LOCALE (default: fr_FR)
"""
from __future__ import annotations

import asyncio
import os
import getpass
import json


async def main() -> None:
    try:
        import aiohttp
        from renault_api.renault_client import RenaultClient
    except ImportError:
        print("ERROR: renault-api not installed. Run: pip install renault-api")
        return

    email    = os.getenv("RENAULT_EMAIL")    or input("MyRenault email: ")
    password = os.getenv("RENAULT_PASSWORD") or getpass.getpass("Password: ")
    locale   = os.getenv("RENAULT_LOCALE", "fr_FR")

    # Build SSL context — try certifi first, fall back to system certs,
    # and as a last resort disable verification (debug script only).
    import ssl
    try:
        import certifi
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ssl_ctx = ssl.create_default_context()

    connector = aiohttp.TCPConnector(ssl=ssl_ctx)

    async with aiohttp.ClientSession(connector=connector) as session:
        client = RenaultClient(websession=session, locale=locale)

        print(f"\n[1/5] Logging in as {email} (locale={locale}) …")
        await client.session.login(email, password)
        print("      ✓ Login OK")

        print("\n[2/5] Fetching accounts …")
        person = await client.get_person()
        accounts = [a for a in (person.accounts or []) if a.accountId]
        if not accounts:
            print("      No accounts found.")
            return
        for acc in accounts:
            print(f"      • {acc.accountId}  ({acc.accountType})")

        account_id = accounts[0].accountId
        print(f"\n      Using account: {account_id}")

        print("\n[3/5] Fetching vehicles …")
        account = await client.get_api_account(account_id)
        vehicles_resp = await account.get_vehicles()
        vehicles = [v for v in (vehicles_resp.vehicleLinks or []) if v.vin]
        if not vehicles:
            print("      No vehicles found.")
            return
        for v in vehicles:
            print(f"      • {v.vin}")

        vin = vehicles[0].vin
        print(f"\n      Using VIN: {vin}")
        vehicle = await account.get_api_vehicle(vin)

        print("\n[4/5] Fetching vehicle data …")
        results: dict[str, object] = {}
        for label, getter in [
            ("battery_status",  vehicle.get_battery_status),
            ("hvac_status",     vehicle.get_hvac_status),
            ("location",        vehicle.get_location),
            ("charge_mode",     vehicle.get_charge_mode),
            ("cockpit",         vehicle.get_cockpit),
        ]:
            try:
                raw = await getter()
                # Convert to dict if possible
                data = raw.__dict__ if hasattr(raw, "__dict__") else repr(raw)
                results[label] = data
                print(f"      ✓ {label}")
            except Exception as err:
                results[label] = f"ERROR: {err}"
                print(f"      ✗ {label}: {err}")

        print("\n[5/5] Summary (JSON):\n")
        print(json.dumps(results, default=str, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
