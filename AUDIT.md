# Research sources and release evidence

The dissertation (Thomas, 2025) is authoritative for historical research claims. Its two studies show the methodology in action. Original dissertation, paper editions and supplements are protected byte for byte by source-integrity.json. Run `node scripts/verify-sources.mjs` to check them.

The maintained methods paper is a separate, identified edition. It explains the historical method and transfers it to the public Trump archive. The one tutorial corpus has 34,416 posts, June 16, 2015 through January 8, 2021. Its provenance, exact selection and hashes are in docs/data/trump/manifest.json. Dissertation datasets are not part of the release.

Campaign discovery, naming and two-human synthesis are complete. The approved 12-theme codebook, map and original reviewer submission are preserved under docs/data/trump/campaign/. Live calls use that codebook; individual responses and visitor maps do not constitute classifier validation. Development annotation and adjudication are complete for 100 posts. Independent human agreement was 85% (κ = 0.809); all 15 differences were adjudicated. The first development comparison selected LLM (64% agreement) over Boolean (30%). The held-out sample remains unopened; classifier acceptance and presidential prevalence remain pending. The research gates require those inputs before corpus classification and inference. Never compare tutorial output to the dissertation as though the two corpora should yield the same findings.

Source readers: https://topicllm.dev/audit/ . Execution evidence: https://topicllm.dev/validation/ . Agent workflow: REPRODUCE.md and AGENTS.md. Active methods source mapping: docs/paper/source-map.json.

Software validation checks implementation properties: source hashes, data selection, guarded research approvals, classifications, inference, budget controls, downloaded package and website behavior. These checks do not constitute independent scientific replication. Report exact scope whenever describing validation.
