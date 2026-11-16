# TopicLLM: instructions for research agents

The website is a visual demonstration. The Python package is the maintained research implementation. Read `README.md`, `REPRODUCE.md`, `docs/protocol.json`, the revised methods in `docs/paper/index.html`, and `AUDIT.md` before substantive analysis.

## Preserve the evidence

- The dissertation governs historical claims. Never edit any file protected by `source-integrity.json`; report apparent source errors separately. Run `node scripts/verify-sources.mjs` before and after changes.
- Distinguish reported study results, calibrated synthetic reconstruction, newly measured synthetic results, mock outputs and new research. Never describe planted categories or generator labels as recovered topics or human annotations.
- Seven topics is the dissertation's observed result, not a required model setting. Do not tune, filter or overwrite results merely to force seven.
- Preserve the actual model count, failed candidates, ballots, raw responses, validation failures and exclusions. A failed gate is a result to investigate, not permission to weaken a threshold.

## Start in the researcher's environment

1. Identify the repository commit and operating system. Create an isolated Python environment. Read the platform scope of dependency locks; do not apply a Windows lock blindly on another platform.
2. Install the package and run `topicllm --profile quickcheck --output-dir runs/quickcheck`. This is an inference check using generator truth, not classifier validation.
3. Inspect input columns, stable IDs, missing text, dates, duplicates, sampling frame and exclusions. Python expects `tweet`; the browser sandbox additionally accepts `text`. Save input hashes and the effective configuration.
4. Plan API calls and use the researcher's already-approved spending ceiling. Paid runs require `--budget-usd`; do not place API credentials in files, code, command arguments, reports or chat. Use the researcher's private environment-variable setup.

## Respect human decisions

- For research, stop after the Stage 3 review packet. Prepare proposed mappings and evidence, but do not invent reviewer names, consensus, approvals or benchmark annotations.
- Two actual researchers must review the evidence and approve the final theme map. Record their attestation with `--record-review --reviewers ...`; the record binds the inputs, assignments, naming output, taxonomy and map by hash. It records an attestation, not proof that a person acted.
- Only the explicit `synthetic-e2e` profile may use `review_mode=synthetic-oracle`, with `human_review_performed=false`. This route requires exact bundled inputs and cannot authorize research data.
- Never reuse the synthetic benchmark for a new research corpus. Keep prompt development separate from independent validation. Report support, precision, sensitivity, confusion counts and overall agreement for every theme. Researchers must justify acceptance criteria for their question.

## Execute and deliver an auditable run

- Keep each analysis in its own output directory. Changed inputs, prompts, taxonomy or settings require new outputs; do not erase an earlier run to make a checkpoint fit.
- Use the persisted API ledger and cached completed operations for resume. Independent naming ballots have distinct operation IDs. Uncertain requests retain conservative budget reservations. Never rerun paid steps just to improve a result without declaring the new analysis.
- Block inference on missing, ambiguous or failed classifications. Preserve all rows and IDs, exclusions, counts, denominators, period definitions, test directions and multiplicity adjustments.
- Finish with the exact commands, environment, source/input/model hashes, effective settings, stage artifacts, API usage, validation report and scientific limitations. Run the applicable tests and verify source hashes. Do not claim historical numerical replication from synthetic data.
- The public classification endpoint accepts only fixed synthetic examples. The separate conversational guide answers bounded questions about public research and documentation. Do not send private research records to the website's operator gateway; run research with approved credentials in the researcher's own environment.

## Changes to this repository

Use the existing scripts and test contracts. Keep archival sources untouched. For package changes, verify wheel installation and the quickcheck outside the checkout. For website changes, verify the guided demo, live-example boundaries, responsive layout and downloads. Budget reservations must remain atomic and must fail closed when storage is unavailable.
