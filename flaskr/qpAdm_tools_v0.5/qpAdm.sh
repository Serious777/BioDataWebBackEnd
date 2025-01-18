#! /bin/bash
# 在脚本开头添加错误检查
set -e  # 遇到错误立即退出
set -u  # 使用未定义的变量时报错

# 添加调试输出函数
debug_log() {
    echo "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 添加错误输出函数
error_log() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 接收工作目录作为参数
work_dir=$1
if [ -z "$work_dir" ]; then
    error_log "Work directory not provided"
    exit 1
fi

# 检查必要文件
required_files=("qpadm_local.py" "2.bsub_qpAdm.sh" "3.grep_result.sh" "5.result2excel.py" "6.excel2r.py" "7.barplot.r" "utils.py")
for file in "${required_files[@]}"; do
    if [ ! -f "${SCRIPT_DIR}/${file}" ]; then
        error_log "Required file not found: ${file}"
        exit 1
    fi
done

# 设置文件路径
geno_dir=${work_dir}
geno_file=example  # prefix

cd ${geno_dir} || {
    error_log "Failed to change directory to ${geno_dir}"
    exit 1
}

debug_log "Copying required files to working directory"
# 复制必要文件到工作目录
cp ${SCRIPT_DIR}/qpadm_local.py \
   ${SCRIPT_DIR}/2.bsub_qpAdm.sh \
   ${SCRIPT_DIR}/3.grep_result.sh \
   ${SCRIPT_DIR}/5.result2excel.py \
   ${SCRIPT_DIR}/6.excel2r.py \
   ${SCRIPT_DIR}/7.barplot.r \
   ${SCRIPT_DIR}/utils.py \
   ./ || {
    error_log "Failed to copy required files"
    exit 1
}

debug_log "Running qpadm_local.py"
python qpadm_local.py || {
    error_log "qpadm_local.py failed"
    exit 1
}

debug_log "Creating result zip file"
zip -r qpadm.zip ./result ./qpadm_plot.pdf ./qpadm_result.xlsx || {
    error_log "Failed to create zip file"
    exit 1
}

debug_log "qpAdm analysis completed successfully"
