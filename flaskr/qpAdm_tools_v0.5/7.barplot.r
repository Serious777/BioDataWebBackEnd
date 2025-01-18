#!/usr/bin/env Rscript

# 检查并加载必要的包
required_packages <- c("ggplot2", "reshape2", "ggsci")
for(pkg in required_packages) {
    if(!require(pkg, character.only = TRUE, quietly = TRUE)) {
        cat(sprintf("Installing package: %s\n", pkg))
        install.packages(pkg, repos = "https://cloud.r-project.org")
        if(!require(pkg, character.only = TRUE, quietly = TRUE)) {
            stop(sprintf("Failed to install package: %s", pkg))
        }
    }
}

# 检查输入文件
if(!file.exists("r_input.txt")) {
    stop("Input file 'r_input.txt' not found")
}

# 读取数据并检查格式
tryCatch({
    df <- read.table("r_input.txt", header=TRUE, sep='\t')
    required_cols <- c("target", "source", "percent", "std", "sum_per", "tail")
    missing_cols <- setdiff(required_cols, names(df))
    if(length(missing_cols) > 0) {
        stop(sprintf("Missing required columns: %s", paste(missing_cols, collapse=", ")))
    }
}, error = function(e) {
    stop(sprintf("Error reading input file: %s", e$message))
})

# 确保数值列是数值类型
df$percent <- as.numeric(df$percent)
df$std <- as.numeric(df$std)
df$sum_per <- as.numeric(df$sum_per)

# 打印数据统计信息
cat("原始数据统计:\n")
print(summary(df))

# 数据筛选和清理
df <- df[!is.na(df$percent) & !is.na(df$std),]  # 移除NA值

# 按每个target分组，只保留tail值最大的组合
df <- do.call(rbind, lapply(split(df, df$target), function(x) {
    # 获取每个target的最大p值
    p_values <- as.numeric(sub("P=", "", x$tail[x$tail != ""]))
    if(length(p_values) > 0) {
        max_p <- max(p_values, na.rm=TRUE)
        # 保留p值最大的组合
        result <- x[x$tail == sprintf("P=%.3f", max_p) | x$tail == "",]
        # 检查系数总和
        total <- sum(result$percent)
        if(abs(total - 1) < 0.01) {  # 允许1%的误差
            return(result)
        }
    }
    return(NULL)
}))

# 打印筛选后的数据统计
cat("\n筛选后数据统计:\n")
print(summary(df))
cat(sprintf("剩余行数: %d\n", nrow(df)))

# 如果没有数据，退出
if(nrow(df) == 0) {
    stop("没有符合条件的数据可以绘图")
}

# 重新排序
df$source <- factor(df$source, levels=unique(df$source))
df <- df[order(df$target, df$tail, df$source),]

# 创建主题
theme_pub <- theme_bw() +
  theme(
    legend.position = "bottom",
    legend.box = "horizontal",
    legend.margin = margin(t = 10, b = 10),
    panel.grid = element_blank(),
    panel.border = element_rect(colour = "black", linewidth=0.5),
    axis.text = element_text(size=10, color="black"),
    axis.title = element_text(size=12, face="bold"),
    legend.title = element_blank(),
    legend.text = element_text(size=10),
    plot.title = element_text(hjust=0.5, size=14, face="bold"),
    plot.margin = unit(c(1,1,1,1), "cm")
  )

# 绘图
tryCatch({
    p <- ggplot(df, aes(x=target, y=percent, fill=source)) +
      geom_bar(position="stack", 
               stat="identity", 
               width=0.7, 
               color="black", 
               linewidth=0.3) +
      geom_segment(aes(x = as.numeric(target) + 0.35,
                       xend = as.numeric(target) + 0.35,
                       y = percent,
                       yend = percent + 0.05),
                   position=position_stack(),
                   linewidth=0.3,
                   color="black") +
      geom_segment(aes(x = as.numeric(target) + 0.3,
                       xend = as.numeric(target) + 0.4,
                       y = percent + 0.05,
                       yend = percent + 0.05),
                   position=position_stack(),
                   linewidth=0.3,
                   color="black") +
      scale_fill_npg(alpha=0.9) +
      geom_text(aes(label=sprintf("%.1f%%", percent*100)),
                position=position_stack(vjust=0.5), 
                size=3,
                check_overlap=TRUE) +
      geom_text(aes(y=-0.05,
                    label=ifelse(tail != "", 
                               sprintf("p = %.3f", as.numeric(sub("P=", "", tail))),
                               "")),
                size=3, vjust=1) +
      ggtitle("qpAdm Analysis Results") +
      labs(x="Target Population", 
           y="Ancestry Proportion (%)",
           caption="Error bars represent 5% of each component") +
      scale_y_continuous(limits=c(-0.1, 1.1), 
                        labels=scales::percent_format(accuracy=1),
                        expand=c(0,0)) +
      theme_pub +
      theme(panel.grid.major.y = element_line(color="grey90", linewidth=0.2)) +
      coord_flip()

    # 根据数据量自动调整图片尺寸
    n_targets <- length(unique(df$target))
    n_sources <- length(unique(df$source))

    # 保存图片
    ggsave("qpadm_plot.pdf", 
           p, 
           width = max(8, n_sources * 1.2),
           height = max(4, n_targets * 0.8 + 2),
           limitsize = FALSE)
}, error = function(e) {
    stop(sprintf("Error creating plot: %s", e$message))
})

# 打印最终统计信息
cat("\n最终统计:\n")
cat(sprintf("目标群体数: %d\n", length(unique(df$target))))
cat(sprintf("源群体数: %d\n", length(unique(df$source))))
cat(sprintf("总行数: %d\n", nrow(df)))

cat("\n绘图完成!\n")