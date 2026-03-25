import anthropic
import os
from dotenv import load_dotenv
import json

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ── 虚拟地图（Among Us风格简化版）──────────────────────
MAP = {
    "Cafeteria": ["Weapons", "MedBay", "Admin"],
    "Weapons": ["Cafeteria", "O2"],
    "MedBay": ["Cafeteria", "Electrical"],
    "Electrical": ["MedBay", "Storage"],
    "Storage": ["Electrical", "Admin"],
    "Admin": ["Cafeteria", "Storage"],
    "O2": ["Weapons"],
}

# ── 游戏状态 ──────────────────────────────────────────
game_state = {
    "player_location": "Cafeteria",
    "visited_rooms": ["Cafeteria"],
    "step": 0
}

# ── 定义工具：移动到相邻房间 ───────────────────────────
tools = [
    {
        "name": "move_to_room",
        "description": "Move to an adjacent room. You can only move to rooms directly connected to your current location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_room": {
                    "type": "string",
                    "description": "The name of the room you want to move to (must be adjacent to current room)"
                }
            },
            "required": ["target_room"]
        }
    }
]

# ── 工具执行函数 ───────────────────────────────────────
def execute_move(target_room: str) -> dict:
    current = game_state["player_location"]
    
    if target_room not in MAP.get(current, []):
        return {"success": False, "message": f"Cannot move from {current} to {target_room}. Not adjacent."}
    
    game_state["player_location"] = target_room
    game_state["visited_rooms"].append(target_room)
    game_state["step"] += 1
    
    return {
        "success": True,
        "message": f"Moved to {target_room}",
        "adjacent_rooms": MAP[target_room]
    }

# ── Agent主循环 ────────────────────────────────────────
def run_agent(max_steps=5):
    messages = []
    
    # 初始System Prompt
    system_prompt = """You are exploring a spaceship. Your goal is to visit as many different rooms as possible in 5 steps.

Current map connections:
""" + json.dumps(MAP, indent=2) + f"""

Current location: {game_state['player_location']}
Visited rooms: {game_state['visited_rooms']}

Think strategically about which rooms to visit to maximize coverage."""

    # 第一个用户消息
    messages.append({
        "role": "user",
        "content": f"You are in {game_state['player_location']}. Adjacent rooms: {MAP[game_state['player_location']]}. Where do you want to go?"
    })
    
    for step in range(max_steps):
        print(f"\n{'='*60}")
        print(f"STEP {step + 1}")
        print(f"Current location: {game_state['player_location']}")
        print(f"{'='*60}")
        
        # 调用Claude
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=messages
        )
        
        print(f"\nClaude's response: {response.stop_reason}")
        
        # 处理响应
        if response.stop_reason == "tool_use":
            # Claude决定调用工具
            tool_use_block = next(block for block in response.content if block.type == "tool_use")
            tool_name = tool_use_block.name
            tool_input = tool_use_block.input
            
            print(f"  Tool called: {tool_name}")
            print(f"  Input: {tool_input}")
            
            # 执行工具
            result = execute_move(tool_input["target_room"])
            print(f"  Result: {result}")
            
            # 把Claude的响应加入历史
            messages.append({"role": "assistant", "content": response.content})
            
            # 把工具结果回传
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": json.dumps(result)
                    }
                ]
            })
            
        elif response.stop_reason == "end_turn":
            # Claude完成了思考，继续下一步
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": f"Good. Now you are in {game_state['player_location']}. Adjacent rooms: {MAP[game_state['player_location']]}. Continue exploring."
            })
        
        else:
            print(f"Unexpected stop reason: {response.stop_reason}")
            break
    
    print(f"\n{'='*60}")
    print("EXPLORATION COMPLETE")
    print(f"Visited {len(set(game_state['visited_rooms']))} unique rooms: {set(game_state['visited_rooms'])}")
    print(f"{'='*60}")

if __name__ == "__main__":
    run_agent(max_steps=5)