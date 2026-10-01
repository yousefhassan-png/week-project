# ============================================================
# الملف 2: الاستعلامات التحليلية (الخطوة 2 و 3 و 4)
# كل استعلام يرجع نتيجته على شكل جدول (DataFrame)
# ============================================================

import sqlite3
import pandas as pd

اسم_القاعدة = "store.db"

# قيمة العملية = الكمية × سعر المنتج (هذا هو تعريف الإيراد في المشروع)

# ---------- الاستعلام 1: أفضل 5 عملاء من ناحية الإنفاق ----------
# يستخدم: JOIN (ثلاث جداول) + GROUP BY + ORDER BY
استعلام_أفضل_العملاء = """
SELECT c.customer_id   AS "رقم_العميل",
       c.customer_name AS "اسم_العميل",
       c.city          AS "المدينة",
       COUNT(s.sale_id)             AS "عدد_المشتريات",
       SUM(s.quantity * p.price)    AS "إجمالي_الإنفاق"
FROM customers c
JOIN sales s    ON c.customer_id = s.customer_id
JOIN products p ON s.product_id  = p.product_id
GROUP BY c.customer_id, c.customer_name, c.city
ORDER BY "إجمالي_الإنفاق" DESC
LIMIT 5
"""

# ---------- الاستعلام 2: العملاء الذين لم يشتروا إطلاقاً ----------
# يستخدم: LEFT JOIN + WHERE ... IS NULL
استعلام_بدون_شراء = """
SELECT c.customer_id   AS "رقم_العميل",
       c.customer_name AS "اسم_العميل",
       c.city          AS "المدينة",
       c.signup_date   AS "تاريخ_التسجيل"
FROM customers c
LEFT JOIN sales s ON c.customer_id = s.customer_id
WHERE s.sale_id IS NULL
"""

# ---------- الاستعلام 3: متوسط قيمة الشراء لكل عميل مقابل المتوسط العام ----------
# يستخدم: Subquery (استعلام فرعي لحساب المتوسط العام)
استعلام_متوسط_الشراء = """
SELECT c.customer_name AS "اسم_العميل",
       c.city          AS "المدينة",
       ROUND(AVG(s.quantity * p.price), 2) AS "متوسط_قيمة_الشراء",
       (SELECT ROUND(AVG(s2.quantity * p2.price), 2)
        FROM sales s2
        JOIN products p2 ON s2.product_id = p2.product_id) AS "المتوسط_العام"
FROM customers c
JOIN sales s    ON c.customer_id = s.customer_id
JOIN products p ON s.product_id  = p.product_id
GROUP BY c.customer_id, c.customer_name, c.city
ORDER BY "متوسط_قيمة_الشراء" DESC
"""

# ---------- الاستعلام 4: ترتيب العملاء داخل كل مدينة حسب الإنفاق ----------
# يستخدم: Window Function (RANK مع PARTITION BY) + LEFT JOIN
# LEFT JOIN عشان يظهر العملاء الذين لم يشتروا (إنفاقهم صفر)
استعلام_ترتيب_المدن = """
SELECT c.city          AS "المدينة",
       c.customer_name AS "اسم_العميل",
       COALESCE(SUM(s.quantity * p.price), 0) AS "إجمالي_الإنفاق",
       RANK() OVER (
           PARTITION BY c.city
           ORDER BY COALESCE(SUM(s.quantity * p.price), 0) DESC
       ) AS "الترتيب_داخل_المدينة"
FROM customers c
LEFT JOIN sales s    ON c.customer_id = s.customer_id
LEFT JOIN products p ON s.product_id  = p.product_id
GROUP BY c.customer_id, c.customer_name, c.city
ORDER BY c.city, "الترتيب_داخل_المدينة"
"""

# ---------- الاستعلام 5: الاتجاه الشهري للإيراد ----------
# يستخدم: strftime + GROUP BY
استعلام_الاتجاه_الشهري = """
SELECT strftime('%Y-%m', s.sale_date) AS "الشهر",
       COUNT(s.sale_id)            AS "عدد_العمليات",
       SUM(s.quantity)             AS "إجمالي_الكمية",
       SUM(s.quantity * p.price)   AS "إجمالي_الإيراد"
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY strftime('%Y-%m', s.sale_date)
ORDER BY "الشهر"
"""

# ---------- الاستعلام 6: الاتجاه اليومي مع الإيراد التراكمي ----------
# يستخدم: Window Function (SUM OVER) + GROUP BY
# (لأن كل المبيعات في شهر واحد، نحتاج الاتجاه اليومي لنشوف التغير عبر الوقت)
استعلام_الاتجاه_اليومي = """
SELECT s.sale_date AS "التاريخ",
       SUM(s.quantity * p.price) AS "إيراد_اليوم",
       SUM(SUM(s.quantity * p.price)) OVER (ORDER BY s.sale_date) AS "الإيراد_التراكمي"
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY s.sale_date
ORDER BY s.sale_date
"""

# ---------- الاستعلام 7: أفضل فئة منتجات من ناحية الإيراد ----------
# يستخدم: JOIN + GROUP BY + Subquery (لحساب النسبة من الإجمالي)
استعلام_الفئات = """
SELECT p.category                AS "الفئة",
       SUM(s.quantity)           AS "إجمالي_الكمية",
       SUM(s.quantity * p.price) AS "إجمالي_الإيراد",
       ROUND(100.0 * SUM(s.quantity * p.price) /
            (SELECT SUM(s2.quantity * p2.price)
             FROM sales s2 JOIN products p2 ON s2.product_id = p2.product_id), 1) AS "النسبة_من_الإيراد"
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.category
ORDER BY "إجمالي_الإيراد" DESC
"""

# ---------- الاستعلام 8: العلاقة بين تاريخ التسجيل وحجم الإنفاق ----------
# يستخدم: LEFT JOIN + Subquery (لمعرفة آخر تاريخ بيع) + GROUP BY
# "عدد_الأيام_منذ_التسجيل" = الفرق بين آخر تاريخ بيع في القاعدة وتاريخ تسجيل العميل
استعلام_التسجيل_والإنفاق = """
SELECT c.customer_id   AS "رقم_العميل",
       c.customer_name AS "اسم_العميل",
       c.signup_date   AS "تاريخ_التسجيل",
       CAST(julianday((SELECT MAX(sale_date) FROM sales)) - julianday(c.signup_date) AS INTEGER)
                       AS "عدد_الأيام_منذ_التسجيل",
       COUNT(s.sale_id)                       AS "عدد_المشتريات",
       COALESCE(SUM(s.quantity * p.price), 0) AS "إجمالي_الإنفاق"
FROM customers c
LEFT JOIN sales s    ON c.customer_id = s.customer_id
LEFT JOIN products p ON s.product_id  = p.product_id
GROUP BY c.customer_id, c.customer_name, c.signup_date
ORDER BY "عدد_الأيام_منذ_التسجيل" DESC
"""

# ---------- الاستعلام 9: نسبة العملاء المتكررين ----------
# يستخدم: Subquery في FROM + CASE + GROUP BY داخلي
استعلام_المتكررين = """
SELECT COUNT(*) AS "إجمالي_العملاء",
       SUM(CASE WHEN عدد = 0 THEN 1 ELSE 0 END) AS "عملاء_بدون_شراء",
       SUM(CASE WHEN عدد = 1 THEN 1 ELSE 0 END) AS "عملاء_اشتروا_مرة_واحدة",
       SUM(CASE WHEN عدد > 1 THEN 1 ELSE 0 END) AS "العملاء_المتكررون",
       ROUND(100.0 * SUM(CASE WHEN عدد > 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS "نسبة_المتكررين_من_الكل"
FROM (
    SELECT c.customer_id, COUNT(s.sale_id) AS عدد
    FROM customers c
    LEFT JOIN sales s ON c.customer_id = s.customer_id
    GROUP BY c.customer_id
)
"""

# ---------- الاستعلام 10: الإيراد حسب مدينة العميل ----------
# يستخدم: JOIN + GROUP BY
استعلام_المدن = """
SELECT c.city AS "المدينة",
       COUNT(DISTINCT c.customer_id) AS "عدد_العملاء_المشترين",
       COUNT(s.sale_id)              AS "عدد_العمليات",
       SUM(s.quantity * p.price)     AS "إجمالي_الإيراد"
FROM customers c
JOIN sales s    ON c.customer_id = s.customer_id
JOIN products p ON s.product_id  = p.product_id
GROUP BY c.city
ORDER BY "إجمالي_الإيراد" DESC
"""

# ---------- الاستعلام 11: تفاصيل كل عمليات البيع (لصفحة الإكسل) ----------
استعلام_التفاصيل = """
SELECT s.sale_id        AS "رقم_العملية",
       s.sale_date      AS "التاريخ",
       c.customer_name  AS "اسم_العميل",
       s.city           AS "المدينة",
       p.product_name   AS "المنتج",
       p.category       AS "الفئة",
       s.quantity       AS "الكمية",
       p.price          AS "سعر_الوحدة",
       s.quantity * p.price AS "قيمة_العملية"
FROM sales s
JOIN customers c ON s.customer_id = c.customer_id
JOIN products p  ON s.product_id  = p.product_id
ORDER BY s.sale_id
"""

# أسماء الفئات بالعربي (للعرض فقط)
أسماء_الفئات = {
    "electronics": "إلكترونيات",
    "furniture":   "أثاث",
    "stationery":  "قرطاسية",
}


def جلب_كل_النتائج():
    """تشغل كل الاستعلامات وترجع النتائج في قاموس من الجداول"""
    الاتصال = sqlite3.connect(اسم_القاعدة)

    النتائج = {
        "أفضل_العملاء":     pd.read_sql_query(استعلام_أفضل_العملاء, الاتصال),
        "بدون_شراء":        pd.read_sql_query(استعلام_بدون_شراء, الاتصال),
        "متوسط_الشراء":     pd.read_sql_query(استعلام_متوسط_الشراء, الاتصال),
        "ترتيب_المدن":      pd.read_sql_query(استعلام_ترتيب_المدن, الاتصال),
        "الاتجاه_الشهري":   pd.read_sql_query(استعلام_الاتجاه_الشهري, الاتصال),
        "الاتجاه_اليومي":   pd.read_sql_query(استعلام_الاتجاه_اليومي, الاتصال),
        "الفئات":           pd.read_sql_query(استعلام_الفئات, الاتصال),
        "التسجيل_والإنفاق": pd.read_sql_query(استعلام_التسجيل_والإنفاق, الاتصال),
        "المتكررون":        pd.read_sql_query(استعلام_المتكررين, الاتصال),
        "المدن":            pd.read_sql_query(استعلام_المدن, الاتصال),
        "التفاصيل":         pd.read_sql_query(استعلام_التفاصيل, الاتصال),
    }
    الاتصال.close()

    # --- تعديلات بسيطة بعد جلب النتائج ---
    # الفرق بين متوسط العميل والمتوسط العام (استعلام 3)
    النتائج["متوسط_الشراء"]["الفرق_عن_المتوسط"] = (
        النتائج["متوسط_الشراء"]["متوسط_قيمة_الشراء"] - النتائج["متوسط_الشراء"]["المتوسط_العام"]
    ).round(2)
    النتائج["متوسط_الشراء"]["الحالة"] = النتائج["متوسط_الشراء"]["الفرق_عن_المتوسط"].apply(
        lambda الفرق: "أعلى من المتوسط" if الفرق > 0 else "أقل من المتوسط"
    )

    # ترجمة أسماء الفئات للعربي
    النتائج["الفئات"]["الفئة"] = النتائج["الفئات"]["الفئة"].map(أسماء_الفئات)
    النتائج["التفاصيل"]["الفئة"] = النتائج["التفاصيل"]["الفئة"].map(أسماء_الفئات)

    return النتائج


# عند تشغيل هذا الملف مباشرة نطبع كل النتائج للمراجعة
if __name__ == "__main__":
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    for الاسم, الجدول in جلب_كل_النتائج().items():
        print("\n===== ", الاسم, " =====")
        print(الجدول.to_string(index=False))
