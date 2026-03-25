# Probing Generative Models Through Adversarial Social Games

UCSD ECE 285 Deep Generative Models - Final Project

## Overview

本项目使用 Among Us 社交推理游戏作为实验平台，研究大语言模型（LLM）在对抗性社交场景中的认知能力，包括欺骗生成与检测、记忆利用、以及推理策略。

核心研究问题：在需要欺骗、推理和社交互动的博弈环境中，生成式模型表现出怎样的认知能力？

## 项目结构

```
.
├── amongagents/                # 核心实现
│   ├── main.py                 # 游戏主循环
│   ├── agent.py                # LLM Agent (OpenAI function calling)
│   ├── random_agent.py         # 随机 baseline agent
│   ├── game_state.py           # 游戏状态管理
│   ├── game_map.py             # 14房间地图拓扑
│   ├── config.py               # 实验配置 & 人格定义
│   ├── logger.py               # JSON日志系统
│   ├── run_experiments.py      # 批量实验脚本
│   ├── run_additional.py       # 追加实验脚本
│   ├── test_map.py             # 地图测试
│   ├── test_state.py           # 状态测试
│   ├── requirements.txt        # 依赖
│   └── analysis/               # 分析工具
│       ├── win_rates.py        # 胜率统计 & 可视化
│       ├── ablations.py        # 消融实验分析
│       ├── conversation_analysis.py  # 会议发言分类
│       ├── controlled_eval.py  # 认知能力评估 (5维度)
│       └── run_all.py          # 一键跑全部分析
├── report/                     # 论文 (NeurIPS格式)
│   ├── final_report.tex
│   ├── final_report.pdf
│   └── *.pdf                   # 实验图表
├── test_hello.py               # API连通性测试
├── agent_map.py                # Agent导航demo
└── 285midtermreport.pdf        # 中期报告
```

## 游戏机制

- **地图**: 14个房间的连通图 (Cafeteria, Weapons, MedBay, Electrical, etc.)
- **角色**: 4 Crewmates vs 1 Impostor
- **目标**: Crewmate完成任务或投票驱逐Impostor；Impostor消灭Crewmate
- **会议**: 每5个回合触发一次定期会议，或发现尸体时紧急会议
- **会议流程**: 2轮讨论 + 1轮投票

## Agent架构

LLM Agent 基于 OpenAI GPT function calling 实现：

- **观察序列化**: 当前位置、同房间玩家、尸体、相邻房间、任务状态
- **记忆系统**: 滚动缓冲区 + LLM压缩摘要
- **人格系统**: 10种人格原型 (5 Impostor + 5 Crewmate)
- **ReAct提示**: [THOUGHT] -> [PLAN] -> [ACTION] 结构化推理
- **函数调用**: move, speak, complete_task, kill, vote

## 实验设计

### 主实验 (4种配置)
| 配置 | Crewmate Agent | Impostor Agent |
|------|---------------|----------------|
| all_random | Random | Random |
| all_llm | LLM | LLM |
| llm_crew | LLM | Random |
| llm_impostor | Random | LLM |

### 消融实验
- **Memory size**: {0, 5, 10, 20}
- **Planning**: ReAct on/off

## 主要发现

1. **欺骗不对称性**: LLM Crewmate对Random Impostor胜率93%，但对LLM Impostor仅36%——说明LLM的欺骗生成能力远超检测能力
2. **记忆是关键**: Crewmate胜率随memory size显著提升 (0→0%, 5→20%, 10→36%)，没有上下文记忆社交推理直接崩溃
3. **Planning不是瓶颈**: ReAct提示 vs 无提示仅差3个百分点，信息获取才是约束，不是推理结构

## 使用方法

```bash
cd amongagents

# 安装依赖
pip install -r requirements.txt

# 设置API key
export OPENAI_API_KEY="your-key"

# 运行实验
python run_experiments.py all_llm
python run_experiments.py --all

# 分析结果
python analysis/run_all.py
python analysis/run_all.py --classify --eval  # 包含LLM分类+评估
```

## 依赖

- Python 3.9+
- openai
- anthropic
- python-dotenv
- matplotlib
- numpy

## Authors

Wenpeng Xu, Jinglin Cao - UC San Diego, ECE Department
