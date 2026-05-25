#!/usr/bin/env python3
"""Agent & Skill Manager — 统一管理入口

提供 CLI 和编程接口：
  python agents/manage.py skill list
  python agents/manage.py skill create <name> --desc "..."
  python agents/manage.py skill stats
  python agents/manage.py agent list
  python agents/manage.py agent show <name>
  python agents/manage.py evolve suggest
  python agents/manage.py evolve run <skill-name>
  python agents/manage.py context get <agent> <key>
  python agents/manage.py context set <agent> <key> <value>
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

AGENTS_DIR = Path(__file__).parent
SHARED_SKILLS_DIR = AGENTS_DIR / "shared-skills"
AGENT_REGISTRY_DIR = AGENTS_DIR / "agent-registry"
KNOWLEDGE_DIR = AGENTS_DIR / "knowledge"
RUNTIME_DIR = AGENTS_DIR / "memory" / "runtime"


# ── Skill 管理 ──────────────────────────────────────────────

def list_skills() -> List[Dict]:
    """列出所有共享 skill"""
    skills = []
    if not SHARED_SKILLS_DIR.exists():
        return skills
    
    for category_dir in sorted(SHARED_SKILLS_DIR.iterdir()):
        if not category_dir.is_dir():
            skill_file = category_dir / "SKILL.md" if category_dir.is_file() else None
            continue
        for skill_dir in sorted(category_dir.iterdir()):
            skill_file = skill_dir / "SKILL.md" if skill_dir.is_dir() else None
            if skill_file and skill_file.exists():
                meta = _parse_frontmatter(skill_file.read_text())
                if meta:
                    skills.append({
                        "name": meta.get("name", skill_dir.name),
                        "description": meta.get("description", ""),
                        "version": meta.get("version", ""),
                        "tags": meta.get("metadata", {}).get("hermes", {}).get("tags", []),
                        "path": str(skill_dir),
                    })
    
    # 也检查平铺的 skill（shared-skills/ 下直接是 skill 目录）
    for skill_dir in sorted(SHARED_SKILLS_DIR.iterdir()):
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                meta = _parse_frontmatter(skill_file.read_text())
                if meta:
                    already = any(s["name"] == meta.get("name") for s in skills)
                    if not already:
                        skills.append({
                            "name": meta.get("name", skill_dir.name),
                            "description": meta.get("description", ""),
                            "version": meta.get("version", ""),
                            "tags": meta.get("metadata", {}).get("hermes", {}).get("tags", []),
                            "path": str(skill_dir),
                        })
    return skills


def create_skill(name: str, description: str, tags: List[str] = None, 
                 instructions: str = "") -> Path:
    """创建新 skill"""
    slug = re.sub(r'[^a-z0-9-]', '-', name.lower()).strip('-')
    skill_dir = SHARED_SKILLS_DIR / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    tags_yaml = json.dumps(tags or [slug])
    
    content = f"""---
name: {slug}
description: {description}
version: 1.0.0
metadata:
  hermes:
    tags: {tags_yaml}
  evolution:
    use_count: 0
    last_used: ""
    success_rate: 0.0
    auto_evolve: true
---

# {name}

{instructions or "TODO: 添加具体指令..."}
"""
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content)
    return skill_file


def show_skill(name: str) -> Optional[Dict]:
    """查看 skill 详情"""
    for skill in list_skills():
        if skill["name"] == name:
            skill_file = Path(skill["path"]) / "SKILL.md"
            content = skill_file.read_text()
            meta, body = _parse_frontmatter_full(content)
            return {**skill, "content": body, "frontmatter": meta}
    return None


def delete_skill(name: str) -> bool:
    """删除 skill"""
    import shutil
    for skill in list_skills():
        if skill["name"] == name:
            shutil.rmtree(skill["path"])
            return True
    return False


# ── Agent 管理 ──────────────────────────────────────────────

def list_agents() -> List[Dict]:
    """列出所有 agent"""
    agents = []
    if not AGENT_REGISTRY_DIR.exists():
        return agents
    
    for agent_dir in sorted(AGENT_REGISTRY_DIR.iterdir()):
        if not agent_dir.is_dir():
            continue
        soul_file = agent_dir / "SOUL.md"
        if soul_file.exists():
            meta = _parse_frontmatter(soul_file.read_text())
            if meta:
                agents.append({
                    "name": meta.get("name", agent_dir.name),
                    "version": meta.get("version", ""),
                    "description": meta.get("description", ""),
                    "skills": meta.get("skills", []),
                    "tools": meta.get("tools", []),
                    "path": str(agent_dir),
                })
    return agents


def show_agent(name: str) -> Optional[Dict]:
    """查看 agent 详情"""
    for agent in list_agents():
        if agent["name"] == name:
            soul_file = Path(agent["path"]) / "SOUL.md"
            content = soul_file.read_text()
            meta, body = _parse_frontmatter_full(content)
            return {**agent, "content": body, "frontmatter": meta}
    return None


def add_skill_to_agent(agent_name: str, skill_name: str) -> bool:
    """给 agent 添加 skill"""
    for agent in list_agents():
        if agent["name"] == agent_name:
            soul_file = Path(agent["path"]) / "SOUL.md"
            content = soul_file.read_text()
            skills = list(agent.get("skills", []))
            if skill_name not in skills:
                skills.append(skill_name)
                # 行级别替换 frontmatter 中的 skills 列表
                lines = content.split("\n")
                new_lines = []
                skip_old = False
                for line in lines:
                    if line.startswith("skills:"):
                        # 写入新的 skills 列表
                        new_lines.append("skills:")
                        for s in skills:
                            new_lines.append(f"  - {s}")
                        skip_old = True
                        continue
                    if skip_old and line.startswith("  - "):
                        continue  # 跳过旧的 skill 条目
                    skip_old = False
                    new_lines.append(line)
                soul_file.write_text("\n".join(new_lines))
            return True
    return False


# ── 进化系统 ────────────────────────────────────────────────

def get_evolution_stats() -> List[Dict]:
    """获取 skill 进化统计"""
    sys.path.insert(0, str(AGENTS_DIR / "hooks"))
    from skill_evolution import get_all_skill_stats, generate_evolution_suggestions
    return {
        "stats": get_all_skill_stats(),
        "suggestions": generate_evolution_suggestions(),
    }


# ── 辅助函数 ────────────────────────────────────────────────

def _parse_frontmatter(content: str) -> Optional[Dict]:
    """解析 YAML frontmatter"""
    if not content.startswith("---"):
        return None
    end = re.search(r"\n---\s*\n", content[3:])
    if not end:
        return None
    yaml_str = content[3:end.start() + 3]
    try:
        import yaml
        return yaml.safe_load(yaml_str)
    except:
        return None


def _parse_frontmatter_full(content: str) -> tuple:
    """解析 frontmatter 返回 (meta, body)"""
    if not content.startswith("---"):
        return {}, content
    end = re.search(r"\n---\s*\n", content[3:])
    if not end:
        return {}, content
    yaml_str = content[3:end.start() + 3]
    body = content[end.end():]
    try:
        import yaml
        meta = yaml.safe_load(yaml_str) or {}
    except:
        meta = {}
    return meta, body


# ── CLI ─────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        _print_help()
        return
    
    cmd = args[0]
    
    if cmd == "skill":
        _handle_skill(args[1:])
    elif cmd == "agent":
        _handle_agent(args[1:])
    elif cmd == "evolve":
        _handle_evolve(args[1:])
    elif cmd == "context":
        _handle_context(args[1:])
    else:
        print(f"Unknown command: {cmd}")
        _print_help()


def _print_help():
    print("""
Agent & Skill Manager
=====================
  skill list              列出所有共享 skill
  skill create <name>     创建新 skill
  skill show <name>       查看 skill 详情
  skill delete <name>     删除 skill
  skill stats             查看使用统计
  
  agent list              列出所有 agent
  agent show <name>       查看 agent 详情
  agent add-skill <agent> <skill>  给 agent 添加 skill
  
  evolve stats            进化统计
  evolve suggest          进化建议
  
  context get [agent] [key]  读取共享上下文
  context set <agent> <key> <value>  写入共享上下文
""")


def _handle_skill(args):
    if not args:
        print("Usage: skill list|create|show|delete|stats")
        return
    
    sub = args[0]
    if sub == "list":
        skills = list_skills()
        if not skills:
            print("No shared skills yet. Create one with: skill create <name>")
            return
        for s in skills:
            tags = ", ".join(s.get("tags", [])[:3])
            print(f"  📦 {s['name']:20s} v{s.get('version', '?'):5s} {s.get('description', '')[:50]}")
            if tags:
                print(f"     tags: {tags}")
    
    elif sub == "create" and len(args) > 1:
        name = args[1]
        desc = ""
        tags = []
        instructions = ""
        for i, a in enumerate(args[2:], 2):
            if a.startswith("--desc="):
                desc = a[7:].strip('"\'')
            elif a.startswith("--tags="):
                tags = a[7:].split(",")
            elif a.startswith("--instructions="):
                instructions = a[14:].strip('"\'')
        
        path = create_skill(name, desc or f"{name} skill", tags, instructions)
        print(f"✅ Created: {path}")
    
    elif sub == "show" and len(args) > 1:
        info = show_skill(args[1])
        if info:
            print(f"## {info['name']} (v{info.get('version', '?')})")
            print(f"Description: {info.get('description', '')}")
            print(f"Tags: {', '.join(info.get('tags', []))}")
            print(f"Path: {info.get('path', '')}")
            print(f"\n{info.get('content', '')}")
        else:
            print(f"❌ Skill not found: {args[1]}")
    
    elif sub == "delete" and len(args) > 1:
        if delete_skill(args[1]):
            print(f"✅ Deleted: {args[1]}")
        else:
            print(f"❌ Skill not found: {args[1]}")
    
    elif sub == "stats":
        try:
            stats = get_evolution_stats()
            for s in stats.get("stats", []):
                print(f"  {s['skill_name']:20s} uses={s['total']:4d}")
        except Exception as e:
            print(f"No evolution data yet. ({e})")
    
    else:
        print(f"Unknown skill subcommand: {sub}")


def _handle_agent(args):
    if not args:
        print("Usage: agent list|show|add-skill")
        return
    
    sub = args[0]
    if sub == "list":
        agents = list_agents()
        for a in agents:
            skills = ", ".join(a.get("skills", [])[:4])
            print(f"  🤖 {a['name']:15s} v{a.get('version', '?'):5s} {a.get('description', '')[:40]}")
            print(f"     skills: {skills}")
    
    elif sub == "show" and len(args) > 1:
        info = show_agent(args[1])
        if info:
            print(f"## {info['name']} (v{info.get('version', '?')})")
            print(f"Description: {info.get('description', '')}")
            print(f"Skills: {', '.join(info.get('skills', []))}")
            print(f"Tools: {', '.join(info.get('tools', []))}")
            print(f"\n{info.get('content', '')}")
        else:
            print(f"❌ Agent not found: {args[1]}")
    
    elif sub == "add-skill" and len(args) > 2:
        if add_skill_to_agent(args[1], args[2]):
            print(f"✅ Added skill '{args[2]}' to agent '{args[1]}'")
        else:
            print(f"❌ Agent not found: {args[1]}")
    
    else:
        print(f"Unknown agent subcommand: {sub}")


def _handle_evolve(args):
    if not args:
        print("Usage: evolve stats|suggest")
        return
    
    sub = args[0]
    try:
        stats = get_evolution_stats()
    except Exception as e:
        print(f"Evolution engine error: {e}")
        return
    
    if sub == "stats":
        for s in stats.get("stats", []):
            rate = s["successes"] / s["total"] if s["total"] > 0 else 0
            print(f"  {s['skill_name']:20s} uses={s['total']:4d} success={rate:.0%} avg={s['avg_duration']:.1f}s")
        if not stats.get("stats"):
            print("No usage data yet — start using skills to build evolution history!")
    
    elif sub == "suggest":
        suggestions = stats.get("suggestions", [])
        if not suggestions:
            print("✅ All skills performing well — no evolution needed!")
        for s in suggestions:
            print(f"  [{s['priority'].upper()}] {s['skill']} — action: {s['action']}")
            for h in s.get("hints", []):
                if h.strip():
                    print(f"    → {h.strip()}")


def _handle_context(args):
    if not args:
        print("Usage: context get [agent] [key] | set <agent> <key> <value>")
        return
    
    sub = args[0]
    sys.path.insert(0, str(AGENTS_DIR / "hooks"))
    from skill_evolution import get_shared_context, set_shared_context
    
    if sub == "get":
        agent = args[1] if len(args) > 1 else ""
        key = args[2] if len(args) > 2 else ""
        ctx = get_shared_context(agent, key)
        for c in ctx:
            print(f"  {c['agent_name']}/{c['key']}: {c['value'][:100]}")
        if not ctx:
            print("No shared context found.")
    
    elif sub == "set" and len(args) > 3:
        set_shared_context(args[1], args[2], " ".join(args[3:]))
        print(f"✅ Set {args[1]}/{args[2]}")


if __name__ == "__main__":
    main()
