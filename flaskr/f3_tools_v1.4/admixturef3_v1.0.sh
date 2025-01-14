#!/bin/bash

# coding:utf-8
# @Time : 2022/3/29 01:50
# @Author : cewinhot 
# @Version: 1.0
# @File : admixturef3.v1.sh


work_dir=/home/KongyangZhu/dulan/25.admixturef3/test1
geno_dir=/home/KongyangZhu/dulan/25.admixturef3/test1
f3_sh=/home/KongyangZhu/sh/admixturef3/1.0
geno_file=HO  # prefix
p1s=$(cat p1s)
p2s=$(cat p2s)
target=$(cat target)
thread=20


cd ${work_dir}
# extract
poplist="${p1s} ${p2s} ${target}" ; rm extract.poplist
for i in ${poplist};do echo ${i} ; done | sort -u > extract.poplist
echo "genotypename: ${geno_dir}/${geno_file}.geno"  > extract.par
echo "snpname: ${geno_dir}/${geno_file}.snp"       >> extract.par
echo "indivname: ${geno_dir}/${geno_file}.ind"     >> extract.par
echo "outputformat: PACKEDANCESTRYMAP"             >> extract.par
echo "genotypeoutname: extract.geno"               >> extract.par
echo "snpoutname: extract.snp"                     >> extract.par
echo "indivoutname: extract.ind"                   >> extract.par
echo "poplistname: extract.poplist"                >> extract.par
convertf -p extract.par

# qp3pop
parallel echo {1} {2} {3} ::: ${p1s} ::: ${p2s} ::: ${target} > qp3pop

# qp3.par
echo "genotypename:   extract.geno"   > qp3.par
echo "snpname:        extract.snp"   >> qp3.par
echo "indivname:      extract.ind"   >> qp3.par
echo "popfilename:    qp3pop"        >> qp3.par
echo "inbreed:        YES"           >> qp3.par

# multi_admixture-f3
a=$(wc -l qp3pop | cut -d ' ' -f 1)
b=$(expr ${a} / ${thread} )
line=$(expr ${b} + 1 )
split -l ${line} qp3pop spop
li=$(ls spop*)
for i in ${li};do cat qp3.par | sed "s/qp3pop/${i}/g" > ${i}.par ; done
parallel --verbose qp3Pop -p {1}.par ">" {1}.result ::: ${li}
cat *result > result.txt
cat result.txt | grep result: | sort -nk 7 > summ.result
mkdir p1 p2 tar
for i in ${p1s};do cat summ.result | awk -v tmp=${i} '{if($2==tmp)print $0}' > ./p1/${i}.result ; done
for i in ${p2s};do cat summ.result | awk -v tmp=${i} '{if($3==tmp)print $0}' > ./p2/${i}.result ; done
for i in ${target};do cat summ.result | awk -v tmp=${i} '{if($4==tmp)print $0}' > ./tar/${i}.result ; done
zipname=$(basename $(pwd)) ; rm spop*
cp ${f3_sh}/merge_f3_result.v1.0.py ./
cd p1 ; python merge_f3_result.v1.0.py ; mv result.xlsx p1.xlsx  ; cd ../
cd p2 ; python merge_f3_result.v1.0.py ; mv result.xlsx p2.xlsx  ; cd ../
cd tar; python merge_f3_result.v1.0.py ; mv result.xlsx tar.xlsx ; cd ../
zip -r ${zipname}.zip result.txt summ.result p1 p2 tar merge_f3_result.v1.0.py p1s p2s target

