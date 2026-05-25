#!/usr/bin/env python3
"""Skill Evolution Engine — skill 自我进化机制

借鉴 ECC 的 session 记录 + skill 自动改进，实现：
1. 记录每次 skill 使用情况（成功/失败/改进点）
2. 定期分析使用模式，自动生成 patch
3. 多 agent 共享进化结果

数据存储: agents/memory/evolution/evolution.db (SQLite)
"""

import json
import sqlite3
import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── 路径配置 ────────────────────────────────────────────────

AGENTS_DIR = Path(__file__).parent.parent
EVOLUTION_DB = AGENTS_DIR / "memory" / "evolution" / "evolution.db"
SHARED_SKILLS_DIR = AGENTS_DIR / "shared-skills"
RUNTIME_DIR = AGENTS_DIR / "memory" / "runtime"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_db() -> sqlite3.Connection:
    """获取进化数据库连接（自动建表）"""
    EVOLUTION_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(EVOLUTION_DB))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS skill_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            session_id TEXT,
            timestamp TEXT NOT NULL,
            success INTEGER NOT NULL DEFAULT 1,
            duration_seconds REAL,
            input_summary TEXT,
            output_summary TEXT,
            error_message TEXT,
            improvement_hint TEXT,
            context_hash TEXT
        );
        
        CREATE TABLE IF NOT EXISTS skill_evolution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL,
            version_before TEXT,
            version_after TEXT,
            timestamp TEXT NOT NULL,
            trigger_reason TEXT,
            changes_summary TEXT,
            patch_diff TEXT,
            approved INTEGER DEFAULT 0,
            applied INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS shared_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            ttl_seconds INTEGER DEFAULT 3600
        );
        
        CREATE INDEX IF NOT EXISTS idx_usage_skill ON skill_usage(skill_name);
        CREATE INDEX IF NOT EXISTS idx_usage_agent ON skill_usage(agent_name);
        CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON skill_usage(timestamp);
        CREATE INDEX IF NOT EXISTS idx_evolution_skill ON skill_evolution(skill_name);
        CREATE INDEX IF NOT EXISTS idx_context_key ON shared_context(agent_name, key);
    """)
    return conn


# ── Skill 使用记录 ──────────────────────────────────────────

def record_usage(
    skill_name: str,
    agent_name: str,
    success: bool = True,
    duration_seconds: float = 0,
    session_id: str = "",
    input_summary: str = "",
    output_summary: str = "",
    error_message: str = "",
    improvement_hint: str = "",
) -> int:
    """记录一次 skill 使用"""
    conn = _get_db()
    try:
        # 生成上下文 hash 用于去重
        ctx = f"{skill_name}:{agent_name}:{input_summary}"
        ctx_hash = hashlib.md5(ctx.encode()).hexdigest()[:12]
        
        cur = conn.execute("""
            INSERT INTO skill_usage 
            (skill_name, agent_name, session_id, timestamp, success, 
             duration_seconds, input_summary, output_summary, 
             error_message, improvement_hint, context_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (skill_name, agent_name, session_id, _now(), int(success),
              duration_seconds, input_summary[:500], output_summary[:500],
              error_message[:500], improvement_hint[:500], ctx_hash))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ── Skill 进化分析 ──────────────────────────────────────────

def analyze_skill(skill_name: str, min_uses: int = 5) -> Dict[str, Any]:
    """分析一个 skill 的使用情况"""
    conn = _get_db()
    try:
        rows = conn.execute("""
            SELECT success, duration_seconds, error_message, improvement_hint, timestamp
            FROM skill_usage WHERE skill_name = ?
            ORDER BY timestamp DESC LIMIT 100
        """, (skill_name,)).fetchall()
        
        if not rows:
            return {"skill": skill_name, "status": "no_data"}
        
        total = len(rows)
        successes = sum(1 for r in rows if r["success"])
        avg_duration = sum(r["duration_seconds"] or 0 for r in rows) / max(total, 1)
        errors = [r["error_message"] for r in rows if r["error_message"]]
        hints = [r["improvement_hint"] for r in rows if r["improvement_hint"]]
        
        return {
            "skill": skill_name,
            "total_uses": total,
            "success_rate": round(successes / total, 3),
            "avg_duration": round(avg_duration, 2),
            "recent_errors": errors[-5:],
            "improvement_hints": hints[-5:],
            "should_evolve": total >= min_uses and successes / total < 0.8,
        }
    finally:
        conn.close()


def get_all_skill_stats() -> List[Dict[str, Any]]:
    """获取所有 skill 的统计"""
    conn = _get_db()
    try:
        skills = conn.execute("""
            SELECT skill_name, 
                   COUNT(*) as total,
                   SUM(success) as successes,
                   AVG(duration_seconds) as avg_duration
            FROM skill_usage
            GROUP BY skill_name
            ORDER BY total DESC
        """).fetchall()
        
        return [dict(s) for s in skills]
    finally:
        conn.close()


# ── 进化建议生成 ────────────────────────────────────────────

def generate_evolution_suggestions() -> List[Dict[str, Any]]:
    """基于使用数据生成进化建议"""
    conn = _get_db()
    try:
        skills = conn.execute("""
            SELECT skill_name, 
                   COUNT(*) as total,
                   SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures,
                   GROUP_CONCAT(DISTINCT improvement_hint) as hints
            FROM skill_usage
            WHERE timestamp > datetime('now', '-7 days')
            GROUP BY skill_name
            HAVING total >= 3
        """).fetchall()
        
        suggestions = []
        for s in skills:
            failure_rate = s["failures"] / s["total"] if s["total"] > 0 else 0
            if failure_rate > 0.2:  # 失败率超过 20%
                suggestions.append({
                    "skill": s["skill_name"],
                    "priority": "high" if failure_rate > 0.5 else "medium",
                    "failure_rate": round(failure_rate, 3),
                    "hints": s["hints"].split(",") if s["hints"] else [],
                    "action": "review_and_patch",
                })
            elif s["hints"]:
                hints = [h for h in s["hints"].split(",") if h.strip()]
                if len(hints) >= 2:  # 多次提到同一改进点
                    suggestions.append({
                        "skill": s["skill_name"],
                        "priority": "low",
                        "hints": hints,
                        "action": "consider_improvement",
                    })
        
        return sorted(suggestions, key=lambda x: 
                      {"high": 0, "medium": 1, "low": 2}[x["priority"]])
    finally:
        conn.close()


# ── 共享上下文 ──────────────────────────────────────────────

def set_shared_context(agent_name: str, key: str, value: str, ttl: int = 3600):
    """写入共享上下文"""
    conn = _get_db()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO shared_context (agent_name, key, value, timestamp, ttl_seconds)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, key, value, _now(), ttl))
        conn.commit()
    finally:
        conn.close()


def get_shared_context(agent_name: str = "", key: str = "") -> List[Dict]:
    """读取共享上下文"""
    conn = _get_db()
    try:
        # 清理过期
        conn.execute("""
            DELETE FROM shared_context 
            WHERE datetime(timestamp, '+' || ttl_seconds || ' seconds') < datetime('now')
        """)
        conn.commit()
        
        if agent_name and key:
            rows = conn.execute(
                "SELECT * FROM shared_context WHERE agent_name = ? AND key = ?",
                (agent_name, key)
            ).fetchall()
        elif agent_name:
            rows = conn.execute(
                "SELECT * FROM shared_context WHERE agent_name = ?",
                (agent_name,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM shared_context").fetchall()
        
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── SKILL.md 元数据更新 ─────────────────────────────────────

def update_skill_metadata(skill_path: Path, key: str, value: Any) -> bool:
    """更新 SKILL.md 的 frontmatter 元数据"""
    if not skill_path.exists():
        return False
    
    content = skill_path.read_text()
    
    # 解析 frontmatter
    if not content.startswith("---"):
        return False
    
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return False
    
    yaml_part = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3:]
    
    # 简单更新（对嵌套 key 用点号表示）
    lines = yaml_part.split("\n")
    key_parts = key.split(".")
    updated = False
    
    if len(key_parts) == 1:
        for i, line in enumerate(lines):
            if line.startswith(f"{key}:"):
                if isinstance(value, str):
                    lines[i] = f'{key}: "{value}"'
                elif isinstance(value, (int, float)):
                    lines[i] = f"{key}: {value}"
                else:
                    lines[i] = f"{key}: {json.dumps(value)}"
                updated = True
                break
        if not updated:
            if isinstance(value, str):
                lines.append(f'{key}: "{value}"')
            elif isinstance(value, (int, float)):
                lines.append(f"{key}: {value}")
            else:
                lines.append(f"{key}: {json.dumps(value)}")
    
    new_yaml = "\n".join(lines)
    skill_path.write_text(f"---\n{new_yaml}\n---\n{body}")
    return True


# ── CLI 接口 ────────────────────────────────────────────────

def main():
    import sys
    args = sys.argv[1:]
    
    if not args:
        print("Usage: skill_evolution.py <command> [args...]")
        print("Commands: stats, analyze <skill>, suggest, record <skill> <agent> [--fail] [--hint '...']")
        return
    
    cmd = args[0]
    
    if cmd == "stats":
        stats = get_all_skill_stats()
        for s in stats:
            rate = s["successes"] / s["total"] if s["total"] > 0 else 0
            print(f"  {s['skill_name']:30s} uses={s['total']:4d}  success={rate:.1%}  avg={s['avg_duration']:.1f}s")
    
    elif cmd == "analyze" and len(args) > 1:
        result = analyze_skill(args[1])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif cmd == "suggest":
        suggestions = generate_evolution_suggestions()
        if not suggestions:
            print("No evolution suggestions — all skills performing well!")
        for s in suggestions:
            print(f"  [{s['priority'].upper()}] {s['skill']} — {s.get('failure_rate', 'N/A')} failure rate")
            for h in s.get("hints", []):
                if h.strip():
                    print(f"    → {h.strip()}")
    
    elif cmd == "record" and len(args) > 2:
        success = "--fail" not in args
        hint = ""
        if "--hint" in args:
            idx = args.index("--hint")
            if idx + 1 < len(args):
                hint = args[idx + 1]
        
        record_usage(
            skill_name=args[1],
            agent_name=args[2],
            success=success,
            improvement_hint=hint,
        )
        print(f"✓ Recorded: {args[1]} by {args[2]} ({'success' if success else 'failure'})")
    
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
