"""
Win rate analysis and visualization.
"""

import json
import os
import glob
import math
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load_summaries(log_dir: str = "logs") -> dict:
    """Load all summary JSON files from the log directory."""
    summaries = {}
    for path in glob.glob(os.path.join(log_dir, "summary_*.json")):
        with open(path) as f:
            data = json.load(f)
            summaries[data["config"]] = data
    return summaries


def load_game_logs(log_dir: str = "logs", config_filter: str = None) -> list:
    """Load individual game log files."""
    pattern = f"game_{config_filter}_*.json" if config_filter else "game_*.json"
    logs = []
    for path in sorted(glob.glob(os.path.join(log_dir, pattern))):
        if "summary" in path:
            continue
        with open(path) as f:
            logs.append(json.load(f))
    return logs


def compute_win_rates(summaries: dict) -> dict:
    """Compute win rates with 95% confidence intervals."""
    results = {}
    for config, data in summaries.items():
        n = data["valid_games"]
        if n == 0:
            continue
        p_crew = data["crewmate_win_rate"]
        p_imp = data["impostor_win_rate"]
        # Wilson score interval
        z = 1.96
        ci_crew = z * math.sqrt(p_crew * (1 - p_crew) / n) if n > 0 else 0
        ci_imp = z * math.sqrt(p_imp * (1 - p_imp) / n) if n > 0 else 0

        results[config] = {
            "n": n,
            "crew_wins": data["crewmate_wins"],
            "imp_wins": data["impostor_wins"],
            "crew_rate": p_crew,
            "imp_rate": p_imp,
            "crew_ci": ci_crew,
            "imp_ci": ci_imp,
            "avg_steps": data["avg_timesteps"],
            "avg_kills": data["avg_kills"],
        }
    return results


def generate_win_rate_chart(results: dict, output_path: str = "figures/win_rates.pdf"):
    """Generate grouped bar chart comparing crew vs impostor win rates."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    configs = list(results.keys())
    crew_rates = [results[c]["crew_rate"] for c in configs]
    imp_rates = [results[c]["imp_rate"] for c in configs]
    crew_ci = [results[c]["crew_ci"] for c in configs]
    imp_ci = [results[c]["imp_ci"] for c in configs]

    x = np.arange(len(configs))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width/2, crew_rates, width, yerr=crew_ci, label="Crewmate Win Rate",
           color="#4878CF", capsize=4)
    ax.bar(x + width/2, imp_rates, width, yerr=imp_ci, label="Impostor Win Rate",
           color="#E8743B", capsize=4)

    ax.set_ylabel("Win Rate")
    ax.set_title("Win Rates Across Configurations")
    ax.set_xticks(x)
    labels = [c.replace("_", "\n") for c in configs]
    ax.set_xticklabels(labels)
    ax.legend()
    ax.set_ylim(0, 1.1)
    ax.axhline(y=0.5, color="gray", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def generate_latex_table(results: dict) -> str:
    """Output a LaTeX table of win rate results."""
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Win rates across experimental configurations. CI = 95\% confidence interval.}",
        r"\label{tab:winrates}",
        r"\begin{tabular}{lcccccc}",
        r"\toprule",
        r"Config & $N$ & Crew Win\% & Imp Win\% & Avg Steps & Avg Kills \\",
        r"\midrule",
    ]
    for config, r in results.items():
        name = config.replace("_", r"\_")
        lines.append(
            f"{name} & {r['n']} & {r['crew_rate']:.0%} $\\pm$ {r['crew_ci']:.0%} & "
            f"{r['imp_rate']:.0%} $\\pm$ {r['imp_ci']:.0%} & "
            f"{r['avg_steps']:.1f} & {r['avg_kills']:.1f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def generate_game_length_chart(log_dir: str = "logs", output_path: str = "figures/game_lengths.pdf"):
    """Box plot of game lengths across configs."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    summaries = load_summaries(log_dir)
    data = {}
    for config, s in summaries.items():
        lengths = [r["timesteps"] for r in s["results"] if "timesteps" in r]
        if lengths:
            data[config] = lengths

    if not data:
        print("No data for game length chart")
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    configs = list(data.keys())
    ax.boxplot([data[c] for c in configs], labels=[c.replace("_", "\n") for c in configs])
    ax.set_ylabel("Game Length (timesteps)")
    ax.set_title("Game Length Distribution")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    summaries = load_summaries()
    if not summaries:
        print("No summary files found in logs/. Run experiments first.")
        exit(1)

    results = compute_win_rates(summaries)

    print("\n=== Win Rate Results ===")
    for config, r in results.items():
        print(f"{config}: Crew {r['crew_rate']:.0%} (±{r['crew_ci']:.0%}), "
              f"Imp {r['imp_rate']:.0%} (±{r['imp_ci']:.0%}), "
              f"Steps {r['avg_steps']:.1f}, Kills {r['avg_kills']:.1f}")

    generate_win_rate_chart(results)
    generate_game_length_chart()

    latex = generate_latex_table(results)
    os.makedirs("figures", exist_ok=True)
    with open("figures/win_rates_table.tex", "w") as f:
        f.write(latex)
    print(f"\nLaTeX table saved to figures/win_rates_table.tex")
