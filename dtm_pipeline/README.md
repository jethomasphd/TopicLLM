# TopicLLM Python implementation

Read [REPRODUCE.md](../REPRODUCE.md), [AGENTS.md](../AGENTS.md) and the [standalone methods](https://topicllm.dev/paper/). The scripts execute the analysis; humans supply interpretation and independent annotation.

The campaign application uses one public Trump archive with two disjoint temporal views. `topicllm --profile quickcheck` checks the canonical source without calls. `topicllm --profile trump-demo` discovers topics only in the 7,805 campaign posts (2015-06-16–2016-11-08). The target is the 26,239 presidential posts (2017-01-20–2021-01-08). Generic `PipelineConfig` requires explicit windows for that design; use [the campaign configuration](../examples/campaign-presidency-config.json).

Stage 1 retains all candidate evidence and the numerical coherence winner. Researchers inspect model quality and record any alternative selection. Stage 2 collects a declared vote budget; Stage 3 prepares actual human synthesis. The codebook and theme map must be reviewed by two real people.

Stage 4 has three separate actions: `development` selects a classifier, `validate` tests the frozen choice against held-out human annotations, and `classify` scales only after actual acceptance. Stage 5 reports overall target-corpus prevalence, including the residual and zero-count themes. Period comparisons and pairwise tests are opt-in; this application requests overall prevalence only.

Use `--plan` before paid stages and an explicitly approved `--budget-usd`. The example uses 500 naming responses/topic, a 32-token output ceiling and 12 bounded workers; the generic fixed-vote default remains 5,000. Neither setting provides scientific approval. Keep credentials private and preserve raw responses, failures, costs and configuration.

`annotations.py` draws independent packets and merges real reviewer exports without resolving disagreements itself. Its standalone local interface displays no model predictions. An agent must never generate the human benchmark or approve its own output.
