# -*- coding: utf-8 -*-
"""读者管理模块：增删改查。"""
from mongodb_connect import get_collection
import audit_manager as am


def _readers():
    return get_collection("readers")


def add_one(reader):
    """新增一位读者。"""
    _readers().insert_one(reader)
    am.log_action("lib_writer", "INSERT_READER",
                  {"card_no": reader.get("card_no"), "name": reader.get("name")})
    print(f"[新增] 读者《{reader.get('name')}》添加成功。")


def delete_one_reader(query):
    """按条件删除读者。"""
    result = _readers().delete_one(query)
    am.log_action("lib_writer", "DELETE_READER",
                  {"query": query, "deleted": result.deleted_count})
    print(f"[删除] 删除了 {result.deleted_count} 位读者。")


def update_one_reader(query, update):
    """按条件更新读者。"""
    result = _readers().update_one(query, update)
    am.log_action("lib_writer", "UPDATE_READER", {"query": query, "update": update})
    print(f"[更新] 更新了 {result.modified_count} 位读者。")


def find_reader(query):
    """按条件查找读者。"""
    return _readers().find_one(query)


def list_all_readers():
    """列出全部读者。"""
    return list(_readers().find())


def college_stats():
    """各学院读者人数统计。"""
    pipeline = [
        {"$group": {"_id": "$college", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    return list(_readers().aggregate(pipeline))