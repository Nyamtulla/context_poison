"""Which numbers.tex macros are used, and which are referenced but missing.

A macro used but not defined is a build error. A macro defined but not used
is usually harmless (a figure caption may have been rewritten) but is also
how a number quietly stops being generated: the macro survives, the prose
goes back to a typed literal, and nothing complains.

Run: python3 scripts/check_macros.py
"""
import re, pathlib
root = pathlib.Path(__file__).resolve().parent.parent / 'latex'
defined = set(re.findall(r'\\newcommand\{\\(\w+)\}', (root/'numbers.tex').read_text()))
used = set()
for f in root.rglob('*.tex'):
    if f.name == 'numbers.tex': continue
    used |= set(re.findall(r'\\([A-Z][A-Za-z]+)\{\}', f.read_text()))
print("used but UNDEFINED:", sorted(used - defined) or "none")
print("defined but UNUSED:", sorted(defined - used) or "none")
