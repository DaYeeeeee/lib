# -*- coding: utf-8 -*-
"""智慧图书馆数字资源平台 · 主菜单程序"""
import sys
from pymongo.errors import PyMongoError

import mongodb_connect as mc
import book_manager as bm
import reader_manager as rm
import borrow_manager as brm
import stat_manager as sm
import file_manager as fm
import audit_manager as am
import data_initializer as di


def print_menu():
    print()
    print("=" * 55)
    print("        智慧图书馆数字资源平台 - 主菜单")
    print("=" * 55)
    print(" 0. ★ 一键初始化导入数据 (请优先执行)")
    print("-" * 55)
    print(" 1. 查看数据库连接状态与集合文档数")
    print(" 2. 条件检索图书（按类别 + 价格区间）")
    print(" 3. 标签多选匹配检索")
    print(" 4. 书名模糊检索")
    print(" 5. 按出版年份范围检索")
    print(" 6. 缺失 tags 字段的图书（数据质量核查）")
    print(" 7. 评分排行 TOP 10")
    print(" 8. 新增一本图书")
    print(" 9. 更新图书库存")
    print("10. 删除图书")
    print("11. 新增读者 / 删除读者")
    print("12. 借书 / 还书")
    print("--- 统计分析 ---")
    print("13. 按类别统计（库存/均价/评分/数量）")
    print("14. 学院借阅排行榜 TOP 5")
    print("15. 借阅趋势统计（年月）")
    print("16. 借阅次数最多 TOP 10 图书（含馆藏位置）")
    print("17. 导出分类统计结果集合")
    print("--- 文件存储与日志 ---")
    print("18. 批量上传电子书与封面")
    print("19. 按 ISBN 或书名下载电子书并校验")
    print("20. 查看 GridFS 文件清单")
    print("21. 查看最近操作日志")
    print("--- 高级验证 ---")
    print("22. 分片集群查询性能对比演示")
    print("23. 索引效果对比（带执行计划）")
    print("99. 退出")
    print("=" * 55)


def get_float(prompt, default=0.0):
    while True:
        try:
            v = input(prompt).strip()
            return float(v) if v else default
        except ValueError:
            print("[提示] 请输入数字！")


def get_int(prompt, default=0):
    while True:
        try:
            v = input(prompt).strip()
            return int(v) if v else default
        except ValueError:
            print("[提示] 请输入整数！")


def safe(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except PyMongoError as e:
        print(f"[数据库错误] {e}")
        print("[提示] 请检查 MongoDB 服务是否已启动！")
    except Exception as e:
        print(f"[错误] {e}")
    return None


def main():
    print("\n正在尝试连接数据库...")
    try:
        mc.print_connection_status()
    except Exception:
        print("\n❌ 连接失败！请确保 MongoDB 服务已启动，且 config.json 配置正确。")
        sys.exit(1)

    while True:
        print_menu()
        choice = input("请输入功能编号：").strip()

        if choice == "0":
            safe(di.initialize_all)
        elif choice == "1":
            safe(mc.print_connection_status)

        # --- 检索功能 ---
        elif choice == "2":
            cat = input("类别（如 计算机）：").strip()
            lo = get_float("最低价格：")
            hi = get_float("最高价格：", 9999)
            rows = safe(bm.search_by_category_price, cat, lo, hi)
            if rows:
                for b in rows:
                    print(f"  {b.get('title')} | ￥{b.get('price')} | 评分{b.get('rating')}")
                print(f"  共 {len(rows)} 条结果")
        elif choice == "3":
            tags = [t.strip() for t in input("标签（逗号分隔，如 编程,入门）：").split(",") if t.strip()]
            rows = safe(bm.search_by_tags, tags)
            if rows:
                for b in rows:
                    print(f"  {b.get('title')} | 标签: {b.get('tags')}")
                print(f"  共 {len(rows)} 条结果")
        elif choice == "4":
            kw = input("书名关键字：").strip()
            rows = safe(bm.search_by_title, kw)
            if rows:
                for b in rows:
                    print(f"  {b.get('title')} | {b.get('author')} | ￥{b.get('price')}")
                print(f"  共 {len(rows)} 条结果")
        elif choice == "5":
            sy = get_int("起始年份：", 2000)
            ey = get_int("结束年份：", 2030)
            rows = safe(bm.search_by_year_range, sy, ey)
            if rows:
                for b in rows:
                    print(f"  {b.get('title')} | 出版: {b.get('publish_date')}")
                print(f"  共 {len(rows)} 条结果")
        elif choice == "6":
            rows = safe(bm.books_missing_tags)
            if rows:
                for b in rows:
                    print(f"  {b.get('title')} | ISBN: {b.get('isbn')}")
                print(f"  共 {len(rows)} 本图书缺少 tags 字段")
        elif choice == "7":
            rows = safe(bm.top_rated, 10)
            if rows:
                for i, b in enumerate(rows, 1):
                    print(f"  {i}. {b.get('title')} | {b.get('author')} | 评分: {b.get('rating')}")

        # --- 增删改 ---
        elif choice == "8":
            book = {
                "isbn": input("ISBN：").strip(),
                "title": input("书名：").strip(),
                "author": input("作者：").strip(),
                "publisher": input("出版社：").strip(),
                "category": input("类别：").strip(),
                "price": get_float("价格："),
                "rating": get_float("评分 (0-5)：", 0),
                "stock": get_int("库存："),
                "tags": [t.strip() for t in input("标签（逗号分隔，可空）：").split(",") if t.strip()],
                "location": {
                    "floor": input("所在楼层（如 一楼中文图书区）：").strip() or "一楼",
                    "shelf": input("架位号（如 A-01）：").strip() or "A-01",
                },
                "publish_date": input("出版日期（YYYY-MM-DD，可空）：").strip() or None,
            }
            ebook = input("电子书文件名（无则回车跳过）：").strip()
            if ebook:
                book["ebook_name"] = ebook
            safe(bm.add_one, book)
        elif choice == "9":
            isbn = input("ISBN：").strip()
            delta = get_int("库存增减（如 -2）：")
            safe(bm.update_one_book, {"isbn": isbn}, {"$inc": {"stock": delta}})
        elif choice == "10":
            isbn = input("要删除的图书 ISBN：").strip()
            safe(bm.delete_one_book, {"isbn": isbn})

        # --- 读者 ---
        elif choice == "11":
            sub = input("1.新增读者  2.删除读者：").strip()
            if sub == "1":
                reader = {
                    "card_no": input("借阅证号：").strip(),
                    "name": input("姓名：").strip(),
                    "college": input("学院：").strip(),
                    "phone": input("电话：").strip(),
                    "level": input("等级 (普通/高级/教师)：").strip() or "普通",
                    "register_date": input("注册日期（YYYY-MM-DD，可空）：").strip() or None,
                }
                email = input("邮箱 (可空)：").strip()
                if email:
                    reader["email"] = email
                fav = input("偏好类别（逗号分隔，可空）：").strip()
                if fav:
                    reader["fav_categories"] = [c.strip() for c in fav.split(",") if c.strip()]
                safe(rm.add_one, reader)
            elif sub == "2":
                card = input("要删除的借阅证号：").strip()
                safe(rm.delete_one_reader, {"card_no": card})

        # --- 借还 ---
        elif choice == "12":
            sub = input("1.借书  2.还书：").strip()
            if sub == "1":
                rc = input("借阅证号：").strip()
                bi = input("图书 ISBN：").strip()
                lid, msg = safe(brm.borrow_book, rc, bi) or (None, "操作失败")
                print(msg, lid or "")
            elif sub == "2":
                lid = input("借阅记录 ID：").strip()
                ok, msg = safe(brm.return_book, lid) or (False, "操作失败")
                print(msg)

        # --- 统计 ---
        elif choice == "13":
            rows = safe(sm.category_stats)
            if rows:
                print("  类别          库存    均价      均分    数量")
                print("  " + "-" * 48)
                for r in rows:
                    print("  %-12s %5d  %7.2f  %6.2f  %4d" % (
                        r["_id"], r.get("total_stock", 0),
                        r.get("avg_price", 0), r.get("avg_rating", 0),
                        r.get("book_count", 0)))
                print("  [提示] 结果已写入 category_summary 集合")
        elif choice == "14":
            rows = safe(sm.college_borrow_top5)
            if rows:
                for i, r in enumerate(rows, 1):
                    print(f"  {i}. {r['_id']}：{r['borrow_count']} 次借阅")
        elif choice == "15":
            rows = safe(sm.borrow_trend)
            if rows:
                for r in rows:
                    print(f"  {r['_id']}：{r['borrow_count']} 次")
        elif choice == "16":
            rows = safe(sm.top10_borrowed_books)
            if rows:
                for i, r in enumerate(rows, 1):
                    loc = r.get("location", {})
                    print(f"  {i}. {r.get('title')} | 借阅{r.get('times')}次 | "
                          f"{loc.get('floor','')} {loc.get('shelf','')}")
        elif choice == "17":
            cnt = safe(sm.export_category_summary)
            print(f"  已导出 {cnt} 条记录到 category_summary_export.json")

        # --- GridFS ---
        elif choice == "18":
            safe(fm.upload_ebooks)
        elif choice == "19":
            key = input("输入 ISBN 或书名关键字：").strip()
            if key.replace("-", "").isdigit():
                safe(fm.download_and_verify, key)
            else:
                safe(fm.download_by_title, key)
        elif choice == "20":
            safe(fm.list_gridfs_files)
        elif choice == "21":
            logs = safe(am.get_recent_logs, 10)
            if logs:
                for log in logs:
                    print("  [%s] %s 执行 %s | 详情: %s" % (
                        log.get("operation_time", "-"),
                        log.get("operator", "-"),
                        log.get("action", "-"),
                        log.get("details", "-")))

        # --- 分片 ---
        elif choice == "22":
            safe(sm.sharding_query_demo)

        # --- 索引对比 ---
        elif choice == "23":
            safe(sm.index_compare)

        elif choice == "99":
            print("正在退出...")
            mc.close_client()
            sys.exit(0)
        else:
            print("[提示] 无效编号，请重新输入")


if __name__ == "__main__":
    main()