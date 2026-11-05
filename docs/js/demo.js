/* demo.js — the TopicLLM demonstration corpus.
 * Loads the open, fully synthetic corpus published in docs/data/ (built by
 * dtm_pipeline/make_demo_data.py): 5,872 posts from 11 fictional brands,
 * Jan 2019 – Jul 2021, with a 250-post human-labeled benchmark and the
 * domain stopword list. Same files the Python pipeline uses by default. */

import { parseCSV } from "./util.js";

export const NONE_LABEL = "The text does not fit into any of these themes";

const DATA = new URL("../data/", import.meta.url);

async function text(name) {
  const resp = await fetch(new URL(name, DATA));
  if (!resp.ok) throw new Error(`could not load ${name} (${resp.status})`);
  return resp.text();
}

export async function loadDemoData() {
  const [corpusCSV, benchCSV, stop] = await Promise.all([
    text("demonstration_corpus.csv"), text("demonstration_benchmark.csv"),
    text("demonstration_stopwords.txt")]);
  const corpus = parseCSV(corpusCSV).rows;
  const benchmark = parseCSV(benchCSV).rows.map(r => ({ tweet: r.tweet, human_label: r.human_label }));
  return { corpus, benchmark, stopwords: stop.trim() };
}
