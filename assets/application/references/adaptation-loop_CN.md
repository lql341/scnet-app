# 完成这个应用 skill

遵循 scnet-app 的[源码到 skill 流程](https://github.com/lql341/scnet-app/blob/main/references/adaptation-loop_CN.md)。
用户在 app.json 定义验收，在 delivery.json 定义 A 级交付。
将源码适配成 runtime/app/ 可运行包，runtime/case/ 中放短算例、检查文件和 Slurm 示例，
runtime/scripts/ 中放环境脚本，并把所有运行包文件列入 app.json 的 files。
在已授权预算内运行 SCNet 作业，保留原始日志并记录每次尝试。
`gate` 列出未过项目和剩余次数；通过后 `build` 才产出 skill 目录和官方 tar。
完成中英文安装、前置条件、使用及算例教程。脚手架或自报的 runtime.json 均不等于认证。
