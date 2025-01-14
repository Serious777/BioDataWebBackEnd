library(reshape2)
library(ggplot2)
title="f4(Mbuti, Reference; X, Target)"
filename="plot.txt"
outfile="plot.pdf"
pagewidth=6
pageheight=15
x_Fst_min=-0.01
x_Fst_max=0.01
mydata=read.table(filename, col.names=c("pop", "Fst", "z_score", "order"), sep="\t")

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

for(k in seq(1,nrow(mydata))){
  if(mydata$Fst[k] <= x_Fst_min){
    mydata$Fst[k] = x_Fst_min}
  if(mydata$Fst[k] > x_Fst_max){
    mydata$Fst[k] = x_Fst_max}
}


Pop=c()
for(k in seq(1,nrow(mydata))){
  Pop=c(Pop,title)
}
mydata$Pop <- Pop
mydata$pop <- factor(mydata$pop, levels=rev(unique(mydata$pop)))
pdf(file=outfile,width=pagewidth,height=pageheight)
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
dev.off()


