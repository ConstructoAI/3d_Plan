"""Lister les mots d'une zone de page (coordonnées en points PDF), triés par y puis x.

Usage : python mots_zone.py PAGE XMIN YMIN XMAX YMAX [filtre_regex]
"""
import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
page_no = int(sys.argv[1])
xmin, ymin, xmax, ymax = (float(v) for v in sys.argv[2:6])
motif = re.compile(sys.argv[6]) if len(sys.argv) > 6 else None
mots = json.loads((ICI / "pages" / f"mots_page_{page_no:02d}.json").read_text(encoding="utf-8"))
sel = [m for m in mots if xmin <= m[0] <= xmax and ymin <= m[1] <= ymax and (not motif or motif.search(m[4]))]
for m in sorted(sel, key=lambda m: (round(m[1]), m[0])):
    print(f"x={m[0]:8.2f}..{m[2]:8.2f}  y={m[1]:8.2f}..{m[3]:8.2f}  {m[4]}")
