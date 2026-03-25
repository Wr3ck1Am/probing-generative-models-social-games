"""
批量实验运行脚本

用法:
    python run_experiments.py all_random
    python run_experiments.py all_llm
    python run_experiments.py --all
    python run_experiments.py --list
"""

import sys
import time
import json
import os
from config import EXPERIMENT_PRESETS, ExperimentConfig
from main import run_game


def run_experiment(config: ExperimentConfig):
    """跑一组实验"""
    print(f"\n{'#'*60}")
    print(f"# EXPERIMENT: {config.name}")
    print(f"# Games: {config.num_games}")
    print(f"# Crew: {config.crew_agent_type}, Impostor: {config.impostor_agent_type}")
    print(f"# Memory: {config.memory_size}, Planning: {config.planning_enabled}")
    print(f"{'#'*60}\n")

    results = []
    for i in range(config.num_games):
        print(f"\n>>> Game {i+1}/{config.num_games} for config '{config.name}' <<<")
        t0 = time.time()
        try:
            outcome = run_game(config, run_id=i)
            outcome["duration_sec"] = round(time.time() - t0, 1)
            results.append(outcome)
        except Exception as e:
            print(f"ERROR in game {i}: {e}")
            results.append({"winner": "error", "reason": str(e), "duration_sec": round(time.time() - t0, 1)})

    # Summary
    wins = {"crewmate": 0, "impostor": 0, "error": 0}
    total_steps = []
    total_kills_list = []
    for r in results:
        wins[r.get("winner", "error")] = wins.get(r.get("winner", "error"), 0) + 1
        if "timesteps" in r:
            total_steps.append(r["timesteps"])
        if "kills" in r:
            total_kills_list.append(r["kills"])

    valid = len(results) - wins["error"]
    summary = {
        "config": config.name,
        "total_games": config.num_games,
        "valid_games": valid,
        "crewmate_wins": wins["crewmate"],
        "impostor_wins": wins["impostor"],
        "crewmate_win_rate": wins["crewmate"] / valid if valid > 0 else 0,
        "impostor_win_rate": wins["impostor"] / valid if valid > 0 else 0,
        "avg_timesteps": sum(total_steps) / len(total_steps) if total_steps else 0,
        "avg_kills": sum(total_kills_list) / len(total_kills_list) if total_kills_list else 0,
        "results": results,
    }

    # Save summary
    os.makedirs(config.log_dir, exist_ok=True)
    summary_path = os.path.join(config.log_dir, f"summary_{config.name}.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"EXPERIMENT SUMMARY: {config.name}")
    print(f"  Crewmate wins: {wins['crewmate']}/{valid} ({summary['crewmate_win_rate']:.0%})")
    print(f"  Impostor wins: {wins['impostor']}/{valid} ({summary['impostor_win_rate']:.0%})")
    print(f"  Avg timesteps: {summary['avg_timesteps']:.1f}")
    print(f"  Avg kills: {summary['avg_kills']:.1f}")
    print(f"  Summary saved: {summary_path}")
    print(f"{'='*60}")

    return summary


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_experiments.py <preset_name> [preset2 ...]")
        print("       python run_experiments.py --all")
        print("       python run_experiments.py --list")
        sys.exit(1)

    if sys.argv[1] == "--list":
        print("Available presets:")
        for name, cfg in EXPERIMENT_PRESETS.items():
            print(f"  {name}: crew={cfg.crew_agent_type}, imp={cfg.impostor_agent_type}, "
                  f"mem={cfg.memory_size}, plan={cfg.planning_enabled}, games={cfg.num_games}")
        sys.exit(0)

    if sys.argv[1] == "--all":
        preset_names = list(EXPERIMENT_PRESETS.keys())
    else:
        preset_names = sys.argv[1:]

    all_summaries = []
    for name in preset_names:
        if name not in EXPERIMENT_PRESETS:
            print(f"Unknown preset: {name}")
            continue
        summary = run_experiment(EXPERIMENT_PRESETS[name])
        all_summaries.append(summary)

    # Print final comparison
    if len(all_summaries) > 1:
        print(f"\n\n{'='*60}")
        print("CROSS-EXPERIMENT COMPARISON")
        print(f"{'='*60}")
        print(f"{'Config':<20} {'Crew Win%':<12} {'Imp Win%':<12} {'Avg Steps':<12} {'Avg Kills':<12}")
        print("-" * 68)
        for s in all_summaries:
            print(f"{s['config']:<20} {s['crewmate_win_rate']:<12.0%} {s['impostor_win_rate']:<12.0%} "
                  f"{s['avg_timesteps']:<12.1f} {s['avg_kills']:<12.1f}")
