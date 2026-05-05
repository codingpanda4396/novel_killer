# NovelRadar LLM 分析 Prompt

## 输入格式

```json
{
  "title": "{{title}}",
  "category": "{{category}}",
  "tags": "{{tags}}",
  "description": "{{description}}",
  "platform": "{{platform}}"
}
```

## 输出格式

```json
{
  "extracted_genre": "题材名称",
  "protagonist_template": "主角模板",
  "golden_finger": "金手指类型",
  "core_hook": "核心钩子",
  "reader_desire": "读者欲望",
  "shuang_points": ["爽点1", "爽点2"],
  "risk_points": ["风险1", "风险2"],
  "platform_fit_score": 85,
  "competition_score": 60,
  "writing_difficulty_score": 40,
  "reasoning": "分析推理过程"
}
```

## Prompt

你是一个专业的中文网文市场分析师。请分析以下作品信息，提取关键特征并评估商业潜力。

**作品信息**：
- 标题：{{title}}
- 分类：{{category}}
- 标签：{{tags}}
- 简介：{{description}}
- 平台：{{platform}}

请从以下维度分析：

1. **题材识别**：识别主要题材类型（仙侠修真、都市重生、系统流、末世囤货等）
2. **主角模板**：识别主角身份模板（重生者、系统宿主、赘婿等）
3. **金手指**：识别核心金手指类型（系统、空间、重生、词条等）
4. **核心钩子**：提取吸引读者的核心卖点
5. **读者欲望**：分析满足的读者欲望（逆袭爽感、打脸快感等）
6. **爽点**：列出作品的爽点元素
7. **风险**：识别可能的市场风险

最后请给出各维度评分（0-100）。

请以 JSON 格式输出结果。
