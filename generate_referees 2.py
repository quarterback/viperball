#!/usr/bin/env python3
"""Generate referee faces one at a time."""
import os, sys, time
os.environ.setdefault("PIXELLAB_API_KEY", "48efcb82-00c3-4066-b50f-390bdeca2143")

from engine.referee_generator import generate_pool_ref, pool_ref_path

for i in range(300):
    p = pool_ref_path(i)
    if p.exists():
        print(f"ref_{i:03d} skip")
        continue
    for attempt in range(3):
        try:
            generate_pool_ref(i)
            print(f"ref_{i:03d} OK")
            break
        except Exception as e:
            print(f"ref_{i:03d} attempt {attempt+1} failed: {e}")
            time.sleep(15)
    else:
        print(f"ref_{i:03d} GAVE UP")

print("Done!")
