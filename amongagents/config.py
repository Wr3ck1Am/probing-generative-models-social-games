"""
Experiment configs and personality definitions.
"""

from dataclasses import dataclass, field
from typing import Dict

# Personality Archetypes

IMPOSTOR_PERSONALITIES = {
    "strategist": (
        "You are The Strategist. You plan several moves ahead, thinking about "
        "long-term positioning. You kill only when the risk is low and you have "
        "a clear escape route. In meetings, you build a consistent narrative."
    ),
    "manipulator": (
        "You are The Manipulator. You excel at social influence. You befriend "
        "other players and use trust to deflect suspicion. You actively frame "
        "innocent players by planting seeds of doubt in meetings."
    ),
    "lone_wolf": (
        "You are The Lone Wolf. You prefer to act alone and avoid groups. "
        "You strike isolated targets and stay quiet in meetings, speaking only "
        "when directly questioned. You try to appear unremarkable."
    ),
    "paranoid": (
        "You are The Paranoid. You preemptively accuse others to shift attention "
        "away from yourself. You act nervous and over-explain your movements, "
        "which can either help or hurt your disguise."
    ),
    "cold_calculator": (
        "You are The Cold Calculator. You treat the game as pure optimization. "
        "You track everyone's movements methodically, kill when the math favors "
        "you (e.g., when you can force a tie), and vote logically in meetings."
    ),
}

CREWMATE_PERSONALITIES = {
    "leader": (
        "You are The Leader. You take charge during meetings, organizing "
        "discussion and proposing voting strategies. You ask direct questions "
        "and try to coordinate the crew's investigation efforts."
    ),
    "observer": (
        "You are The Observer. You are quiet but watchful. You carefully track "
        "who was where and when. In meetings, you share detailed observations "
        "about player movements and look for inconsistencies."
    ),
    "skeptic": (
        "You are The Skeptic. You question everything and everyone. You "
        "challenge alibis, point out contradictions, and are hard to convince. "
        "You vote to skip unless you have strong evidence."
    ),
    "loyal_companion": (
        "You are The Loyal Companion. You tend to buddy up with another player "
        "and vouch for them. You are trusting by nature but become fierce when "
        "your ally is threatened or killed."
    ),
    "tech_expert": (
        "You are The Tech Expert. You prioritize completing tasks efficiently. "
        "You plan optimal routes through the map and focus on task progress. "
        "In meetings, you report task completion status as evidence."
    ),
}

ALL_PERSONALITIES = {**IMPOSTOR_PERSONALITIES, **CREWMATE_PERSONALITIES}


@dataclass
class ExperimentConfig:
    """Config for a single experiment run."""
    name: str = "default"
    # Agent type per role: "llm" or "random"
    crew_agent_type: str = "llm"
    impostor_agent_type: str = "llm"
    # LLM settings
    model: str = "gpt-5-mini-2025-08-07"
    # Memory
    memory_size: int = 10
    # Planning
    planning_enabled: bool = True
    # Personality: mapping of player_name -> personality_key, or "default"/"random"
    personality_mode: str = "default"  # "default", "random", or specific config
    personality_config: Dict[str, str] = field(default_factory=dict)
    # Game settings
    num_crewmates: int = 4
    num_impostors: int = 1
    max_timesteps: int = 20
    meeting_interval: int = 5  # trigger meeting every N task steps
    # Experiment settings
    num_games: int = 10
    log_dir: str = "logs"


# Preset experiment configs

EXPERIMENT_PRESETS = {
    "all_random": ExperimentConfig(
        name="all_random",
        crew_agent_type="random",
        impostor_agent_type="random",
        num_games=10,
    ),
    "all_llm": ExperimentConfig(
        name="all_llm",
        crew_agent_type="llm",
        impostor_agent_type="llm",
        num_games=5,
    ),
    "llm_crew": ExperimentConfig(
        name="llm_crew",
        crew_agent_type="llm",
        impostor_agent_type="random",
        num_games=5,
    ),
    "llm_impostor": ExperimentConfig(
        name="llm_impostor",
        crew_agent_type="random",
        impostor_agent_type="llm",
        num_games=5,
    ),
    # Memory ablations
    "memory_0": ExperimentConfig(
        name="memory_0", memory_size=0, num_games=3,
    ),
    "memory_5": ExperimentConfig(
        name="memory_5", memory_size=5, num_games=3,
    ),
    "memory_20": ExperimentConfig(
        name="memory_20", memory_size=20, num_games=3,
    ),
    # Planning ablation
    "no_planning": ExperimentConfig(
        name="no_planning", planning_enabled=False, num_games=3,
    ),
}
