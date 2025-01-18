#!/usr/bin/env python3
"""
qpAdm Local Analysis Pipeline
主脚本用于整合本地qpAdm分析流程

输入:
- source.txt: 源群体列表，可以包含"# Rotate"标记
- target.txt: 目标群体列表  
- outgroup.txt: 外群列表

当source.txt包含"# Rotate"标记时:
- 未被选为source的群体会被加入outgroup
- 实现source群体的轮换分析

输出:
- parfile/: 参数文件目录
- result/: 结果文件目录
- qpadm_result.xlsx: 结果Excel文件
- qpadm_plot.pdf: 可视化结果
"""

import os
import sys
from pathlib import Path
import argparse
from utils import *

def read_file(filename):
    """读取文件，忽略注释和空行"""
    with open(filename) as f:
        return [x.strip() for x in f if x.strip() and not x.startswith('#')]

def read_sources():
    """读取source文件,检查是否有Rotate标记"""
    rotate = False
    sources = []
    
    with open("source.txt") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                if "rotate" in line.lower():
                    rotate = True
                continue
            sources.append(line)
    
    return sources, rotate

def prepare_files(geno_dir, max_way):
    """准备qpAdm运行所需文件"""
    # 创建目录
    os.makedirs("parfile", exist_ok=True) 
    os.makedirs("result", exist_ok=True)

    # 查找eigenstat文件
    geno_file, snp_file, ind_file = find_eigenstat_files(geno_dir)

    # 读取输入文件
    sources, rotate = read_sources()
    targets = read_file("target.txt")
    outgroups = read_file("outgroup.txt")

    print(f"Sources: {sources}")
    print(f"Targets: {targets}")
    print(f"Outgroups: {outgroups}")

    # 生成参数文件
    par_template = f'''genotypename: {geno_file}
snpname: {snp_file}
indivname: {ind_file}
popleft: {{0}}/left.pops
popright: {{0}}/right.pops
details: YES
allsnps: YES
inbreed: YES
'''
    
    # 生成不同的source组合
    source_combs = []
    for i in range(1, max_way + 1):  # 1-way到max-way
        if i == 1:
            source_combs.extend([[s] for s in sources])
        elif i == 2:
            source_combs.extend([[s1, s2] for j, s1 in enumerate(sources) 
                               for s2 in sources[j+1:]])
        elif i == 3:
            source_combs.extend([[s1, s2, s3] for j, s1 in enumerate(sources)
                               for k, s2 in enumerate(sources[j+1:])
                               for s3 in sources[k+j+2:]])
    
    print(f"生成的组合数: {len(source_combs)}")
    print("示例组合:")
    for comb in source_combs[:3]:
        print(f"- {'-'.join(comb)}")
    
    # 为每个组合生成文件
    for target in targets:
        for src_comb in source_combs:
            # 确定outgroups
            if rotate and len(src_comb) > 1:
                unused_sources = [s for s in sources if s not in src_comb]
                curr_outgroups = outgroups + unused_sources
            else:
                curr_outgroups = outgroups
                
            pops = f"{target}-" + "-".join(src_comb)
            
            # 创建组合目录
            comb_dir = os.path.join("parfile", pops)
            os.makedirs(comb_dir, exist_ok=True)
            
            # 写outgroups文件
            with open(os.path.join(comb_dir, "right.pops"), "w") as f:
                f.write("\n".join(curr_outgroups) + "\n")
            
            # 写pops文件
            with open(os.path.join(comb_dir, "left.pops"), "w") as f:
                f.write(f"{target}\n" + "\n".join(src_comb) + "\n")
                
            # 写par文件
            with open(f"parfile/{pops}.par", "w") as f:
                par_content = par_template.format(
                    os.path.join("parfile", pops)  # 使用相对路径
                )
                f.write(par_content)

def find_eigenstat_files(geno_dir):
    """查找前缀为example的eigenstat文件"""
    geno_file = ""
    snp_file = ""
    ind_file = ""
    
    for f in os.listdir(geno_dir):
        if f.startswith("example"):
            if f.endswith(".geno"):
                geno_file = os.path.abspath(os.path.join(geno_dir, f))
            elif f.endswith(".snp"):
                snp_file = os.path.abspath(os.path.join(geno_dir, f))
            elif f.endswith(".ind"):
                ind_file = os.path.abspath(os.path.join(geno_dir, f))
                
    if not (geno_file and snp_file and ind_file):
        raise FileNotFoundError("未找到完整的eigenstat文件(example.geno/.snp/.ind)")
        
    return geno_file, snp_file, ind_file

def run_qpadm():
    """运行qpAdm分析"""
    success = False
    for par in sorted(os.listdir("parfile")):
        if par.endswith(".par"):
            name = par[:-4]
            cmd = f"qpAdm -p parfile/{par} > result/{name}.result"
            print(f"Running: {cmd}")
            # 打印par文件内容以便调试
            with open(f"parfile/{par}") as f:
                print("Par file content:")
                print(f.read())
            ret = os.system(cmd)
            if ret == 0:
                success = True
    return success

def check_populations(ind_file, all_pops):
    """检查所有群体是否存在于ind文件中"""
    existing_pops = set()
    with open(ind_file) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3:
                existing_pops.add(parts[2])
    
    missing_pops = []
    for pop in all_pops:
        if pop not in existing_pops:
            missing_pops.append(pop)
    
    return missing_pops

def process_results():
    """处理和筛选结果"""
    filtered_results = []
    with open("4.all_result.txt") as f:
        for line in f:
            result = parse_result_line(line)
            if result:
                # 筛选条件
                if (result['tail'] > 0.05 and  # p值要大于0.05
                    all(0 <= c <= 1 for c in result['coeffs']) and  # 比例在0-1之间
                    all(s < 0.5 for s in result['stds'])):  # 标准误差要小于0.5
                    filtered_results.append(result)
    return filtered_results

def main():
    parser = argparse.ArgumentParser(description="qpAdm Local Analysis Pipeline")
    parser.add_argument("--geno-dir", default="./", help="eigenstat文件所在目录")
    parser.add_argument("--max-way", type=int, default=3, choices=[1,2,3],
                      help="进行n-way分析的最大n值(默认:3)")
    args = parser.parse_args()
    
    try:
        print("=== qpAdm Analysis Pipeline Started ===")
        
        # 读取所有群体
        print("\n1. Reading population files...")
        sources, rotate = read_sources()
        targets = read_file("target.txt")
        outgroups = read_file("outgroup.txt")
        all_pops = sources + targets + outgroups
        
        print("读取到的群体:")
        print(f"Sources: {sources}")
        print(f"Targets: {targets}")
        print(f"Outgroups: {outgroups}")
        
        # 检查并调整max_way
        max_way = min(args.max_way, len(sources))
        if max_way < args.max_way:
            print(f"警告: 由于source群体数量({len(sources)})小于指定的max-way({args.max_way}),")
            print(f"实际将执行{max_way}-way分析")
        
        print("\n2. Checking input files...")
        # 查找eigenstat文件
        geno_file, snp_file, ind_file = find_eigenstat_files(args.geno_dir)
        
        # 检查群体是否存在
        missing_pops = check_populations(ind_file, all_pops)
        if missing_pops:
            print("错误: 以下群体在数据文件中不存在:")
            for pop in missing_pops:
                print(f"- {pop}")
            sys.exit(1)
        
        print("\n3. Preparing parameter files...")
        # 准备文件
        prepare_files(args.geno_dir, max_way)
        
        print("\n4. Running qpAdm analysis...")
        # 运行分析
        success = run_qpadm()
        
        if success:
            print("\n5. Processing results...")
            
            print("  - Extracting results...")
            # 提取结果
            ret = os.system("bash 3.grep_result.sh")
            if ret != 0:
                raise RuntimeError("结果提取失败")
                
            # 检查结果文件
            if not os.path.exists("4.all_result.txt") or os.path.getsize("4.all_result.txt") == 0:
                raise RuntimeError("未生成有效的结果文件")
                
            print("  - Generating Excel report...")
            # 生成Excel结果
            ret = os.system("python 5.result2excel.py")
            if ret != 0:
                raise RuntimeError("Excel生成失败")
                
            print("  - Preparing visualization data...")
            # 生成可视化
            ret = os.system("python 6.excel2r.py")
            if ret != 0:
                raise RuntimeError("R输入文件生成失败")
                
            print("  - Creating plots...")
            ret = os.system("Rscript 7.barplot.r")
            if ret != 0:
                raise RuntimeError("可视化生成失败")
                
            print("\n=== Analysis completed successfully! ===")
        else:
            raise RuntimeError("qpAdm分析失败，请检查输入文件和参数")
            
    except Exception as e:
        print(f"\n错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 