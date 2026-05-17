"""提示词参数化引擎

支持 {{variable}} 占位符替换，参数类型：slider, select, boolean
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ParamType(str, Enum):
    SLIDER = "slider"
    SELECT = "select"
    BOOLEAN = "boolean"
    TEXT = "text"
    INT = "int"
    FLOAT = "float"


@dataclass
class ParamDef:
    """参数定义"""
    name: str
    type: ParamType
    description: str = ""
    default: Any = None
    # slider参数
    min: float | None = None
    max: float | None = None
    step: float | None = None
    # select参数
    options: list[str] | None = None
    # 验证
    required: bool = False

    def validate(self, value: Any) -> tuple[bool, str]:
        """验证参数值"""
        if value is None:
            if self.required:
                return False, f"参数 {self.name} 是必填项"
            return True, ""

        if self.type == ParamType.BOOLEAN:
            if not isinstance(value, bool):
                return False, f"参数 {self.name} 必须是布尔值"
            return True, ""

        if self.type in (ParamType.INT, ParamType.SLIDER):
            try:
                num = int(value)
            except (TypeError, ValueError):
                return False, f"参数 {self.name} 必须是整数"
            if self.min is not None and num < self.min:
                return False, f"参数 {self.name} 不能小于 {self.min}"
            if self.max is not None and num > self.max:
                return False, f"参数 {self.name} 不能大于 {self.max}"
            return True, ""

        if self.type == ParamType.FLOAT:
            try:
                num = float(value)
            except (TypeError, ValueError):
                return False, f"参数 {self.name} 必须是数字"
            if self.min is not None and num < self.min:
                return False, f"参数 {self.name} 不能小于 {self.min}"
            if self.max is not None and num > self.max:
                return False, f"参数 {self.name} 不能大于 {self.max}"
            return True, ""

        if self.type == ParamType.SELECT:
            if self.options and str(value) not in self.options:
                return False, f"参数 {self.name} 必须是以下之一: {', '.join(self.options)}"
            return True, ""

        return True, ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "default": self.default,
            "required": self.required,
        }
        if self.min is not None:
            data["min"] = self.min
        if self.max is not None:
            data["max"] = self.max
        if self.step is not None:
            data["step"] = self.step
        if self.options is not None:
            data["options"] = self.options
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParamDef:
        """从字典创建"""
        return cls(
            name=data["name"],
            type=ParamType(data["type"]),
            description=data.get("description", ""),
            default=data.get("default"),
            min=data.get("min"),
            max=data.get("max"),
            step=data.get("step"),
            options=data.get("options"),
            required=data.get("required", False),
        )


@dataclass
class PromptTemplate:
    """提示词模板"""
    id: str
    stage: str
    name: str
    system_prompt: str = ""
    user_prompt_template: str = ""
    description: str = ""
    params: list[ParamDef] = field(default_factory=list)
    genre: str | None = None
    is_default: bool = False
    version: int = 1

    def get_param(self, name: str) -> ParamDef | None:
        """获取参数定义"""
        for p in self.params:
            if p.name == name:
                return p
        return None

    def get_defaults(self) -> dict[str, Any]:
        """获取所有参数默认值"""
        return {p.name: p.default for p in self.params if p.default is not None}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "stage": self.stage,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "user_prompt_template": self.user_prompt_template,
            "description": self.description,
            "params": [p.to_dict() for p in self.params],
            "genre": self.genre,
            "is_default": self.is_default,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptTemplate:
        """从字典创建"""
        return cls(
            id=data["id"],
            stage=data["stage"],
            name=data["name"],
            system_prompt=data.get("system_prompt", ""),
            user_prompt_template=data.get("user_prompt_template", ""),
            description=data.get("description", ""),
            params=[ParamDef.from_dict(p) for p in data.get("params", [])],
            genre=data.get("genre"),
            is_default=data.get("is_default", False),
            version=data.get("version", 1),
        )


class PromptEngine:
    """提示词参数化引擎

    支持 {{variable}} 占位符替换，自动注入examples
    """

    # 占位符模式：{{variable}} 或 {{variable | default_value}}
    PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*(\w+)(?:\s*\|\s*(.+?))?\s*\}\}")

    def __init__(self, template: PromptTemplate):
        self.template = template
        self._param_defs = {p.name: p for p in template.params}

    def extract_placeholders(self, text: str | None = None) -> list[str]:
        """提取模板中的所有占位符"""
        target = text or self.template.user_prompt_template
        return list(set(self.PLACEHOLDER_PATTERN.findall(target)))

    def render(
        self,
        params: dict[str, Any] | None = None,
        examples: list[dict[str, Any]] | None = None,
    ) -> tuple[str, str]:
        """渲染模板

        Args:
            params: 参数值，未提供则使用默认值
            examples: 示例列表，每项包含 {"type": "positive"/"negative", "input": str, "output": str}

        Returns:
            (system_prompt, user_prompt) 元组
        """
        merged_params = self.template.get_defaults()
        if params:
            merged_params.update(params)

        # 验证参数
        errors = []
        for name, value in merged_params.items():
            if name in self._param_defs:
                valid, msg = self._param_defs[name].validate(value)
                if not valid:
                    errors.append(msg)
        if errors:
            raise ValueError(f"参数验证失败: {'; '.join(errors)}")

        # 渲染模板
        system = self._render_text(self.template.system_prompt, merged_params)
        user = self._render_text(self.template.user_prompt_template, merged_params)

        # 注入示例
        if examples:
            examples_text = self._format_examples(examples)
            user = user + "\n\n" + examples_text

        return system, user

    def render_with_defaults(self, extra_params: dict[str, Any] | None = None) -> tuple[str, str]:
        """使用默认值渲染，可选覆盖部分参数"""
        params = self.template.get_defaults()
        if extra_params:
            params.update(extra_params)
        return self.render(params)

    def _render_text(self, text: str, params: dict[str, Any]) -> str:
        """替换文本中的占位符"""
        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            default_value = match.group(2) or ""

            if var_name in params:
                return str(params[var_name])
            return default_value

        return self.PLACEHOLDER_PATTERN.sub(replacer, text)

    def _format_examples(self, examples: list[dict[str, Any]]) -> str:
        """格式化示例"""
        if not examples:
            return ""

        lines = ["【参考示例】"]
        for i, ex in enumerate(examples, 1):
            ex_type = ex.get("type", "positive")
            label = "✓ 正例" if ex_type == "positive" else "✗ 反例"
            lines.append(f"\n{label} {i}:")
            if ex.get("input"):
                lines.append(f"输入: {ex['input'][:200]}...")
            if ex.get("output"):
                lines.append(f"输出: {ex['output'][:300]}...")
            if ex.get("notes"):
                lines.append(f"说明: {ex['notes']}")

        return "\n".join(lines)


def create_template_from_dict(data: dict[str, Any]) -> PromptTemplate:
    """从字典创建模板"""
    return PromptTemplate.from_dict(data)


def create_engine(template: PromptTemplate) -> PromptEngine:
    """创建引擎实例"""
    return PromptEngine(template)
