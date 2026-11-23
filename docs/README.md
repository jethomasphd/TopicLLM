# The `docs/` folder

This folder is the published website (https://topicllm.dev), plus the tutorial's public data and evidence.

| Path | What it is |
|---|---|
| `index.html`, `tutorial/`, `use/`, `research/`, `paper/`, `privacy/`, `studies/` | Pages. The shared navigation is stamped in by `scripts/site_shell.py` |
| `style.css`, `guide.css`, `source-reader.css` | One site stylesheet, the Ask panel and the dissertation chapter reader |
| `js/site.js`, `js/lab.js`, `js/guide.js` | Shared behavior, the tutorial's live lab, and the Ask guide |
| `assets/figures/` | The figures used by the site, the paper and the README (`scripts/build-figures.py`) |
| `data/trump/corpus.csv` | The tutorial archive: 34,416 posts, 2015-06-16 to 2021-01-08 ([data card](data/README.md)) |
| `data/trump/campaign/` | The recorded tutorial: candidates, ballots, codebook, aggregate evaluation, human-sample shares, selection rule, classifier counts |
| `preprints/` | The software paper's PDF and the original papers (protected) |
| `protocol.json` | The machine-readable protocol |
| `guide/knowledge.md` | The Ask guide's briefing |

[MAINTAINING.md](../MAINTAINING.md) lists every builder and check.
