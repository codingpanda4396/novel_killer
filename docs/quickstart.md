# NovelOps 内测版快速启动指南

## 本地开发测试

### 1. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置邀请码

编辑 `config/novelops.json`（如果不存在，复制 `config/novelops.example.json`）：

```json
{
  "default_project": "life_balance",
  "db_path": "runtime/novelops.sqlite3",
  "web": {
    "host": "127.0.0.1",
    "port": 8787,
    "session_secret": "dev-secret-key"
  },
  "invites": {
    "TEST-001": {
      "project": "life_balance",
      "label": "测试用户"
    }
  }
}
```

### 3. 准备项目数据

```bash
# 如果还没有项目，创建一个
python -m novelops.cli init-project life_balance \
  --name "生活平衡" \
  --genre "都市生活"

# 重建索引
python -m novelops.cli index
```

### 4. 启动服务

```bash
python -m novelops.cli serve
```

### 5. 访问测试

1. 打开浏览器访问 `http://127.0.0.1:8787`
2. 输入邀请码 `TEST-001`
3. 进入工作台

## 内测用户使用流程

### 首次登录

1. 打开内测网址
2. 输入您收到的邀请码
3. 进入您的作品工作台

### 工作台功能

- **生成下一章**：AI 自动生成下一章内容
- **审稿最新章**：对最新章节进行质量审核
- **查看待修订**：查看需要修改的章节列表
- **导出章节**：导出已完成的章节
- **下一步建议**：获取创作建议

### 自定义操作

在"自定义操作"输入框中，您可以输入自然语言指令，例如：

- "查看第 10 章详情"
- "生成第 15 章"
- "审稿第 20 章"
- "查看项目状态"

## 常见问题

### Q: 邀请码在哪里？

A: 邀请码由管理员分配，请联系项目负责人获取。

### Q: 生成章节需要多久？

A: 通常需要 1-3 分钟，请耐心等待。

### Q: 可以修改已生成的章节吗？

A: 目前内测版暂不支持在线编辑，建议导出后使用本地编辑器修改。

### Q: 忘记邀请码怎么办？

A: 请联系管理员重新获取。

### Q: 如何退出登录？

A: 点击右上角的"退出"按钮。

## 反馈问题

如果遇到问题或有建议，请联系：

- 邮箱：support@example.com
- 微信：novelops_support
