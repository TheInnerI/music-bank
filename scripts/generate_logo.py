#!/usr/bin/env python3
"""Generate Inner I Music Bank logo — 128x128 PNG for Stripe dashboard."""

from PIL import Image, ImageDraw, ImageFont
import os

SIZE = 128
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "static", "img", "logo-128.png")
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

# Colors
VOID = (8, 8, 15, 255)
OBSERVER = (139, 92, 246, 255)
OBSERVER_LIGHT = (167, 139, 250, 255)
BREATH = (34, 211, 238, 255)
GOLD = (251, 191, 36, 255)
WHITE = (240, 240, 245, 255)

# Create image
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Background rounded rectangle
draw.rounded_rectangle([4, 4, SIZE-4, SIZE-4], radius=28, fill=VOID, outline=OBSERVER, width=2)

# Eye (Observer)
eye_cx, eye_cy = SIZE // 2, SIZE // 2 - 10
eye_w, eye_h = 48, 30

# Eye glow
for i in range(4):
    offset = 4 - i
    alpha = int(40 + i * 40)
    draw.ellipse(
        [eye_cx - eye_w//2 - offset, eye_cy - eye_h//2 - offset,
         eye_cx + eye_w//2 + offset, eye_cy + eye_h//2 + offset],
        fill=(*OBSERVER_LIGHT[:3], alpha)
    )

# Eye outline
draw.ellipse(
    [eye_cx - eye_w//2, eye_cy - eye_h//2,
     eye_cx + eye_w//2, eye_cy + eye_h//2],
    fill=(*OBSERVER[:3], 40), outline=OBSERVER, width=2
)

# Iris (gradient from observer to breath)
iris_r = 12
for r in range(iris_r, 0, -1):
    t = r / iris_r
    rc = int(OBSERVER[0] * (1-t) + BREATH[0] * t)
    gc = int(OBSERVER[1] * (1-t) + BREATH[1] * t)
    bc = int(OBSERVER[2] * (1-t) + BREATH[2] * t)
    draw.ellipse(
        [eye_cx - r, eye_cy - r, eye_cx + r, eye_cy + r],
        fill=(rc, gc, bc, 255)
    )

# Pupil
draw.ellipse([eye_cx-5, eye_cy-5, eye_cx+5, eye_cy+5], fill=VOID)

# Highlight
draw.ellipse([eye_cx-4, eye_cy-4, eye_cx-1, eye_cy-1], fill=WHITE)

# Music note (small, near eye)
nx, ny = eye_cx + 16, eye_cy - 8
draw.ellipse([nx, ny, nx+7, ny+5], fill=GOLD)
draw.line([nx+6, ny+3, nx+6, ny-10], fill=GOLD, width=2)
draw.arc([nx+6, ny-10, nx+14, ny-2], 270, 0, fill=GOLD, width=2)

# Sound waves
for i in range(3):
    r = 5 + i * 5
    alpha = max(40, 140 - i * 40)
    draw.arc(
        [eye_cx + eye_w//2 + 8 + i*4 - r, eye_cy - r,
         eye_cx + eye_w//2 + 8 + i*4 + r, eye_cy + r],
        200, 340, fill=(*BREATH[:3], alpha), width=2
    )

# Text
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
except:
    font = ImageFont.load_default()
    small = font

# "INNER I" at top
bbox = draw.textbbox((0, 0), "INNER I", font=small)
tw = bbox[2] - bbox[0]
draw.text(((SIZE - tw) // 2, 10), "INNER I", fill=(*OBSERVER_LIGHT[:3], 160), font=small)

# "MUSIC" at bottom
bbox = draw.textbbox((0, 0), "MUSIC", font=font)
tw = bbox[2] - bbox[0]
draw.text(((SIZE - tw) // 2, SIZE - 34), "MUSIC", fill=WHITE, font=font)

# "BANK" below MUSIC
bbox = draw.textbbox((0, 0), "BANK", font=font)
tw = bbox[2] - bbox[0]
draw.text(((SIZE - tw) // 2, SIZE - 18), "BANK", fill=OBSERVER_LIGHT, font=font)

# Save
img.save(OUTPUT, "PNG", optimize=True)
print(f"Logo saved: {OUTPUT} ({img.size[0]}x{img.size[1]} PNG)")
