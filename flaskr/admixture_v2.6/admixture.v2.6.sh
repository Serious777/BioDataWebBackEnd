#!/bin/sh

# coding:utf-8
# @Time : 2022/9/28 16:30
# @Version: 2.6
# @File : admixture.2.6.sh
# @Author : zky

# 接收工作目录作为参数
workdir=$1
if [ -z "$workdir" ]; then
    echo "Error: Work directory not provided"
    exit 1
fi

# 设置文件路径
geno_dir=${workdir}
geno_file=example  # prefix

# 设置脚本路径（使用绝对路径）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
fancy=${SCRIPT_DIR}
remove_excess_py=${SCRIPT_DIR}/remove_excess.py

# 其他参数设置

K_st=2
K_en=6
thread=$((K_en - K_st + 1))  # 使用 $((...)) 进行算术运算
# bootstrap="-B100"  # 不需要bootstrap放空""
bootstrap=""  # 不需要bootstrap放空""
cd ${workdir}

# 验证必需文件
if [ ! -f ${geno_dir}/${geno_file}.geno ] || [ ! -f ${geno_dir}/${geno_file}.ind ] || [ ! -f ${geno_dir}/${geno_file}.snp ] || [ ! -f ${geno_dir}/poplist.txt ]; then
    echo "Error: Missing required files"
    echo "Checking files:"
    echo "Geno file: ${geno_dir}/${geno_file}.geno"
    echo "Ind file: ${geno_dir}/${geno_file}.ind"
    echo "Snp file: ${geno_dir}/${geno_file}.snp"
    echo "Population list: ${geno_dir}/poplist.txt"
    exit 1
fi

# 1. extract poplist
cat poplist.txt | grep -v "=" > extract.poplist
for i in "extract.par";do
    echo "genotypename: ${geno_dir}/${geno_file}.geno"
    echo "snpname: ${geno_dir}/${geno_file}.snp"
    echo "indivname: ${geno_dir}/${geno_file}.ind"
    echo "outputformat: PACKEDANCESTRYMAP"
    echo "genotypeoutname: tmp.geno"
    echo "snpoutname: tmp.snp"
    echo "indivoutname: tmp.ind"
    echo "poplistname: extract.poplist"
done > extract.par ; convertf -p extract.par ; echo ""

# 2. remove individual larger than MAX
MAX=15
while read a;do grep -w ${a} tmp.ind | wc -l | awk -v pop=${a} -v max=${MAX} '{if($1 > max)print pop" "$1-max}'; done < extract.poplist > remove.counts
python ${remove_excess_py} > tmp.edit.ind
for i in "extract.par";do
    echo "genotypename: tmp.geno"
    echo "snpname: tmp.snp"
    echo "indivname: tmp.edit.ind"
    echo "outputformat: PACKEDANCESTRYMAP"
    echo "genotypeoutname: extract.geno"
    echo "snpoutname: extract.snp"
    echo "indivoutname: extract.ind"
    echo "poplistname: extract.poplist"
done > extract.par ; convertf -p extract.par ; echo "" ; rm tmp.*

# 3. convert to bed,bim,fam
for i in "eig2bed.par";do
    echo "genotypename: extract.geno"
    echo "snpname: extract.snp"
    echo "indivname: extract.ind"
    echo "outputformat: PACKEDPED"
    echo "genotypeoutname: extract.bed"
    echo "snpoutname: extract.bim"
    echo "indivoutname: extract.fam"
done > eig2bed.par ; convertf -p eig2bed.par ; echo ""

# 4. generate bed,bim,fam
plink --bfile extract --indep-pairwise 200 25 0.4 --out plink --allow-no-sex
plink --bfile extract --extract plink.prune.in  --make-bed --out prune  --allow-no-sex
cat extract.ind | awk '{print $3,$1,$2}' > prune.fam

# 5. Admixture
bed_file=prune.bed
parallel -j ${thread} --verbose admixture -s time ${bootstrap} -j2 --cv ${bed_file} {} "2>> error.txt | tee -a result.out" ::: $(seq ${K_st} ${K_en})
# 检查 ADMIXTURE 是否成功完成
if [ ! -f prune.${K_st}.Q ]; then
    echo "Error: ADMIXTURE analysis failed"
    cat error.txt
    exit 1
fi

# 等待所有 Q 文件生成
for k in $(seq ${K_st} ${K_en}); do
    while [ ! -f prune.${k}.Q ]; do
        sleep 1
    done
done
# grep result
cat result.out | grep "CV error" | sort -k 4 -n > CV_error.txt
min=$(cat CV_error.txt  | sort -k 4 -n | head -n 1 | awk '{print $3}' | egrep -o '[0-9]{1,2}')

# 首先复制所有必需的R脚本到工作目录
cp ${fancy}/fancyADMIXTURE.r ${fancy}/makePalette.r ${fancy}/averagePopsUnsorted.r ${fancy}/averagePops.r ./

# 然后创建并修改R脚本
#cat > full.R << EOF
#source('fancyADMIXTURE.r')
#fancyADMIXTURE('prune',KMIN=2,KMAX=${K_en},HCLUST=T,PNG=F,OUTFILEPREFIX='full')
#q()
#EOF

for i in $(seq ${K_st} ${K_en}); do
    cat > ${i}.R << EOF
source('fancyADMIXTURE.r')
fancyADMIXTURE('prune',KMIN=${i},KMAX=${i},HCLUST=T,PNG=F,OUTFILEPREFIX='${i}')
q()
EOF
    Rscript ${i}.R
done

# 检查R脚本执行结果
if [ $? -ne 0 ]; then
    echo "Error: R scripts execution failed"
    ls -l  # 列出当前目录文件，帮助调试
    exit 1
fi

# 打包结果文件
zip -r admixture.zip \
    *.pdf \
    *.Q \
    CV_error.txt \
    result.out \
    poplist.txt \
    prune.fam \
    2>/dev/null || true

# 检查压缩文件
if [ ! -f admixture.zip ] || [ ! -s admixture.zip ]; then
    echo "Error: Failed to create admixture.zip or file is empty"
    ls -l  # 列出当前目录文件，帮助调试
    exit 1
fi

# 清理中间文件前列出所有文件（用于调试）
echo "Files before cleanup:"
ls -l

# 清理中间文件
#rm -f extract.* tmp.* plink.* *.R full.* [0-9].* result.out \
#    fancyADMIXTURE.r makePalette.r averagePopsUnsorted.r averagePops.r
