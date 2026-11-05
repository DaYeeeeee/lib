# -*- coding: utf-8 -*-
"""一键初始化：导入三份数据文件 + 自动创建索引（幂等，可重复执行）。"""
import json
import os
from datetime import datetime
from mongodb_connect import get_collection, get_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# audit_logs 固定大小集合参数（约100KB，足够存数百条日志）
AUDIT_CAPPED_SIZE = 102400  # 100 KB
AUDIT_CAPPED_MAX = 500      # 最多500条（超限后旧记录自动淘汰）

# 任务二设计的索引清单（重复执行不报错）
INDEX_SPECS = [
    ("books", [("isbn", 1)], {"unique": True}),
    ("books", [("category", 1), ("price", 1)], {}),
    ("books", [("title", 1)], {}),
    ("books", [("tags", 1)], {}),
    ("books", [("publish_date", 1)], {}),
    ("books", [("rating", -1)], {}),
    ("readers", [("card_no", 1)], {"unique": True}),
    ("borrow_logs", [("reader_card", 1)], {}),
    ("borrow_logs", [("book_isbn", 1)], {}),
    ("borrow_logs", [("borrow_date", 1)], {}),
    ("borrow_logs", [("status", 1)], {}),
    ("audit_logs", [("operation_time", -1)], {}),
]


def ensure_capped_audit_logs():
    """确保 audit_logs 是固定大小集合（capped）。已存在则跳过，保留已有数据。"""
    db = get_db()
    name = "audit_logs"
    if name in db.list_collection_names():
        opts = db[name].options()
        if opts.get("capped"):
            print(f"✅ {name} 已是固定大小集合（{opts.get('size','?')} bytes），跳过。")
            return
        # 非 capped → 不动已有数据，只提示
        print(f"[提示] {name} 不是固定大小集合，手动重建请先 db.{name}.drop()")
        return
    db.create_collection(name, capped=True, size=AUDIT_CAPPED_SIZE, max=AUDIT_CAPPED_MAX)
    print(f"✅ 已创建固定大小集合 {name}（{AUDIT_CAPPED_SIZE} bytes, 最多{AUDIT_CAPPED_MAX}条）")


def ensure_indexes(verbose=True):
    """按设计建索引（幂等）。先建索引再导数据，delete_many 不会删索引。"""
    created = []
    for coll_name, keys, opts in INDEX_SPECS:
        name = get_collection(coll_name).create_index(keys, **opts)
        created.append("%s.%s" % (coll_name, name))
    if verbose:
        print("✅ 索引就绪，共 %d 个：%s" % (len(created), ", ".join(created)))
    return created


def import_json(filepath, collection_name, date_fields):
    """从 JSON 数组文件导入数据到指定集合，自动转换日期字段。"""
    if not os.path.exists(filepath):
        print(f"[警告] 找不到数据文件 {filepath}，跳过。")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for doc in data:
        for field in date_fields:
            if field in doc and isinstance(doc[field], str):
                try:
                    doc[field] = datetime.fromisoformat(doc[field].replace('Z', '+00:00'))
                except ValueError:
                    pass

    coll = get_collection(collection_name)
    coll.delete_many({})  # 清空数据保留索引（drop 会连索引一起删）
    if data:
        coll.insert_many(data)
    print(f"✅ 导入 {collection_name} 成功，共 {len(data)} 条")


def initialize_all():
    """一键执行：先建固定集合 audit_logs，再建索引，最后导入三份数据。"""
    print("\n--- 正在初始化数据库 ---")
    ensure_capped_audit_logs()
    ensure_indexes()
    import_json(os.path.join(BASE_DIR, 'books.txt'), 'books', ['publish_date'])
    import_json(os.path.join(BASE_DIR, 'readers.txt'), 'readers', ['register_date'])
    import_json(os.path.join(BASE_DIR, 'borrow_logs.txt'), 'borrow_logs',
                ['borrow_date', 'return_date'])
    print("--- 数据库初始化完成 ---\n")


if __name__ == "__main__":
    initialize_all()