# -*- coding: utf-8 -*-
"""图书管理模块：增删改查 + 6 项检索功能。"""
from datetime import datetime
from mongodb_connect import get_collection
import audit_manager as am


def _books():
    return get_collection("books")


def add_one(book):
    """新增一本图书。"""
    book.setdefault("borrow_count", 0)
    _books().insert_one(book)
    am.log_action("lib_writer", "INSERT_BOOK", {"isbn": book.get("isbn"), "title": book.get("title")})
    print(f"[新增] 图书《{book.get('title')}》添加成功。")


def delete_one_book(query):
    """按条件删除图书。"""
    result = _books().delete_one(query)
    am.log_action("lib_writer", "DELETE_BOOK", {"query": query, "deleted": result.deleted_count})
    print(f"[删除] 删除了 {result.deleted_count} 本图书。")


def update_one_book(query, update):
    """按条件更新图书。"""
    result = _books().update_one(query, update)
    am.log_action("lib_writer", "UPDATE_BOOK", {"query": query, "update": update})
    print(f"[更新] 更新了 {result.modified_count} 本图书。")


def find_books(query, limit=10):
    """通用图书检索。"""
    return list(_books().find(query).limit(limit))


def top_rated(n=10):
    """评分最高的 n 本图书（仅返回书名、作者、评分）。"""
    return list(_books().find(
        {}, {"title": 1, "author": 1, "rating": 1, "_id": 0}
    ).sort([("rating", -1), ("title", 1)]).limit(n))


def search_by_category_price(category, min_price, max_price):
    """按类别与价格区间组合筛选。"""
    return list(_books().find({
        "category": category,
        "price": {"$gte": min_price, "$lte": max_price}
    }))


def search_by_tags(tags):
    """按标签多选匹配（同时含所有指定标签）。"""
    return list(_books().find({"tags": {"$all": tags}}))


def search_by_title(keyword):
    """按书名模糊检索（正则，不区分大小写）。"""
    return list(_books().find({"title": {"$regex": keyword, "$options": "i"}}))


def search_by_year_range(start_year, end_year):
    """按出版年份范围检索。"""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year + 1, 1, 1)
    return list(_books().find({"publish_date": {"$gte": start, "$lt": end}}))


def books_missing_tags():
    """查询缺少 tags 字段的图书（数据质量核查）。"""
    return list(_books().find({"tags": {"$exists": False}}))


def list_all_books():
    """列出全部图书。"""
    return list(_books().find())