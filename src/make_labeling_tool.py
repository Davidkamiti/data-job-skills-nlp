"""Build a local labelling page for the hand-labelled "gold" set.

Usage (from the repo root):
    python src/make_labeling_tool.py
Then open  data/labeling/label_tool.html  in your browser (double-click it).

Sampling is stratified so the gold set contains enough real data/ML posts:
  - 100 posts the headline rule flags as data/ML
  - 140 posts it does not flag
Posts are shuffled and the rule's flag is NEVER shown while labelling, so your
labels are not influenced by it. The strata are saved in a separate manifest,
used later to weight the metrics back to the real mix of posts.

Privacy: label_tool.html contains post text, so keep it out of GitHub
(data/labeling/ is gitignored). Only post ids and labels go in the repo.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from explore_skills import DATA_ML_HEADLINE

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gold-set labelling</title>
<style>
  :root { --bg:#ffffff; --fg:#1f2328; --muted:#59636e; --card:#f6f8fa; --line:#d1d9e0;
          --accent:#2a6f97; --ok:#1a7f37; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0d1117; --fg:#e6edf3; --muted:#9198a1; --card:#161b22; --line:#30363d;
            --accent:#58a6ff; --ok:#3fb950; } }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
  main { max-width:900px; margin:0 auto; padding:16px; }
  h1 { font-size:20px; margin:0 0 4px; }
  .bar { height:8px; background:var(--card); border:1px solid var(--line); border-radius:6px; overflow:hidden; }
  .bar > div { height:100%; background:var(--accent); width:0%; }
  .meta { display:flex; justify-content:space-between; color:var(--muted); font-size:14px; margin:6px 0 12px; }
  details { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:8px 12px; margin-bottom:12px; }
  summary { cursor:pointer; font-weight:600; }
  #post { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:14px;
          white-space:pre-wrap; word-wrap:break-word; max-height:52vh; overflow:auto; }
  .buttons { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:12px 0; }
  button { font:inherit; padding:12px 8px; border-radius:8px; border:1px solid var(--line);
           background:var(--card); color:var(--fg); cursor:pointer; }
  button:hover { border-color:var(--accent); }
  button.chosen { outline:2px solid var(--ok); }
  button kbd { display:block; font-size:12px; color:var(--muted); }
  .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
  .small { font-size:14px; color:var(--muted); }
  @media (max-width:560px) { .buttons { grid-template-columns:repeat(2,1fr); } }
</style>
</head>
<body>
<main>
  <h1>Gold-set labelling</h1>
  <div class="bar"><div id="fill"></div></div>
  <div class="meta"><span id="pos"></span><span id="counts"></span></div>

  <details>
    <summary>Labelling rules (read before starting)</summary>
    <p><b>1 = data/ML role.</b> At least one role in the post is mainly data science, data engineering, data analysis,
       or building ML/AI models and systems (this includes "AI Engineer" and "ML Engineer").</p>
    <p><b>0 = other role.</b> Software, product, sales, ops and similar, including "AI Fullstack Engineer" or
       "AI Product Engineer", and any role at a company with "AI" in its name that is not a data/ML role.</p>
    <p><b>U = unsure.</b> You cannot decide in about 20 seconds. <b>X = not a job post.</b></p>
    <p><b>Several roles in one post:</b> label 1 if ANY listed role is data/ML.</p>
    <p class="small">Judge the roles being hired for, not the company's industry. Go with your first judgement and keep moving.</p>
  </details>

  <div id="post"></div>

  <div class="buttons">
    <button data-v="1">Data/ML role<kbd>press 1</kbd></button>
    <button data-v="0">Other role<kbd>press 0</kbd></button>
    <button data-v="U">Unsure<kbd>press U</kbd></button>
    <button data-v="X">Not a job post<kbd>press X</kbd></button>
  </div>

  <div class="row">
    <button id="back" style="padding:8px 14px">&larr; Back (B)</button>
    <button id="download" style="padding:8px 14px">Download labels CSV</button>
    <span class="small" id="saved"></span>
  </div>
  <p class="small">Progress saves automatically in this browser. Download the CSV now and then as a backup,
     and again when you finish.</p>
</main>

<script>
const POSTS = __DATA__;
const STORE_KEY = "gold_labels_v1_" + POSTS.length + "_" + POSTS[0].id;
let labels = {};
try { labels = JSON.parse(localStorage.getItem(STORE_KEY) || "{}"); } catch (e) { labels = {}; }

let idx = POSTS.findIndex(p => !(String(p.id) in labels));
if (idx === -1) idx = POSTS.length - 1;

function save() {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(labels)); } catch (e) {}
}

function counts() {
  const c = {"1":0, "0":0, "U":0, "X":0};
  Object.values(labels).forEach(v => { if (v in c) c[v]++; });
  return c;
}

function render() {
  const done = Object.keys(labels).length;
  const p = POSTS[idx];
  const allDone = done >= POSTS.length;
  document.getElementById("post").textContent = p.text;
  document.getElementById("post").scrollTop = 0;
  document.getElementById("pos").textContent =
    "Post " + (idx + 1) + " of " + POSTS.length + (allDone ? "  -  all done, download your CSV" : "");
  document.getElementById("fill").style.width = (100 * done / POSTS.length) + "%";
  const c = counts();
  document.getElementById("counts").textContent =
    "data/ML " + c["1"] + "  other " + c["0"] + "  unsure " + c["U"] + "  not-job " + c["X"];
  const current = labels[String(p.id)];
  document.querySelectorAll(".buttons button").forEach(b =>
    b.classList.toggle("chosen", b.dataset.v === current));
}

function setLabel(v) {
  labels[String(POSTS[idx].id)] = v;
  save();
  document.getElementById("saved").textContent = "Saved";
  if (idx < POSTS.length - 1) idx++;
  render();
}

function back() { if (idx > 0) { idx--; render(); } }

function downloadCsv() {
  const rows = ["post_id,label"];
  POSTS.forEach(p => { const v = labels[String(p.id)]; if (v) rows.push(p.id + "," + v); });
  const blob = new Blob([rows.join("\n") + "\n"], {type: "text/csv"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "gold_labels.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

document.querySelectorAll(".buttons button").forEach(b =>
  b.addEventListener("click", () => setLabel(b.dataset.v)));
document.getElementById("back").addEventListener("click", back);
document.getElementById("download").addEventListener("click", downloadCsv);
document.addEventListener("keydown", e => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === "1" || k === "0") setLabel(k);
  else if (k === "u") setLabel("U");
  else if (k === "x") setLabel("X");
  else if (k === "b" || e.key === "ArrowLeft" || e.key === "Backspace") { e.preventDefault(); back(); }
});
render();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/hn_hiring_posts.csv")
    ap.add_argument("--flagged", type=int, default=100)
    ap.add_argument("--unflagged", type=int, default=140)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    df["headline"] = df["headline"].fillna("")
    df["text"] = df["text"].fillna("")
    df["flagged"] = df["headline"].str.contains(DATA_ML_HEADLINE)

    flagged = df[df["flagged"]]
    unflagged = df[~df["flagged"]]
    print(f"Posts: {len(df)}  flagged by rule: {len(flagged)}  not flagged: {len(unflagged)}")

    sample = pd.concat([
        flagged.sample(min(args.flagged, len(flagged)), random_state=args.seed),
        unflagged.sample(min(args.unflagged, len(unflagged)), random_state=args.seed),
    ]).sample(frac=1, random_state=args.seed).reset_index(drop=True)   # shuffled

    gold_dir = Path("data/gold")
    tool_dir = Path("data/labeling")
    gold_dir.mkdir(parents=True, exist_ok=True)
    tool_dir.mkdir(parents=True, exist_ok=True)

    # Manifest: ids and strata only (no text), safe to commit
    manifest = sample[["post_id", "flagged"]].rename(columns={"flagged": "rule_flagged"})
    manifest["stratum_size"] = manifest["rule_flagged"].map(
        {True: len(flagged), False: len(unflagged)})
    manifest.to_csv(gold_dir / "sample_manifest.csv", index=False)

    data = [{"id": int(r.post_id), "text": r.text} for r in sample.itertuples()]
    payload = json.dumps(data, ensure_ascii=True).replace("</", "<\\/")
    (tool_dir / "label_tool.html").write_text(PAGE.replace("__DATA__", payload), encoding="utf-8")

    print(f"Wrote {len(sample)} posts to {tool_dir / 'label_tool.html'}")
    print(f"Wrote {gold_dir / 'sample_manifest.csv'}")
    print("Open label_tool.html in your browser and start labelling.")


if __name__ == "__main__":
    main()
