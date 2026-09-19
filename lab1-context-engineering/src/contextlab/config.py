"""Paths, env loading, and shared constants for the lab."""

from pathlib import Path
from dotenv import load_dotenv

LAB_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = LAB_ROOT.parent

load_dotenv(REPO_ROOT / ".env")

CORPUS_DIR = LAB_ROOT / "corpus"
CHUNKS_PATH = CORPUS_DIR / "chunks.jsonl"
GOLD_PATH = CORPUS_DIR / "gold_questions.json"
RESULTS_DIR = LAB_ROOT / "results"

HAIKU_MODEL_NAME = "claude-haiku-4-5-20251001"
HAIKU_CONTEXT_WINDOW = 200_000
HAIKU_MAX_OUTPUT = 64_000
