from pilot import iPhoneClient
import time

client = iPhoneClient()
try:
    print("Tapping Adventure (0.500, 0.804)...")
    client.tap(0.500, 0.804)
    time.sleep(2.5)
    items = client.get_ocr_items()
    print("Screen after tapping Adventure:")
    for it in items:
        print(f"  {it['text']} -> ({it['x']}, {it['y']})")
finally:
    client.close()
