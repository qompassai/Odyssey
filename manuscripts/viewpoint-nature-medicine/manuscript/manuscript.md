---
title: "Small Is Beautiful: Capable AI for Hospitals That Will Never Have a GPU Farm"
short-title: "Small Is Beautiful"
journal: "Nature Medicine"
article-type: "Comment"
author:
  - name: "Matthew A. Porter"
    orcid: "0000-0002-0302-4812"
---

<!-- Scaffold: diver research.templates.render('nature_medicine', 'Comment', 'markdown', ...)
     adapted to the Comment form (no Abstract/IMRaD; standfirst plus main text). First draft for
     Pax's gate. Bracketed RESULTS PENDING and AUTHOR TO CONFIRM markers are deliberate. -->

# Title Page

Title: Small Is Beautiful: Capable AI for Hospitals That Will Never Have a GPU Farm

Article Type: Comment

Authors: Matthew A. Porter (ORCID 0000-0002-0302-4812), Qompass AI, Spokane, WA, USA. [AUTHOR TO CONFIRM: degrees and affiliation line]

Corresponding author: Matthew A. Porter [AUTHOR TO CONFIRM: postal address and email]

Word counts: Standfirst 52 / Main text 1616 (excluding standfirst, headings, figure legend and references) / References 12 / Figures 1

# Standfirst

Many hospitals will never own the computing that frontier medical AI assumes. Small language models that run on an ordinary processor are beginning to show they can carry real work, and the case for them has to be made, and tested, on what they produce inside the resources a hospital actually has.

# Main Text

In January 2023, the World Health Organization, the World Bank and their partners reported that close to 1 billion people in low- and lower-middle-income countries are served by health-care facilities with unreliable electricity or none at all, and that only about half of hospitals in sub-Saharan Africa have reliable power [1]. These facilities are not waiting for a data centre. They are waiting for a generator, a vaccine refrigerator and a working light. Any plan for artificial intelligence (AI) in medicine that begins with a cluster of graphics processing units (GPUs) has already left them out.

The flagship results in clinical language modelling come from institutions that can afford the hardware. NYUTron, a 109-million-parameter model trained on the notes of a large New York health system, needed 24 NVIDIA A100 GPUs for three weeks of pretraining and 8 A100 GPUs for each six-hour fine-tuning run, and its authors noted that this amount of computation is not commonly accessible to research groups [2]. That is a small model by current standards. The general-purpose systems that dominate public attention are larger again [3], and most hospitals would reach them through a remote service. For a district hospital, a remote service means a reliable connection, a recurring bill and patient text leaving the building, and it may have neither of the first two nor permission for the third. Governance guidance for these systems already names safety, transparency, accountability, privacy and equity as conditions of use [4]. A model that cannot run where the patient is treated fails the last of these before any of the others are tested.

## Small has to be measured

E. F. Schumacher argued in 1973 for technology sized to the people and places that would use it [5]. The same argument applies to clinical AI, with one amendment that matters in medicine: small has to be measured, not assumed. What can a hospital run on the computer it already owns, and how would it know? Not from a parameter count. Our position is that the resource envelope (the bytes on disk, the peak memory and the speed on a processor the facility already owns) is a primary outcome of any clinical AI evaluation, reported beside accuracy, with denominators, and never in a footnote. Local models also keep patient text inside the facility, which removes a privacy question rather than managing it.

We have been measuring this in our own program, Kintsugi, on one workstation, scoring first answers only, at temperature zero, with no re-rolls [6]. The tasks so far are not clinical. They come from a frozen event log of our multi-agent software estate: a structured digest of six log windows, twelve triage labels and six tool calls, each scored by fixed rules against the log itself. That choice was deliberate, because it let us build and debug the measurement discipline on records we own before any patient-derived text enters it. The limits are plain: one machine, one operator's records, tiers of 6, 12 and 6 items, and no clinical text yet. The clinical battery is next, and its results are not in hand [RESULTS PENDING: clinical fixture battery, Trials 2-4].

On a 16-thread laptop-class processor with the GPU unused, every model we tested below 1 GB on disk completed the digest task inside 1.2 to 4.6 GiB of peak memory, at 2 to 5 tokens per second including prompt processing, served by open-source llama.cpp-family software [7]. A six-window digest took between about 3 and 14 minutes. That is slow for a conversation and adequate for work that can wait for a batch, such as an overnight summary or a triage queue. Speed was not the constraint. Production was.

## Reputation is not production

The more useful finding is how poorly reputation predicted production. We scored each model as a player (a plain count of measured successes out of 24, beside its cost in bytes and memory), the way a scout reads a box score rather than a highlight reel. Granite 4.0 1B, the least regarded entry in its family, scored 14 of 24 from a 0.98 GB file and was the only small model whose digests never drifted from the required format. Bonsai-8B, a natively 1-bit model, scored 15 of 24 from 1.16 GB. Its vendor reports 1.15 GB of parameter memory [8], but at our 16,384-token context the server's peak was 6.51 GiB, because weights are not the whole working set.

BitNet b1.58 2B4T, among the best-known native 1-bit models and one published with strong efficiency results [9], scored zero on every tier as shipped, through its own runtime. The single large incumbent, a 30-billion-parameter-class coding model, scored 20 of 24 from an 18.56 GB file. None of these rankings could have been read off a parameter count or a model card.

Several zeros were not model failures at all. Three sizes of one small coding model (0.5, 1.5 and 3 billion parameters) wrote the correct tool call, with the right name and arguments, on 6 of 6 tasks, as plain text that the serving software never recognized, and each scored 0 of 6. When we rebuilt four larger models with a working chat template (the instruction format a model expects) embedded in the model file, three made 6 of 6 parsed calls, and the fourth wrote six correct calls into the text channel and scored 0 of 6. Their unrebuilt versions were never served, so this is not a before-and-after comparison.

Two newer small models spent their entire output budget on hidden reasoning and returned empty answers to all 12 triage items, while making 6 of 6 correct tool calls. A radiology group reported the same budget exhaustion in a 4-billion-parameter model [10]. A hospital that downloads a model, sees a zero and concludes that the model cannot do the job may be looking at a template, a parser or a default setting. Models have to be evaluated as they will be served, and the serving path has to be reported with the score.

## Adaptation is cheap, and training is not running

Where a seat could not be filled by a raw model, adaptation filled it. A low-rank adapter [11] (a small set of extra weights trained on top of a frozen model) trained on 36 examples took the 3-billion-parameter model from 0 to 18 clean digests out of 20 held-out windows, in 24 seconds of training on one workstation GPU, and served through the ordinary runtime it kept 17 of 20. An earlier pilot on an 8-billion-parameter base went from 0 to 19 of 20 [6]. The adapter file is about 30 MB.

Training needs a GPU once. Running does not. For hospitals that division matters, because a regional centre or university can train and validate adapters while a facility with a laptop runs them. Independent clinical work points the same way: radiology adapters on 3- and 4-billion-parameter models, quantized to 1.8 to 2.4 GB, ran on consumer processors at 4 to 8 tokens per second, after about 26 hours of training per model on a single GPU [10].

## Build the team from the statistics

Because the small models failed in different ways, the natural unit is a team, not a model. Our roster rule, fixed before the collaboration trials, fills each seat (digest, triage, tool calls) by measured production per unit cost and never by reputation, parameter count or release date. On the numbers in hand it selects the adapted 3-billion-parameter model for the digest, Bonsai-8B for triage (9 of 12 labels correct) and LFM2.5-1.2B for tool calls (6 of 6 at 1.39 GiB of peak memory). Together their files total about 4.2 GB, 23% of the large model's file (Fig. 1).

Whether the team matches the large model's production on identical fixtures is the question the next trials answer, and we will report it whichever way it falls [RESULTS PENDING: team versus single large model, aggregate production]. This is Moneyball [12] applied to compute: buy the production the statistics show, not the reputation the market prices.

## Keep authority where it can be checked

Small models make mistakes, and so do large ones. In medicine the answer to a model error cannot be trust in a bigger model. In the architecture we use, the models propose and a deterministic record disposes [6], so every model claim that can be checked against the record is checked before anyone acts on it. Bonsai's digest errors, for example, fell almost entirely in claims the record can verify mechanically (class attributions and event pairings), while its count section was right in all six windows.

The models never commit an action, and a clinician decides. Where the record or the serving endpoint fails, the model layer fails closed rather than handing the work to an unverified substitute. These are design rules, and they cost nothing in hardware.

## What we ask of the field

Three changes would let hospitals without GPU farms make these choices on evidence. First, every clinical AI benchmark should report its resource envelope (file size, peak memory and throughput on named, commodity hardware) beside its accuracy, with denominators, so that a reader can tell whether the result exists for them at all. Second, models should be evaluated as served, through the runtime and template a facility would actually use, and serving failures should be reported as findings rather than hidden as model zeros. Third, evaluations should test teams of small models against single large ones on identical clinical fixtures and publish the failure classes, because the useful information is in how models fail differently. Null and negative results belong in the record with the rest. None of this requires new hardware. It requires deciding that the facility with a generator and a laptop is part of the denominator.

Whether a hospital runs on a grid or a generator, the obligation is the same: deploy the smallest system the evidence shows can do the work safely, and publish the evidence.

# Competing Interests

[AUTHOR TO CONFIRM: competing interests, including any interest in Qompass AI and in the Kintsugi software cited as ref. 6.]

# Funding

[AUTHOR TO CONFIRM: funding sources, or "None".]

# Use of Artificial Intelligence

A drafting assistant (Grok Bot) was used to render the author's argument into prose from his notes and run records, and to write the script that draws Fig. 1 from the recorded measurements. The argument, the selection of evidence and the conclusions are the author's. [AUTHOR TO CONFIRM after review: the author has checked every sentence, number and reference and takes responsibility for the content.]

# Data Availability

The measurements cited here come from the author's Kintsugi run records of 17 October 2026 (the small-model tier record and the chat-template rebuild record), which are not yet public. [AUTHOR ACTION before submission: deposit both records with the Kintsugi repository (ref. 6) and cite the deposit here.]

# Figure Legends

**Fig. 1 | The resource envelope, seat by seat.** **a**, Files on disk, drawn to scale. One large coding model (18.56 GB file; 20 of 24 points on our non-clinical coordination battery; served on a workstation GPU, with memory on a processor alone not measured) against the three-seat team chosen by the pre-registered roster rule, whose files total about 4.2 GB, 23% of the large model's file. Whether the team matches the large model's production is not yet measured (RESULTS PENDING). **b**, Each seat with its measured result and its peak memory when run on the processor alone. Digest seat: Qwen2.5-Coder-3B with a 30 MB low-rank adapter (2.10 GB file; 18 of 20 held-out digests clean, 17 of 20 as served; processor-only memory not measured). Triage seat: Bonsai-8B Q1_0 (1.16 GB file; 9 of 12 triage labels; 6.51 GiB peak at a 16,384-token context). Tool seat: LFM2.5-1.2B (0.96 GB file; 6 of 6 parsed tool calls; 1.39 GiB peak). **c**, The authority rule: models propose, a deterministic record checks, a clinician decides, and the model layer fails closed if the record or the serving endpoint fails. All measurements come from one workstation, recorded on 17 October 2026; the tasks are not clinical, and the clinical battery is RESULTS PENDING. Colours are from the Okabe-Ito colour-blind-safe palette. The figure is generated by fig1-resource-envelope.py, which checks every drawn number against the run record before writing.

# References

1. World Health Organization, World Bank, International Renewable Energy Agency & Sustainable Energy for All. *Energizing Health: Accelerating Electricity Access in Health-Care Facilities* (WHO, 2023).
2. Jiang, L. Y. et al. *Nature* **619**, 357–362 (2023).
3. Thirunavukarasu, A. J. et al. *Nat. Med.* **29**, 1930–1940 (2023).
4. World Health Organization. *Ethics and Governance of Artificial Intelligence for Health: Guidance on Large Multi-Modal Models* (WHO, 2024).
5. Schumacher, E. F. *Small Is Beautiful: A Study of Economics as if People Mattered* (Blond & Briggs, 1973).
6. Porter, M. A. Kintsugi. *GitHub* https://github.com/qompassai/kintsugi (2026).
7. ggml-org. llama.cpp. *GitHub* https://github.com/ggml-org/llama.cpp (2026).
8. PrismML. Bonsai-8B-gguf. *Hugging Face* https://huggingface.co/prism-ml/Bonsai-8B-gguf (2026).
9. Ma, S. et al. Preprint at https://arxiv.org/abs/2504.12285 (2025).
10. Gupta, P. & Bose, K. Preprint at https://arxiv.org/abs/2605.00421 (2026).
11. Hu, E. J. et al. Preprint at https://arxiv.org/abs/2106.09685 (2021).
12. Lewis, M. *Moneyball: The Art of Winning an Unfair Game* (W. W. Norton, 2003).
