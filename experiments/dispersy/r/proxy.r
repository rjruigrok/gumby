library(ggplot2)
library(reshape2)
library(stringr)
library(plyr)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()
print(df2)

if(file.exists("sum_statistics_reduced.txt")){
	df <- read.table("sum_statistics_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df <- subset(df, str_sub(variable, -1) == '_')

	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	p <- p + geom_step(alpha = 0.8, aes(time, value, group=variable, colour=variable, shape=variable))
	p <- p + theme(legend.position="bottom", legend.direction="horizontal")
	p <- p + labs(x = "\nTime into experiment [s]", y = "Broken circuits\n")
	p <- p + xlim(minX, maxX)
	p

	ggsave(file="broken_circuits.pdf", width=12, height=6, dpi=100)

	df <- read.table("sum_statistics_reduced.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	df <- subset(df, str_sub(variable, -1) != '_')
	df <- subset(df, variable != 'speed-others')

	df$value <- df$value / 1024.0 / 1024.0

	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	p <- p + geom_step(alpha = 0.8, aes(time, value, group=variable, colour=variable, shape=variable))
	p <- p + theme(legend.position="bottom", legend.direction="horizontal")
    p <- p + labs(x = "\nTime into experiment [s]", y = "Speed [MB/s]\n")

	p <- p + xlim(minX, maxX)
	p

	ggsave(file="speeds.pdf", width=12, height=6, dpi=100)
}

if(file.exists("_latencies.txt")){
	df <- read.table("_latencies.txt", header = TRUE, check.names = FALSE)
    df$latency <- df$latency * 1000

    p <- ggplot(df, aes(x=hops, y=latency)) + theme_bw()
    p <- p + scale_y_log10()
    p <- p + scale_x_discrete(limits=c("1","2","3")) + geom_boxplot(aes(x=hops, y=latency, group=hops))
    p <- p + theme(legend.position="bottom", legend.direction="horizontal")
    p <- p + labs(x = "\nCircuit length [hops]", y = "Round-trip time [ms]\n")
    p

    ggsave(file="latencies.pdf", width=12, height=6, dpi=100)
    ggsave(file="latencies.png", width=12, height=6, dpi=100)

    cdf <- ddply(df, "hops", summarise, latency.mean=mean(latency))
    p <- ggplot(df, aes(x=latency, fill=factor(hops), group=hops))
    p <- p + geom_density(alpha=0.3)
    p <- p + geom_vline(data=cdf, aes(xintercept=latency.mean,  colour=factor(hops)), linetype="dashed", size=1)
    p <- p + xlim(0, 4)
    p <- p + scale_fill_discrete(name="Number of hops")
    p <- p + theme_bw()
    p <- p + theme(legend.position="bottom", legend.direction="horizontal")
    p <- p + labs(y = "Probability density\n", x = "\nRound-trip time [ms]")
    p

    ggsave(file="latencies_density.png", width=12, height=6, dpi=100)
    ggsave(file="latencies_density.pdf", width=12, height=6, dpi=100)
}