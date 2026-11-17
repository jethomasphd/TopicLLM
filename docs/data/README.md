# Original Study 1 data

The author has authorized release of the Study 1 alcohol-brand data. This is the website and Python package's default demonstration dataset. Study 2 individual-user data are not included.

The demonstration is an illustrative modern rerun. Topic models and LLMs include probabilistic steps. A fresh run can group or label some posts differently, especially when the random seed, model, or software version changes.

| File | Records | Purpose |
| --- | ---: | --- |
| [study1/collection.csv](study1/collection.csv) | 6,174 | Minimized collection records for tracing preparation |
| [study1/full.csv](study1/full.csv) | 5,872 | Recovered full cohort, including one blank text |
| [study1/analysis.csv](study1/analysis.csv) | 5,871 | Explicit nonempty text-analysis input |
| [study1/discovery.csv](study1/discovery.csv) | 704 | Archived March 25-May 31, 2020 discovery input |
| [study1/stopwords.txt](study1/stopwords.txt) | 32 custom words | Supplied domain stopwords |
| [study1/manifest.json](study1/manifest.json) | — | Hashes, counts, preparation, settings and recorded results |

Fields are stable `post_id`, `brand`, ISO `date` and `tweet`. The discovery file also has `display_text`: readable collection transcription. Its `tweet` field preserves the archived model-input text, including encoding artifacts. The recorded run uses `tweet`, without silent text repair.

Full-cohort preparation: keep the first occurrence of each exact tweet text (267 duplicate rows removed), exclude 20 Topo Chico records and 15 August 2021 records, then retain the archived row order. `retained-order.json` makes that ordering explicit. The package quickcheck verifies the reconstruction. The collected file retains excluded brand posts solely to make preparation inspectable.

The lockdown branch filters March 25-May 31 before deduplication: 742 records become 705 distinct texts, including one blank, then 704 nonempty inputs. It is not interchangeable with filtering the globally deduplicated full corpus. Full-period counts are 1,707 pre, 806 peri, 3,106 post and 253 February records outside those periods; nonempty-text denominators are reported separately when needed.

The recovered CSV, original notebook output and summary workbook agree on all 11 brand counts. Five name/count pairings differ in the printed dissertation table; the PDF is preserved unchanged and the release reports counts directly from the data. The 5,872 total and 11-brand sample align exactly.

The recorded modern discovery evaluated 1,200 candidate results and selected five statistical topics, c_v 0.7803344, with 433/704 outliers. These are not asserted to be the dissertation's five interpreted themes. See [all candidates](study1/all_iteration_results.json), [assignments](study1/discovery-assignments.csv), and [environment](study1/run_manifest.json). Published seven-topic/five-theme findings remain labeled as reported.

No final human benchmark, historical fitted model or historical LLM ballots are asserted by this release. Researchers supply independent annotations for research validation. Live website calls illustrate naming and classification on released records.

Only brand content and research fields are released. Collector identities, emails, administrative timestamps, screenshot links and collection annotations are omitted. No Study 2 user records are included. Public brand text is third-party content; the repository's code and documentation licenses do not relicense that text.

Legacy `demonstration_*`, `study-demo.json`, `reference_run/` and synthetic validation files remain software-test fixtures or historical engineering evidence. They are not the current website demonstration or default research inputs. Their generated labels are never human annotations.
