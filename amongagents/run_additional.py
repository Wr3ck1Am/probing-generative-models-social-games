"""
Append more game runs to an existing experiment without overwriting logs.
"""

import os
import sys
import glob
import time
import json
from config import EXPERIMENT_PRESETS, ExperimentConfig
from main import run_game


def get_next_run_id(log_dir: str, config_name: str) -> int:
    """Find the next available run_id by scanning existing log files."""
    existing = glob.glob(os.path.join(log_dir, f"game_{config_name}_*.json"))
    if not existing:
        return 0
    ids = []
    for path in existing:
        basename = os.path.basename(path)
        # game_configname_NNN.json
        parts = basename.replace(".json", "").split("_")
        try:
            ids.append(int(parts[-1]))
        except ValueError:
            continue
    return max(ids) + 1 if ids else 0


def run_additional(config_name: str, additional_games: int):
    """Run additional games on top of whatever already exists."""
    if config_name not in EXPERIMENT_PRESETS:
        print(f"Unknown config: {config_name}")
        return

    config = EXPERIMENT_PRESETS[config_name]
    start_id = get_next_run_id(config.log_dir, config_name)

    print(f"\n{'#'*60}")
    print(f"# ADDITIONAL RUNS: {config_name}")
    print(f"# Starting from run_id={start_id}, running {additional_games} more")
    print(f"# Crew: {config.crew_agent_type}, Impostor: {config.impostor_agent_type}")
    print(f"# Memory: {config.memory_size}, Planning: {config.planning_enabled}")
    print(f"{'#'*60}\n")

    results = []
    for i in range(additional_games):
        run_id = start_id + i
        print(f"\n>>> Game {i+1}/{additional_games} (run_id={run_id}) for '{config_name}' <<<")
        t0 = time.time()
        try:
            outcome = run_game(config, run_id=run_id)
            outcome["duration_sec"] = round(time.time() - t0, 1)
            results.append(outcome)
            print(f"  Result: {outcome['winner']} won in {outcome['timesteps']} steps ({outcome['duration_sec']}s)")
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"winner": "error", "reason": str(e), "duration_sec": round(time.time() - t0, 1)})

    # Update summary file by loading existing + appending new results
    summary_path = os.path.join(config.log_dir, f"summary_{config_name}.json")
    if os.path.exists(summary_path):
        with open(summary_path) as f:
            existing_summary = json.load(f)
        all_results = existing_summary.get("results", []) + results
    else:
        all_results = results

    # Recompute summary
    wins = {"crewmate": 0, "impostor": 0, "error": 0}
    total_steps = []
    total_kills = []
    for r in all_results:
        w = r.get("winner", "error")
        wins[w] = wins.get(w, 0) + 1
        if "timesteps" in r:
            total_steps.append(r["timesteps"])
        if "kills" in r:
            total_kills.append(r["kills"])

    valid = len(all_results) - wins.get("error", 0)
    summary = {
        "config": config_name,
        "total_games": len(all_results),
        "valid_games": valid,
        "crewmate_wins": wins["crewmate"],
        "impostor_wins": wins["impostor"],
        "crewmate_win_rate": wins["crewmate"] / valid if valid > 0 else 0,
        "impostor_win_rate": wins["impostor"] / valid if valid > 0 else 0,
        "avg_timesteps": sum(total_steps) / len(total_steps) if total_steps else 0,
        "avg_kills": sum(total_kills) / len(total_kills) if total_kills else 0,
        "results": all_results,
    }

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"UPDATED SUMMARY: {config_name}")
    print(f"  Total games: {len(all_results)} ({valid} valid)")
    print(f"  Crewmate wins: {wins['crewmate']}/{valid} ({summary['crewmate_win_rate']:.0%})")
    print(f"  Impostor wins: {wins['impostor']}/{valid} ({summary['impostor_win_rate']:.0%})")
    print(f"  Avg timesteps: {summary['avg_timesteps']:.1f}")
    print(f"  Avg kills: {summary['avg_kills']:.1f}")
    print(f"{'='*60}")

    return summary


# Define what additional runs we need
ADDITIONAL_RUNS = {
    "all_llm": 10,
    "llm_crew": 10,
    "llm_impostor": 10,
    "memory_0": 5,
    "memory_5": 5,
    "memory_20": 4,
    "no_planning": 5,
}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            for name, count in ADDITIONAL_RUNS.items():
                start = get_next_run_id("logs", name)
                print(f"  {name}: +{count} games (starting from run_id={start})")
            sys.exit(0)
        # Run specific configs
        configs_to_run = sys.argv[1:]
    else:
        configs_to_run = list(ADDITIONAL_RUNS.keys())

    all_summaries = []
    for name in configs_to_run:
        if name not in ADDITIONAL_RUNS:
            print(f"Unknown config: {name}")
            continue
        summary = run_additional(name, ADDITIONAL_RUNS[name])
        if summary:
            all_summaries.append(summary)

    if len(all_summaries) > 1:
        print(f"\n\n{'='*60}")
        print("FINAL COMPARISON (ALL CONFIGS)")
        print(f"{'='*60}")
        print(f"{'Config':<16} {'N':<5} {'Crew%':<8} {'Imp%':<8} {'Steps':<8} {'Kills':<8}")
        print("-" * 54)
        for s in all_summaries:
            print(f"{s['config']:<16} {s['valid_games']:<5} "
                  f"{s['crewmate_win_rate']:<8.0%} {s['impostor_win_rate']:<8.0%} "
                  f"{s['avg_timesteps']:<8.1f} {s['avg_kills']:<8.1f}")
