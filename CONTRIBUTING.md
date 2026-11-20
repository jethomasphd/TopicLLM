# Contribute to TopicLLM

Replication reports, clearer explanations, usability improvements and software fixes are welcome through [GitHub issues](https://github.com/jethomasphd/TopicLLM/issues) or pull requests. For orientation, start with the [repository map](docs/README.md) and [agent contract](AGENTS.md).

## Propose a focused change

Explain the problem, the expected behavior and how to reproduce it. Keep credentials, private research data and individual human annotation records out of issues, commits and test fixtures. Use a small public or invented example when a bug needs input data.

Do not edit the protected dissertation or original publications. Keep recorded research artifacts and their hashes intact. A changed method, codebook, model or sampling design needs a new run record; it must not overwrite the evidence for the published demonstration.

## Check the behavior you change

Use an isolated Python environment and install `.[dev]`; install the website tools with `pnpm install --frozen-lockfile`. Run relevant Python tests from `dtm_pipeline/tests` and JavaScript tests with `pnpm test`. A package change should also pass the offline installed-wheel quickcheck. Follow [DEPLOYMENT.md](DEPLOYMENT.md) for complete publication checks and builders.

For visible changes, inspect the actual page at desktop and mobile widths, in light and dark themes. Verify keyboard operation, readable labels, page introductions and source links. For manuscript edits, rebuild and inspect every PDF page. Describe the changed behavior and actual checks in the pull request.

## Preserve the human research boundary

Agents run scripts and prepare evidence. Two-pass human theme review and two independent human coding passes require real human work. Never invent approvals or treat software tests as scientific validation. Preserve negative results: the current demonstration failed its declared classifier criteria, so its full-corpus output remains unvalidated model-assigned shares.
