"""
config.py — Single source of truth for the democratic topic modeling pipeline.

Defaults follow the maintained methods implementation described in:
Thomas et al. (2026), "TopicLLM: A Human-Guided, Agent-Executable Workflow
for Topic Interpretation and Prevalence Analysis." Change values here, not in the stage scripts,
so a run remains auditable from one file.
"""

import os
from dataclasses import dataclass, field

# The only bundled tutorial corpus is the selected Trump account archive.
# Dissertation datasets are not distributed.
DEMO_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "docs", "data"))
if not os.path.isdir(DEMO_DIR):
    DEMO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


@dataclass
class PipelineConfig:
    run_mode: str = 'research'
    api_budget_usd: float | None = None # explicit authorization before paid calls
    max_api_calls: int = 10000
    gateway_url: str = 'https://topicllm.dev'
    # ----- I/O ---------------------------------------------------------------
    input_csv: str = os.path.join(DEMO_DIR, "trump", "corpus.csv")
    discovery_input_csv: str | None = None  # one corpus for discovery and classification
    output_dir: str = "pipeline_output"        # all stage artifacts land here
    stopwords_file: str = os.path.join(DEMO_DIR, "trump", "stopwords.txt")
    strip_platform_artifacts: bool = True  # decode HTML entities; remove URLs and @handles before tokenization

    # ----- Stage 1: coherence-optimized topic discovery ---------------------
    embedding_model: str = "all-MiniLM-L6-v2"  # SentenceTransformer model
    embedding_revision: str | None = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41" # validated MiniLM snapshot; change for another model
    search_iterations: int = 50                # random hyperparameter draws
    topic_min: int = 2                         # max-topic solutions evaluated:
    topic_max: int = 25                        # range(topic_min, topic_max + 1)
    random_seed: int = 42                      # seeds the search AND each UMAP fit; logged
    seed_umap: bool = True                     # UMAP random_state=random_seed -> reproducible
                                               # runs (umap-learn then runs single-threaded)
    refit_per_solution: bool = False           # False: fit UMAP+HDBSCAN once per sampled
                                               # configuration, then reduce to each maximum
                                               # topic solution (a maintained optimization,
                                               # not historical byte equivalence). True: refit the
                                               # whole model for every solution, as archival S1 did.
    save_visualizations: bool = False          # per-iteration HTML (heavy; final model always saved)

    # UMAP / HDBSCAN sampling spaces (identical to the reference implementation)
    umap_space: dict = field(default_factory=lambda: {
        "n_neighbors": [5, 10, 15, 20, 25, 30, 35],
        "n_components": [3, 4, 5, 6, 7, 8, 9, 10],
        "min_dist": [0.01, 0.05, 0.1, 0.5],
        "metric": ["cosine"],
    })
    hdbscan_space: dict = field(default_factory=lambda: {
        "min_cluster_size": [5, 10, 15, 20, 25, 30, 35],
        "metric": ["euclidean"],
        "cluster_selection_method": ["eom"],
    })

    # ----- Stages 2 & 4: LLM settings ---------------------------------------
    llm_backend: str = "openai"                # "openai", or "mock" for a keyless dry run
                                               # (deterministic stand-in; outputs are labeled
                                               # MOCK and are NOT measurements)
    llm_model: str = "gpt-4o-2024-08-06"                  # pin and report the identifier
    domain_context: str = (
        "posts from the Donald Trump account archive, June 16, 2015 to January 8, 2021, including retweets; describe content neutrally"
    )                                          # domain-specific naming context

    # Stage 2: democratic naming
    votes_per_topic: int = 5000                # reference implementation value
    naming_temperature: float = 0.5
    naming_max_tokens: int = 15
    early_stop: bool = False                   # optional cost control:
    early_stop_window: int = 500               # minimum votes before checking cumulative
    early_stop_share: float = 0.60             # leader share; this is not a convergence test
    max_retries: int = 5                       # exponential backoff on API errors

    # Stage 4: corpus-scale classification
    themes: list = field(default_factory=list)  # supplied by researchers after Stage 3 review
    none_label: str = "The text does not fit into any of these themes"
    classify_temperature: float = 0.5
    classify_max_tokens: int = 120 # maintained safeguard; archival value was 30
    benchmark_csv: str = "human_labels.csv"  # supplied independent annotations; no final study benchmark is asserted
    agreement_threshold: float = 0.85          # do not scale below this
    classify_workers: int = 1                  # concurrent API calls in Stage 4 (raise for
                                               # large corpora, e.g. 8-16, within rate limits)
    checkpoint_every: int = 500                # Stage 4 writes progress every N documents and
                                               # resumes from it after an interruption

    # ----- Stage 5: theme prevalence ----------------------------------------
    # Period boundaries for proportional z-tests (inclusive, YYYY-MM-DD).
    # Requires a 'date' column in the input CSV.
    periods: dict = field(default_factory=lambda: {
        "campaign": ("2015-06-16", "2016-11-08"),
        "transition": ("2016-11-09", "2017-01-19"),
        "presidency": ("2017-01-20", "2021-01-08"),
    })
    alpha: float = 0.05                        # Bonferroni-corrected in stage 5


CONFIG = PipelineConfig()
