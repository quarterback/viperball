#!/usr/bin/env python3
"""Generate female coach faces only, one at a time."""
import os, sys, time
os.environ.setdefault("PIXELLAB_API_KEY", "48efcb82-00c3-4066-b50f-390bdeca2143")

from engine.coach_face_generator import generate_pool_face, pool_face_path

for i in range(150):
    p = pool_face_path(i, "f")
    if p.exists():
        print(f"coach_f_{i:03d} skip")
        continue
    for attempt in range(3):
        try:
            generate_pool_face(i, "f")
            print(f"coach_f_{i:03d} OK")
            break
        except Exception as e:
            print(f"coach_f_{i:03d} attempt {attempt+1} failed: {e}")
            time.sleep(15)
    else:
        print(f"coach_f_{i:03d} GAVE UP")

print("Done!")
