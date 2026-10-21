"""Explore the collected posts: basic stats, skill frequencies and monthly trends.

Usage (from the repo root):
    python src/explore_skills.py

Reads  data/raw/hn_hiring_posts.csv
Writes aggregated tables to results/ and charts to results/figures/.
Only aggregates are written there, so they are safe to commit.
"""
import argparse
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from skills import SKILL_PATTERNS, find_skills

# Weak label: does the HEADLINE (first line of the post) look like a data/ML role?
# Headlines include the company name, so this is noisy ("Acme AI | Frontend Engineer"
# would match). Week 3 measures how noisy it is using a hand-labelled gold set.
DATA_ML_HEADLINE = re.compile(
    r"data scien|data engineer|data analy|machine learning|\bML\b|\bAI\b|\bLLM\b|\bNLP\b|"
    r"research scien|applied scien|mlops|analytics engineer",
    re.IGNORECASE,
)
MIN_POSTS_FOR_MONTH_ESTIMATE = 20


def pct(series):
    return f"{series.mean() * 100:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/hn_hiring_posts.csv")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()

    out = Path(args.out)
    (out / "figures").mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.data)
    df["text"] = df["text"].fillna("")
    df["headline"] = df["headline"].fillna("")
    months = sorted(df["thread_month"].unique())

    # ---- 1. Basic descriptive statistics --------------------------------
    flags = {
        "mentions remote": df["text"].str.contains(r"\bremote\b", case=False),
        "mentions onsite": df["text"].str.contains(r"\bon-?site\b", case=False),
        "mentions hybrid": df["text"].str.contains(r"\bhybrid\b", case=False),
        "mentions a salary figure": df["text"].str.contains(r"[$€£]\s?\d|\b\d{2,3}\s?k\b", case=False),
    }
    df["is_data_ml"] = df["headline"].str.contains(DATA_ML_HEADLINE)

    print(f"Posts: {len(df)} across {len(months)} months ({months[0]} to {months[-1]})")
    print(f"Post length: median {int(df['text'].str.len().median())} characters, "
          f"90th percentile {int(df['text'].str.len().quantile(.9))}")
    for name, flag in flags.items():
        print(f"  {name}: {pct(flag)}")
    print(f"  headline looks data/ML (weak label): {pct(df['is_data_ml'])} "
          f"({int(df['is_data_ml'].sum())} posts)")

    month_counts = (df.groupby("thread_month")
                    .agg(posts=("post_id", "size"), data_ml_posts=("is_data_ml", "sum")))
    month_counts.to_csv(out / "month_counts.csv")
    print("\nPosts per month (all / data-ML headline):")
    print(month_counts.to_string())

    # ---- 2. Skill extraction --------------------------------------------
    skill_sets = df["text"].apply(find_skills)
    skills_df = pd.DataFrame(
        {name: skill_sets.apply(lambda s, n=name: n in s) for name in SKILL_PATTERNS})
    skills_df["thread_month"] = df["thread_month"]
    skills_df["is_data_ml"] = df["is_data_ml"]

    skill_cols = list(SKILL_PATTERNS)
    overall = pd.DataFrame({
        "share_all_posts": skills_df[skill_cols].mean(),
        "share_data_ml_posts": skills_df.loc[skills_df["is_data_ml"], skill_cols].mean(),
        "n_all": skills_df[skill_cols].sum(),
        "n_data_ml": skills_df.loc[skills_df["is_data_ml"], skill_cols].sum(),
    }).sort_values("share_data_ml_posts", ascending=False)
    overall.round(4).to_csv(out / "skills_overall.csv")

    print("\nTop 15 skills in data/ML-headline posts (share of those posts):")
    print((overall.head(15)[["share_data_ml_posts", "share_all_posts"]] * 100).round(1).to_string())

    # ---- 3. Monthly trends (share of ALL posts per month) ---------------
    by_month = skills_df.groupby("thread_month")[skill_cols].mean()
    by_month.round(4).to_csv(out / "skills_by_month_all.csv")
    by_month_ml = skills_df[skills_df["is_data_ml"]].groupby("thread_month")[skill_cols].mean()
    by_month_ml.round(4).to_csv(out / "skills_by_month_data_ml.csv")

    # ---- 4. Figures -----------------------------------------------------
    top = overall.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 6))
    pos = range(len(top))
    ax.barh([p + 0.2 for p in pos], top["share_data_ml_posts"] * 100, height=0.4,
            label=f"Data/ML headline posts (n={int(df['is_data_ml'].sum())})", color="#2a6f97")
    ax.barh([p - 0.2 for p in pos], top["share_all_posts"] * 100, height=0.4,
            label=f"All posts (n={len(df)})", color="#adb5bd")
    ax.set_yticks(list(pos))
    ax.set_yticklabels(top.index)
    ax.set_xlabel("% of posts mentioning the skill")
    ax.set_title("Most requested skills in Hacker News hiring posts")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(out / "figures" / "top_skills.png", dpi=150)
    plt.close(fig)

    trend_skills = list(dict.fromkeys(["LLM", "RAG"] + list(overall.head(4).index)))[:6]
    smooth = (by_month[trend_skills] * 100).rolling(3, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(9, 5))
    for s in trend_skills:
        ax.plot(smooth.index, smooth[s], marker="o", label=s)
    ax.set_ylabel("% of all posts (3-month rolling average)")
    ax.set_title("How demand for selected skills changed over time")
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5))   # outside, so it hides no data
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    lo, hi = int(month_counts["posts"].min()), int(month_counts["posts"].max())
    fig.text(0.01, 0.005,
             f"Each month rests on {lo}-{hi} posts; shifts of a few points can be sampling noise.",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "figures" / "skill_trends.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    thin = month_counts[month_counts["data_ml_posts"] < MIN_POSTS_FOR_MONTH_ESTIMATE]
    if len(thin):
        print(f"\nNote: {len(thin)} month(s) have fewer than {MIN_POSTS_FOR_MONTH_ESTIMATE} "
              "data/ML-headline posts, so month-level data/ML shares are noisy. "
              "Trend charts therefore use all posts and a rolling average.")
    print(f"\nWrote tables and figures to {out}/")


if __name__ == "__main__":
    main()
