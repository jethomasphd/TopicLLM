# TopicLLM Python implementation

This is the maintained five-stage research workflow. Read ../REPRODUCE.md for the complete recipe and ../AGENTS.md for the agent contract.

Default input: the public Trump account corpus, 34,416 posts from June 16, 2015 to January 8, 2021. Dissertation datasets and synthetic reconstructions are not distributed. `topicllm --profile quickcheck` verifies the tutorial without calls; `topicllm --profile trump-demo` runs discovery only. `--profile research --stages 2,3` collects names and prepares researcher review; stages 4–5 require actual approval and an independent benchmark.

Configure `PipelineConfig` fields with `--config file.json`; see ../examples/trump-config.json. The initial `themes` list is empty deliberately. Researchers define it after inspecting the evidence. Historical defaults of 50 search draws and 5,000 naming votes are computational parameters, not evidence of validation. Use `--plan` and an explicit `--budget-usd` for paid stages. Twenty naming votes are a declared teaching adaptation.

Each stage writes reviewable artifacts under its own run directory. Never fabricate review or annotations. Preserve unsuccessful outcomes as well as selected results. The browser walkthrough explains and illustrates; this package executes research in your approved environment.
