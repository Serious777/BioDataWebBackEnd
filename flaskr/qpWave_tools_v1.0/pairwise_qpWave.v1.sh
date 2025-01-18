#!/bin/bash

# coding:utf-8
# @Time : 2022/1/15 17:21
# @Author : cewinhot 
# @Version：v1
# @File : pairwise_qpWave.v1.sh


work_dir=/home/KongyangZhu/dulan/17.pairwise_qpWave/test
geno_dir=/home/KongyangZhu/dulan/1240k
geno_file=1240k  # prefix
poplist=qpWave.poplist
outgroup=outgroup.poplist  # Mbuti.DG in first line
pairwise_dir=/home/KongyangZhu/sh/pairwise_qpWave
thread=40

# unique
cd ${work_dir}; mkdir -p result; cp ${outgroup} ./result/outgroup
cat ${poplist} | sort -u | grep -v "^$" > tmp ; cat tmp > ${poplist}
echo "Mbuti.DG" > tmp
cat ${outgroup} | sort -u | grep -v "^$" | grep -v "Mbuti.DG" >> tmp ; cat tmp > ${outgroup}
cat ${poplist} ${outgroup} > extract.poplist ; rm tmp

# extract population
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
convertf -p extract.par

# pairwise qpWave
cp ${pairwise_dir}/gen_scripts.py ./
cp ${pairwise_dir}/pairwise_qpWave.v1.r ./
cp ${pairwise_dir}/parqpWave.template ./result
python gen_scripts.py ${poplist} > run_script.txt
cat run_script.txt | parallel --verbose -j ${thread}

# post-processing
alias rmsp='sed "s/^\s*//g" | sed "s/[[:blank:]]\+/\t/g"'
cd result ; li=$(ls *result) ; rm -f final_result.txt ; touch final_result.txt
for i in ${li};do
    echo ${i} | sed 's/.result//g' | sed 's/-/\t/g' >> final_result.txt
    cat ${i} | grep "f4rank: 1 dof:" | rmsp | cut -f 14 >> final_result.txt  # taildiff
    echo "" >> final_result.txt
done
mv final_result.txt ../ ; cd ../
zip pairwise_qpWave.zip qpWave.poplist outgroup.poplist extract.poplist final_result.txt pairwise_qpWave.v1.r gen_scripts.py run_script.txt pairwise_qpWave.v1.sh