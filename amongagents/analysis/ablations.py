"""
消融实验分析
"""

import json
import os
import glob

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load_summaries(log_dir: str = "logs") -> dict:
    summaries = {}
    for path in glob.glob(os.path.join(log_dir, "summary_*.json")):
        with open(path) as f:
            data = json.load(f)
            summaries[data["config"]] = data
    return summaries


def analyze_memory_ablation(summaries: dict) -> dict:
    """分析memory size的消融结果"""
    memory_configs = {
        0: "memory_0",
        5: "memory_5",
        10: "all_llm",  # default uses memory=10
        20: "memory_20",
    }

    results = {}
    for size, config_name in memory_configs.items():
        if config_name in summaries:
            s = summaries[config_name]
            n = s["valid_games"]
            results[size] = {
                "crew_rate": s["crewmate_win_rate"],
                "imp_rate": s["impostor_win_rate"],
                "avg_steps": s["avg_timesteps"],
                "n": n,
            }
    return results


def analyze_planning_ablation(summaries: dict) -> dict:
    """分析planning开关的消融"""
    results = {}
    for label, config_name in [("With Planning", "all_llm"), ("No Planning", "no_planning")]:
        if config_name in summaries:
            s = summaries[config_name]
            results[label] = {
                "crew_rate": s["crewmate_win_rate"],
                "imp_rate": s["impostor_win_rate"],
                "avg_steps": s["avg_timesteps"],
                "n": s["valid_games"],
            }
    return results


def generate_memory_chart(memory_results: dict, output_path: str = "figures/memory_ablation.pdf"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    sizes = sorted(memory_results.keys())
    crew_rates = [memory_results[s]["crew_rate"] for s in sizes]
    imp_rates = [memory_results[s]["imp_rate"] for s in sizes]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(sizes, crew_rates, "o-", color="#4878CF", linewidth=2, markersize=8, label="Crewmate Win Rate")
    ax.plot(sizes, imp_rates, "s-", color="#E8743B", linewidth=2, markersize=8, label="Impostor Win Rate")

    ax.set_xlabel("Memory Size (N_max)")
    ax.set_ylabel("Win Rate")
    ax.set_title("Effect of Memory Size on Win Rates")
    ax.set_xticks(sizes)
    ax.legend()
    ax.set_ylim(0, 1.05)
    ax.axhline(y=0.5, color="gray", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def generate_planning_chart(planning_results: dict, output_path: str = "figures/planning_ablation.pdf"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    labels = list(planning_results.keys())
    crew_rates = [planning_results[l]["crew_rate"] for l in labels]
    imp_rates = [planning_results[l]["imp_rate"] for l in labels]

    x = np.arange(len(labels))
    width = 0.3

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.bar(x - width/2, crew_rates, width, label="Crewmate", color="#4878CF")
    ax.bar(x + width/2, imp_rates, width, label="Impostor", color="#E8743B")

    ax.set_ylabel("Win Rate")
    ax.set_title("Planning Ablation")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.set_ylim(0, 1.1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def generate_latex_table(memory_results: dict, planning_results: dict) -> str:
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Ablation study results.}",
        r"\label{tab:ablations}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Setting & $N$ & Crew Win\% & Imp Win\% \\",
        r"\midrule",
        r"\multicolumn{4}{l}{\textit{Memory Size}} \\",
    ]
    for size in sorted(memory_results.keys()):
        r = memory_results[size]
        lines.append(f"$N_{{\\max}}={size}$ & {r['n']} & {r['crew_rate']:.0%} & {r['imp_rate']:.0%} \\\\")

    lines.append(r"\midrule")
    lines.append(r"\multicolumn{4}{l}{\textit{Planning}} \\")
    for label, r in planning_results.items():
        lines.append(f"{label} & {r['n']} & {r['crew_rate']:.0%} & {r['imp_rate']:.0%} \\\\")

    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


if __name__ == "__main__":
    summaries = load_summaries()
    if not summaries:
        print("No summaries found. Run experiments first.")
        exit(1)

    memory_results = analyze_memory_ablation(summaries)
    planning_results = analyze_planning_ablation(summaries)

    if memory_results:
        print("\n=== Memory Ablation ===")
        for size, r in sorted(memory_results.items()):
            print(f"  Memory={size}: Crew {r['crew_rate']:.0%}, Imp {r['imp_rate']:.0%}")
        generate_memory_chart(memory_results)

    if planning_results:
        print("\n=== Planning Ablation ===")
        for label, r in planning_results.items():
            print(f"  {label}: Crew {r['crew_rate']:.0%}, Imp {r['imp_rate']:.0%}")
        generate_planning_chart(planning_results)

    if memory_results or planning_results:
        latex = generate_latex_table(memory_results, planning_results)
        os.makedirs("figures", exist_ok=True)
        with open("figures/ablation_table.tex", "w") as f:
            f.write(latex)
        print(f"\nLaTeX table saved to figures/ablation_table.tex")
