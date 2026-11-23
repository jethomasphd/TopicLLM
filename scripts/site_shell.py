"""Stamp the shared head, navigation bar and footer into every website page.

    python scripts/site_shell.py

Pages carry three markers, which this script fills (and refills, idempotently):

    <!--shell-head-->   inside <head>, after the page's own <title> and description
    <!--shell-bar-->    first thing in <body>
    <!--shell-foot-->   last thing in <body>

The current navigation item is inferred from the page's folder. The Research
page deliberately carries no guide ("Ask") button.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
NAV = [("tutorial/", "Tutorial", "tutorial"), ("use/", "Use it", "use"),
       ("research/", "Research", "research"), ("paper/", "Paper", "paper")]
FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500"
         "&family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap")
GITHUB = ('<svg viewBox="0 0 16 16" aria-hidden="true" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 '
          '2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13'
          '-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64'
          '-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 '
          '1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 '
          '1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>')


def head(prefix: str, guide: bool) -> str:
    parts = [
        f'<link rel="icon" href="{prefix}assets/topicllm-mark.svg" type="image/svg+xml">',
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        f'<link rel="stylesheet" href="{FONTS.replace("&", "&amp;")}">',
        f'<link rel="stylesheet" href="{prefix}style.css">',
        "<script>document.documentElement.classList.remove('no-js')</script>",
        f'<script type="module" src="{prefix}js/site.js"></script>',
    ]
    if guide:
        parts += [f'<link rel="stylesheet" href="{prefix}guide.css">',
                  f'<script type="module" src="{prefix}js/guide.js"></script>']
    return "".join(parts)


def bar(prefix: str, current: str, guide: bool) -> str:
    links = "".join(f'<a href="{prefix}{href}"' + (' aria-current="page"' if key == current else "") + f">{label}</a>"
                    for href, label, key in NAV)
    ask = '<button class="ask" type="button" data-ask aria-haspopup="dialog">Ask</button>' if guide else ""
    return (f'<a class="skip" href="#main">Skip to content</a><header class="bar"><div class="bar-in">'
            f'<a class="brand" href="{prefix}" aria-label="TopicLLM home"><svg viewBox="0 0 64 64" aria-hidden="true">'
            f'<use href="{prefix}assets/topicllm-mark.svg#mark"/></svg>TopicLLM</a>'
            f'<nav id="site-nav" aria-label="Main">{links}</nav>{ask}'
            f'<a class="gh" href="https://github.com/jethomasphd/TopicLLM" aria-label="TopicLLM on GitHub">{GITHUB}</a>'
            f'<button class="menu" type="button" aria-controls="site-nav" aria-expanded="false" data-menu>Menu</button>'
            f"</div></header>")


def foot(prefix: str) -> str:
    return (f'<footer class="foot"><div class="foot-in"><div><p><b>TopicLLM</b> is pilot software built from Jacob E. '
            f"Thomas's dissertation research at The University of Texas at Austin. It has not been independently validated. "
            f'<a href="https://github.com/jethomasphd/TopicLLM/issues">Try to break it</a>.</p>'
            f'<p>Code: MIT. Documentation: CC BY 4.0. Trump posts remain © their original authors.</p></div>'
            f'<ul><li><a href="{prefix}tutorial/">Tutorial</a></li><li><a href="{prefix}use/">Use it</a></li>'
            f'<li><a href="{prefix}research/">Research</a></li><li><a href="{prefix}paper/">Paper</a></li>'
            f'<li><a href="{prefix}privacy/">Privacy and limits</a></li>'
            f'<li><a href="https://github.com/jethomasphd/TopicLLM">GitHub</a></li></ul></div></footer>')


def stamp(path: Path) -> bool:
    rel = path.relative_to(DOCS)
    depth = len(rel.parts) - 1
    prefix = "../" * depth if depth else "./"
    current = rel.parts[0] if depth else ""
    if current == "studies":
        current = "research"
    guide = current != "research" or rel.parts[0] == "studies"
    page = path.read_text(encoding="utf-8")
    if "<!--shell-bar-->" not in page:
        return False
    blocks = {"head": head(prefix, guide), "bar": bar(prefix, current, guide), "foot": foot(prefix)}
    for name, html in blocks.items():
        pattern = re.compile(rf"<!--shell-{name}-->.*?<!--/shell-{name}-->|<!--shell-{name}-->", re.S)
        page = pattern.sub(lambda _: f"<!--shell-{name}-->{html}<!--/shell-{name}-->", page, count=1)
    path.write_text(page, encoding="utf-8", newline="\n")
    return True


def main() -> None:
    stamped = [p for p in sorted(DOCS.rglob("*.html")) if stamp(p)]
    for p in stamped:
        print(f"stamped {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
