#!/bin/bash
# 看山小苗圃 · Docker 构建修复脚本
# 用途：修复 pip 超时问题，使用阿里云镜像，增加超时时间
#
# 使用方法：
#   1. 在本地运行：bash scripts/fix-docker-build.sh
#   2. 或者推送到服务器后运行：bash /opt/kanshan/scripts/fix-docker-build.sh

set -e

echo "=========================================="
echo "看山小苗圃 · Docker 构建修复脚本"
echo "=========================================="

# 检查是否在正确的目录
if [ ! -f "infra/docker-compose.yml" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    echo "当前目录：$(pwd)"
    exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT_DIR}/infra"

echo ""
echo "📁 项目根目录：${ROOT_DIR}"
echo "📁 Infra 目录：${INFRA_DIR}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 步骤 1：备份 Dockerfile
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "📦 步骤 1：备份 Dockerfile..."
BACKUP_DIR="${ROOT_DIR}/.docker-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "${BACKUP_DIR}"
find services -name "Dockerfile" -exec cp {} "${BACKUP_DIR}/" \;
echo "✅ 备份完成：${BACKUP_DIR}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 步骤 2：修改 Dockerfile
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "🔧 步骤 2：修改 Dockerfile..."

# 2.1 注释掉清华镜像配置
echo "   - 注释掉清华镜像配置..."
find services -name "Dockerfile" -exec sed -i 's|^RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple|# RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple|g' {} \;

# 2.2 替换为阿里云镜像（可选，如果需要使用镜像）
echo "   - 添加阿里云镜像配置..."
find services -name "Dockerfile" -exec sed -i 's|^# RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple|RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple|g' {} \;

# 2.3 增加 pip 超时时间
echo "   - 增加 pip 超时时间（100秒）..."
find services -name "Dockerfile" -exec sed -i 's|pip install --no-cache-dir -r|pip install --no-cache-dir --timeout 100 -r|g' {} \;

# 2.4 删除可能残留的 EOF
echo "   - 清理残留的 EOF..."
find services -name "Dockerfile" -exec sed -i '/^EOF$/d' {} \;

echo "✅ Dockerfile 修改完成"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 步骤 3：验证修改
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "🔍 步骤 3：验证修改..."

echo "   检查是否还有清华镜像配置："
if grep -r "pypi.tuna.tsinghua.edu.cn" services/*/Dockerfile > /dev/null 2>&1; then
    echo "   ⚠️  警告：仍然有清华镜像配置"
    grep -r "pypi.tuna.tsinghua.edu.cn" services/*/Dockerfile
else
    echo "   ✅ 没有找到清华镜像配置"
fi

echo ""
echo "   检查阿里云镜像配置："
if grep -r "mirrors.aliyun.com" services/*/Dockerfile > /dev/null 2>&1; then
    echo "   ✅ 找到阿里云镜像配置"
else
    echo "   ⚠️  警告：没有找到阿里云镜像配置"
fi

echo ""
echo "   检查超时配置："
if grep -r "timeout" services/*/Dockerfile > /dev/null 2>&1; then
    echo "   ✅ 找到超时配置"
else
    echo "   ⚠️  警告：没有找到超时配置"
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 步骤 4：查看修改后的 Dockerfile
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "📄 步骤 4：查看修改后的 Dockerfile（api-gateway）..."
echo "----------------------------------------"
cat services/api-gateway/Dockerfile
echo "----------------------------------------"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 步骤 5：停止所有服务
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "🛑 步骤 5：停止所有服务..."
cd "${INFRA_DIR}"
docker compose down
echo "✅ 服务已停止"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 步骤 6：清理 Docker 缓存
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "🧹 步骤 6：清理 Docker 缓存..."
docker system prune -f
echo "✅ 缓存已清理"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 步骤 7：重新构建所有服务
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "🔨 步骤 7：重新构建所有服务（可能需要 5-10 分钟）..."
docker compose build --no-cache
echo "✅ 构建完成"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 步骤 8：启动所有服务
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "🚀 步骤 8：启动所有服务..."
docker compose up -d
echo "✅ 服务已启动"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 步骤 9：等待服务启动
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "⏳ 步骤 9：等待服务启动（60秒）..."
sleep 60
echo "✅ 等待完成"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 步骤 10：检查服务状态
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "📊 步骤 10：检查服务状态..."
docker compose ps

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 步骤 11：测试服务
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "🧪 步骤 11：测试服务..."

echo ""
echo "测试 PostgreSQL："
docker exec kanshan-postgres pg_isready -U kanshan || echo "❌ PostgreSQL 未就绪"

echo ""
echo "测试 Redis："
docker exec kanshan-redis redis-cli ping || echo "❌ Redis 未响应"

echo ""
echo "测试 profile-service (8010)："
curl -s http://localhost:8010/health || echo "❌ profile-service 未响应"

echo ""
echo "测试 content-service (8020)："
curl -s http://localhost:8020/health || echo "❌ content-service 未响应"

echo ""
echo "测试 api-gateway (8000)："
curl -s http://localhost:8000/health || echo "❌ api-gateway 未响应"

echo ""
echo "测试外部访问："
curl -s http://113.44.217.169:8000/health || echo "❌ 外部访问失败"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 完成
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo "=========================================="
echo "✅ 修复完成！"
echo "=========================================="
echo ""
echo "📋 后续步骤："
echo "   1. 检查服务状态：docker compose ps"
echo "   2. 查看日志：docker compose logs -f"
echo "   3. 访问前端：http://113.44.217.169:3000"
echo ""
echo "📁 备份位置：${BACKUP_DIR}"
echo ""
