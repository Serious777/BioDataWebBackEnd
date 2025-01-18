#!/bin/bash
# coding:utf-8
# @Time : 2022/10/08 01:09
# @Version: v2.6
# @File : smartpca.2.5.sh
# @Author : zky

# 添加调试输出函数
debug_log() {
    echo "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

error_log() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 接收工作目录作为参数
workdir=$1
if [ -z "$workdir" ]; then
    error_log "Work directory not provided"
    exit 1
fi

# 设置文件路径
geno_dir=${workdir}
geno_file=example  # prefix
poplist=${workdir}/pop-list.txt

debug_log "Working directory: ${workdir}"
debug_log "Geno directory: ${geno_dir}"
debug_log "Population list: ${poplist}"

# 设置脚本路径（使用绝对路径）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
pcaRploter=${SCRIPT_DIR}/pcaRploter.v4.4.py
bc=${SCRIPT_DIR}/bc.py

debug_log "Script directory: ${SCRIPT_DIR}"
debug_log "PCA plotter script: ${pcaRploter}"
debug_log "BC script: ${bc}"

# alias rmsp='sed "s/^\s*//g" | sed "s/[[:blank:]]\+/\t/g"'
rmsp() {
    sed "s/^\s*//g" | sed "s/[[:blank:]]\+/\t/g"
}

cd ${workdir}
debug_log "Changed to working directory: $(pwd)"

# 验证必需文件
debug_log "Checking required files..."
if [ ! -f ${geno_dir}/${geno_file}.geno ] || [ ! -f ${pcaRploter} ] || [ ! -f ${poplist} ]; then
    error_log "Missing required files"
    debug_log "Checking files:"
    debug_log "Geno file: ${geno_dir}/${geno_file}.geno (exists: $([ -f ${geno_dir}/${geno_file}.geno ] && echo 'yes' || echo 'no'))"
    debug_log "PCA plotter: ${pcaRploter} (exists: $([ -f ${pcaRploter} ] && echo 'yes' || echo 'no'))"
    debug_log "Population list: ${poplist} (exists: $([ -f ${poplist} ] && echo 'yes' || echo 'no'))"
    exit 1
fi

# check extract.poplist
debug_log "Checking populations..."
lack_pops=""
cat ${poplist} | grep -v "=" > extract.poplist
cat ${geno_dir}/${geno_file}.ind | awk '{print $3}' | sort -u > ind.tmp

debug_log "Cleaning Windows line endings..."
tr -d '\r' < extract.poplist > extract.poplist.clean
tr -d '\r' < ind.tmp > ind.tmp.clean
mv -f extract.poplist.clean extract.poplist
mv -f ind.tmp.clean ind.tmp

debug_log "Validating population list..."
pops=$(cat extract.poplist)
for pop in ${pops}; do
    debug_log "Checking population: ${pop}"
    cat ind.tmp | grep -x ${pop} >/dev/null 2>&1
    if [ ! $? -eq 0 ]; then 
        lack_pops="${lack_pops} [${pop}]"
        flag="FALSE"
        error_log "Population not found: ${pop}"
    fi
done

debug_log "Population check completed"
rm -f ind.tmp

if [[ ${flag} == "FALSE" ]]; then
    error_log "Missing populations: ${lack_pops}"
    exit 1
fi

# extract poplist from HO
debug_log "Running convertf..."
debug_log "Creating extract.par file"
for i in "extract.par"; do
    echo "genotypename: ${geno_dir}/${geno_file}.geno"
    echo "snpname: ${geno_dir}/${geno_file}.snp"
    echo "indivname: ${geno_dir}/${geno_file}.ind"
    echo "genotypeoutname: extract.geno"
    echo "snpoutname: extract.snp"
    echo "indivoutname: extract.ind"
    echo "poplistname: extract.poplist"
    echo "hashcheck: NO"
    echo "strandcheck: NO"
    echo "allowdups: YES"
done > extract.par

debug_log "Running convertf with extract.par"
convertf -p extract.par
debug_log "Convertf completed"

# smartpca preprocessing
debug_log "Preprocessing for smartpca..."
row=$(cat ${poplist} -n | grep "====Ancient" | head -n 1 | rmsp | cut -f 1)
row=$[ ${row} - 1 ]
debug_log "Ancient marker row: ${row}"
cat ${poplist} | head -n ${row} | grep -v "=" > modern.poplist
debug_log "Created modern.poplist"

# smartpca.par
debug_log "Creating smartpca.par file"
for i in "smartpca.par"; do
    echo "genotypename: extract.geno"
    echo "snpname:      extract.snp"
    echo "indivname:    extract.ind"
    echo "evecoutname:  smartpca.evec"
    echo "evaloutname:  smartpca.eval"
    echo "poplistname:  modern.poplist"
    echo "lsqproject: YES"
    echo "numoutevec: 5"
    echo "altnormstyle: NO"
    echo "numoutlieriter : 0"
    echo "numthreads: 20"
done > smartpca.par

# smartpca
debug_log "Running smartpca..."
smartpca -p smartpca.par > smartpca.log 2>&1
debug_log "Smartpca completed"

# Calculate PCs
debug_log "Calculating PCs..."
lines=$(wc -l smartpca.eval | rmsp | cut -f 1)
lines=$(expr ${lines} - 1 )
pc1=$(head -n 1 smartpca.eval)
pc2=$(tail -n+2 smartpca.eval | head -n 1)
debug_log "PC1 value: ${pc1}"
debug_log "PC2 value: ${pc2}"

echo -n "PC1: " >  PCs.txt ; echo "${pc1}/${lines}*100" | xargs -n 1 python ${bc} >> PCs.txt ; echo "%" >> PCs.txt
echo -n "PC2: " >> PCs.txt ; echo "${pc2}/${lines}*100" | xargs -n 1 python ${bc} >> PCs.txt ; echo "%" >> PCs.txt

# Post-Processing
debug_log "Post-processing results..."
tail -n+2 smartpca.evec | awk '{print $7,$1,$2,$3}' > plot.txt
cp ${pcaRploter} ./
debug_log "Running PCA plotter..."
python pcaRploter.v4.4.py
debug_log "Running R script..."
Rscript smartpca.r

debug_log "Creating result archive..."
zip smartpca.zip extract.poplist modern.poplist plot.txt pop-list.txt smartpca.eval smartpca.evec smartpca.pdf legend.pdf smartpca.log PCs.txt

# 删除中间文件
debug_log "Cleaning up temporary files..."
rm -f modern.poplist extract.poplist extract.par extract.snp extract.ind extract.geno plot.txt pcaRploter.v4.4.py smartpca.eval smartpca.evec smartpca.log smartpca.r smartpca.par

debug_log "Analysis completed successfully"
