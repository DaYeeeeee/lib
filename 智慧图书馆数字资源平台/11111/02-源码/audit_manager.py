# -*- coding: utf-8 -*-
"""操作审计日志模块：所有增删改导出操作写入 audit_logs（固定大小集合）。"""
from datetime import datetime
from mongodb_connect import get_collection


def log_action(operator, action, details=None):
    """写入一条操作日志到 audit_logs。operator=操作者，action=操作类型，details=详细信息。"""
    doc = {
        "operation_time": datetime.now(),
        "operator": operator,
        "action": action,
        "details": details or {},
    }
    get_collection("audit_logs").insert_one(doc)


def get_recent_logs(limit=100):
    """按时间倒序返回最近 limit 条操作日志。"""
    return list(
        get_collection("audit_logs")
        .find()
        .sort([("$natural", -1)])
        .limit(limit)
    )