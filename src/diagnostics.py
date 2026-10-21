"""Quick checks before hand-labelling: is the headline flag noisy, and is SQL really rare?

Usage (from the repo root):
    python src/diagnostics.py
Prints a short report. Do not commit the output: it contains headline text.
"""
import pandas as pd

from explore_skills import DATA_ML_HEADLINE
from skills import find_skills

df = pd.read_csv("data/raw/hn_hiring_posts.csv")
df["headline"] = df["headline"].fillna("")
df["text"] = df["text"].fillna("")
flag = df["headline"].str.contains(DATA_ML_HEADLINE)

print("=== 1. Skill shares among all posts and flagged data/ML posts ===")
overall = pd.read_csv("results/skills_overall.csv", index_col=0)
wanted = ["SQL", "Python", "Pandas", "Spark", "Airflow", "dbt", "Snowflake", "PyTorch"]
print((overall.loc[wanted, ["share_all_posts", "share_data_ml_posts"]] * 100).round(1).to_string())

print("\n=== 2. Raw-text cross-check for SQL (not using skills.py) ===")
raw_sql = df["text"].str.contains(r"\bsql\b", case=False, regex=True)
any_sql = df["text"].str.contains("sql", case=False, regex=False)
print(f"posts with the word SQL:           {raw_sql.sum()} ({raw_sql.mean() * 100:.1f}%)")
print(f"posts containing 'sql' anywhere:   {any_sql.sum()} ({any_sql.mean() * 100:.1f}%)  "
      "(includes PostgreSQL, MySQL, NoSQL)")
print(f"flagged data/ML posts with SQL:    {raw_sql[flag].sum()} of {flag.sum()} "
      f"({raw_sql[flag].mean() * 100:.1f}%)")

print("\n=== 3. 25 random flagged headlines (are these really data/ML roles?) ===")
for h in df.loc[flag, "headline"].sample(25, random_state=1):
    print("  " + h[:110])

print("\n=== 4. 15-post skill spot-check ===")
for _, r in df.sample(15, random_state=1).iterrows():
    print(f"  {r['headline'][:80]} -> {sorted(find_skills(r['text']))}")
