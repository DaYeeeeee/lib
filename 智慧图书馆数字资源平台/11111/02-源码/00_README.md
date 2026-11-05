# 智慧图书馆数字资源平台 - 源码说明

## 怎么运行

所有文件路径都以脚本自身所在目录为基准（`os.path.dirname(os.path.abspath(__file__))`），
不依赖当前工作目录。在任意目录下用完整路径运行即可：

```bash
python /你的路径/02-源码/01_main.py
```

数据文件（books.txt / readers.txt / borrow_logs.txt）、config.json、gridfs_files/、导出文件
全部在源码目录里读写。

## 连接配置

连接串集中在 `config.json`，业务代码不写死地址。也可用环境变量覆盖：

| 环境变量 | 用途 |
|---|---|
| `MONGODB_URI` | 主程序连接串（副本集三节点） |
| `MONGODB_DB` | 数据库名（默认 smart_library） |
| `MONGODB_SHARD_URI` | mongos 应用连接串（菜单22用） |
| `MONGODB_SHARD_ADMIN_URI` | mongos 管理连接串（verify_topology.py 用） |
| `MONGODB_STANDALONE_URI` | 单节点连接串（init_repl.py 初始化用） |
| `MONGODB_ADMIN_URI` | 管理账号连接串（运维脚本用） |
| `MONGODB_REPL_MEMBERS` | 副本集成员地址（逗号分隔） |
| `MONGODB_REPL_SET` | 副本集名（默认 rs0） |

## 老师演示步骤

1. `python 01_main.py`
2. 输入 **0**：一键导入三份数据（books 50 / readers 30 / borrow_logs 3000）并自动建索引
3. 输入 **1**：打印连接状态与各集合文档数
4. 输入 **2** → 类别 `计算机`：条件检索
5. 输入 **3** → 标签 `编程,入门`：标签多选匹配
6. 输入 **7**：评分排行 TOP 10
7. 输入 **13**：类别统计（库存/均价/均分/数量）
8. 输入 **14**：学院借阅 TOP 5（$lookup 联合查询）
9. 输入 **15**：月度借阅趋势
10. 输入 **16**：借阅最多 TOP 10 + 馆藏位置
11. 输入 **18**：上传 6 个文件到 GridFS → **20** 查看清单
12. 输入 **19** → ISBN `9787115428028` 或书名 `深入理解`：下载并校验字节数
13. 输入 **22**：分片集群查询对比（需先启动分片集群与 mongos）
14. 输入 **99** 退出

> 想验证多端口多节点是否部署成功，到 `03-数据库与配置` 目录执行 `python verify_topology.py`。

## 只用单机 MongoDB 验证

如果想快速跑通业务功能，可起一个单机 mongod（不带 --auth）：

```bash
mongod --port 27017 --dbpath ./data
export MONGODB_URI=mongodb://127.0.0.1:27017/
python 01_main.py
```

菜单 0 导入 → 1 核对 → 2~7 检索 → 13~16 统计 → 18~20 GridFS → 22 跳过（分片未启动）→ 99 退出。

## 项目结构

| 文件 | 职责 |
|---|---|
| `01_main.py` | 菜单式主交互界面（23 个功能项） |
| `mongodb_connect.py` | 统一连接模块（读 config.json + 环境变量覆盖 + 脱敏打印） |
| `config.json` | 连接配置（副本集/单机/分片 四种 URI） |
| `data_initializer.py` | 一键导入三份数据 + 自动创建 12 个索引 |
| `book_manager.py` | 图书管理：增删改 + 6 项检索 |
| `reader_manager.py` | 读者管理：增删改查 + 学院统计 |
| `borrow_manager.py` | 借还书管理 + 库存联动 |
| `stat_manager.py` | 统计分析 + $lookup 联合 + $merge 物化 + 分片查询对比 |
| `file_manager.py` | GridFS 上传下载 + 字节校验 + 元数据管理 |
| `audit_manager.py` | 操作审计日志 |
| `init_repl.py` | 副本集初始化脚本 |
| `test_failover.py` | 副本集故障转移测试 |
| `requirements.txt` | Python 依赖（pymongo） |
| `books.txt` / `readers.txt` / `borrow_logs.txt` | 原始数据文件 |
| `gridfs_files/` | 6 个待上传的电子书与封面 |