/* preprocess.js — Stage 1 text preparation (browser port of the Python
 * reference: non-alphabetic removal, lowercasing, tokenization, stopword
 * removal, lemmatization). The WordNet POS-aware lemmatizer is approximated
 * with rule-based English inflection stripping; the approximation is
 * documented in the app's Help tab. */

/** NLTK English stopword list (the reference implementation's base list). */
export const NLTK_STOPWORDS = new Set(("i me my myself we our ours ourselves you your yours yourself yourselves " +
  "he him his himself she her hers herself it its itself they them their theirs themselves what which who whom " +
  "this that these those am is are was were be been being have has had having do does did doing a an the and but " +
  "if or because as until while of at by for with about against between into through during before after above " +
  "below to from up down in out on off over under again further then once here there when where why how all any " +
  "both each few more most other some such no nor not only own same so than too very s t can will just don should " +
  "now d ll m o re ve y ain aren couldn didn doesn hadn hasn haven isn ma mightn mustn needn shan shouldn wasn " +
  "weren won wouldn").split(/\s+/));

const VOWELS = new Set(["a", "e", "i", "o", "u"]);

function isCVC(stem) {
  // consonant-vowel-consonant ending (and last consonant not w/x/y):
  // the classic e-restoration heuristic (lov -> love, mak -> make).
  if (stem.length < 3) return false;
  const [c1, v, c2] = [stem[stem.length - 3], stem[stem.length - 2], stem[stem.length - 1]];
  return !VOWELS.has(c1) && VOWELS.has(v) && !VOWELS.has(c2) && !"wxy".includes(c2);
}

/** Rule-based lemmatizer approximating WordNet noun/verb lemmatization. */
export function lemmatize(word) {
  let w = word;
  // plural nouns / 3rd-person verbs
  if (w.length > 4 && w.endsWith("ies")) return w.slice(0, -3) + "y";
  if (w.length > 4 && (w.endsWith("sses") || w.endsWith("shes") || w.endsWith("ches") || w.endsWith("xes") || w.endsWith("zes"))) {
    return w.slice(0, -2);
  }
  if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss") && !w.endsWith("us") && !w.endsWith("is")) {
    return w.slice(0, -1);
  }
  // progressive / past forms
  for (const suf of ["ing", "ed"]) {
    if (w.length > suf.length + 3 && w.endsWith(suf)) {
      let stem = w.slice(0, -suf.length);
      if (stem.length >= 3 && stem[stem.length - 1] === stem[stem.length - 2] &&
          !VOWELS.has(stem[stem.length - 1]) && !"ls".includes(stem[stem.length - 1])) {
        stem = stem.slice(0, -1);          // stopp -> stop
      } else if (isCVC(stem)) {
        stem = stem + "e";                 // lov -> love
      }
      return stem;
    }
  }
  return w;
}

/** Build the combined stopword set from a comma-separated custom list. */
export function buildStopwords(customText) {
  const custom = (customText || "").split(/[,\n]/).map(w => w.trim().toLowerCase()).filter(Boolean);
  return new Set([...NLTK_STOPWORDS, ...custom]);
}

/** tweet -> cleaned string (mirrors the Python preprocess()). */
export function preprocessDoc(text, stopwords) {
  const cleaned = String(text).replace(/[^a-zA-Z]/g, " ").replace(/\s+/g, " ").trim().toLowerCase();
  const tokens = cleaned.split(" ").filter(t => t.length >= 2 && !stopwords.has(t));
  return tokens.map(lemmatize).join(" ");
}

/** Preprocess a corpus; drops rows that become empty (like the reference). */
export function preprocessCorpus(rows, textCol, stopwords) {
  const kept = [];
  for (const row of rows) {
    const pre = preprocessDoc(row[textCol], stopwords);
    if (pre.trim() !== "") kept.push({ ...row, preprocessed: pre });
  }
  return kept;
}
