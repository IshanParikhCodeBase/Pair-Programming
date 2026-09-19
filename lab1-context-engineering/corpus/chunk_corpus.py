"""Reference chunker for the Nimbus corpus.

Splits the markdown docs and source files into retrieval chunks and writes them to
chunks.jsonl (one JSON object per line: {id, source, text}). You are free to
replace this with your own chunking strategy -- it's provided so you have a
working starting point and a reproducible chunk count.

Markdown is split on headings and blank-line paragraphs; source files are split on
blank lines (so each function/comment block is roughly its own chunk). Very short
fragments are dropped, and code fences are kept intact with their surrounding text.

Usage:
    python chunk_corpus.py            # writes chunks.jsonl
    python chunk_corpus.py --stats    # also prints a per-source count
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
FILES = [
    "README.md",
    "docs/getting-started.md",
    "docs/api-reference.md",
    "docs/faq.md",
    "docs/configuration.md",
    "docs/changelog.md",
    "src/client.py",
    "src/worker.py",
]

MIN_CHARS = 80  # drop fragments shorter than this


def split_markdown(text):
    """Split on headings, then on blank lines, keeping paragraphs whole."""
    # Break the doc into sections at headings, keeping the heading with its body.
    sections = re.split(r"\n(?=#{1,6}\s)", text)
    chunks = []
    for section in sections:
        # Within a section, split on blank lines but keep fenced code blocks intact.
        parts = re.split(r"\n\s*\n", section)
        buf = ""
        in_fence = False
        for part in parts:
            fences = part.count("```")
            if in_fence or fences % 2 == 1:
                buf += ("\n\n" if buf else "") + part
                in_fence = (buf.count("```") % 2 == 1)
                if not in_fence:
                    chunks.append(buf)
                    buf = ""
            else:
                if buf:
                    buf += "\n\n" + part
                    chunks.append(buf)
                    buf = ""
                else:
                    chunks.append(part)
        if buf:
            chunks.append(buf)
    return chunks


def split_source(text):
    """Split source files on blank lines into comment/def-sized blocks."""
    return re.split(r"\n\s*\n", text)


def chunk_file(path):
    text = (ROOT / path).read_text()
    raw = split_source(text) if path.endswith(".py") else split_markdown(text)
    out = []
    for c in raw:
        c = c.strip()
        if len(c) >= MIN_CHARS:
            out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--out", default="chunks.jsonl")
    args = ap.parse_args()

    records = []
    per_source = {}
    for path in FILES:
        chunks = chunk_file(path)
        per_source[path] = len(chunks)
        for i, text in enumerate(chunks):
            records.append({"id": f"{path}::{i}", "source": path, "text": text})

    out_path = ROOT / args.out
    with out_path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    print(f"Wrote {len(records)} chunks to {out_path}")
    if args.stats:
        for path, n in per_source.items():
            print(f"  {n:3d}  {path}")


if __name__ == "__main__":
    main()
