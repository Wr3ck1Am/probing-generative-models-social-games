"""
主游戏循环
"""

import os
from collections import Counter
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

from game_state import initialize_game, Phase, MeetingState, GameState
from game_map import is_adjacent
from config import ExperimentConfig
from logger import GameLogger


def create_agents(game: GameState, config: ExperimentConfig):
    """根据config创建agent"""
    from agent import AmongUsAgent
    from random_agent import RandomAgent

    api_key = os.environ.get("OPENAI_API_KEY", "")
    agents = {}

    for player in game.players:
        if player.role.value == "crewmate":
            agent_type = config.crew_agent_type
        else:
            agent_type = config.impostor_agent_type

        if agent_type == "llm":
            agents[player.id] = AmongUsAgent(
                player, api_key,
                model=config.model,
                memory_size=config.memory_size,
                planning_enabled=config.planning_enabled,
            )
        else:
            agents[player.id] = RandomAgent(player)

    return agents


def execute_action(player, action: Dict, game: GameState) -> Dict:
    """执行玩家动作"""
    act = action.get("action", "idle")
    params = action.get("params", {})

    if act == "move":
        target = params.get("target_room", "")
        if is_adjacent(player.location, target):
            player.location = target
            return {"success": True, "detail": f"Moved to {target}"}
        return {"success": False, "detail": f"Invalid move to {target}"}

    elif act == "complete_task":
        task_name = params.get("task_name", "")
        for task in player.tasks:
            if (task.name == task_name or task_name.startswith(task.name)) and not task.completed:
                if task.location == player.location:
                    task.steps_remaining -= 1
                    if task.steps_remaining <= 0:
                        task.completed = True
                        return {"success": True, "detail": f"Completed task {task_name}"}
                    return {"success": True, "detail": f"Worked on {task_name} ({task.steps_remaining} steps left)"}
                return {"success": False, "detail": f"Not at task location (need {task.location})"}
        return {"success": False, "detail": f"Task {task_name} not found or already done"}

    elif act == "kill":
        target_name = params.get("target_player", "")
        target_player = game.get_player_by_name(target_name)
        if target_player and target_player.alive and target_player.location == player.location:
            target_player.alive = False
            game.dead_bodies.append({"player_id": target_player.id, "location": target_player.location})
            game.kill_log.append({
                "killer": player.name, "victim": target_name,
                "location": player.location, "timestep": game.timestep
            })
            return {"success": True, "detail": f"Killed {target_name}"}
        return {"success": False, "detail": f"Cannot kill {target_name}"}

    elif act == "speak":
        msg = params.get("message", "")
        return {"success": True, "detail": f"Said: {msg[:100]}"}

    return {"success": False, "detail": "Unknown action"}


def check_body_discovery(game: GameState) -> Optional[Dict]:
    """检查是否有玩家发现尸体"""
    for body in game.dead_bodies:
        for player in game.get_alive_players():
            # The killer shouldn't trigger discovery on their own kill in the same step
            if player.location == body["location"]:
                # Check if it's a crewmate (impostors don't report their own kills)
                if player.role.value == "crewmate":
                    return {"finder": player.name, "location": body["location"],
                            "body_id": body["player_id"]}
    return None


def run_meeting(game: GameState, agents: Dict, logger: GameLogger,
                trigger_reason: str = "scheduled",
                body_info: Optional[Dict] = None):
    """2轮讨论 + 1轮投票"""
    meeting = MeetingState(trigger_reason=trigger_reason)
    if body_info:
        meeting.body_found_by = body_info["finder"]
        meeting.body_location = body_info["location"]
    game.meeting_state = meeting
    game.phase = Phase.MEETING

    discussion_log = []

    # 2 discussion rounds
    for round_num in range(2):
        round_speeches = []
        for player in game.get_alive_players():
            agent = agents[player.id]
            action, metadata = agent.decide_meeting_action(game, meeting)

            if action.get("action") == "speak":
                message = action["params"].get("message", "")
                meeting.add_speech(player.name, message)
                round_speeches.append({
                    "player_name": player.name,
                    "message": message,
                    "thought": metadata.get("thought", ""),
                    "api_usage": {"input_tokens": metadata.get("input_tokens", 0),
                                  "output_tokens": metadata.get("output_tokens", 0)},
                })
                print(f"  {player.name}: {message[:120]}")

        meeting.current_round += 1
        discussion_log.append(round_speeches)

    # Voting round
    votes = {}
    for player in game.get_alive_players():
        agent = agents[player.id]
        action, metadata = agent.decide_meeting_action(game, meeting)

        if action.get("action") == "vote":
            target = action["params"].get("target", "skip")
            meeting.votes[player.id] = target
            votes[player.name] = target
            print(f"  {player.name} voted for: {target}")

    # Tally votes
    vote_counts = Counter(meeting.votes.values())
    ejected = None
    ejected_role = None
    if vote_counts:
        most_voted = vote_counts.most_common(1)[0]
        if most_voted[0] != "skip" and most_voted[1] > len(game.get_alive_players()) // 2:
            ejected_name = most_voted[0]
            for p in game.players:
                if p.name == ejected_name:
                    p.alive = False
                    ejected = ejected_name
                    ejected_role = p.role.value
                    print(f"  >> {ejected_name} was ejected! (Role: {p.role.value})")
                    break
        else:
            print("  >> No one was ejected.")

    vote_result = {
        "ejected": ejected,
        "ejected_role": ejected_role,
        "vote_counts": dict(vote_counts),
    }

    logger.log_meeting(
        timestep=game.timestep,
        trigger_reason=trigger_reason,
        discussion_rounds=discussion_log,
        votes=votes,
        vote_result=vote_result,
        body_info=body_info,
    )

    # Clean up: remove bodies, reset meeting
    game.dead_bodies.clear()
    game.phase = Phase.TASK
    game.meeting_state = None
    return vote_result


def run_game(config: ExperimentConfig, run_id: int = 0) -> Dict:
    """跑一局游戏，返回结果"""
    personalities = config.personality_config if config.personality_config else None
    game = initialize_game(
        num_crewmates=config.num_crewmates,
        num_impostors=config.num_impostors,
        personalities=personalities,
    )
    agents = create_agents(game, config)
    logger = GameLogger(config.name, run_id, config.log_dir)
    logger.set_meta(config, game.players)

    print("=" * 60)
    print(f"AMONG US - Game {config.name}_{run_id:03d}")
    print(f"Players: {[(p.name, p.role.value) for p in game.players]}")
    print("=" * 60)

    task_steps_since_meeting = 0
    total_meetings = 0

    while True:
        game.timestep += 1
        print(f"\n--- Timestep {game.timestep} [{game.phase.value.upper()}] ---")

        # Task Phase
        turn_actions = []
        for player in game.get_alive_players():
            agent = agents[player.id]
            action, metadata = agent.decide_action(game)

            result = execute_action(player, action, game)
            entry = logger.log_action(player, "", action, result, metadata)
            turn_actions.append(entry)

            print(f"  {player.name}: {action['action']} {action['params']} -> {result['detail'][:60]}")

            # Check for body discovery after each player's action
            if action.get("action") != "kill":
                body = check_body_discovery(game)
                if body:
                    print(f"\n  !! {body['finder']} found a dead body in {body['location']}!")
                    total_meetings += 1
                    run_meeting(game, agents, logger, "body_found", body)
                    task_steps_since_meeting = 0
                    # Check victory after meeting
                    winner = game.check_victory()
                    if winner:
                        break
                    break  # restart the timestep loop after meeting

        logger.log_turn(game.timestep, "task", turn_actions)

        # Check victory
        winner = game.check_victory()
        if winner:
            reason = "impostor_ejected" if winner == "crewmate" else "crewmates_eliminated"
            break

        # Scheduled meeting every N task steps
        task_steps_since_meeting += 1
        if task_steps_since_meeting >= config.meeting_interval:
            print(f"\n  >> Scheduled meeting!")
            total_meetings += 1
            run_meeting(game, agents, logger, "scheduled")
            task_steps_since_meeting = 0

            winner = game.check_victory()
            if winner:
                reason = "impostor_ejected" if winner == "crewmate" else "crewmates_eliminated"
                break

        if game.timestep >= game.max_timesteps:
            winner = "impostor"
            reason = "timeout"
            break

    # Count tasks completed
    tasks_completed = sum(1 for p in game.get_crewmates() for t in p.tasks if t.completed)
    total_kills = len(game.kill_log)

    # Check if all tasks done
    all_crew_tasks = [t for p in game.get_crewmates() for t in p.tasks]
    if all_crew_tasks and all(t.completed for t in all_crew_tasks) and winner == "crewmate":
        reason = "tasks_completed"

    print(f"\n{'='*60}")
    print(f"GAME OVER - {winner.upper()} WIN! (Reason: {reason})")
    print(f"Timesteps: {game.timestep}, Kills: {total_kills}, Tasks: {tasks_completed}")
    print(f"{'='*60}")

    logger.set_outcome(winner, reason, game.timestep, total_kills, total_meetings, tasks_completed)
    log_path = logger.finalize()
    print(f"Log saved: {log_path}")

    # Update player survival info in logger
    for pi in logger.players_info:
        p = game.players[pi["id"]]
        pi["survived"] = p.alive
        pi["tasks_completed"] = sum(1 for t in p.tasks if t.completed)

    # Re-save with updated player info
    logger.finalize()

    return {
        "winner": winner,
        "reason": reason,
        "timesteps": game.timestep,
        "kills": total_kills,
        "tasks_completed": tasks_completed,
        "meetings": total_meetings,
    }


if __name__ == "__main__":
    config = ExperimentConfig(name="test", num_games=1, max_timesteps=20)
    run_game(config, run_id=0)
