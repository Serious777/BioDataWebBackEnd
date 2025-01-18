#!/usr/bin/env python3
import sys
import os
import re

def parse_result_line(line):
    """解析结果行，返回组合的结果数据"""
    # 提取目标群体和源群体
    pops = line.split('best coefficients:')[0].strip().split()
    target = pops[0]
    sources = pops[1:]
    
    # 提取系数
    coeffs = re.findall(r'best coefficients:\s*([-\d\.\s]+)', line)
    if coeffs:
        coeffs = [float(x) for x in coeffs[0].strip().split()]
    else:
        return None
        
    # 提取标准误差
    stds = re.findall(r'std\. errors:\s*([-\d\.\s]+)', line)
    if stds:
        stds = [float(x) for x in stds[0].strip().split()]
    else:
        return None
        
    # 提取tail值
    tail = re.findall(r'tail:\s*([-\d\.]+)', line)
    if not tail:
        return None
    tail = float(tail[0])
    
    return {
        'target': target,
        'sources': sources,
        'coeffs': coeffs,
        'stds': stds,
        'tail': tail
    }

def process_result_line(result):
    """处理单个结果行"""
    output_lines = []
    
    # 只处理所有系数为正数的组合
    if not all(c >= 0 for c in result['coeffs']):
        print(f"跳过 {result['target']}: 包含负系数 {result['coeffs']}")
        return []
        
    # 计算系数总和并标准化
    total = sum(result['coeffs'])
    if total <= 0:
        print(f"跳过 {result['target']}: 系数总和不为正 {total}")
        return []
        
    # 标准化系数确保总和为1
    norm_coeffs = [c/total for c in result['coeffs']]
    print(f"处理 {result['target']} 与 {result['sources']}")
    print(f"原始系数: {result['coeffs']}, 标准化后: {norm_coeffs}")
    
    # 生成输出行
    for i, (source, coeff, std) in enumerate(zip(result['sources'], 
                                               norm_coeffs, 
                                               result['stds'])):
        # 第一个source带p值，其他不带
        tail_str = f"P={result['tail']:.3f}" if i == 0 else ""
        
        # 计算累计比例
        sum_per = sum(norm_coeffs[:i+1])
        
        # 使用固定的标准误差0.02
        output_lines.append(f"{result['target']}\t{tail_str}\t{source}\t{coeff:.3f}\t0.02\t{sum_per:.3f}")
            
    return output_lines

def main():
    # 检查4.all_result.txt是否存在
    if not os.path.exists("4.all_result.txt"):
        print("错误: 未找到结果文件 4.all_result.txt")
        sys.exit(1)
        
    with open('r_input.txt', 'wt', encoding='utf-8') as out:
        # 写入表头
        out.write("target\ttail\tsource\tpercent\tstd\tsum_per\n")
        
        # 读取并处理每一行
        with open("4.all_result.txt", 'rt', encoding='utf-8') as f:
            for line in f:
                result = parse_result_line(line)
                if result:
                    # 使用新的处理函数
                    output_lines = process_result_line(result)
                    for line in output_lines:
                        out.write(line + "\n")

if __name__ == "__main__":
    main()
