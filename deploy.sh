#!/bin/bash

# MinIO Web Manager 部署脚本
# 使用方法: ./deploy.sh [docker|systemd]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Docker（如果使用Docker部署）
    if [[ "$1" == "docker" ]]; then
        if ! command -v docker &> /dev/null; then
            log_error "Docker未安装，请先安装Docker"
            exit 1
        fi
        
        if ! command -v docker-compose &> /dev/null; then
            log_error "Docker Compose未安装，请先安装Docker Compose"
            exit 1
        fi
        
        log_success "Docker环境检查通过"
    fi
    
    # 检查Python（如果使用systemd部署）
    if [[ "$1" == "systemd" ]]; then
        if ! command -v python3 &> /dev/null; then
            log_error "Python3未安装，请先安装Python3"
            exit 1
        fi
        
        if ! command -v pip3 &> /dev/null; then
            log_error "pip3未安装，请先安装pip3"
            exit 1
        fi
        
        log_success "Python环境检查通过"
    fi
}

# Docker部署
deploy_docker() {
    log_info "开始Docker部署..."
    
    # 创建必要的目录
    mkdir -p logs ssl
    
    # 构建并启动服务
    log_info "构建Docker镜像..."
    docker-compose build
    
    log_info "启动服务..."
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 检查服务状态
    log_info "检查服务状态..."
    docker-compose ps
    
    # 检查健康状态
    log_info "检查健康状态..."
    if curl -f http://localhost/health &> /dev/null; then
        log_success "服务启动成功！"
        log_info "访问地址: http://localhost"
        log_info "MinIO控制台: http://localhost:9001"
        log_info "MinIO API: http://localhost:9000"
    else
        log_error "服务启动失败，请检查日志"
        docker-compose logs
        exit 1
    fi
}

# Systemd部署
deploy_systemd() {
    log_info "开始Systemd部署..."
    
    # 创建应用目录
    sudo mkdir -p /opt/minio-web-manager
    sudo mkdir -p /var/log/minio-web-manager
    
    # 复制应用文件
    log_info "复制应用文件..."
    sudo cp -r . /opt/minio-web-manager/
    sudo chown -R www-data:www-data /opt/minio-web-manager
    sudo chown -R www-data:www-data /var/log/minio-web-manager
    
    # 创建虚拟环境
    log_info "创建Python虚拟环境..."
    cd /opt/minio-web-manager
    sudo -u www-data python3 -m venv venv
    sudo -u www-data venv/bin/pip install --upgrade pip
    sudo -u www-data venv/bin/pip install -r requirements.txt
    
    # 安装systemd服务
    log_info "安装systemd服务..."
    sudo cp systemd/minio-web-manager.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable minio-web-manager
    
    # 启动服务
    log_info "启动服务..."
    sudo systemctl start minio-web-manager
    
    # 检查服务状态
    sleep 5
    if sudo systemctl is-active --quiet minio-web-manager; then
        log_success "服务启动成功！"
        log_info "服务状态: $(sudo systemctl is-active minio-web-manager)"
        log_info "访问地址: http://localhost:5000"
    else
        log_error "服务启动失败"
        sudo systemctl status minio-web-manager
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "MinIO Web Manager 部署脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 docker     - 使用Docker Compose部署"
    echo "  $0 systemd    - 使用Systemd部署"
    echo "  $0 help       - 显示此帮助信息"
    echo ""
    echo "Docker部署特点:"
    echo "  - 包含完整的服务栈（Web应用 + MinIO + Nginx）"
    echo "  - 自动健康检查"
    echo "  - 易于扩展和维护"
    echo ""
    echo "Systemd部署特点:"
    echo "  - 直接部署在主机上"
    echo "  - 更好的性能"
    echo "  - 需要手动配置MinIO和Nginx"
    echo ""
}

# 主函数
main() {
    case "$1" in
        "docker")
            check_dependencies docker
            deploy_docker
            ;;
        "systemd")
            check_dependencies systemd
            deploy_systemd
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "无效的参数: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@" 