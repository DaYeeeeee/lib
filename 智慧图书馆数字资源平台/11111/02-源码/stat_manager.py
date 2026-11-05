# -*- coding: utf-8 -*-
"""统计分析模块：聚合查询、多集合联合、物化视图导出、分片查询对比。"""
import json
import os
from pymongo import MongoClient
from mongodb_connect import get_collection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _books():
    return get_collection("books")


def _logs():
    return get_collection("borrow_logs")


def category_stats():
    """S1: 按类别统计藏书量、均价、数量。结果写入 category_summary 集合。"""
    pipeline = [
        {"$group": {
            "_id": "$category",
            "total_stock": {"$sum": "$stock"},
            "avg_price": {"$avg": "$price"},
            "avg_rating": {"$avg": "$rating"},
            "book_count": {"$sum": 1},
        }},
        {"$sort": {"book_count": -1}},
    ]
    rows = list(_books().aggregate(pipeline))
    # $merge 写入物化视图
    _books().aggregate(pipeline + [
        {"$merge": {"into": "category_summary",
                    "whenMatched": "replace", "whenNotMatched": "insert"}}
    ])
    return rows


def college_borrow_top5():
    """S2: 各学院借阅总量 Top5（$lookup 联合 readers）。"""
    pipeline = [
        {"$lookup": {"from": "readers", "localField": "reader_card",
                     "foreignField": "card_no", "as": "reader"}},
        {"$unwind": "$reader"},
        {"$group": {"_id": "$reader.college", "borrow_count": {"$sum": 1}}},
        # 并列时按学院名升序，保证多次运行结果稳定
        {"$sort": {"borrow_count": -1, "_id": 1}},
        {"$limit": 5},
    ]
    return list(_logs().aggregate(pipeline))


def borrow_trend():
    """S3: 按年月统计借阅趋势。"""
    pipeline = [
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m", "date": "$borrow_date"}},
            "borrow_count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    return list(_logs().aggregate(pipeline))


def top10_borrowed_books():
    """S4: 借阅次数最多的 10 本图书 + 馆藏位置（联合 books）。"""
    pipeline = [
        {"$group": {"_id": "$book_isbn", "times": {"$sum": 1}}},
        # 并列时按 ISBN 升序作第二排序键，保证多次运行结果稳定
        {"$sort": {"times": -1, "_id": 1}},
        {"$limit": 10},
        {"$lookup": {"from": "books", "localField": "_id",
                     "foreignField": "isbn", "as": "book"}},
        {"$unwind": "$book"},
        {"$project": {
            "_id": 0, "isbn": "$_id", "title": "$book.title",
            "times": 1, "location": "$book.location",
        }},
    ]
    return list(_logs().aggregate(pipeline))


def bestsellers(n=10):
    """借阅次数最多的 n 本图书（直接按 books.borrow_count 字段排序）。"""
    return list(_books().find(
        {}, {"title": 1, "borrow_count": 1, "rating": 1, "_id": 0}
    ).sort([("borrow_count", -1), ("title", 1)]).limit(n))


def export_category_summary():
    """S5: 导出分类统计结果为 JSON 文件。"""
    data = list(get_collection("category_summary").find({}, {"_id": 0}))
    filename = os.path.join(BASE_DIR, "category_summary_export.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[导出] 成功导出 category_summary 集合到 {os.path.basename(filename)}（源码目录下）")
    return len(data)


# ================ 分片集群查询对比演示 ================

def _shard_uri():
    with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return (os.environ.get("MONGODB_SHARD_URI") or cfg.get("shard_uri"),
            cfg.get("db", "smart_library"))


def _plan_once(coll, query):
    """返回(执行阶段, 命中分片, 扫描文档数, 服务器端耗时ms)。"""
    ex = coll.database.command("explain",
                               {"find": coll.name, "filter": query},
                               verbosity="executionStats")
    wp = ex.get("queryPlanner", {}).get("winningPlan", {})
    stage = wp.get("stage", "-")
    raw = wp.get("shards") or []
    shards = [s.get("shardName") if isinstance(s, dict) else s for s in raw]
    if not shards and wp.get("shardName"):
        shards = [wp["shardName"]]
    es = ex.get("executionStats", {})
    return stage, shards, es.get("totalDocsExamined", 0), es.get("executionTimeMillis", 0)


def _compare(coll, query, rounds=20):
    stage, shards, docs, _ = _plan_once(coll, query)
    took = 0
    for _ in range(rounds):
        took += _plan_once(coll, query)[3]
    return stage, shards, docs, took / float(rounds)


def _show(title, coll, query, rounds=20):
    stage, shards, docs, ms = _compare(coll, query, rounds)
    print("%s" % title)
    print("  查询条件: %s" % query)
    print("  执行阶段: %-12s 命中分片: %-12s 扫描文档: %-7d 平均耗时: %.2f ms"
          % (stage, ",".join(shards) or "-", docs, ms))
    return ms, shards, docs


def sharding_query_demo():
    """在 mongos 上对比定向查询 vs 广播查询。"""
    uri, dbname = _shard_uri()
    if not uri:
        print("[提示] config.json 中未配置 shard_uri，跳过分片演示。")
        return
    client = MongoClient(uri, serverSelectionTimeoutMS=4000)
    try:
        client.admin.command("ping")
    except Exception as e:
        print("[提示] 连接 mongos 失败：%s" % str(e).split(":")[0])
        print("[提示] 未启动分片集群时本演示不可用，请先按 03-数据库与配置/启动与部署说明.md 搭建。")
        return
    try:
        db = client[dbname]
        coll = db["borrow_logs"]
        total = coll.estimated_document_count()
        print("已连接 mongos（27300），演示集合 %s.%s 共 %d 条（已分片）" % (dbname, "borrow_logs", total))
        print()
        ms1, sh1, d1 = _show("--- 1. 定向查询：条件里带分片键 book_isbn ---",
                             coll, {"book_isbn": "9787115428028"})
        print()
        ms2, sh2, d2 = _show("--- 2. 广播查询：条件里不带分片键 ---",
                             coll, {"status": "已归还"})
        print()
        ratio = (ms2 / ms1) if ms1 else 0
        print("结论：定向 %.2f ms（扫描 %d 文档、命中 %s），广播 %.2f ms（扫描 %d 文档、命中 %s），"
              % (ms1, d1, ",".join(sh1) or "-", ms2, d2, ",".join(sh2) or "-"))
        print("      相差约 %.1f 倍。把分片键写进查询条件即可避免 scatter-gather。" % ratio)
    finally:
        client.close()


# ================ 索引效果对比（任务三索引优化验证）================

def _explain_coll(collection, query):
    """对查询执行 explain('executionStats')，返回(执行阶段, 扫描文档数, 耗时ms)。"""
    ex = collection.database.command(
        "explain",
        {"find": collection.name, "filter": query},
        verbosity="executionStats"
    )
    wp = ex.get("queryPlanner", {}).get("winningPlan", {})
    stage = wp.get("stage", "-")
    es = ex.get("executionStats", {})
    return stage, es.get("totalDocsExamined", 0), es.get("executionTimeMillis", 0)


def index_compare():
    """对比 2 条查询在有/无索引时的执行计划。先展示有索引的情况，再临时删除索引做无索引对比。"""
    print("\n======== 索引效果对比（执行计划）========")

    # 查询1: category + price 范围查询
    coll = _books()
    q1 = {"category": "计算机", "price": {"$gte": 50, "$lte": 100}}
    s1, d1, ms1 = _explain_coll(coll, q1)
    print("\n1️⃣  查询：类别='计算机' AND 50≤价格≤100")
    print("   有索引时：执行阶段=%s，扫描文档=%d，耗时=%dms" % (s1, d1, ms1))
    # 临时删除复合索引查看全表扫描效果
    try:
        idx_name = coll.index_information()
        target_idx = None
        for name, spec in idx_name.items():
            if spec.get("key") == [("category", 1), ("price", 1)]:
                target_idx = name
                break
        if target_idx:
            coll.drop_index(target_idx)
            s1n, d1n, ms1n = _explain_coll(coll, q1)
            print("   无索引时：执行阶段=%s，扫描文档=%d，耗时=%dms" % (s1n, d1n, ms1n))
            print("   → 复合索引使扫描从 %d 降为 %d，提升约 %.1f 倍" %
                  (d1n, d1, d1n / max(d1, 1)))
            # 恢复索引
            coll.create_index([("category", 1), ("price", 1)])
    except Exception as e:
        print("   [无法演示无索引阶段：%s]" % e)

    # 查询2: title 模糊搜索
    q2 = {"title": {"$regex": "Python"}}
    s2, d2, ms2 = _explain_coll(coll, q2)
    print("\n2️⃣  查询：书名模糊匹配 'Python'（$regex）")
    print("   有索引时：执行阶段=%s，扫描文档=%d，耗时=%dms" % (s2, d2, ms2))
    try:
        idx_name2 = coll.index_information()
        target_idx2 = None
        for name, spec in idx_name2.items():
            if spec.get("key") == [("title", 1)]:
                target_idx2 = name
                break
        if target_idx2:
            coll.drop_index(target_idx2)
            s2n, d2n, ms2n = _explain_coll(coll, q2)
            print("   无索引时：执行阶段=%s，扫描文档=%d，耗时=%dms" % (s2n, d2n, ms2n))
            print("   → title 索引使扫描从 %d 降为 %d，提升约 %.1f 倍" %
                  (d2n, d2, d2n / max(d2, 1)))
            coll.create_index([("title", 1)])
    except Exception as e:
        print("   [无法演示无索引阶段：%s]" % e)

    print("\n✅ 索引对比完成。结论：合理索引能将 COLLSCAN 转为 IXSCAN，大幅减少扫描文档数。")