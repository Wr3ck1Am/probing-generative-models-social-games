# Probing Generative Models Through Adversarial Social Games

**UCSD ECE 285 Deep Generative Models -- Final Project (Winter 2025)**

## Overview

This project uses the social deduction game *Among Us* as a testbed to investigate the cognitive capabilities of large language models in adversarial, multi-agent settings. We focus on three axes: **deception** (generation and detection), **memory utilization**, and **strategic reasoning**.

**Research question:** What cognitive capabilities do generative models exhibit in game environments that require deception, reasoning, and social interaction?

## Repository Structure

```
.
├── amongagents/                # Core simulation code
│   ├── agent.py                # LLM agent (OpenAI function calling)
│   ├── random_agent.py         # Random baseline agent
│   ├── game_state.py           # Game state & initialization
│   ├── game_map.py             # 14-room map graph
│   ├── main.py                 # Game loop
│   ├── config.py               # Experiment configs & personality archetypes
│   ├── logger.py               # Per-game JSON logger
│   ├── run_experiments.py      # Batch runner
│   ├── run_additional.py       # Append runs to existing experiments
│   ├── test_map.py             # Quick map sanity check
│   ├── test_state.py           # Quick state sanity check
│   ├── requirements.txt
│   └── analysis/
│       ├── win_rates.py        # Win-rate stats & bar charts
│       ├── ablations.py        # Memory / planning ablation plots
│       ├── conversation_analysis.py   # LLM-based speech classification
│       ├── controlled_eval.py  # 5-dimension cognitive evaluation
│       └── run_all.py          # Run all analyses in sequence
├── report/
│   ├── final_report.tex        # Paper source (NeurIPS format)
│   └── final_report.pdf
├── agent_map.py                # Standalone agent navigation demo
├── test_hello.py               # API connectivity smoke test
└── 285midtermreport.pdf
```

## Game Design

- **Map:** 14-room connected graph mirroring the Among Us Skeld layout.
- **Players:** 4 Crewmates + 1 Impostor, each controlled by an LLM or random agent.
- **Win conditions:** Crewmates win by voting out the Impostor or completing all tasks; Impostor wins by eliminating enough Crewmates or running out the clock.
- **Meetings:** Triggered every 5 task turns or upon body discovery. Each meeting has 2 discussion rounds + 1 voting round.

## Agent Architecture

The LLM agent wraps OpenAI GPT function calling with:

- **Observation serializer** -- encodes location, co-located players, dead bodies, adjacent rooms, and task status into a text prompt.
- **Rolling memory buffer** -- stores recent observations and actions; older entries are compressed via LLM summarization.
- **Personality system** -- 10 archetypes (5 Impostor, 5 Crewmate) injected into the system prompt.
- **ReAct prompting** -- optional `[THOUGHT] -> [PLAN] -> [ACTION]` chain-of-thought before tool calls.

## Experiments

| Config | Crewmate | Impostor | Purpose |
|---|---|---|---|
| `all_random` | Random | Random | Baseline |
| `all_llm` | LLM | LLM | Full LLM vs LLM |
| `llm_crew` | LLM | Random | Test deception *detection* |
| `llm_impostor` | Random | LLM | Test deception *generation* |

**Ablations:**
- Memory size: {0, 5, 10, 20}
- Planning: ReAct on / off

## Key Findings

1. **Deception asymmetry** -- LLM Crewmates reach 93% win rate against Random Impostors but only 36% against LLM Impostors. Deception generation outpaces detection.
2. **Memory matters** -- Crewmate win rate scales sharply with memory (0 -> 0%, 5 -> 20%, 10 -> 36%). Social reasoning collapses without temporal context.
3. **Planning is not the bottleneck** -- ReAct vs. minimal prompting differs by only ~3 pp. Information access constrains performance more than reasoning structure.

## Quick Start

```bash
cd amongagents
pip install -r requirements.txt
export OPENAI_API_KEY="your-key"

# Run a single experiment config
python run_experiments.py all_llm

# Run all configs
python run_experiments.py --all

# Generate figures and tables (no API calls needed)
python analysis/run_all.py

# Include LLM-based speech classification and cognitive eval
python analysis/run_all.py --classify --eval
```

## Dependencies

- Python 3.9+
- openai
- anthropic
- python-dotenv
- matplotlib
- numpy

## Authors

Wenpeng Xu, Jinglin Cao -- UC San Diego, Department of Electrical and Computer Engineering
