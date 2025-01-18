#!/bin/bash

# 检查result目录是否存在且不为空
if [ ! -d "result" ] || [ -z "$(ls -A result)" ]; then
    echo "错误: result目录不存在或为空"
    exit 1
fi

# 提取所有结果文件中的关键信息
echo "处理结果文件..."
for i in $(ls ./result/*.result); do
    if [ -s "$i" ]; then  # 检查文件是否存在且不为空
        echo "处理文件: $i"
        echo "${i} " | sed 's/.\/result\///g' | sed 's/.result//g' | sed 's/-/ /g' | awk '{printf "%s %s %s %s ",$1,$2,$3,$4}'
        cat ${i} | grep "best coefficient" | awk '{printf "%s %s %s %s %s ",$1,$2,$3,$4,$5}'
        cat ${i} | grep "std. errors" | awk '{printf "%s %s %s %s %s ",$1,$2,$3,$4,$5}'
        cat ${i} | grep "summ:" | awk '{printf "%s %s ","tail:",$4}'; cat ${i} | grep "Jackknife" | awk '{printf "%s %s %s %s %s \n",$1,$2,$3,$4,$5}'
    fi
done > 4.all_result.txt

# 检查是否成功生成结果
if [ ! -s "4.all_result.txt" ]; then
    echo "错误: 未能生成有效的结果文件"
    exit 1
fi

echo "结果已保存到 4.all_result.txt"