# -*- coding: utf-8 -*-
"""借阅管理模块：借书、还书、查询借阅记录。"""
from datetime import datetime
from bson import ObjectId
from mongodb_connect import get_collection
import audit_manager as am


def _logs():
    return get_collection("borrow_logs")


def borrow_book(reader_card, book_isbn, duration_days=30):
    """借书：扣库存 + 增借阅计数 + 写入借阅记录。"""
    books = get_collection("books")
    book = books.find_one({"isbn": book_isbn})
    if not book or book.get("stock", 0) <= 0:
        return None, "库存不足或图书不存在"

    doc = {
        "reader_card": reader_card,
        "book_isbn": book_isbn,
        "borrow_date": datetime.now(),
        "status": "借出",
        "duration_days": duration_days,
    }
    result = _logs().insert_one(doc)
    books.update_one({"isbn": book_isbn}, {"$inc": {"stock": -1, "borrow_count": 1}})
    am.log_action("lib_writer", "BORROW",
                  {"reader_card": reader_card, "book_isbn": book_isbn,
                   "log_id": str(result.inserted_id)})
    return str(result.inserted_id), "借阅成功"


def return_book(log_id):
    """还书：恢复库存 + 更新归还日期与状态。"""
    log = _logs().find_one({"_id": ObjectId(log_id)})
    if not log:
        return False, "借阅记录不存在"

    _logs().update_one(
        {"_id": log["_id"]},
        {"$set": {"return_date": datetime.now(), "status": "已归还"}},
    )
    get_collection("books").update_one(
        {"isbn": log["book_isbn"]}, {"$inc": {"stock": 1}}
    )
    am.log_action("lib_writer", "RETURN",
                  {"log_id": log_id, "book_isbn": log["book_isbn"]})
    return True, "归还成功"


def list_borrow_by_reader(reader_card):
    """按读者证号查询借阅记录。"""
    return list(_logs().find({"reader_card": reader_card}))