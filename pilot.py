"""
Backward-compatible wrapper for ms_pilot.core.client.iPhoneClient.
Existing scripts (farm_asagiri.py, runner.py) can continue importing `from pilot import iPhoneClient`.
"""

from ms_pilot.core.client import iPhoneClient, resolve_mcp_binary

__all__ = ["iPhoneClient", "resolve_mcp_binary"]

if __name__ == "__main__":
    with iPhoneClient() as client:
        items = client.get_ocr_items()
        print("Parsed items count:", len(items))
        for it in items:
            print(f"  {it['text']} -> ({it['x']}, {it['y']})")
