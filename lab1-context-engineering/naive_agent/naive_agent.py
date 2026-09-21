"""Phase 0 baseline: the deliberately naive agent.

Embeds the question, grabs a big top-15, concatenates every retrieved chunk
verbatim, and asks the model to answer -- no clustering, no selection, no
compression. This is the "before" picture every later pipeline improvement in
this lab is measured against.

Usage (from this folder, with the venv active):
    python naive_agent.py --model mock    # free, instant, for testing plumbing
    python naive_agent.py --model haiku   # real Haiku 4.5 -- costs a little money
"""

import argparse
import json
import sys
from pathlib import Path

# This folder lives outside src/, so point Python at the shared contextlab
# package instead of duplicating embeddings/retrieval/model_client here.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextlab import config
from contextlab.embeddings import embed_texts, load_chunks
from contextlab.model_client import get_model
from contextlab.retrieval import top_k

TOP_K = 15
SYSTEM_PROMPT = (
    "Answer the question using only the context provided below. Be concise: "
    "answer in as few words as possible, using the exact wording/values from "
    "the context where relevant. If the context does not contain the answer, "
    "say \"I don't know.\""
)


def build_prompt(question, retrieved_chunks):
    context_block = "\n\n".join(
        f"[{chunk['source']}]\n{chunk['text']}" for chunk, _ in retrieved_chunks
    )
    return f"Context:\n{context_block}\n\nQuestion: {question}"


def answer_question(question, chunks, chunk_vecs, model):
    retrieved = top_k(question, chunks, chunk_vecs, k=TOP_K)
    prompt = build_prompt(question, retrieved)
    response = model.generate(system=SYSTEM_PROMPT, user_message=prompt)
    return response, retrieved


def load_gold_questions():
    with open(config.GOLD_PATH) as f:
        return json.load(f)["questions"]


def run(model_name, out_path):
    chunks = load_chunks()
    chunk_vecs = embed_texts([c["text"] for c in chunks])
    model = get_model(model_name)
    gold = load_gold_questions()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for item in gold:
            response, retrieved = answer_question(item["question"], chunks, chunk_vecs, model)
            record = {
                "id": item["id"],
                "question": item["question"],
                "reference_answer": item["answer"],
                "tags": item["tags"],
                "model_answer": response.text,
                "retrieved_chunk_ids": [c["id"] for c, _ in retrieved],
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "input_cost": response.cost.input_cost,
                "output_cost": response.cost.output_cost,
                "total_cost": response.cost.total,
                "model": model.name,
            }
            f.write(json.dumps(record) + "\n")
            print(f"{item['id']:>4}  ${response.cost.total:.6f}  {response.text[:70]}")

    total_cost = sum(
        json.loads(line)["total_cost"] for line in open(out_path)
    )
    print(f"\nWrote {len(gold)} runs to {out_path}")
    print(f"Total cost: ${total_cost:.6f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mock", choices=["mock", "haiku"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out_path = (
        Path(args.out) if args.out else config.RESULTS_DIR / f"naive_runs_{args.model}.jsonl"
    )
    run(args.model, out_path)
