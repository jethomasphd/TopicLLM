# Contribute to TopicLLM

Replication reports, clearer explanations, usability improvements and software fixes are welcome through [GitHub issues](https://github.com/jethomasphd/TopicLLM/issues) or pull requests. For orientation, start with the [README](README.md) and the [agent rules](AGENTS.md).

## Propose a focused change

Explain the problem, the expected behavior and how to reproduce it. Keep credentials, private research data and individual human annotation records out of issues, commits and test fixtures. Use a small public or invented example when a bug needs input data.

Do not edit the protected dissertation or original publications. Keep recorded research artifacts and their hashes intact. A changed method, codebook, model or sampling design needs a new run record; it must not overwrite the evidence for the published demonstration.

## Check the behavior you change

Use an isolated Python environment and install `.[dev]`; install the website tools with `pnpm install --frozen-lockfile`. Run relevant Python tests from `dtm_pipeline/tests` and JavaScript tests with `pnpm test`. A package change should also pass the offline installed-wheel quickcheck. Follow [MAINTAINING.md](MAINTAINING.md) for the builders and complete publication checks.

For visible changes, inspect the actual page at desktop and mobile widths, in light and dark themes. Verify keyboard operation, readable labels and source links. For paper edits, rebuild and inspect every PDF page; for chart edits, rebuild the figures once and check them on the site, in the paper and in the README. Describe the changed behavior and actual checks in the pull request.

## Preserve the human research boundary

Agents run scripts and prepare evidence. Theme review by two researchers and two independent human coding passes require real people. Never invent approvals or treat software tests as scientific validation. Preserve negative results: the tutorial's classifier failed its declared criteria, so its full-corpus output stays labeled as unvalidated model-assigned shares.
