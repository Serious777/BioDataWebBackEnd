#!/bin/bash

# 添加调试输出函数
debug_log() {
    echo "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 接收工作目录作为参数
work_dir=$1
if [ -z "$work_dir" ]; then
    echo "Error: Work directory not provided"
    exit 1
fi

# 设置文件路径
geno_dir=${work_dir}
geno_file=example  # prefix
thread=4
# 设置脚本路径（使用绝对路径）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd ${work_dir}
debug_log "Working directory: $(pwd)"
debug_log "Listing initial files:"
ls -l

# 转换文本文件行尾为LF
debug_log "Converting text files to Unix format (LF)..."
for txt_file in p1s.txt p2s.txt target.txt; do
    if [ -f "$txt_file" ]; then
        debug_log "Processing $txt_file"
        debug_log "Original content of $txt_file:"
        cat "$txt_file"
        
        # 创建临时文件
        tr -d '\r' < "$txt_file" > "${txt_file}.tmp"
        # 替换原文件
        mv "${txt_file}.tmp" "$txt_file"
        # 确保文件末尾有换行符
        sed -i -e '$a\' "$txt_file"
        
        debug_log "Converted content of $txt_file:"
        cat "$txt_file"
    else
        echo "Warning: $txt_file not found"
    fi
done

debug_log "Reading population lists..."
p1s=$(cat p1s.txt)
debug_log "P1 populations: ${p1s}"
p2s=$(cat p2s.txt)
debug_log "P2 populations: ${p2s}"
target=$(cat target.txt)
debug_log "Target populations: ${target}"

# extract
debug_log "Creating extract.poplist..."
poplist="${p1s} ${p2s} ${target}"
for i in ${poplist}; do echo ${i}; done | sort -u > extract.poplist
debug_log "Content of extract.poplist:"
cat extract.poplist

debug_log "Creating extract.par..."
echo "genotypename: ${geno_dir}/${geno_file}.geno" > extract.par
echo "snpname: ${geno_dir}/${geno_file}.snp" >> extract.par
echo "indivname: ${geno_dir}/${geno_file}.ind" >> extract.par
echo "outputformat: PACKEDANCESTRYMAP" >> extract.par
echo "genotypeoutname: extract.geno" >> extract.par
echo "snpoutname: extract.snp" >> extract.par
echo "indivoutname: extract.ind" >> extract.par
echo "poplistname: extract.poplist" >> extract.par

debug_log "Running convertf..."
convertf -p extract.par
debug_log "Checking convertf output files:"
ls -l extract.*

# qp3pop
debug_log "Creating qp3pop file..."
parallel echo {1} {2} {3} ::: ${p1s} ::: ${p2s} ::: ${target} > qp3pop
debug_log "Content of qp3pop file:"
cat qp3pop

# qp3.par
debug_log "Creating qp3.par..."
echo "genotypename:   extract.geno" > qp3.par
echo "snpname:        extract.snp" >> qp3.par
echo "indivname:      extract.ind" >> qp3.par
echo "popfilename:    qp3pop" >> qp3.par
echo "inbreed:        YES" >> qp3.par

# 检查qp3pop文件是否生成成功
if [ ! -s qp3pop ]; then
    echo "Error: Failed to generate qp3pop file or file is empty"
    debug_log "Directory contents:"
    ls -l
    exit 1
fi

# 分割文件并准备参数文件
debug_log "Splitting qp3pop file..."
a=$(wc -l qp3pop | cut -d ' ' -f 1)
b=$(expr ${a} / ${thread} )
line=$(expr ${b} + 1 )
split -l ${line} qp3pop spop
li=$(ls spop*)
debug_log "Split files created: ${li}"

for i in ${li}; do
    debug_log "Creating parameter file for ${i}..."
    cat qp3.par | sed "s/qp3pop/${i}/g" > ${i}.par
done

# 运行qp3Pop
debug_log "Running qp3Pop..."
for i in ${li}; do
    debug_log "Processing ${i}..."
    qp3Pop -p ${i}.par > ${i}.result
    debug_log "Result file ${i}.result content:"
    cat ${i}.result
done

# 合并结果
debug_log "Merging results..."
cat spop*.result > result.txt 2>/dev/null || true
if [ ! -s result.txt ]; then
    echo "Error: Failed to generate results"
    debug_log "Content of working directory:"
    ls -l
    exit 1
fi

debug_log "Extracting result lines..."
cat result.txt | grep result: | sort -nk 7 > summ.result
debug_log "Content of summ.result:"
cat summ.result

debug_log "Creating result directories..."
mkdir -p p1 p2 tar

debug_log "Processing results by population..."
for i in ${p1s}; do
    debug_log "Processing P1 population: ${i}"
    cat summ.result | awk -v tmp=${i} '{if($2==tmp)print $0}' > ./p1/${i}.result
done

for i in ${p2s}; do
    debug_log "Processing P2 population: ${i}"
    cat summ.result | awk -v tmp=${i} '{if($3==tmp)print $0}' > ./p2/${i}.result
done

for i in ${target}; do
    debug_log "Processing target population: ${i}"
    cat summ.result | awk -v tmp=${i} '{if($4==tmp)print $0}' > ./tar/${i}.result
done

cp ${SCRIPT_DIR}/merge_f3_result.v1.0.py ./
cp ${SCRIPT_DIR}/f3_plot.R ./


python merge_f3_result.v1.0.py

#cd p1 ;cat *result > summ.result; python ../merge_f3_result.v1.0.py ; mv result.xlsx p1.xlsx  ; cd ../
#cd p2 ;cat *result > summ.result; python ../merge_f3_result.v1.0.py ; mv result.xlsx p2.xlsx  ; cd ../
#cd tar;cat *result > summ.result; python ../merge_f3_result.v1.0.py ; mv result.xlsx tar.xlsx ; cd ../

Rscript ./f3_plot.R
# 打包结果文件
zip -r f3.zip \
    result.xlsx \
    summ.result \
    *.pdf \
    p1 \
    p2 \
    tar \
    p1s.txt \
    p2s.txt \
    target.txt \
    2>/dev/null

# 清理中间文件
rm -f extract.* tmp.* plink.* spop* *.par error.txt

