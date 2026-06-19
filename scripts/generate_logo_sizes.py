#!/usr/bin/env python3
"""Generate additional logo sizes for Stripe and web use."""

from PIL import Image
import os

SOURCE = os.path.join(os.path.dirname(__file__), "..", "static", "img", "logo-128.png")
OUT_DIR = os.path.dirname(SOURCE)

img = Image.open(SOURCE)

# 32x32 favicon
favicon = img.resize((32, 32), Image.LANCZOS)
favicon.save(os.path.join(OUT_DIR, "favicon-32.png"), "PNG", optimize=True)
print(f"favicon-32.png: {favicon.size}")

# 64x64 (medium icon)
icon64 = img.resize((64, 64), Image.LANCZOS)
icon64.save(os.path.join(OUT_DIR, "logo-64.png"), "PNG", optimize=True)
print(f"logo-64.png: {icon64.size}")

# 256x256 (high res for Stripe)
icon256 = img.resize((256, 256), Image.LANCZOS)
icon256.save(os.path.join(OUT_DIR, "logo-256.png"), "PNG", optimize=True)
print(f"logo-256.png: {icon256.size}")

# 512x512 (extra high res)
icon512 = img.resize((512, 512), Image.LANCZOS)
icon512.save(os.path.join(OUT_DIR, "logo-512.png"), "PNG", optimize=True)
print(f"logo-512.png: {icon512.size}")

# Also save as ICO for favicon.ico
favicon.save(os.path.join(OUT_DIR, "favicon.ico"), "ICO", sizes=[(16,16),(32,32),(48,48)])
print(f"favicon.ico: multi-size ICO")

print("\nAll logos generated!")
