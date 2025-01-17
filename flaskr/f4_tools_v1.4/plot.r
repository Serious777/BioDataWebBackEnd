library(ggplot2)

# 设置错误处理
options(error = function() {
    cat("Error occurred in R script:\n")
    print(geterrmessage())
    quit(status = 1)
})

# 设置文件名和参数
filename="plot.txt"
outfile="plot.pdf"
title="f4(Outgroup, Reference; X, Target)"
pagewidth=6
pageheight=15
x_Fst_min=-0.01
x_Fst_max=0.01

# 检查输入文件是否存在
if (!file.exists(filename)) {
    stop(paste("Input file not found:", filename))
}

# 读取数据并检查
mydata=read.table(filename, col.names=c("pop", "Fst", "z_score", "order"), sep="\t")
if (nrow(mydata) == 0) {
    stop("No data found in input file")
}

# 打印数据摘要以帮助调试
cat("Data summary:\n")
cat("Number of rows:", nrow(mydata), "\n")
cat("Unique populations:", paste(unique(mydata$pop), collapse=", "), "\n")
cat("Data structure:\n")
str(mydata)

Color=c()
for(k in seq(1,nrow(mydata))){
  if(mydata$z_score[k] <= -3){
    Color=c(Color,"#ff0000")} 
  else if(mydata$z_score[k] <= -2){
    Color=c(Color,"#ff8a80")}
  else if(mydata$z_score[k] < 2){
    Color=c(Color,"#bdbdbd")}
  else if(mydata$z_score[k] <= 3){
    Color=c(Color,"#82b1ff")}
  else if(mydata$z_score[k] > 3){
    Color=c(Color,"#0000ff")}
}

# 限制Fst值的范围
mydata$Fst <- pmax(pmin(mydata$Fst, x_Fst_max), x_Fst_min)

Pop=c()
for(k in seq(1,nrow(mydata))){
  Pop=c(Pop,title)
}
mydata$Pop <- Pop
mydata$pop <- factor(mydata$pop, levels=rev(unique(mydata$pop)))

# 打印处理后的数据摘要
cat("\nProcessed data summary:\n")
cat("Fst range:", range(mydata$Fst), "\n")
cat("z_score range:", range(mydata$z_score), "\n")

# 尝试创建PDF设备
tryCatch({
    pdf(file=outfile,width=pagewidth,height=pageheight)
}, error = function(e) {
    cat("Error creating PDF device:", e$message, "\n")
    quit(status = 1)
})

# 尝试创建图形
tryCatch({
    ggplot(data = mydata, aes(y = pop,x = Fst)) +  # 图例设置成离散的 就直接加factor就行 
          # geom_line() + 
          geom_point(fill = Color,color= Color,shape=1,size=2)+
          labs(y=" ")+
          theme_bw()+
          geom_vline(xintercept = c(0), colour = "orange",linetype="dashed")+  # 参考线
          scale_x_continuous(limits=c(x_Fst_min, x_Fst_max))+ #, breaks=c(-5, -3, 0, 3, 5))+
          theme(legend.position = "bottom", 
                panel.grid.major =element_blank(), 
                panel.grid.minor = element_blank(),  # 底色
                panel.background = element_blank(), 
                axis.line=element_line(colour = "black"))+ 
          facet_grid(.~ Pop)
}, error = function(e) {
    cat("Error creating plot:", e$message, "\n")
    dev.off()
    quit(status = 1)
})

# 确保图形设备被正确关闭
tryCatch({
    dev.off()
}, error = function(e) {
    cat("Warning: Error closing PDF device:", e$message, "\n")
})

# 检查PDF是否生成
if (!file.exists(outfile)) {
    stop(paste("Failed to generate PDF:", outfile))
}

cat("Successfully generated", outfile, "\n")


