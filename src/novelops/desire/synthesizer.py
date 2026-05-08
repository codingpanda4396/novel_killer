"""DesireSynthesizer: aggregate Radar signals into 4 markdown documents."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import load_project_path
from ..llm import LLMClient
from ..project_paths import ProjectPaths
from .aggregators import (
    aggregate_desires,
    aggregate_emotions,
    aggregate_genres,
    aggregate_golden_fingers,
    aggregate_hooks,
    aggregate_risks,
    build_competitor_patterns,
    build_trope_library,
    fetch_analyzed_signals,
)
from .schemas import DemandStatement, DesireSynthesisResult, ReaderPersonaProfile


_MANIFEST_NAME = ".desire_synthesis.json"


class DesireSynthesizer:
    """Synthesize demand analysis from Radar signals."""

    def __init__(self, project_path: Path, llm_client: LLMClient | None = None) -> None:
        self.project_path = project_path
        self.paths = ProjectPaths(project_path)
        self.llm = llm_client or LLMClient()

    def run(self, window_days: int = 14, force: bool = False) -> DesireSynthesisResult:
        """Run the full synthesis pipeline.

        Returns DesireSynthesisResult. Also writes 4 markdown files + manifest.
        """
        # Load project config for genre filter
        try:
            cfg = load_project_path(self.project_path)
            genre_filter = cfg.get("genre", "")
        except Exception:
            genre_filter = ""

        # Determine radar DB path
        from ..config import db_path as radar_db_path
        radar_db = radar_db_path()

        # Fetch signals
        signals = fetch_analyzed_signals(radar_db, window_days=window_days, genre_filter=genre_filter)

        # Check idempotency
        manifest = self._load_manifest()
        if not force and manifest:
            sig_count = len(signals)
            max_at = max((s.get("analyzed_at", "") for s in signals), default="")
            if manifest.get("signal_count") == sig_count and manifest.get("max_analyzed_at") == max_at:
                print(f"No new signals since last run (count={sig_count}). Skipping. Use --force to re-run.")
                return DesireSynthesisResult(
                    demands=[], personas=[], tropes=[], competitors=[],
                    signal_count=sig_count, window_days=window_days, max_analyzed_at=max_at,
                )

        # Aggregate
        emotions = aggregate_emotions(signals)
        golden_fingers = aggregate_golden_fingers(signals)
        hooks = aggregate_hooks(signals)
        risks = aggregate_risks(signals)
        desires = aggregate_desires(signals)
        genres = aggregate_genres(signals)
        tropes = build_trope_library(signals)
        competitors = build_competitor_patterns(signals)

        # LLM synthesis
        demands = self._synthesize_demand(signals, desires, emotions, golden_fingers, hooks, risks)
        personas = self._synthesize_personas(signals, emotions, desires)

        # Write outputs
        outputs: dict[str, str] = {}
        errors: list[str] = []

        for name, content in [
            ("demand_analysis.md", self._render_demand_analysis(demands, signals)),
            ("reader_personas.md", self._render_reader_personas(personas)),
            ("trope_library.md", self._render_trope_library(tropes)),
            ("competitor_patterns.md", self._render_competitor_patterns(competitors)),
        ]:
            try:
                path = self.paths.market / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                outputs[name] = hashlib.sha256(content.encode()).hexdigest()
                print(f"  Written: {path}")
            except Exception as e:
                errors.append(f"Failed to write {name}: {e}")

        # Write manifest only if all succeeded
        max_at = max((s.get("analyzed_at", "") for s in signals), default="")
        if not errors:
            self._save_manifest({
                "signal_count": len(signals),
                "max_analyzed_at": max_at,
                "window_days": window_days,
                "outputs": outputs,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })

        return DesireSynthesisResult(
            demands=demands,
            personas=personas,
            tropes=[],
            competitors=[],
            signal_count=len(signals),
            window_days=window_days,
            max_analyzed_at=max_at,
        )

    # ── LLM synthesis ───────────────────────────────────────────────

    def _synthesize_demand(
        self,
        signals: list[dict[str, Any]],
        desires: list[tuple[str, int]],
        emotions: list[tuple[str, int]],
        golden_fingers: list[tuple[str, int]],
        hooks: list[tuple[str, int]],
        risks: list[tuple[str, int]],
    ) -> list[DemandStatement]:
        """LLM call 1: synthesize demand clusters."""
        if not signals:
            return []

        aggregated = {
            "desires": desires[:10],
            "emotions": emotions[:10],
            "golden_fingers": golden_fingers[:10],
            "hooks": hooks[:10],
            "risks": risks[:5],
            "sample_titles": [s.get("title", "") for s in signals[:20]],
        }

        prompt = (
            "基于以下中文网文市场信号聚合数据，提炼 3-5 个欲望集群。\n"
            "每个集群必须包含：cluster_name, desire_statement, frequency, representative_titles, "
            "linked_emotions, recommended_golden_fingers, risk。\n"
            "返回 JSON 数组。\n\n"
            f"聚合数据：\n{json.dumps(aggregated, ensure_ascii=False, indent=2)}"
        )

        system = "你是中文网文市场需求分析师。只返回 JSON 数组。"

        try:
            result = self.llm.complete_json(prompt, system=system, stage="assistant")
            if isinstance(result, list):
                return [DemandStatement(**item) for item in result if isinstance(item, dict)]
            if isinstance(result, dict) and "demands" in result:
                return [DemandStatement(**item) for item in result["demands"] if isinstance(item, dict)]
        except Exception as e:
            print(f"  Warning: demand synthesis LLM call failed: {e}")
        return []

    def _synthesize_personas(
        self,
        signals: list[dict[str, Any]],
        emotions: list[tuple[str, int]],
        desires: list[tuple[str, int]],
    ) -> list[ReaderPersonaProfile]:
        """LLM call 2: synthesize reader personas."""
        if not signals:
            return []

        aggregated = {
            "emotions": emotions[:10],
            "desires": desires[:10],
            "sample_count": len(signals),
            "sample_titles": [s.get("title", "") for s in signals[:15]],
        }

        prompt = (
            "基于以下中文网文市场信号，提炼 3-5 个典型读者画像。\n"
            "每个画像必须包含：name(英文标识), display_name(中文), wants, dislikes, "
            "typical_emotions, representative_works, share_pct(占比百分比)。\n"
            "返回 JSON 数组。\n\n"
            f"聚合数据：\n{json.dumps(aggregated, ensure_ascii=False, indent=2)}"
        )

        system = "你是中文网文读者研究分析师。只返回 JSON 数组。"

        try:
            result = self.llm.complete_json(prompt, system=system, stage="assistant")
            if isinstance(result, list):
                return [ReaderPersonaProfile(**item) for item in result if isinstance(item, dict)]
            if isinstance(result, dict) and "personas" in result:
                return [ReaderPersonaProfile(**item) for item in result["personas"] if isinstance(item, dict)]
        except Exception as e:
            print(f"  Warning: persona synthesis LLM call failed: {e}")
        return []

    # ── Markdown renderers ──────────────────────────────────────────

    def _render_demand_analysis(self, demands: list[DemandStatement], signals: list[dict[str, Any]]) -> str:
        lines = ["# 需求分析\n"]
        lines.append(f"信号总数: {len(signals)}\n")
        lines.append(f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")

        if not demands:
            lines.append("\n> 暂无足够信号生成欲望集群。请先运行 Radar 采集。\n")
        else:
            for i, d in enumerate(demands, 1):
                lines.append(f"\n## {i}. {d.cluster_name}\n")
                lines.append(f"- **欲望陈述**: {d.desire_statement}")
                lines.append(f"- **频次**: {d.frequency}")
                lines.append(f"- **代表标题**: {', '.join(d.representative_titles)}")
                lines.append(f"- **关联情绪**: {', '.join(d.linked_emotions)}")
                lines.append(f"- **推荐金手指**: {', '.join(d.recommended_golden_fingers)}")
                lines.append(f"- **风险**: {d.risk}")

        return "\n".join(lines) + "\n"

    def _render_reader_personas(self, personas: list[ReaderPersonaProfile]) -> str:
        lines = ["# 读者画像\n"]
        lines.append(f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")

        if not personas:
            lines.append("\n> 暂无足够信号生成读者画像。请先运行 Radar 采集。\n")
        else:
            for p in personas:
                lines.append(f"\n## {p.display_name} ({p.name})\n")
                lines.append(f"- **占比**: {p.share_pct:.1f}%")
                lines.append(f"- **想要看到**: {', '.join(p.wants)}")
                lines.append(f"- **讨厌看到**: {', '.join(p.dislikes)}")
                lines.append(f"- **典型情绪**: {', '.join(p.typical_emotions)}")
                lines.append(f"- **代表作品**: {', '.join(p.representative_works)}")

        return "\n".join(lines) + "\n"

    def _render_trope_library(self, tropes: list[dict[str, Any]]) -> str:
        lines = ["# 套路库\n"]
        lines.append(f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")

        if not tropes:
            lines.append("\n> 暂无足够信号生成套路库。\n")
        else:
            for t in tropes:
                lines.append(f"\n## {t['name']} (频次: {t['frequency']})\n")
                lines.append(f"- **代表作品**: {', '.join(t.get('representative_works', []))}")
                lines.append(f"- **热门钩子**: {', '.join(t.get('top_hooks', []))}")
                lines.append(f"- **热门金手指**: {', '.join(t.get('top_golden_fingers', []))}")
                if t.get('platform_distribution'):
                    dist = ', '.join(f"{k}:{v}" for k, v in t['platform_distribution'].items())
                    lines.append(f"- **平台分布**: {dist}")

        return "\n".join(lines) + "\n"

    def _render_competitor_patterns(self, patterns: list[dict[str, Any]]) -> str:
        lines = ["# 竞品模式\n"]
        lines.append(f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")

        if not patterns:
            lines.append("\n> 暂无足够信号生成竞品模式。\n")
        else:
            for p in patterns:
                lines.append(f"\n## {p['genre']}\n")
                lines.append(f"- **常见开篇钩子**: {', '.join(p.get('opening_hooks', []))}")
                lines.append(f"- **饱和警告**: {', '.join(p.get('saturation_warnings', []))}")

        return "\n".join(lines) + "\n"

    # ── Manifest ────────────────────────────────────────────────────

    def _manifest_path(self) -> Path:
        return self.paths.market / _MANIFEST_NAME

    def _load_manifest(self) -> dict[str, Any] | None:
        path = self._manifest_path()
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save_manifest(self, data: dict[str, Any]) -> None:
        path = self._manifest_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
