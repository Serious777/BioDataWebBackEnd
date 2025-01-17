# 读取数据
read_f3_data <- function(file_path) {
    # 直接读取文件并手动解析
    lines <- readLines(file_path)
    # 过滤包含"result:"的行
    result_lines <- lines[grep("^\\s*result:", lines)]
    
    if(length(result_lines) == 0) {
        stop("No result lines found in the input file")
    }
    
    # 创建空的数据框
    data <- data.frame(
        Source1 = character(),
        Source2 = character(),
        Target = character(),
        f3 = numeric(),
        StdErr = numeric(),
        Z = numeric(),
        SNPs = numeric(),
        stringsAsFactors = FALSE
    )
    
    # 解析每一行
    for(line in result_lines) {
        # 分割字段
        fields <- strsplit(trimws(line), "\\s+")[[1]]
        # 跳过"result:"
        fields <- fields[fields != "result:"]
        
        if(length(fields) >= 7) {
            data <- rbind(data, data.frame(
                Source1 = fields[1],
                Source2 = fields[2],
                Target = fields[3],
                f3 = as.numeric(fields[4]),
                StdErr = as.numeric(fields[5]),
                Z = as.numeric(fields[6]),
                SNPs = as.numeric(fields[7]),
                stringsAsFactors = FALSE
            ))
        }
    }
    
    # 数据检查
    if(nrow(data) == 0) {
        cat("File contents:\n")
        cat(paste(readLines(file_path), collapse="\n"))
        stop("No valid data could be parsed from the file")
    }
    
    # 打印数据检查信息
    cat("Data summary:\n")
    cat("Number of rows:", nrow(data), "\n")
    cat("Unique targets:", paste(unique(data$Target), collapse=", "), "\n")
    
    return(data)
}

# 绘制单个Target的F3统计图
plot_single_f3_stats <- function(target_data, target) {
    # 按f3值排序
    target_data <- target_data[order(target_data$f3),]
    
    if(nrow(target_data) == 0) {
        warning(paste("No data for target:", target))
        return(FALSE)
    }
    
    # 计算x轴范围
    x_range <- range(c(target_data$f3 - target_data$StdErr,
                      target_data$f3 + target_data$StdErr))
    x_margin <- diff(x_range) * 0.1
    xlim <- c(x_range[1] - x_margin, x_range[2] + x_margin)
    
    # 创建空白图
    plot(NA, NA,
         xlim=xlim,
         ylim=c(0.5, nrow(target_data) + 0.5),
         xlab="f3-statistic",
         ylab="",
         main=target,
         yaxt="n")  # 不绘制y轴刻度
    
    # 添加网格线
    abline(v=0, col="gray", lty=2)  # 垂直于0的虚线
    grid(nx=NULL, ny=NA, col="lightgray", lty="dotted")
    
    # 绘制误差线
    arrows(target_data$f3 - target_data$StdErr, 1:nrow(target_data),
           target_data$f3 + target_data$StdErr, 1:nrow(target_data),
           code=3, angle=90, length=0.05, col="darkgray")
    
    # 绘制点
    points(target_data$f3, 1:nrow(target_data),
           pch=21,           # 圆形带填充
           bg="black",       # 填充色改为黑色
           col="black",      # 边框色
           cex=1.5)         # 点的大小
    
    # 添加y轴标签
    axis(2, at=1:nrow(target_data),
         labels=paste(target_data$Source1, target_data$Source2, sep=" - "),
         las=2,             # 水平显示标签
         cex.axis=0.8)      # 标签字体大小
    
    # 添加边框
    box()
    
    return(TRUE)
}

# 主程序
main <- function() {
    tryCatch({
        # 检查文件是否存在
        if(!file.exists("./summ.result")) {
            stop("Input file './summ.result' not found")
        }
        
        # 读取数据
        data <- read_f3_data("./summ.result")
        
        # 获取唯一的Target值
        targets <- unique(data$Target)
        targets <- targets[!is.na(targets) & targets != ""]  # 移除NA和空值
        
        # 检查数据有效性
        if(length(targets) == 0) {
            print("Data content:")
            print(head(data))
            stop("No target populations found in data")
        }
        
        # 为每个target创建单独的PDF
        for(target in targets) {
            # 筛选当前Target的数据
            target_data <- data[data$Target == target,]
            
            # 创建PDF文件
            pdf_file <- paste0("f3_statistics_", target, ".pdf")
            pdf(pdf_file, width=10, height=8)
            
            # 设置绘图参数
            par(mar=c(5, 10, 4, 2))  # 调整边距，给y轴标签留出空间
            
            # 绘制图形
            if(plot_single_f3_stats(target_data, target)) {
                cat("Created plot for target:", target, "\n")
            } else {
                cat("Skipped plot for target:", target, "(no data)\n")
            }
            
            # 关闭PDF设备
            dev.off()
        }
        
    }, error=function(e) {
        message("Error: ", e$message)
        if(dev.cur() > 1) dev.off()  # 确保PDF设备被关闭
    })
}

# 运行主程序
main()
