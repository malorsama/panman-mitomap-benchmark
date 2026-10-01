# 人类线粒体 PanMAN 万条序列实验报告

计划运行 1 组，其中 1 组记录为成功。数据规模为 [10000]，每规模重复 1 次，线程预算为 4。未运行、失败和输入不足均单独标记。

本报告由实际运行记录生成。成功要求各阶段退出正常、输出非空、比对去除 gap 后与输入一致、树叶数量及名称匹配。尚未进行 PanMAN 解码回原始序列的往返验证，因此不能据此宣称无损压缩验证完成。

## 输入与实验范围

原始输入 /home/USER/bioconda/mitomap_download/mitomap_mtDNA.fasta，共 66774 条序列。输入 SHA256 为 37fffeb0e0754f763fdf5523eb2d68e3d143ee3380bc17b5b8254f5c645e3c25。

每个规模取原始文件前 N 条，构成嵌套子集；不随机抽样、不去重、不调整序列方向。子集重新写为每条两行的 FASTA，压缩基线使用这一份相同输入。结果只代表该顺序和数据组成。

## 运行状态与耗时

| 序列数 | 重复 | 状态 | 流程秒 | PanMAN 秒 |
| --- | --- | --- | --- | --- |
| 10000 | 1 | SUCCESS | 58,083.397 | 418.250 |

## 内存记录

| 序列数 | 重复 | GNU RSS KiB | 采样进程树 RSS MiB |
| --- | --- | --- | --- |
| 10000 | 1 | 23,709,032.000 | 23,180.363 |

GNU time 的最大 RSS 与每隔固定时间对父子进程 RSS 求和得到的最大值分别保存。后者可能重复计算共享页，也可能漏掉采样间隔内的瞬时峰值；两者均不等同于整台机器的精确峰值内存。资源时间序列位于各尝试目录的 logs/*.resources.tsv。

## 文件大小与体积比

| 序列数 | 重复 | FASTA MiB | gzip MiB | PanMAN MiB |
| --- | --- | --- | --- | --- |
| 10000 | 1 | 157.750 | 1.934 | 0.095 |

| 序列数 | 重复 | FASTA 除以 PanMAN | gzip 除以 PanMAN |
| --- | --- | --- | --- |
| 10000 | 1 | 1,664.720 | 20.414 |

比值大于 1 表示 PanMAN 文件更小。该比较是存储体积比较；FASTA、带 gap 的比对、gzip 和 PanMAN 的表示及元数据不同。gzip 使用 -n -9。字节原值、树及比对文件大小保存在 TSV 中。

## 测量口径

workflow_seconds 从启动 Conda 和 Snakemake 到其退出，包含拆分、MashTree、树名称恢复、MAFFT、PanMAN 和这些步骤的启动开销；不包含子集构建、gzip、产物校验及报告生成。attempt_seconds 另含本次 gzip 和输出校验，但不含子集复制及末尾报告生成。各阶段单独保留 wall time、CPU 用户态和内核态时间、GNU RSS、退出码与完整命令。

MAFFT 使用 --auto --thread CORES --threadit 0，自动策略可能随输入规模变化。CORES 是调度预算，不保证每个工具持续占用该数量的核。实验按规模递增串行运行，不清空操作系统文件缓存。重复次数为 1 时只能报告单次测量，不能用于估计运行波动。

## 结果路径与追溯

每次尝试保存在 results/序列数/rep_编号/attempt_编号 下，最终文件为 panman/out.panman；同目录保留 input.fasta、input.fasta.gz、output/mafft.aln、output/mashtree.nwk、validation.json、checksums.json、config.json 和 logs。所有尝试均保留，不删除原始工作流结果。

benchmark_summary.tsv 选用每个规模和重复的最近成功记录；没有成功记录时保留最新失败或未完成状态。all_attempts.tsv 包含全部尝试。aggregate.tsv 只统计成功重复的流程时间。metadata 记录三套 Conda 包清单、软件版本、硬件、原始工作流和实验代码快照。
