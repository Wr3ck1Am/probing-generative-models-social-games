"""
一键跑全部分析

    python analysis/run_all.py                    # 只跑统计+画图
    python analysis/run_all.py --classify --eval  # 包含LLM分类和评估
"""

import sys
import os

# Ensure we run from the amongagents directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
os.chdir(project_dir)

from analysis.win_rates import (
    load_summaries, compute_win_rates, generate_win_rate_chart,
    generate_game_length_chart, generate_latex_table as wr_latex
)
from analysis.ablations import (
    analyze_memory_ablation, analyze_planning_ablation,
    generate_memory_chart, generate_planning_chart,
    generate_latex_table as abl_latex
)


def main():
    do_classify = "--classify" in sys.argv
    do_eval = "--eval" in sys.argv

    os.makedirs("figures", exist_ok=True)

    # Stage 1: Win rates (no API needed)
    print("\n" + "=" * 40)
    print("STAGE 1: Win Rate Analysis")
    print("=" * 40)
    summaries = load_summaries()
    if summaries:
        results = compute_win_rates(summaries)
        generate_win_rate_chart(results)
        generate_game_length_chart()
        with open("figures/win_rates_table.tex", "w") as f:
            f.write(wr_latex(results))
        print("Win rate analysis complete.")
    else:
        print("No summary files found.")

    # Stage 2: Ablations (no API needed)
    print("\n" + "=" * 40)
    print("STAGE 2: Ablation Analysis")
    print("=" * 40)
    if summaries:
        mem = analyze_memory_ablation(summaries)
        plan = analyze_planning_ablation(summaries)
        if mem:
            generate_memory_chart(mem)
        if plan:
            generate_planning_chart(plan)
        if mem or plan:
            with open("figures/ablation_table.tex", "w") as f:
                f.write(abl_latex(mem, plan))
        print("Ablation analysis complete.")

    # Stage 3: Conversation analysis (needs API for classification)
    print("\n" + "=" * 40)
    print("STAGE 3: Conversation Analysis")
    print("=" * 40)
    if do_classify:
        from analysis.conversation_analysis import classify_speeches, analyze_classifications, generate_speech_chart
        from analysis.conversation_analysis import generate_latex_table as conv_latex
        classify_speeches()
        stats = analyze_classifications()
        generate_speech_chart(stats)
        with open("figures/conversation_table.tex", "w") as f:
            f.write(conv_latex(stats))
        print("Conversation analysis complete.")
    elif os.path.exists("logs/speech_classifications.json"):
        from analysis.conversation_analysis import analyze_classifications, generate_speech_chart
        from analysis.conversation_analysis import generate_latex_table as conv_latex
        stats = analyze_classifications()
        generate_speech_chart(stats)
        with open("figures/conversation_table.tex", "w") as f:
            f.write(conv_latex(stats))
        print("Conversation analysis complete (from cached classifications).")
    else:
        print("Skipped (run with --classify to classify speeches).")

    # Stage 4: Controlled evaluation (needs API)
    print("\n" + "=" * 40)
    print("STAGE 4: Controlled Evaluation")
    print("=" * 40)
    if do_eval:
        from analysis.controlled_eval import evaluate_agents, analyze_evaluations, generate_radar_chart
        from analysis.controlled_eval import generate_latex_table as eval_latex
        evaluate_agents()
        stats = analyze_evaluations()
        generate_radar_chart(stats)
        with open("figures/controlled_eval_table.tex", "w") as f:
            f.write(eval_latex(stats))
        print("Controlled evaluation complete.")
    elif os.path.exists("logs/controlled_eval.json"):
        from analysis.controlled_eval import analyze_evaluations, generate_radar_chart
        from analysis.controlled_eval import generate_latex_table as eval_latex
        stats = analyze_evaluations()
        generate_radar_chart(stats)
        with open("figures/controlled_eval_table.tex", "w") as f:
            f.write(eval_latex(stats))
        print("Controlled evaluation complete (from cached scores).")
    else:
        print("Skipped (run with --eval to evaluate agents).")

    print("\n" + "=" * 40)
    print("ALL ANALYSIS COMPLETE")
    print(f"Figures saved to: figures/")
    print("=" * 40)


if __name__ == "__main__":
    main()
