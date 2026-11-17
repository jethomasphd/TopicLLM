# TopicLLM Python workflow

The package uses original Study 1 brand data by default. Agents execute the workflow and retain evidence; researchers review interpretation and validation. See [the full execution guide](../REPRODUCE.md) for commands and [the data card](../docs/data/README.md) for file provenance.

```sh
topicllm --profile quickcheck --output-dir runs/check
topicllm --profile study1-demo --output-dir runs/study1
```

The quickcheck verifies hashes and cohort preparation without model calls. The study1-demo profile runs local discovery on 704 archived texts. The full release has 5,872 records, including one blank; the separate analysis input has 5,871 nonempty texts. Install the ML extra for discovery. No Study 2 user data are bundled.

Topic models and LLMs include probabilistic steps. Different seeds, models or software versions can change outputs. This is an illustrative rerun, not a promise of identical historical results. Research naming, synthesis, classification and inference retain explicit human-review and benchmark requirements. Synthetic profiles are legacy software fixtures only.
