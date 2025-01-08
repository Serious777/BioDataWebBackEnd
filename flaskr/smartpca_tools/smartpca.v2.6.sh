#!/bin/bash
# coding:utf-8
# @Time : 2022/10/08 01:09
# @Version: v2.6
# @File : smartpca.2.5.sh
# @Author : zky

geno_dir=/root/data-upload/smartpca
geno_file=example  # prefix
workdir=/root/data-upload/smartpca
poplist=/root/data-upload/smartpca/pop-list.txt
pcaRploter=/root/my-project/web-database-backend/backend/flaskr/smartpca_tools/pcaRploter.v4.4.py
bc=/root/my-project/web-database-backend/backend/flaskr/smartpca_tools/bc.py

# alias rmsp='sed "s/^\s*//g" | sed "s/[[:blank:]]\+/\t/g"'
rmsp() {
    sed "s/^\s*//g" | sed "s/[[:blank:]]\+/\t/g"
}

cd ${workdir}

if [ ! -f ${geno_dir}/${geno_file}.geno ] || [ ! -f ${pcaRploter} ] || [ ! -f ${poplist} ];then echo "!!! Missing files !!! " ; exit ; fi

# check extract.poplist
echo -e "=== checking popluations ! ==="
lack_pops=""
cat ${poplist} | grep -v "=" > extract.poplist
cat ${geno_dir}/${geno_file}.ind | awk '{print $3}' | sort -u > ind.tmp
# 清理文件中的 Windows 换行符
tr -d '\r' < extract.poplist > extract.poplist.clean
tr -d '\r' < ind.tmp > ind.tmp.clean
mv -f extract.poplist.clean extract.poplist
mv -f ind.tmp.clean ind.tmp


pops=$(cat extract.poplist)
for pop in ${pops};do
    cat ind.tmp | grep -x ${pop} >/dev/null 2>&1
    if [ ! $? -eq 0 ];then lack_pops="${lack_pops} [${pop}]" ; flag="FALSE"; fi
done && echo -e "=== check poplist done ! ===\n\n" ;  rm -f ind.tmp
if [[ ${flag} == "FALSE" ]];then echo ${lack_pops} not in dataset; exit; fi

# extract poplist from HO
echo "=== running convertf ! ==="
echo "DEBUG: convertf input paramter file is extract.par" # 添加调试信息
echo "DEBUG: convertf ran successfully"
for i in "extract.par";do
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
done > extract.par && convertf -p extract.par
# smartpca preprocessing
row=$(cat ${poplist} -n | grep "====Ancient" | head -n 1 | rmsp | cut -f 1)
row=$[ ${row} - 1 ]
cat ${poplist} | head -n ${row} | grep -v "=" > modern.poplist

# smartpca.par
for i in "smartpca.par";do
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
smartpca -p smartpca.par > smartpca.log 2>&1

# Calculate PCs
lines=$(wc -l smartpca.eval | rmsp | cut -f 1)
lines=$(expr ${lines} - 1 )
pc1=$(head -n 1 smartpca.eval)
pc2=$(tail -n+2 smartpca.eval | head -n 1)
echo -n "PC1: " >  PCs.txt ; echo "${pc1}/${lines}*100" | xargs -n 1 python ${bc} >> PCs.txt ; echo "%" >> PCs.txt
echo -n "PC2: " >> PCs.txt ; echo "${pc2}/${lines}*100" | xargs -n 1 python ${bc} >> PCs.txt ; echo "%" >> PCs.txt

# Post-Processing
tail -n+2 smartpca.evec | awk '{print $7,$1,$2,$3}' > plot.txt
cp ${pcaRploter} ./
python pcaRploter.v4.4.py
Rscript smartpca.r
zip smartpca.zip extract.poplist modern.poplist plot.txt pop-list.txt smartpca.eval smartpca.evec smartpca.pdf legend.pdf  smartpca.log PCs.txt

# 删除中间文件
rm -f modern.poplist extract.poplist extract.par extract.snp extract.ind extract.geno plot.txt pcaRploter.v4.4.py smartpca.eval smartpca.evec smartpca.log smartpca.r smartpca.par
