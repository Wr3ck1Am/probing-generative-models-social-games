"""
认知能力评估 - 5个维度打分
"""

import json
import os
import glob
from openai import OpenAI
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


EVAL_PROMPT = """You are evaluating an AI agent's performance in an Among Us game.

Agent name: {name}
Agent role: {role}
Game outcome: {outcome}

Here are representative moments from the agent's gameplay:

=== Agent's Thoughts ===
{thoughts}

=== Agent's Actions ===
{actions}

=== Meeting Behavior ===
{meeting_behavior}

Score this agent on 5 dimensions (1-10 each):

1. Self-Awareness: Does the agent understand its role and goals?
2. Memory: Does the agent reference and use past events effectively?
3. Planning: Does the agent form coherent multi-step strategies?
4. Reasoning: Does the agent make logical deductions about other players?
5. Reflection: Does the agent adapt its strategy based on new information?

Respond in JSON format only:
{{"self_awareness": 7, "memory": 6, "planning": 8, "reasoning": 5, "reflection": 6, "justification": "brief explanation"}}"""


def extract_agent_data(game_log: dict, player_name: str) -> dict:
    """从日志中提取agent的关键数据"""
    thoughts = []
    actions = []
    meeting_speeches = []

    for turn in game_log.get("turns", []):
        for pa in turn.get("player_actions", []):
            if pa.get("player_name") == player_name:
                if pa.get("thought"):
                    thoughts.append(f"T{turn['timestep']}: {pa['thought'][:150]}")
                act = pa.get("action", {})
                actions.append(f"T{turn['timestep']}: {act.get('action', '?')} {act.get('params', {})}")

    for meeting in game_log.get("meetings", []):
        for round_speeches in meeting.get("discussion_rounds", []):
            for speech in round_speeches:
                if speech.get("player_name") == player_name:
                    meeting_speeches.append(speech.get("message", "")[:150])
        votes = meeting.get("votes", {})
        if player_name in votes:
            meeting_speeches.append(f"[VOTE] {votes[player_name]}")

    return {
        "thoughts": "\n".join(thoughts[-5:]) if thoughts else "No thought data available.",
        "actions": "\n".join(actions[-8:]) if actions else "No action data available.",
        "meeting_behavior": "\n".join(meeting_speeches[-5:]) if meeting_speeches else "No meeting data.",
    }


def evaluate_agents(log_dir: str = "logs", output_path: str = "logs/controlled_eval.json",
                    config_filter: str = None):
    """对日志中所有agent做认知评估"""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    pattern = f"game_{config_filter}_*.json" if config_filter else "game_*.json"
    evaluations = []

    for path in sorted(glob.glob(os.path.join(log_dir, pattern))):
        if "summary" in path or "classification" in path or "eval" in path:
            continue
        with open(path) as f:
            game_log = json.load(f)

        game_id = game_log["meta"]["game_id"]
        outcome = game_log.get("outcome", {})
        outcome_str = f"{outcome.get('winner', '?')} won ({outcome.get('reason', '?')})"

        for player in game_log["players"]:
            name = player["name"]
            role = player["role"]

            agent_data = extract_agent_data(game_log, name)

            try:
                response = client.chat.completions.create(
                    model="gpt-5-mini-2025-08-07",
                    max_completion_tokens=800,
                    messages=[{
                        "role": "user",
                        "content": EVAL_PROMPT.format(
                            name=name, role=role, outcome=outcome_str,
                            **agent_data
                        )
                    }]
                )
                result_text = response.choices[0].message.content.strip()
                if "{" in result_text:
                    json_str = result_text[result_text.index("{"):result_text.rindex("}") + 1]
                    scores = json.loads(json_str)
                else:
                    scores = {}
            except Exception as e:
                print(f"  Error evaluating {name} in {game_id}: {e}")
                scores = {}

            evaluations.append({
                "game_id": game_id,
                "player_name": name,
                "role": role,
                "config": game_log["meta"].get("config", "unknown"),
                **{k: scores.get(k, 5) for k in
                   ["self_awareness", "memory", "planning", "reasoning", "reflection"]},
                "justification": scores.get("justification", ""),
            })
            print(f"  Evaluated {name} ({role}) in {game_id}")

    with open(output_path, "w") as f:
        json.dump(evaluations, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(evaluations)} evaluations to {output_path}")
    return evaluations


def analyze_evaluations(input_path: str = "logs/controlled_eval.json") -> dict:
    """按角色统计平均得分"""
    with open(input_path) as f:
        data = json.load(f)

    dimensions = ["self_awareness", "memory", "planning", "reasoning", "reflection"]

    # By role
    by_role = defaultdict(lambda: defaultdict(list))
    for entry in data:
        role = entry["role"]
        for dim in dimensions:
            by_role[role][dim].append(entry.get(dim, 5))

    stats = {}
    for role in ["crewmate", "impostor"]:
        stats[role] = {}
        for dim in dimensions:
            values = by_role[role].get(dim, [5])
            stats[role][dim] = {
                "mean": sum(values) / len(values),
                "std": np.std(values) if len(values) > 1 else 0,
                "n": len(values),
            }

    return stats


def generate_radar_chart(stats: dict, output_path: str = "figures/cognitive_radar.pdf"):
    """认知维度雷达图"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    dimensions = ["self_awareness", "memory", "planning", "reasoning", "reflection"]
    labels = ["Self-\nAwareness", "Memory", "Planning", "Reasoning", "Reflection"]

    angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

    for role, color, label in [("crewmate", "#4878CF", "Crewmate"), ("impostor", "#E8743B", "Impostor")]:
        values = [stats[role][d]["mean"] for d in dimensions]
        values += values[:1]
        ax.plot(angles, values, "o-", color=color, linewidth=2, label=label)
        ax.fill(angles, values, alpha=0.15, color=color)

    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 10)
    ax.set_title("Cognitive Evaluation by Role", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def generate_latex_table(stats: dict) -> str:
    dimensions = ["self_awareness", "memory", "planning", "reasoning", "reflection"]
    dim_labels = ["Self-Awareness", "Memory", "Planning", "Reasoning", "Reflection"]

    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Controlled evaluation scores (1--10) by role. Mean $\pm$ std.}",
        r"\label{tab:controlled_eval}",
        r"\begin{tabular}{lcc}",
        r"\toprule",
        r"Dimension & Crewmate & Impostor \\",
        r"\midrule",
    ]
    for dim, label in zip(dimensions, dim_labels):
        crew = stats["crewmate"][dim]
        imp = stats["impostor"][dim]
        lines.append(f"{label} & {crew['mean']:.1f} $\\pm$ {crew['std']:.1f} & "
                     f"{imp['mean']:.1f} $\\pm$ {imp['std']:.1f} \\\\")

    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if "--evaluate" in sys.argv:
        evaluate_agents()

    if os.path.exists("logs/controlled_eval.json"):
        stats = analyze_evaluations()
        print("\n=== Controlled Evaluation ===")
        for role, scores in stats.items():
            print(f"\n{role.upper()}:")
            for dim, s in scores.items():
                print(f"  {dim}: {s['mean']:.1f} ± {s['std']:.1f} (n={s['n']})")

        generate_radar_chart(stats)
        latex = generate_latex_table(stats)
        os.makedirs("figures", exist_ok=True)
        with open("figures/controlled_eval_table.tex", "w") as f:
            f.write(latex)
    else:
        print("Run with --evaluate first.")
