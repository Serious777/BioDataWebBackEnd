#!/bin/bash

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

# 检查输入文件
for file in p1s.txt p2s.txt p3s.txt p4s.txt; do
    if [ ! -f "$file" ]; then
        echo "Error: $file not found"
        exit 1
    fi
done

# 转换文本文件行尾为LF
echo "Converting text files to Unix format (LF)..."
for txt_file in p1s.txt p2s.txt p3s.txt p4s.txt; do
    if [ -f "$txt_file" ]; then
        tr -d '\r' < "$txt_file" > "${txt_file}.tmp"
        mv "${txt_file}.tmp" "$txt_file"
        sed -i -e '$a\' "$txt_file"
        echo "Converted $txt_file to LF format"
    fi
done

# 读取群体列表
p1s=$(cat p1s.txt)
p2s=$(cat p2s.txt)
p3s=$(cat p3s.txt)
p4s=$(cat p4s.txt)

# 检查群体列表是否为空
if [ -z "$p1s" ] || [ -z "$p2s" ] || [ -z "$p3s" ] || [ -z "$p4s" ]; then
    echo "Error: One or more population lists are empty"
    exit 1
fi

# 生成f4组合
parallel echo "{1} {2} {3} {4}" ::: ${p1s} ::: ${p2s} ::: ${p3s} ::: ${p4s} > 0.pop

# 检查0.pop是否生成成功
if [ ! -s 0.pop ]; then
    echo "Error: Failed to generate 0.pop or file is empty"
    echo "Contents of input files:"
    echo "p1s.txt:"
    cat p1s.txt
    echo "p2s.txt:"
    cat p2s.txt
    echo "p3s.txt:"
    cat p3s.txt
    echo "p4s.txt:"
    cat p4s.txt
    exit 1
fi

# 准备参数文件
echo "genotypename: ${geno_dir}/${geno_file}.geno" > 0.pars
echo "snpname: ${geno_dir}/${geno_file}.snp" >> 0.pars
echo "indivname: ${geno_dir}/${geno_file}.ind" >> 0.pars
echo "popfilename: replacepop" >> 0.pars
echo "f4mode: YES" >> 0.pars
echo "printsd: YES" >> 0.pars
echo "inbreed: YES" >> 0.pars

# 检查参数文件
if [ ! -s 0.pars ]; then
    echo "Error: Failed to create or modify 0.pars"
    echo "Content of 0.pars:"
    cat 0.pars
    exit 1
fi

# 检查输入文件是否存在
for ext in geno snp ind; do
    if [ ! -f "${geno_dir}/${geno_file}.${ext}" ]; then
        echo "Error: ${geno_file}.${ext} not found in ${geno_dir}"
        echo "Directory contents:"
        ls -l ${geno_dir}
        exit 1
    fi
done

# 保存当前工作目录
WORK_DIR=$(pwd)

# 分割任务
a=$(wc -l 0.pop | cut -d ' ' -f 1)
b=$(expr ${a} / ${thread})
line=$(expr ${b} + 1)
split -l ${line} 0.pop spop

# 检查分割后的文件
if ! ls spop* >/dev/null 2>&1; then
    echo "Error: Failed to split 0.pop"
    echo "Content of 0.pop:"
    cat 0.pop
    exit 1
fi

# 运行qpDstat
li=$(ls spop*)
for i in ${li}; do
    # 创建每个任务的参数文件
    echo "genotypename: ${geno_dir}/${geno_file}.geno" > ${i}.par
    echo "snpname: ${geno_dir}/${geno_file}.snp" >> ${i}.par
    echo "indivname: ${geno_dir}/${geno_file}.ind" >> ${i}.par
    echo "popfilename: ${i}" >> ${i}.par
    echo "f4mode: YES" >> ${i}.par
    echo "printsd: YES" >> ${i}.par
    echo "inbreed: YES" >> ${i}.par
done

echo "Starting qpDstat analysis..."
# 显示参数文件内容
echo "Parameter file content:"
cat spopaa.par

parallel --verbose qpDstat -p {1}.par ">" {1}.result ::: ${li}

# 合并结果
echo "Merging results..."
cat spop*.result > result.txt 2>/dev/null || true
if [ ! -s result.txt ]; then
    echo "Error: Failed to generate results"
    echo "Checking individual result files:"
    for f in spop*.result; do
        echo "=== $f ==="
        cat "$f"
    done
    ls -l
    exit 1
fi

cat result.txt | grep result: | sort -nk 8 > summ.txt

# 检查summ.txt
if [ ! -s summ.txt ]; then
    echo "Error: summ.txt is empty"
    echo "Content of result.txt:"
    cat result.txt
    exit 1
fi

# 后处理
mkdir -p p2 p3 p4
for i in ${p2s}; do 
    cat summ.txt | awk -v tmp=${i} '{if($3==tmp)print $0}' > ./p2/${i}.result
done
for i in ${p3s}; do 
    cat summ.txt | awk -v tmp=${i} '{if($4==tmp)print $0}' > ./p3/${i}.result
done
for i in ${p4s}; do 
    cat summ.txt | awk -v tmp=${i} '{if($5==tmp)print $0}' > ./p4/${i}.result
done

# 复制并运行处理脚本
echo "Copying processing scripts..."
cp ${SCRIPT_DIR}/{4.merge_f4_result.v2.py,8.adjust_excel.py,plot.r} ./

# 检查脚本是否复制成功
for script in 4.merge_f4_result.v2.py 8.adjust_excel.py plot.r; do
    if [ ! -f "$script" ]; then
        echo "Error: Failed to copy $script"
        exit 1
    fi
done

echo "Processing results..."
# 确保在正确的目录中执行
cd "${WORK_DIR}"

# 处理p2目录
cd p2 || exit 1
echo "Running merge_f4_result.v2.py in p2..."
python ../4.merge_f4_result.v2.py
if [ $? -ne 0 ]; then
    echo "Error running merge_f4_result.v2.py in p2"
    echo "Directory contents:"
    ls -l
    exit 1
fi

echo "Running adjust_excel.py in p2..."
python ../8.adjust_excel.py --head
if [ $? -ne 0 ]; then
    echo "Error running adjust_excel.py in p2"
    echo "Directory contents:"
    ls -l
    exit 1
fi

mv result.xlsx p2.xlsx || exit 1
cp ../plot.r ./ || exit 1
echo "Running R script in p2..."
# 检查plot.txt是否存在
if [ ! -f plot.txt ]; then
    echo "Error: plot.txt not found in p2"
    echo "Directory contents:"
    ls -l
    exit 1
fi
# 显示plot.txt的内容
echo "Content of plot.txt in p2:"
head -n 5 plot.txt
# 执行R脚本并捕获输出
echo "Running Rscript..."
Rscript plot.r 2>&1
RSCRIPT_EXIT=$?
if [ $RSCRIPT_EXIT -ne 0 ]; then
    echo "Error: Rscript failed with exit code $RSCRIPT_EXIT"
    echo "Directory contents:"
    ls -l
    exit 1
fi
[ -f plot.pdf ] && mv plot.pdf p2.pdf || echo "Warning: plot.pdf not generated in p2"
cd ..

# 处理p3目录
cd p3 || exit 1
python ../4.merge_f4_result.v2.py || exit 1
python ../8.adjust_excel.py --head || exit 1
mv result.xlsx p3.xlsx || exit 1
cp ../plot.r ./ || exit 1
echo "Running R script in p3..."
# 检查plot.txt是否存在
if [ ! -f plot.txt ]; then
    echo "Error: plot.txt not found in p3"
    ls -l
    exit 1
fi
# 显示plot.txt的内容
echo "Content of plot.txt in p3:"
head -n 5 plot.txt
Rscript plot.r || exit 1
[ -f plot.pdf ] && mv plot.pdf p3.pdf || echo "Warning: plot.pdf not generated in p3"
cd ..

# 处理p4目录
cd p4 || exit 1
python ../4.merge_f4_result.v2.py || exit 1
python ../8.adjust_excel.py --head || exit 1
mv result.xlsx p4.xlsx || exit 1
cp ../plot.r ./ || exit 1
echo "Running R script in p4..."
# 检查plot.txt是否存在
if [ ! -f plot.txt ]; then
    echo "Error: plot.txt not found in p4"
    ls -l
    exit 1
fi
# 显示plot.txt的内容
echo "Content of plot.txt in p4:"
head -n 5 plot.txt
Rscript plot.r || exit 1
[ -f plot.pdf ] && mv plot.pdf p4.pdf || echo "Warning: plot.pdf not generated in p4"
cd ..

# 返回工作目录
cd "${WORK_DIR}"

# 打包结果
echo "Creating zip archive..."
# 检查所需文件是否存在
for file in 0.pars 0.pop result.txt summ.txt p1s.txt p2s.txt p3s.txt p4s.txt; do
    if [ ! -f "$file" ]; then
        echo "Warning: $file not found"
    fi
done

for dir in p2 p3 p4; do
    if [ ! -d "$dir" ]; then
        echo "Warning: Directory $dir not found"
    fi
done

# 使用find命令创建文件列表
echo "Creating file list for zip..."
find . -type f \( -name "*.txt" -o -name "*.xlsx" -o -name "*.pdf" -o -name "*.result" \) > files_to_zip.txt

# 打包所有找到的文件
zip -r f4.zip . -i@files_to_zip.txt 2>&1 || echo "Zip command failed with status $?"

# 检查结果文件是否生成
if [ ! -f f4.zip ]; then
    echo "Error: Failed to create f4.zip"
    echo "Directory contents:"
    ls -l
    exit 1
fi

if [ ! -s f4.zip ]; then
    echo "Error: f4.zip is empty"
    exit 1
fi

# 清理中间文件
rm -f spop* *.par 