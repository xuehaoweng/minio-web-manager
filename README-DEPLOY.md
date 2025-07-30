# MinIO Web Manager 部署指南

本文档详细说明如何部署 MinIO Web Manager 项目。

## 📋 部署选项

### 1. Docker Compose 部署（推荐）
- **优点**: 一键部署，包含完整服务栈
- **适用场景**: 开发环境、测试环境、生产环境
- **包含服务**: Web应用 + MinIO + Nginx

### 2. Systemd 部署
- **优点**: 更好的性能，直接部署在主机上
- **适用场景**: 生产环境
- **需要**: 手动配置 MinIO 和 Nginx

## 🚀 快速部署

### 方法一：使用部署脚本（推荐）

```bash
# 给脚本执行权限
chmod +x deploy.sh

# Docker部署
./deploy.sh docker

# Systemd部署
./deploy.sh systemd

# 查看帮助
./deploy.sh help
```

### 方法二：手动部署

#### Docker Compose 部署

1. **准备环境**
```bash
# 确保已安装 Docker 和 Docker Compose
docker --version
docker-compose --version
```

2. **配置环境变量**
```bash
# 编辑 config.env 文件
vim config.env
```

3. **启动服务**
```bash
# 构建并启动
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

4. **访问应用**
- Web应用: http://localhost
- MinIO控制台: http://localhost:9001
- MinIO API: http://localhost:9000

#### Systemd 部署

1. **准备环境**
```bash
# 安装 Python3 和 pip3
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

2. **部署应用**
```bash
# 创建应用目录
sudo mkdir -p /opt/minio-web-manager
sudo mkdir -p /var/log/minio-web-manager

# 复制应用文件
sudo cp -r . /opt/minio-web-manager/
sudo chown -R www-data:www-data /opt/minio-web-manager
sudo chown -R www-data:www-data /var/log/minio-web-manager

# 创建虚拟环境
cd /opt/minio-web-manager
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install -r requirements.txt

# 安装 systemd 服务
sudo cp systemd/minio-web-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable minio-web-manager
sudo systemctl start minio-web-manager
```

3. **配置 Nginx（可选）**
```bash
# 安装 Nginx
sudo apt install nginx

# 复制配置文件
sudo cp nginx.conf /etc/nginx/sites-available/minio-web-manager
sudo ln -s /etc/nginx/sites-available/minio-web-manager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## ⚙️ 配置说明

### 环境变量配置 (config.env)

```env
# MinIO 配置
MINIO_ENDPOINT=http://localhost:9000
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=12345678
MINIO_BUCKET_NAME=uploads
MINIO_SECURE=false

# 文件上传配置
MAX_FILE_SIZE=104857600  # 100MB
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,pdf,doc,docx,txt,zip
```

### Docker Compose 配置

- **Web应用**: 端口 5000
- **MinIO API**: 端口 9000
- **MinIO控制台**: 端口 9001
- **Nginx**: 端口 80

### Systemd 服务配置

- **服务名称**: minio-web-manager
- **运行用户**: www-data
- **工作目录**: /opt/minio-web-manager
- **日志目录**: /var/log/minio-web-manager

## 🔧 管理命令

### Docker Compose 管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f minio-web-manager

# 进入容器
docker-compose exec minio-web-manager bash

# 更新应用
docker-compose build
docker-compose up -d
```

### Systemd 管理

```bash
# 启动服务
sudo systemctl start minio-web-manager

# 停止服务
sudo systemctl stop minio-web-manager

# 重启服务
sudo systemctl restart minio-web-manager

# 查看状态
sudo systemctl status minio-web-manager

# 查看日志
sudo journalctl -u minio-web-manager -f

# 启用开机自启
sudo systemctl enable minio-web-manager
```

## 📊 监控和日志

### 健康检查

- **Web应用**: http://localhost/status
- **Nginx**: http://localhost/health
- **MinIO**: http://localhost:9000/minio/health/live

### 日志位置

#### Docker 部署
```bash
# 应用日志
docker-compose logs minio-web-manager

# Nginx 日志
docker-compose logs nginx

# MinIO 日志
docker-compose logs minio
```

#### Systemd 部署
```bash
# 应用日志
sudo journalctl -u minio-web-manager

# 系统日志
sudo tail -f /var/log/syslog
```

## 🔒 安全配置

### 生产环境建议

1. **修改默认密码**
```env
MINIO_ROOT_USER=your-username
MINIO_ROOT_PASSWORD=your-strong-password
```

2. **启用 HTTPS**
```nginx
# 在 nginx.conf 中取消注释 HTTPS 配置
# 并配置 SSL 证书
```

3. **防火墙配置**
```bash
# 只开放必要端口
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 9000
sudo ufw allow 9001
```

4. **定期备份**
```bash
# 备份 MinIO 数据
docker-compose exec minio mc mirror /data /backup

# 备份配置文件
cp config.env config.env.backup
```

## 🐛 故障排除

### 常见问题

1. **端口被占用**
```bash
# 检查端口占用
netstat -tlnp | grep :5000

# 修改端口
# 在 docker-compose.yml 中修改端口映射
```

2. **权限问题**
```bash
# 修复文件权限
sudo chown -R www-data:www-data /opt/minio-web-manager
sudo chmod -R 755 /opt/minio-web-manager
```

3. **内存不足**
```bash
# 增加 Docker 内存限制
# 在 docker-compose.yml 中添加
# deploy:
#   resources:
#     limits:
#       memory: 1G
```

4. **磁盘空间不足**
```bash
# 清理 Docker 缓存
docker system prune -a

# 清理日志
sudo journalctl --vacuum-time=7d
```

### 调试模式

```bash
# 启用调试日志
export FLASK_ENV=development
export FLASK_DEBUG=1

# 直接运行应用
python app.py
```

## 📈 性能优化

### Docker 优化

1. **多实例部署**
```yaml
# 在 docker-compose.yml 中添加多个实例
services:
  minio-web-manager-1:
    build: .
    # ... 配置
  minio-web-manager-2:
    build: .
    # ... 配置
```

2. **资源限制**
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
```

### Systemd 优化

1. **调整工作进程数**
```bash
# 修改 gunicorn 参数
--workers 4  # 根据 CPU 核心数调整
```

2. **启用日志轮转**
```bash
# 创建 logrotate 配置
sudo vim /etc/logrotate.d/minio-web-manager
```

## 🔄 更新部署

### Docker 更新

```bash
# 拉取最新代码
git pull

# 重新构建并部署
docker-compose build
docker-compose up -d

# 清理旧镜像
docker image prune
```

### Systemd 更新

```bash
# 停止服务
sudo systemctl stop minio-web-manager

# 更新代码
sudo cp -r . /opt/minio-web-manager/

# 更新依赖
cd /opt/minio-web-manager
sudo -u www-data venv/bin/pip install -r requirements.txt

# 重启服务
sudo systemctl start minio-web-manager
```

## 📞 技术支持

如果遇到问题，请：

1. 检查日志文件
2. 查看健康检查状态
3. 确认环境变量配置
4. 验证网络连接
5. 检查端口占用情况

---

**部署完成后，您就可以通过浏览器访问 MinIO Web Manager 了！** 