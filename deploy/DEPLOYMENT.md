# NovelOps 内测版部署指南

本文档说明如何在 ECS 上部署 NovelOps 内测版本。

## 系统要求

- 操作系统：Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- Python：3.10+
- 内存：至少 2GB
- 磁盘：至少 20GB（用于存储项目数据）
- 网络：公网 IP 和域名

## 部署步骤

### 1. 准备服务器环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装依赖
sudo apt install -y python3 python3-pip python3-venv nginx git

# 创建用户
sudo useradd -m -s /bin/bash novelops
```

### 2. 部署应用

```bash
# 切换到 novelops 用户
sudo su - novelops

# 创建应用目录
mkdir -p /opt/novelops
cd /opt/novelops

# 克隆或上传代码
# 方式 1: 从 git 克隆
git clone <your-repo-url> .

# 方式 2: 上传压缩包
# scp novelops.tar.gz novelops@your-server:/opt/novelops/
# tar -xzf novelops.tar.gz

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install -r requirements.txt

# 初始化索引
python -m novelops.cli index
```

### 3. 配置应用

```bash
# 复制配置文件
cp config/novelops.example.json config/novelops.json

# 编辑配置文件
nano config/novelops.json
```

配置示例：

```json
{
  "default_project": "life_balance",
  "db_path": "runtime/novelops.sqlite3",
  "web": {
    "host": "127.0.0.1",
    "port": 8787,
    "session_secret": "生成一个随机字符串作为密钥"
  },
  "invites": {
    "TEST-USER-001": {
      "user_id": "user001",
      "username": "内测用户001"
    },
    "TEST-USER-002": {
      "user_id": "user002",
      "username": "内测用户002"
    }
  },
  "require_manual_publish_confirmation": true
}
```

**重要**：
- `session_secret` 必须设置为随机字符串（可用 `openssl rand -hex 32` 生成）
- 为每个内测用户添加邀请码配置
- **新版本配置格式**：邀请码现在绑定到用户而非项目，每个用户可以创建多个项目

### 4. 准备项目数据

```bash
# 确保项目目录存在
mkdir -p projects/life_balance

# 初始化项目（如果还没有）
python -m novelops.cli init-project life_balance \
  --name "生活平衡" \
  --genre "都市生活"

# 或者从备份恢复项目数据
# tar -xzf project_backup.tar.gz -C projects/
```

### 5. 配置 systemd 服务

```bash
# 退出 novelops 用户
exit

# 复制 service 文件
sudo cp /opt/novelops/deploy/novelops.service /etc/systemd/system/

# 编辑 service 文件，设置 API Key
sudo nano /etc/systemd/system/novelops.service
```

在 service 文件中设置环境变量：

```ini
Environment="DEEPSEEK_API_KEY=your_actual_key_here"
Environment="RIGHTCODE_API_KEY=your_actual_key_here"
```

启动服务：

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start novelops

# 设置开机自启
sudo systemctl enable novelops

# 查看状态
sudo systemctl status novelops

# 查看日志
sudo journalctl -u novelops -f
```

### 6. 配置 Nginx

```bash
# 复制 nginx 配置
sudo cp /opt/novelops/deploy/nginx.conf /etc/nginx/sites-available/novelops

# 编辑配置，修改域名和 SSL 证书路径
sudo nano /etc/nginx/sites-available/novelops

# 启用站点
sudo ln -s /etc/nginx/sites-available/novelops /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 nginx
sudo systemctl reload nginx
```

### 7. 配置 SSL 证书

使用 Let's Encrypt 免费证书：

```bash
# 安装 certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 证书会自动续期
```

### 8. 配置备份

```bash
# 复制备份脚本
sudo cp /opt/novelops/deploy/backup.sh /opt/novelops/
sudo chmod +x /opt/novelops/backup.sh

# 添加到 crontab（每天凌晨 2 点备份）
sudo crontab -e
```

添加以下行：

```
0 2 * * * /opt/novelops/backup.sh >> /var/log/novelops-backup.log 2>&1
```

## 验证部署

1. 访问 `https://your-domain.com`
2. 应该看到邀请码输入页面
3. 输入配置的邀请码（如 `TEST-USER-001`）
4. 进入工作台页面
5. 测试"下一步建议"按钮

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
sudo journalctl -u novelops -n 100 --no-pager

# 检查端口占用
sudo netstat -tlnp | grep 8787

# 手动测试启动
sudo su - novelops
cd /opt/novelops
source .venv/bin/activate
python -m novelops.cli serve
```

### 邀请码无效

检查配置文件：

```bash
cat /opt/novelops/config/novelops.json | grep -A 5 invites
```

### API 调用失败

检查环境变量：

```bash
sudo systemctl show novelops | grep Environment
```

### 数据库错误

重建索引：

```bash
sudo su - novelops
cd /opt/novelops
source .venv/bin/activate
python -m novelops.cli index
```

## 更新部署

### 常规更新

```bash
# 停止服务
sudo systemctl stop novelops

# 切换到 novelops 用户
sudo su - novelops
cd /opt/novelops

# 拉取最新代码
git pull

# 更新依赖
source .venv/bin/activate
pip install -r requirements.txt

# 重建索引
python -m novelops.cli index

# 退出并重启服务
exit
sudo systemctl start novelops
```

### 升级到多项目版本（v2.0+）

如果从旧版本（单项目绑定）升级到新版本（多项目支持），需要执行数据迁移：

```bash
# 停止服务
sudo systemctl stop novelops

# 切换到 novelops 用户
sudo su - novelops
cd /opt/novelops

# 拉取最新代码
git pull

# 更新依赖
source .venv/bin/activate
pip install -r requirements.txt

# 执行数据迁移（将旧的邀请码-项目绑定迁移到用户-项目关联）
python -m novelops.migrate_to_multi_project

# 重建索引
python -m novelops.cli index

# 退出并重启服务
exit
sudo systemctl start novelops
```

**迁移说明**：
- 迁移脚本会自动识别旧格式的邀请码配置
- 旧格式：`{"project": "xxx", "label": "xxx"}`
- 新格式：`{"user_id": "xxx", "username": "xxx"}`
- 迁移后，旧的项目会自动关联到对应用户
- 建议迁移后更新 `config/novelops.json` 为新格式

## 安全建议

1. **API Key 安全**：
   - 只在 systemd service 文件中配置 API Key
   - 不要提交到 git
   - 定期轮换密钥

2. **Session 密钥**：
   - 使用强随机字符串
   - 生产环境必须修改默认值

3. **防火墙**：
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

4. **定期备份**：
   - 确保备份脚本正常运行
   - 定期测试恢复流程

5. **日志监控**：
   ```bash
   # 监控错误日志
   sudo tail -f /var/log/nginx/novelops-error.log
   sudo journalctl -u novelops -f
   ```

## 扩容建议

当用户增多时：

1. **增加服务器资源**：
   - 内存：每 10 个并发用户约需 1GB
   - CPU：2 核起步，4 核推荐

2. **数据库优化**：
   - 考虑迁移到 PostgreSQL
   - 添加数据库索引

3. **引入任务队列**：
   - 使用 Redis + Celery
   - 异步处理长任务

4. **负载均衡**：
   - 多实例部署
   - Nginx 负载均衡
