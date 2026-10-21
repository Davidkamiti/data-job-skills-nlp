"""Skill dictionary and matcher for job-post text.

Each skill maps to a regular expression. Ambiguous names are handled on purpose:
- "R" and "Go" are left out, because as plain words they match far too much
  ("R&D", "go to market"). They would need context rules, so they are listed
  under LIMITATIONS in the README instead.
- Names that are also ordinary words (Rust, React, Spark, RAG, ML) are matched
  case-sensitively.
- (?i: ... ) turns case-insensitivity on for just that part of a pattern.
"""
import re

SKILL_PATTERNS = {
    # Languages and data tools
    "Python": r"(?i:\bpython\b)",
    "SQL": r"(?i:\bsql\b)",
    "Postgres": r"(?i:\bpostgres(?:ql)?\b)",
    "TypeScript": r"(?i:\btypescript\b)",
    "React": r"\bReact\b",
    "Rust": r"\bRust\b",
    "Pandas": r"(?i:\bpandas\b)",
    "Spark": r"\bPySpark\b|\bApache Spark\b|\bSpark\b(?=\s*(?:[,/;).]|$)|\s+(?:SQL|Streaming|and|or)\b)",
    "Airflow": r"(?i:\bairflow\b)",
    "dbt": r"(?i:\bdbt\b)",
    "Snowflake": r"(?i:\bsnowflake\b)",
    "BigQuery": r"(?i:\bbigquery\b)",
    "Databricks": r"(?i:\bdatabricks\b)",
    "Kafka": r"(?i:\bkafka\b)",
    # Infrastructure
    "Docker": r"(?i:\bdocker\b)",
    "Kubernetes": r"(?i:\bkubernetes\b|\bk8s\b)",
    "Terraform": r"(?i:\bterraform\b)",
    "AWS": r"(?i:\baws\b|\bamazon web services\b)",
    "GCP": r"(?i:\bgcp\b|\bgoogle cloud\b)",
    "Azure": r"(?i:\bazure\b)",
    # ML and AI
    "Machine learning": r"(?i:machine[- ]learning)|\bML\b",
    "Deep learning": r"(?i:deep[- ]learning)",
    "NLP": r"\bNLP\b|(?i:natural language processing)",
    "Computer vision": r"(?i:computer vision)",
    "scikit-learn": r"(?i:scikit[- ]?learn|\bsklearn\b)",
    "PyTorch": r"(?i:\bpytorch\b)",
    "TensorFlow": r"(?i:\btensorflow\b)",
    "JAX": r"\bJAX\b",
    "MLOps": r"(?i:\bmlops\b)",
    "LLM": r"(?i:\bllms?\b|large language models?)",
    "Generative AI": r"(?i:\bgen(?:erative)?[ -]?ai\b|\bgenai\b)",
    "RAG": r"\bRAG\b|(?i:retrieval[- ]augmented)",
    "Embeddings / vector search": r"(?i:\bembeddings?\b|vector (?:database|search|store)s?)",
    "Fine-tuning": r"(?i:fine[- ]?tun(?:e|ed|ing))",
    "Hugging Face": r"(?i:hugging ?face)",
    "LangChain": r"(?i:\blangchain\b)",
    # Analytics and statistics
    "Tableau": r"(?i:\btableau\b)",
    "Power BI": r"(?i:power ?bi\b)",
    "Looker": r"(?i:\blooker\b)",
    "A/B testing": r"(?i:\ba/b test(?:s|ing)?\b|\bexperimentation\b)",
    "Statistics": r"(?i:\bstatistic(?:s|al)?\b)",
}

_COMPILED = {name: re.compile(pat) for name, pat in SKILL_PATTERNS.items()}


def find_skills(text):
    """Return the set of skill names mentioned in `text`."""
    text = text or ""
    return {name for name, rx in _COMPILED.items() if rx.search(text)}
