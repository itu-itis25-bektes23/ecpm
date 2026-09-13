"""E1 across many seeds for one model. GPU script for Colab or any CUDA box.

Consumes payload files from gen_payloads.py and writes one jsonl line
per seed with the raw model replies for all three arms. Scoring is not
done here, rescore_e1.py --batch does it officially afterwards.

Colab use: upload this file and the payloads folder, then
  %pip install -q transformers peft datasets accelerate bitsandbytes
  %run e1_batch.py payloads --model Qwen/Qwen2.5-1.5B-Instruct

Resumable: seeds already present in the out file are skipped, so a
timed-out session continues where it stopped.

⚠️ Honest status: written to mirror the notebook cells that ran
successfully on Colab (same generation call, same QLoRA recipe), but
this exact file has not executed on a GPU. Expect at most small
first-run fixes, report tracebacks.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re


def extract_last_json(text):
    depth, start, last = 0, None, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                last = text[start:i + 1]
    if last is None:
        return None
    try:
        return json.loads(last)
    except json.JSONDecodeError:
        try:
            return json.loads(re.sub(r",\s*}", "}", last))
        except json.JSONDecodeError:
            return None


SYSTEM = ("You answer questions about a courier network from observation "
          "logs. Reply with exactly one JSON object and nothing else.")
MAX_NEW_TOKENS = 400


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("payload_dir")
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--arms", default="none,icl,ft,combo")
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--ft-seed", type=int, default=7)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    arms = args.arms.split(",")
    tag = args.model.split("/")[-1]
    out_path = args.out or f"answers_{tag}_ftseed{args.ft_seed}.jsonl"

    done = set()
    if os.path.exists(out_path):
        for line in open(out_path):
            done.add(json.loads(line)["seed"])
        print(f"resuming, {len(done)} seeds already in {out_path}")

    import torch
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig, Trainer, TrainingArguments,
                              DataCollatorForLanguageModeling)
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from datasets import Dataset

    bnb = BitsAndBytesConfig(load_in_4bit=True,
                             bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16)
    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def load_base():
        return AutoModelForCausalLM.from_pretrained(
            args.model, quantization_config=bnb, device_map="auto")

    def ask(model, question, evidence=None):
        user = (evidence + "\n\n" + question) if evidence else question
        msgs = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": user}]
        try:
            enc = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                          return_tensors="pt",
                                          return_dict=True)
        except Exception:
            merged = [{"role": "user", "content": SYSTEM + "\n\n" + user}]
            enc = tok.apply_chat_template(merged, add_generation_prompt=True,
                                          return_tensors="pt",
                                          return_dict=True)
        enc = enc.to(model.device)
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=MAX_NEW_TOKENS,
                                 do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        return tok.decode(out[0, enc["input_ids"].shape[1]:],
                          skip_special_tokens=True)

    def probes(model, questions, evidence=None):
        return {name: {"raw": ask(model, q, evidence),
                       }
                for name, q in questions.items()}

    def finetune(evidence_text, seed):
        model = prepare_model_for_kbit_training(load_base())
        lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                          bias="none", task_type="CAUSAL_LM",
                          target_modules=["q_proj", "k_proj", "v_proj",
                                          "o_proj", "gate_proj", "up_proj",
                                          "down_proj"])
        model = get_peft_model(model, lora)
        ids = tok(evidence_text)["input_ids"]
        ds = Dataset.from_dict({"input_ids": [ids]})
        targs = TrainingArguments(output_dir="ft_tmp", seed=seed,
                                  num_train_epochs=args.epochs,
                                  learning_rate=args.lr,
                                  per_device_train_batch_size=1,
                                  logging_steps=50, report_to=[],
                                  save_strategy="no")
        Trainer(model=model, args=targs, train_dataset=ds,
                data_collator=DataCollatorForLanguageModeling(
                    tok, mlm=False)).train()
        model.eval()
        return model

    base = load_base() if ("icl" in arms or "none" in arms) else None
    files = sorted(glob.glob(os.path.join(args.payload_dir, "payload_*.json")))
    print(f"{len(files)} payload files, model {args.model}, arms {arms}")
    for path in files:
        p = json.load(open(path))
        if p["seed"] in done:
            continue
        evidence = p["shared_context"]
        questions = p["questions"]
        row = {"seed": p["seed"], "deterministic": p["deterministic"],
               "k": p["k"], "model": args.model, "ft_seed": args.ft_seed,
               "evidence_sha1": hashlib.sha1(evidence.encode()).hexdigest()}
        if "none" in arms:
            row["none"] = probes(base, questions, None)
        if "icl" in arms:
            row["icl"] = probes(base, questions, evidence)
        if "ft" in arms or "combo" in arms:
            ft_model = finetune(evidence, args.ft_seed)
            if "ft" in arms:
                row["ft"] = probes(ft_model, questions, None)
            if "combo" in arms:
                row["combo"] = probes(ft_model, questions, evidence)
            del ft_model
            torch.cuda.empty_cache()
        with open(out_path, "a") as f:
            f.write(json.dumps(row) + "\n")
        print(f"seed {p['seed']} done")
    print(f"all done, answers in {out_path}")


if __name__ == "__main__":
    main()
