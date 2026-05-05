# NovelOps 内测版更新说明

## 版本：v2.0-beta（内测版）

### 主要变化

#### 1. 邀请码访问控制

- 用户通过邀请码访问系统
- 每个邀请码绑定一个项目
- 登录后自动进入绑定项目的工作台

#### 2. 全新工作台界面

- 简化的用户界面，隐藏技术细节
- 一键操作按钮：生成、审稿、修订、导出
- 实时显示作品状态和进度
- 支持自定义中文指令

#### 3. 项目隔离

- 每个用户只能访问自己绑定的项目
- 数据完全隔离，保护隐私
- 安全的 session 管理

#### 4. 生产就绪

- systemd 服务管理
- Nginx 反向代理
- HTTPS 支持
- 自动备份脚本

### 文件结构变化

```
novelops/
├── novelops/
│   ├── session.py          # 新增：session 管理
│   ├── web.py              # 更新：邀请码登录和访问控制
│   └── templates/
│       ├── invite.html     # 新增：邀请码登录页
│       └── workspace.html  # 新增：工作台页面
├── deploy/                 # 新增：部署配置
│   ├── nginx.conf
│   ├── novelops.service
│   ├── backup.sh
│   └── DEPLOYMENT.md
├── config/
│   └── novelops.example.json  # 更新：添加 invites 和 session_secret
├── requirements.txt        # 更新：添加 itsdangerous
├── QUICKSTART.md          # 新增：快速启动指南
└── BETA_CHANGELOG.md      # 本文件
```

### 配置变化

#### config/novelops.json

新增字段：

```json
{
  "web": {
    "session_secret": "必须配置"
  },
  "invites": {
    "邀请码": {
      "project": "项目ID",
      "label": "用户标签"
    }
  }
}
```

### API 变化

#### 新增端点

- `GET /invite` - 邀请码输入页面
- `POST /invite` - 邀请码验证
- `POST /logout` - 退出登录
- `GET /` - 工作台（原项目列表页）

#### 修改端点

- `POST /api/ask` - 现在需要登录，只能操作绑定项目
- `GET /projects/{project_id}` - 需要登录，只能访问绑定项目
- `GET /revision-queue` - 只显示当前用户的修订队列

### 升级指南

#### 从 v1.x 升级

1. 备份现有数据：
   ```bash
   tar -czf novelops_backup.tar.gz projects/ config/ runtime/
   ```

2. 更新代码：
   ```bash
   git pull
   pip install -r requirements.txt
   ```

3. 更新配置文件：
   ```bash
   # 在 config/novelops.json 中添加：
   {
     "web": {
       "session_secret": "$(openssl rand -hex 32)"
     },
     "invites": {
       "YOUR-CODE": {
         "project": "your_project_id",
         "label": "用户名"
       }
     }
   }
   ```

4. 重建索引：
   ```bash
   python -m novelops.cli index
   ```

5. 重启服务：
   ```bash
   sudo systemctl restart novelops
   ```

### 已知限制

1. **单项目绑定**：每个邀请码只能绑定一个项目
2. **同步处理**：长任务采用同步等待，可能需要等待 1-3 分钟
3. **无后台队列**：暂不支持后台任务队列
4. **无账号体系**：暂不支持用户注册、密码登录
5. **无计费系统**：暂不支持配额和计费

### 后续计划

- [ ] 支持多项目绑定
- [ ] 引入后台任务队列（Redis + Celery）
- [ ] 添加用户注册和密码登录
- [ ] 实现配额和计费系统
- [ ] 支持在线编辑章节
- [ ] 添加协作功能

### 反馈

如有问题或建议，请提交 Issue 或联系开发团队。
