"""Draw reproducible annotation packets; never generate human labels."""
import csv
import hashlib
import json
import random
from pathlib import Path


def render_annotation_ui(csv_path, codebook_path, output, phase, none_label):
    with open(csv_path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or any(r.get("human_label") for r in rows):
        raise ValueError("Independent annotation interfaces must begin with blank labels.")
    codebook = json.loads(Path(codebook_path).read_text(encoding="utf-8"))
    if not codebook.get('themes') or not codebook.get('decision_rule'):
        raise ValueError('A frozen codebook is required.')
    packet = {"title": "Development annotation" if phase == "development" else "Held-out evaluation annotation",
              "phase": phase, "rows": rows, "codebook": codebook, "none_label": none_label,
              "packet_sha256": hashlib.sha256(Path(csv_path).read_bytes()).hexdigest(),
              "codebook_sha256": hashlib.sha256(Path(codebook_path).read_bytes()).hexdigest()}
    # Escape markup characters so source text can never terminate the JSON block.
    payload=json.dumps(packet,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    template=Path(__file__).with_name('annotation_ui.html').read_text(encoding='utf-8')
    Path(output).write_text(template.replace('__PACKET_JSON__',payload),encoding='utf-8',newline='\n')

if __package__:
    from .sampling import read_selected
else:
    from sampling import read_selected


def draw_packets(cfg, output, development_n=100, evaluation_n=250, seed=20261118):
    target, selection = read_selected(cfg, "target")
    if min(development_n, evaluation_n) < 1 or development_n + evaluation_n > len(target):
        raise ValueError("Annotation sample sizes must be positive and fit the target population.")
    out = Path(output)
    out.mkdir(exist_ok=True, parents=True)
    if (out / "sampling_manifest.json").exists():
        raise ValueError("Annotation packets already exist; never redraw a held-out set silently.")
    rng = random.Random(seed)
    # Draw the evaluation first: simple random sample without replacement from
    # the complete target population. Its texts then stay out of development.
    evaluation = rng.sample(target, evaluation_n)
    test_texts = {row["tweet"] for row in evaluation}
    available = [row for row in target if row["tweet"] not in test_texts]
    if len(available) < development_n:
        raise ValueError("Too few independent texts remain for development.")
    development = rng.sample(available, development_n)
    manifest = {"sampling": selection, "seed": seed,
                "evaluation_design": "simple random sample without replacement; drawn first",
                "development_design": "random sample after excluding all exact evaluation texts",
                "evaluation_n": evaluation_n, "development_n": development_n,
                "development_eligible_n": len(available), "packets": {}}
    for name, rows in [("development", development), ("evaluation", evaluation)]:
        # No predicted or inferred labels are included.
        path = out / f"{name}_blank.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["post_id", "date", "tweet", "human_label", "notes"])
            writer.writeheader()
            writer.writerows({"post_id": r["post_id"], "date": r.get("date", ""), "tweet": r["tweet"], "human_label": "", "notes": ""} for r in rows)
        manifest["packets"][name] = {"ids": [row["post_id"] for row in rows],
                                    "blank_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (out / "sampling_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def adjudication_packet(first, second, output):
    """Retain both actual labels and leave every disagreement unresolved."""
    def read(path):
        with open(path, encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows or any(not r.get("human_label") or not r.get("reviewer") for r in rows):
            raise ValueError("Each independent annotation export needs a label and reviewer.")
        if len({r["post_id"] for r in rows}) != len(rows):
            raise ValueError("Duplicate annotation IDs.")
        return {r["post_id"]: r for r in rows}
    a, b = read(first), read(second)
    if set(a) != set(b):
        raise ValueError("Reviewer packets contain different IDs.")
    rows = []
    for key in a:
        left, right = a[key], b[key]
        if left["tweet"] != right["tweet"] or left["reviewer"].strip().casefold() == right["reviewer"].strip().casefold():
            raise ValueError("Two distinct actual reviewers and identical source texts are required.")
        agreed = left["human_label"] == right["human_label"]
        rows.append({"post_id": key, "date": left.get("date", ""), "tweet": left["tweet"],
                     "reviewer_1": left["reviewer"], "reviewer_2": right["reviewer"],
                     "reviewer_1_label": left["human_label"], "reviewer_2_label": right["human_label"],
                     "human_label": left["human_label"] if agreed else "",
                     "adjudication_note": "Independent agreement" if agreed else "",
                     "reviewer_1_notes": left.get("notes", ""), "reviewer_2_notes": right.get("notes", "")})
    path = Path(output)
    if path.exists():
        raise ValueError("Refusing to overwrite adjudication work.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return {"records": len(rows), "unresolved_disagreements": sum(not r["human_label"] for r in rows)}
