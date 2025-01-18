#!/bin/bash

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

# 接收工作目录作为参数
work_dir=$1
if [ -z "$work_dir" ]; then
    error_log "Work directory not provided"
    exit 1
fi

# 设置文件路径
geno_dir=${work_dir}
geno_file=example  # prefix
thread=4

# 设置脚本路径（使用绝对路径）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
pairwise_dir=${SCRIPT_DIR}

cd ${work_dir}
debug_log "Working directory: $(pwd)"
debug_log "Listing initial files:"
ls -l

# 转换文本文件行尾为LF
debug_log "Converting text files to Unix format (LF)..."
for txt_file in leftPops.txt rightPops.txt; do
    if [ -f "$txt_file" ]; then
        debug_log "Processing $txt_file"
        debug_log "Original content of $txt_file:"
        cat "$txt_file"
        
        # 创建临时文件
        tr -d '\r' < "$txt_file" > "${txt_file}.tmp"
        mv "${txt_file}.tmp" "$txt_file"
        sed -i -e '$a\' "$txt_file"
        
        debug_log "Converted content of $txt_file:"
        cat "$txt_file"
    else
        echo "Error: Required file $txt_file not found"
        exit 1
    fi
done

# 准备群体列表
debug_log "Preparing population lists..."
cat leftPops.txt rightPops.txt > extract.poplist

# extract population
debug_log "Creating extract.par..."
echo "genotypename: ${geno_dir}/${geno_file}.geno" > extract.par
echo "snpname:      ${geno_dir}/${geno_file}.snp" >> extract.par
echo "indivname:    ${geno_dir}/${geno_file}.ind" >> extract.par
echo "genooutfilename: extract.geno" >> extract.par
echo "snpoutfilename:  extract.snp"  >> extract.par
echo "indoutfilename:  extract.ind"  >> extract.par
echo "poplistname:  extract.poplist" >> extract.par
echo "hashcheck:    NO"  >> extract.par
echo "strandcheck:  NO"  >> extract.par
echo "allowdups:    YES" >> extract.par

debug_log "Running convertf..."
convertf -p extract.par
debug_log "Checking convertf output files:"
ls -l extract.*

# 在运行qpWave之前检查必需文件
debug_log "Checking required files..."
for file in example.geno example.ind example.snp leftPops.txt rightPops.txt; do
    if [ ! -f "$file" ]; then
        error_log "Required file missing: $file"
        debug_log "Directory contents:"
        ls -l
        exit 1
    fi
done

# 在运行convertf之后检查输出
debug_log "Checking convertf output..."
for ext in geno snp ind; do
    if [ ! -f "extract.${ext}" ]; then
        error_log "convertf failed to create extract.${ext}"
        exit 1
    fi
done

# 准备qpWave分析
debug_log "Preparing qpWave analysis..."
mkdir -p result
cp rightPops.txt ./result/outgroup

# 生成运行脚本
debug_log "Generating run scripts..."
cp ${pairwise_dir}/gen_scripts.py ./
cp ${pairwise_dir}/pairwise_qpWave.v1.r ./
cp ${pairwise_dir}/parqpWave.template ./result

python gen_scripts.py leftPops.txt > run_script.txt
debug_log "Content of run_script.txt:"
cat run_script.txt

# 运行qpWave
debug_log "Running qpWave analysis..."
mkdir -p result  # 确保目录存在

# 执行生成的命令
while IFS= read -r cmd; do
    if [ -n "$cmd" ]; then  # 只执行非空行
        debug_log "Executing: $cmd"
        eval "$cmd" || {
            error_log "Command failed: $cmd"
            exit 1
        }
    fi
done < run_script.txt

# 处理结果
debug_log "Processing results..."
cd result
li=$(ls *result)
rm -f final_result.txt
touch final_result.txt

for i in ${li}; do
    debug_log "Processing result file: ${i}"
    echo ${i} | sed 's/.result//g' | sed 's/-/\t/g' >> final_result.txt
    cat ${i} | grep "f4rank: 1 dof:" | sed "s/^\s*//g" | sed "s/[[:blank:]]\+/\t/g" | cut -f 14 >> final_result.txt
    echo "" >> final_result.txt
done

mv final_result.txt ../
cd ../

# 运行R脚本生成热图
debug_log "Running R analysis..."
Rscript pairwise_qpWave.v1.r || {
    error_log "R script failed"
    debug_log "Directory contents:"
    ls -l
    exit 1
}

# 打包结果
debug_log "Creating result archive..."
zip -r qpwave.zip \
    leftPops.txt \
    rightPops.txt \
    result \
    final_result.txt \
    final_result.pdf \
    2>/dev/null

debug_log "Analysis completed"
