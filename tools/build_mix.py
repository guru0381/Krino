#!/usr/bin/env python3
"""Krino mix v1: breadth (Malkuth's commercially licensed sources) + depth (Kev's hard-v1, documents-v1, devtools-v1
training partitions), in Kev's --data format, written where Kev's Modal image ships it:

    uv run --no-sync --project third_party/kev python tools/build_mix.py            # -> third_party/kev/evals/krino-mix-v1/
    uv run --no-sync --project third_party/kev python tools/build_mix.py --only hard-v1,arc   # a subset, for a dry run

Breadth is a fork of newfull5/malkuth `tools/build_train_mix.py` (Apache-2.0; Saechan Oh). Sources that are not
commercially licensed are out: XNLI (CC-BY-NC-4.0), RACE (non-commercial research only), BeaverTails (CC-BY-NC-4.0),
tweet_sentiment_multilingual and sms_spam (no licence). CUAD is CC-BY-4.0 but Malkuth measured it hurting ledgar, so it
is out too. Two eval-only overlaps with our development panel are also out: `deepset/prompt-injections` (devtools-v1's
eval-only prompt_injection source draws from it) and anything in `krino-breadth` (Malkuth's held-out suites). Three
more are out because they overlap our transfer-v4 panel (Kev's eval-only sources): MMMLU (the MMLU test set, translated;
transfer-v4 scores English MMLU test items), PAWS-X English (transfer-v4's paws slice is PAWS test; the other six
languages are kept, they are translations of PAWS train) and XQuAD English (SQuAD dev questions, which GLUE QNLI's dev
split, in transfer-v4, is built from; the ten other languages are kept).

Depth is Kev's own training partitions, read through kev.suite.load_split (fetched from the public kev-suites mirror
and checksum-verified); never the development or test partitions. hard-v1 is repeated (--hard-repeat, default 2):
its seven families are the sealed JevBench families, and the hard tier is where the gap to Malkuth-2B is.

Every record carries _meta.source and _meta.id, so scripts/screen_overlap.py can screen the file against the public
JevBench items before it is used (scripts/build_mix.sh does that).
"""
import argparse, csv, io, json, random, sys, urllib.request
from collections import Counter
from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
KEV = ROOT / "third_party" / "kev"
sys.path.insert(0, str(KEV))
from kev.suite import load_split  # noqa: E402

OUT = KEV / "evals" / "krino-mix-v1"
R = random.Random(0)

# the same option names and wording Malkuth's suites use (build_kev_benchmarks.py), so the breadth panel reads as trained
INTENT = "Which assistant intent best describes this user request?"
MNLI = {"entailment": "The hypothesis follows from the premise", "neutral": "The hypothesis may or may not be true given the premise",
        "contradiction": "The hypothesis contradicts the premise"}
ABCD = ["a", "b", "c", "d"]
FLORES = {"en": "eng_Latn", "ko": "kor_Hang", "ja": "jpn_Jpan", "zh": "zho_Hans", "de": "deu_Latn", "fr": "fra_Latn",
          "es": "spa_Latn", "hi": "hin_Deva", "ar": "arb_Arab", "th": "tha_Thai"}


def human(name):
    return name.replace("_", " ")


def lines(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"}), timeout=120).read().decode()


def pick(eval_wording, paraphrases):
    return eval_wording if R.random() < 0.5 else R.choice(paraphrases)


def sample(ds, n):
    idx = list(range(len(ds))); R.shuffle(idx)
    return [ds[i] for i in idx[:n]]


def choice_q(instr, keys, label, src, desc=None, full=True):
    """keys: option names (already human). full=False -> gold + a random subset of the others, shuffled."""
    if not full:
        others = [k for k in keys if k != label]
        keys = [label] + R.sample(others, min(len(others), R.randint(4, 19))); R.shuffle(keys)
    return {"type": "choice", "instructions": instr, "criteria": {k: (desc or {}).get(k) for k in keys}, "label": label, "src": src}


def noul_q(instr, label, src, criteria=None):
    return {"type": "noul", "instructions": instr, "label": bool(label), "src": src, **({"criteria": criteria} if criteria else {})}


def rec(state, q, source, qid="label"):
    return {"state": state, "questions": {qid: q}, "_meta": {"source": source}}


INTENT_P = ["What does the user want?", "Classify the intent of this request.", "Which intent matches this utterance?",
            "Pick the assistant intent for this message."]
NLI_P = ['Premise and hypothesis: does the premise support the hypothesis "{h}"?', 'How does this statement relate to the text: "{h}"',
         'Hypothesis: "{h}" What is its relation to the premise?']


# ---------- breadth: multilingual intent, NLI, paraphrase, reading comprehension, safety ----------

def massive_intent(n=1000):   # Apache-2.0
    codes = {**{k: k for k in FLORES}, "zh": "zh-CN"}
    en = load_dataset("mteb/amazon_massive_intent", "en")
    keys = sorted({human(x) for x in set(en["train"]["label"]) | set(en["test"]["label"])})
    out = []
    for lang, code in codes.items():
        for ex in sample(load_dataset("mteb/amazon_massive_intent", code, split="train"), n):
            out.append(rec(ex["text"], choice_q(pick(INTENT, INTENT_P), keys, human(ex["label"]), f"mix_massive_{lang}", full=R.random() < 0.7),
                           f"massive_intent/{lang}"))
    return out


def massive_scenario(n=300):   # Apache-2.0; topic-like signal for the held-out sib200
    codes = {**{k: k for k in FLORES}, "zh": "zh-CN"}
    en = load_dataset("mteb/amazon_massive_scenario", "en")
    keys = sorted({human(x) for x in set(en["train"]["label"])})
    return [rec(ex["text"], choice_q(pick("Which scenario does this user request belong to?", ["What domain is this request about?", "Which area does this request concern?"]),
                                     keys, human(ex["label"]), f"mix_scenario_{lang}"), f"massive_scenario/{lang}")
            for lang, code in codes.items() for ex in sample(load_dataset("mteb/amazon_massive_scenario", code, split="train"), n)]


def paws_x(n=700):   # free for any purpose (Google)
    crit = {"true": "Same meaning, possibly reworded", "false": "Different meaning, even if most words match"}
    out = []
    for lang in ("ko", "ja", "zh", "de", "fr", "es"):   # not "en": transfer-v4's paws slice is the English PAWS test split
        for ex in sample(load_dataset("google-research-datasets/paws-x", lang, split="train"), n):
            s2 = ex["sentence2"]
            instr = pick(f'Does this sentence mean the same thing: "{s2}"', [f'Is "{s2}" a paraphrase of this sentence?', f'Do these say the same: "{s2}"'])
            out.append(rec(ex["sentence1"], noul_q(instr, ex["label"] == 1, f"mix_paws_{lang}", crit if R.random() < 0.5 else None), f"paws_x/{lang}"))
    return out


def clinc150(n=3000):   # CC-BY-3.0
    ds = load_dataset("clinc/clinc_oos", "plus", split="train")
    names = [human(x) for x in ds.features["intent"].names]
    desc = {"oos": "The request matches none of the other intents"}
    return [rec(ex["text"], choice_q(pick(INTENT, INTENT_P), names, names[ex["intent"]], "mix_clinc150", desc, full=R.random() < 0.7), "clinc150")
            for ex in sample(ds, n)]


def klue(n=1500):   # CC-BY-SA-4.0; Korean. Half of Malkuth's 3,000 per task: JevBench is English-first
    ynat = load_dataset("klue/klue", "ynat", split="train"); yn = ynat.features["label"].names
    nli = load_dataset("klue/klue", "nli", split="train"); nn = nli.features["label"].names
    out = [rec(ex["title"], choice_q(pick("What is the topic of this news headline?", ["Which news section does this headline belong to?"]), yn, yn[ex["label"]], "mix_klue_ynat"), "klue_ynat")
           for ex in sample(ynat, n)]
    for ex in sample(nli, n):
        h = ex["hypothesis"]
        instr = f'Hypothesis: "{h}" How does it relate to the premise?' if R.random() < 0.5 else R.choice(NLI_P).format(h=h)
        out.append(rec(ex["premise"], choice_q(instr, list(MNLI), nn[ex["label"]], "mix_klue_nli", MNLI), "klue_nli"))
    return out


def nsmc(n=1500):   # CC0-1.0; Korean
    rows = [r for r in csv.DictReader(io.StringIO(lines("https://raw.githubusercontent.com/e9t/nsmc/master/ratings_train.txt")), delimiter="\t", quoting=csv.QUOTE_NONE) if r["document"]]
    R.shuffle(rows)
    return [rec(r["document"], noul_q(pick("Is this movie review positive?", ["Does the reviewer like the movie?", "Is the sentiment of this review positive?"]),
                                      r["label"] == "1", "mix_nsmc"), "nsmc") for r in rows[:n]]


def kobest(n=500):   # CC-BY-SA-4.0; Korean
    out = []
    for ex in sample(load_dataset("skt/kobest_v1", "boolq", split="train"), n):
        out.append(rec(ex["paragraph"], noul_q(f"Based on the passage, is the answer to this question yes: {ex['question']}", ex["label"] == 1, "mix_kobest_boolq"), "kobest/boolq"))
    for ex in sample(load_dataset("skt/kobest_v1", "copa", split="train"), n):
        kind = "cause" if ex["question"] == "원인" else "effect"
        out.append(rec(ex["premise"], choice_q(f"Which option is the more plausible {kind} of the situation?", ["a", "b"], "ab"[ex["label"]], "mix_kobest_copa",
                                               {"a": ex["alternative_1"], "b": ex["alternative_2"]}), "kobest/copa"))
    for ex in sample(load_dataset("skt/kobest_v1", "wic", split="train"), n):
        out.append(rec({"sentence 1": ex["context_1"], "sentence 2": ex["context_2"]},
                       noul_q(f'Is the word "{ex["word"]}" used with the same meaning in both sentences?', ex["label"] == 1, "mix_kobest_wic"), "kobest/wic"))
    for ex in sample(load_dataset("skt/kobest_v1", "hellaswag", split="train"), n):
        out.append(rec(ex["context"], choice_q("Which ending most plausibly continues the text?", ABCD, ABCD[ex["label"]], "mix_kobest_hellaswag",
                                               {k: ex[f"ending_{i + 1}"] for i, k in enumerate(ABCD)}), "kobest/hellaswag"))
    for ex in sample(load_dataset("skt/kobest_v1", "sentineg", split="train"), n):
        out.append(rec(ex["sentence"], noul_q("Is the sentiment of this sentence positive?", ex["label"] == 1, "mix_kobest_sentineg"), "kobest/sentineg"))
    return out


def typed_decisions():   # Apache-2.0: 1,200 cases, teacher labels + soft distributions, target = ½ label + ½ teacher
    out = []
    for r in load_dataset("LocalLLaMA/typed-decisions", "all", split="train"):
        qs = json.loads(r["questions"]) if isinstance(r["questions"], str) else r["questions"]
        gold = json.loads(r["gold"]) if isinstance(r["gold"], str) else r["gold"]
        state = r["state"]
        try: state = json.loads(state)
        except Exception: pass
        questions = {}
        for qid, q in qs.items():
            g, t = gold[qid], q["type"]
            probs = g.get("probabilities") or {}
            if t == "choice":
                label = str(g["label"]); keys = list(q["criteria"])
            elif t == "noul":
                label = str(g["label"]).lower() == "true"; keys = ["false", "true"]
                probs = {"true": float(probs.get("true", g.get("noul", 0.5)))}; probs["false"] = 1 - probs["true"]
            else:
                label = int(g["label"]); keys = [str(i) for i in range(len(q["criteria"]))]
            hard = {k: float(k == (str(label).lower() if t == "noul" else str(label))) for k in keys}
            target = {k: 0.5 * hard[k] + 0.5 * float(probs.get(k, 0.0)) for k in keys} if probs else None
            questions[qid] = {**q, "label": label, "src": f"mix_td_{r['workflow']}", **({"target": target} if target else {})}
        out.append({"state": state, "questions": questions, "_meta": {"source": f"typed_decisions/{r['workflow']}"}})
    return out


def arc(n=1500):   # CC-BY-SA-4.0
    out = []
    for cfg in ("ARC-Challenge", "ARC-Easy"):
        for ex in sample(load_dataset("allenai/ai2_arc", cfg, split="train"), n // 2):
            labels, texts = ex["choices"]["label"], ex["choices"]["text"]
            if ex["answerKey"] not in labels or len(labels) > 5: continue
            keys = [l.lower() for l in labels]
            out.append(rec({"question": ex["question"]}, choice_q("Which option correctly answers the question?", keys, ex["answerKey"].lower(), "mix_arc",
                                                                  dict(zip(keys, texts))), "arc"))
    return out


def toxicity(n=500):   # OpenRAIL++ (use restrictions, commercial use allowed)
    langs = ("en", "de", "es", "zh", "ar", "hi", "fr", "ja", "it", "ru")
    d = load_dataset("textdetox/multilingual_toxicity_dataset")
    out = []
    for lang in langs:
        for ex in sample(d[lang], n):
            instr = pick("Is this text toxic, harmful, or offensive?", ["Does this message contain insults, hate, or abuse?", "Is this post toxic?"])
            out.append(rec(ex["text"], noul_q(instr, ex["toxic"] == 1, f"mix_toxic_{lang}"), f"textdetox/{lang}"))
    return out


def jailbreak():   # Apache-2.0. deepset/prompt-injections is NOT used: devtools-v1's eval-only prompt_injection source is built from it
    return [rec(ex["prompt"][:3000], noul_q(pick("Is this prompt trying to jailbreak an AI assistant?", ["Does this prompt try to make an AI ignore its rules?"]),
                                            ex["type"] == "jailbreak", "mix_jailbreak"), "jailbreak_classification")
            for ex in load_dataset("jackhhao/jailbreak-classification", split="train")]


TOX_LEVELS = ["not toxic", "slightly toxic", "moderately toxic", "very toxic", "extremely toxic"]   # the rtp_lx scale wording


def civil_toxicity(total=5000):   # CC0-1.0: annotator toxicity fraction bucketed into five ordinal levels (Score)
    ds = load_dataset("google/civil_comments", split="train[:400000]")
    cuts = [0.1, 0.3, 0.5, 0.7]
    buckets = {i: [] for i in range(5)}
    for ex in ds:
        if ex["text"].strip(): buckets[sum(ex["toxicity"] >= c for c in cuts)].append(ex["text"])
    weight = {l: len(t) ** 0.5 for l, t in buckets.items()}   # sqrt of natural frequency: most text is not toxic, rare levels still get examples
    quota = {l: round(total * w / sum(weight.values())) for l, w in weight.items()}
    print(f"civil_toxicity natural {dict((l, len(t)) for l, t in buckets.items())} -> quota {quota}", flush=True)
    out = []
    for lvl, texts in buckets.items():
        R.shuffle(texts)
        for t in texts[:quota[lvl]]:
            q = {"type": "score", "instructions": pick("How toxic is this text?", ["Rate how offensive this comment is.", "How toxic is this comment?"]),
                 "criteria": TOX_LEVELS, "label": lvl, "src": "mix_civil_toxicity"}
            out.append(rec(t[:2000], q, "civil_comments"))
    return out


def apeach(n=2000):   # CC-BY-SA-4.0; Korean
    return [rec(ex["text"], noul_q(pick("Is this comment offensive?", ["Is this text hateful or insulting?", "Does this comment contain hate speech?"]), ex["class"] == 1,
                                   "mix_apeach"), "apeach") for ex in sample(load_dataset("jason9693/APEACH", split="train"), n)]


def xquad_mc(per_lang=800):   # CC-BY-SA-4.0: extractive QA -> 4 options (gold span + three answers to other questions on the same paragraph)
    out = []
    for lang in ("de", "es", "ar", "hi", "th", "zh", "vi", "ru", "tr", "el"):   # not "en": SQuAD dev questions, which transfer-v4's qnli slice is built from
        ds = load_dataset("google/xquad", f"xquad.{lang}", split="validation")
        by_ctx = {}
        for ex in ds: by_ctx.setdefault(ex["context"], []).append(ex)
        items = []
        for ctx, qs in by_ctx.items():
            answers = list(dict.fromkeys(q["answers"]["text"][0].strip() for q in qs))
            if len(answers) < 4: continue
            for q in qs:
                gold = q["answers"]["text"][0].strip()
                opts = [gold] + R.sample([a for a in answers if a != gold], 3); R.shuffle(opts)
                items.append(rec({"passage": ctx, "question": q["question"]},
                                 choice_q(pick("Which option correctly answers the question, based on the passage?", ["Choose the answer supported by the passage.", "Answer the question using the passage."]),
                                          ABCD, ABCD[opts.index(gold)], f"mix_xquad_{lang}", dict(zip(ABCD, opts))), f"xquad/{lang}"))
        R.shuffle(items); out += items[:per_lang]
    return out


def aegis(n=6000):   # CC-BY-4.0: prompt- and response-level safety from the Aegis 2.0 *train* split (devtools-v1's dev/test aegis items are its validation/test splits)
    out = []
    for ex in sample(load_dataset("nvidia/Aegis-AI-Content-Safety-Dataset-2.0", split="train"), n):
        qs = {}
        if ex["prompt_label"] in ("safe", "unsafe"):
            qs["prompt_harmful"] = noul_q("Is the user's request harmful?", ex["prompt_label"] == "unsafe", "mix_aegis_prompt")
        resp = ex["response"] if ex["response"] and ex["response_label"] in ("safe", "unsafe") else None
        if resp: qs["response_harmful"] = noul_q("Is the assistant's response harmful?", ex["response_label"] == "unsafe", "mix_aegis_response")
        if qs:
            state = {"user": ex["prompt"][:3000], "assistant": resp[:3000]} if resp else ex["prompt"][:3000]
            out.append({"state": state, "questions": qs, "_meta": {"source": "aegis"}})
    return out


BREADTH = {"massive_intent": massive_intent, "massive_scenario": massive_scenario, "paws_x": paws_x, "clinc150": clinc150, "klue": klue,
           "nsmc": nsmc, "kobest": kobest, "typed_decisions": typed_decisions, "arc": arc, "toxicity": toxicity,
           "jailbreak": jailbreak, "civil_toxicity": civil_toxicity, "apeach": apeach, "xquad_mc": xquad_mc, "aegis": aegis}

# ---------- depth: Kev's own training partitions (the families JevBench's hard tier and sealed set are made of) ----------

DEPTH = {"hard-v1": 2, "documents-v1": 1, "devtools-v1": 1}   # suite -> repeats (overridden by --hard-repeat for hard-v1)


def depth(suite, repeats):
    """Kev's training partition, read the way the trainer reads it (checksum-verified; fetched from the public mirror if
    absent). The suite's own _meta (id, family, source) is kept; a repeat gets a distinct id so the overlap screen and
    the trainer's provenance see two records."""
    recs = load_split(str(KEV / "evals" / suite), "train")
    out = []
    for k in range(repeats):
        for r in recs:
            m = {**r["_meta"], "source": f"{suite}/{r['_meta'].get('family', r['_meta']['source'])}", "suite": suite}
            if k: m["id"] = f"{m['id']}#r{k}"
            out.append({"state": r["state"], "questions": r["questions"], "_meta": m})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated subset of sources (breadth names and/or depth suites), for a dry run")
    ap.add_argument("--hard-repeat", type=int, default=2, help="how many times hard-v1's training partition is included")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    DEPTH["hard-v1"] = a.hard_repeat
    only = set(a.only.split(",")) if a.only else None
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    records, counts, licences = [], {}, {}
    for name, fn in BREADTH.items():
        if only and name not in only: continue
        try: rs = fn()
        except Exception as e:
            print(f"FAILED {name}: {type(e).__name__}: {str(e)[:200]}", flush=True); raise
        for i, r in enumerate(rs): r["_meta"].setdefault("id", f"{name}/{i}")
        records += rs; counts[name] = len(rs)
        print(f"{name:18s} {len(rs):6d}", flush=True)
    for suite, repeats in DEPTH.items():
        if only and suite not in only: continue
        rs = depth(suite, repeats)
        records += rs; counts[suite] = len(rs)
        print(f"{suite:18s} {len(rs):6d}  ({repeats} x {len(rs) // max(repeats, 1)})", flush=True)
    if not records: raise SystemExit("nothing selected")
    R.shuffle(records)
    with (out / "train.jsonl").open("w", encoding="utf-8") as f:
        for r in records: f.write(json.dumps(r, ensure_ascii=True) + "\n")   # ensure_ascii: kev.data.load_records splits lines, U+2028 inside strings would break a record
    qtypes = Counter(q["type"] for r in records for q in r["questions"].values())
    sources = Counter(r["_meta"]["source"].split("/")[0] for r in records)
    (out / "manifest.json").write_text(json.dumps({
        "version": "krino-mix-v1", "records": len(records), "questions": sum(qtypes.values()), "question_types": dict(qtypes),
        "by_builder": counts, "by_source": dict(sorted(sources.items())), "hard_repeat": a.hard_repeat, "seed": 0,
        "breadth_from": "newfull5/malkuth tools/build_train_mix.py (Apache-2.0), commercially licensed sources only",
        "dropped": {"xnli": "CC-BY-NC-4.0", "race": "non-commercial research only", "beavertails": "CC-BY-NC-4.0",
                    "tweet_sentiment": "no licence", "spam": "no licence", "cuad": "CC-BY-4.0 but hurt ledgar in Malkuth's runs",
                    "deepset/prompt-injections": "devtools-v1 eval-only source",
                    "mmmlu": "MMLU test items translated; transfer-v4 scores MMLU test (eval-only in Kev)",
                    "paws_x/en": "transfer-v4 scores PAWS test (eval-only in Kev); other languages kept",
                    "xquad_mc/en": "SQuAD dev questions, the source of GLUE QNLI dev in transfer-v4; other languages kept"},
        "depth_from": "Kev training partitions via kev.suite.load_split (train only; never development or test)",
        "licences": {"massive_intent": "Apache-2.0", "massive_scenario": "Apache-2.0", "paws_x": "free for any purpose (Google)",
                     "clinc150": "CC-BY-3.0", "klue": "CC-BY-SA-4.0", "nsmc": "CC0-1.0", "kobest": "CC-BY-SA-4.0", "typed_decisions": "Apache-2.0",
                     "arc": "CC-BY-SA-4.0", "toxicity": "OpenRAIL++", "jailbreak": "Apache-2.0", "civil_toxicity": "CC0-1.0",
                     "apeach": "CC-BY-SA-4.0", "xquad_mc": "CC-BY-SA-4.0", "aegis": "CC-BY-4.0",
                     "hard-v1": "Kev (Apache-2.0; generated)", "documents-v1": "Kev (CFPB complaints, public domain; labels Apache-2.0)",
                     "devtools-v1": "Kev (permissive per-source, see its manifest)"}}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"TOTAL {len(records)} records, {sum(qtypes.values())} questions {dict(qtypes)} -> {out / 'train.jsonl'}")


if __name__ == "__main__":
    main()
