"""Convert docs/phase2-report/phase2-report.html to phase2-report.pdf.

Strategy: screenshot each slide with Chrome headless, then assemble
images into a multi-page PDF using Pillow.  Reuses the same slide
extraction / screenshot logic as html_to_pptx.py.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "docs" / "phase2-report"
HTML_FILE  = REPORT_DIR / "phase2-report.html"
OUT_PDF    = REPORT_DIR / "phase2-report.pdf"
TMP_DIR    = REPORT_DIR / "_slide_tmp"
CHROME     = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

SLIDE_W_PX = 1280
SLIDE_H_PX = 720


def extract_css(html: str) -> str:
    m = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    return m.group(1) if m else ""


def extract_slides(html: str) -> list[str]:
    return re.findall(
        r'<section class="slide"[^>]*>.*?</section>',
        html,
        re.DOTALL,
    )


def build_slide_html(css: str, slide_body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<style>
{css}
html,body{{margin:0;padding:0;width:{SLIDE_W_PX}px;height:{SLIDE_H_PX}px;overflow:hidden;background:var(--bg);}}
.slide{{
  position:relative;width:{SLIDE_W_PX}px;height:{SLIDE_H_PX}px;
  margin:0!important;border-radius:0!important;box-shadow:none!important;
  background:var(--bg);padding:48px 56px 56px 56px;
  display:flex;flex-direction:column;overflow:hidden;
}}
</style>
</head>
<body>
{slide_body}
</body>
</html>"""


def screenshot_slide(html_path: Path, out_png: Path) -> None:
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-software-rasterizer",
        "--force-device-scale-factor=1",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        f"--window-size={SLIDE_W_PX},{SLIDE_H_PX}",
        f"--screenshot={out_png}",
        html_path.as_uri(),
    ]
    subprocess.run(cmd, capture_output=True, timeout=30)


def build_pdf(images: list[Path], out: Path) -> None:
    imgs = [Image.open(p).convert("RGB") for p in images]
    imgs[0].save(
        str(out),
        save_all=True,
        append_images=imgs[1:],
        resolution=150,
    )
    for img in imgs:
        img.close()


def main() -> int:
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    html = HTML_FILE.read_text(encoding="utf-8")
    css  = extract_css(html)
    slides = extract_slides(html)

    visible = [s for s in slides if "display:none" not in s[:100]]
    print(f"Found {len(slides)} slides, {len(slides) - len(visible)} hidden → processing {len(visible)}")

    png_paths: list[Path] = []

    for i, body in enumerate(visible, start=1):
        tmp_html = REPORT_DIR / f"_slide_{i:02d}_tmp.html"
        tmp_png  = TMP_DIR / f"slide_{i:02d}.png"

        tmp_html.write_text(build_slide_html(css, body), encoding="utf-8")
        print(f"  slide {i:02d} …", end=" ", flush=True)
        screenshot_slide(tmp_html, tmp_png)
        tmp_html.unlink(missing_ok=True)

        if tmp_png.exists():
            print(f"ok ({tmp_png.stat().st_size // 1024} KB)")
            png_paths.append(tmp_png)
        else:
            print("FAILED")

    if not png_paths:
        print("ERROR: no screenshots produced")
        return 1

    print(f"\nAssembling {len(png_paths)} pages into PDF …")
    build_pdf(png_paths, OUT_PDF)
    size_kb = OUT_PDF.stat().st_size // 1024
    print(f"Done → {OUT_PDF.relative_to(REPO_ROOT)}  ({size_kb} KB)")

    for f in TMP_DIR.iterdir():
        f.unlink(missing_ok=True)
    TMP_DIR.rmdir()

    return 0


if __name__ == "__main__":
    sys.exit(main())
