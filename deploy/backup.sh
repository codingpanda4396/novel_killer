#!/bin/bash
# NovelOps 备份脚本
# 用法: ./backup.sh

set -e

BACKUP_DIR="/opt/novelops-backups"
NOVELOPS_DIR="/opt/novelops"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="novelops_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

echo "开始备份 NovelOps..."

# 创建备份目录
mkdir -p "${BACKUP_DIR}"
mkdir -p "${BACKUP_PATH}"

# 备份项目数据
echo "备份项目数据..."
if [ -d "${NOVELOPS_DIR}/projects" ]; then
    cp -r "${NOVELOPS_DIR}/projects" "${BACKUP_PATH}/"
fi

# 备份配置文件
echo "备份配置文件..."
if [ -d "${NOVELOPS_DIR}/config" ]; then
    cp -r "${NOVELOPS_DIR}/config" "${BACKUP_PATH}/"
fi

# 备份数据库
echo "备份数据库..."
if [ -f "${NOVELOPS_DIR}/runtime/novelops.sqlite3" ]; then
    mkdir -p "${BACKUP_PATH}/runtime"
    cp "${NOVELOPS_DIR}/runtime/novelops.sqlite3" "${BACKUP_PATH}/runtime/"
fi

# 压缩备份
echo "压缩备份..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"

echo "备份完成: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

# 清理 7 天前的备份
echo "清理旧备份..."
find "${BACKUP_DIR}" -name "novelops_backup_*.tar.gz" -mtime +7 -delete

echo "备份任务完成"
