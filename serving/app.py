import duckdb
import pandas as pd
import streamlit as st
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "northstar.duckdb"

st.set_page_config(
    page_title="NorthStar Retail | Executive Dashboard",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# Database connection
# ============================================================

@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


con = get_connection()


# ============================================================
# Header
# ============================================================

st.title("NorthStar Retail — Executive Dashboard")
st.caption("Gold-layer business intelligence powered by DuckDB")

st.divider()


# ============================================================
# Executive KPIs
# ============================================================

kpi = con.sql("""
    SELECT
        SUM(total_item_value) AS revenue,
        COUNT(DISTINCT order_id) AS orders,
        SUM(total_item_value)
            / COUNT(DISTINCT order_id) AS avg_order_value,
        COUNT(DISTINCT product_key) AS products
    FROM fact_order_items
""").df().iloc[0]

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Total Revenue",
    f"R$ {kpi['revenue']:,.0f}"
)

c2.metric(
    "Orders",
    f"{kpi['orders']:,.0f}"
)

c3.metric(
    "Average Order Value",
    f"R$ {kpi['avg_order_value']:,.2f}"
)

c4.metric(
    "Products Sold",
    f"{kpi['products']:,.0f}"
)


# ============================================================
# 1. Revenue Performance
# ============================================================

st.header("1. Revenue Performance")
st.caption("How is revenue trending over time?")

monthly = con.sql("""
    SELECT
        DATE_TRUNC('month', full_date) AS month,
        SUM(daily_revenue) AS revenue,
        SUM(daily_orders) AS orders
    FROM mart_sales_daily
    GROUP BY 1
    ORDER BY 1
""").df()

monthly["month"] = pd.to_datetime(monthly["month"])

monthly["revenue_mom_pct"] = (
    monthly["revenue"].pct_change() * 100
)

left, right = st.columns(2)

with left:
    st.subheader("Monthly Revenue")
    st.line_chart(
        monthly.set_index("month")[["revenue"]]
    )

with right:
    st.subheader("Monthly Orders")
    st.line_chart(
        monthly.set_index("month")[["orders"]]
    )

latest = monthly.dropna(
    subset=["revenue_mom_pct"]
).iloc[-1]

st.info(
    f"Latest month-over-month revenue change: "
    f"{latest['revenue_mom_pct']:+.1f}%."
)


# ============================================================
# 2. Geographic Performance
# ============================================================

st.header("2. Geographic Performance")
st.caption(
    "Which customer states generate the most revenue?"
)

geo = con.sql("""
    SELECT
        c.customer_state AS state,
        SUM(i.total_item_value) AS revenue,
        COUNT(DISTINCT i.order_id) AS orders,
        SUM(i.total_item_value)
            / COUNT(DISTINCT i.order_id) AS avg_order_value
    FROM fact_order_items i
    JOIN fact_orders o
        ON i.order_id = o.order_id
    JOIN dim_customer c
        ON o.customer_key = c.customer_key
    WHERE c.customer_state IS NOT NULL
    GROUP BY c.customer_state
    ORDER BY revenue DESC
""").df()

st.bar_chart(
    geo.head(10).set_index("state")[["revenue"]]
)

st.dataframe(
    geo.style.format({
        "revenue": "R$ {:,.0f}",
        "avg_order_value": "R$ {:,.2f}",
        "orders": "{:,.0f}",
    }),
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# 3. Product Performance
# ============================================================

st.header("3. Product Performance")
st.caption(
    "Which product categories drive the most sales?"
)

products = con.sql("""
    SELECT
        COALESCE(
            NULLIF(TRIM(p.product_category_name), ''),
            'Unknown'
        ) AS category,
        SUM(i.total_item_value) AS revenue,
        COUNT(*) AS units,
        COUNT(DISTINCT i.order_id) AS orders
    FROM fact_order_items i
    JOIN dim_product p
        ON i.product_key = p.product_key
    GROUP BY 1
    ORDER BY revenue DESC
""").df()

st.bar_chart(
    products.head(10).set_index("category")[["revenue"]]
)

st.dataframe(
    products.head(15).style.format({
        "revenue": "R$ {:,.0f}",
        "units": "{:,.0f}",
        "orders": "{:,.0f}",
    }),
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# 4. Customer Value
# ============================================================

st.header("4. Customer Value")
st.caption(
    "Who are the highest-value customers?"
)

customers = con.sql("""
    SELECT
        c.customer_unique_id AS customer_id,
        COUNT(DISTINCT o.order_id) AS orders,
        SUM(i.total_item_value) AS revenue,
        SUM(i.total_item_value)
            / COUNT(DISTINCT o.order_id) AS avg_order_value
    FROM fact_orders o
    JOIN dim_customer c
        ON o.customer_key = c.customer_key
    JOIN fact_order_items i
        ON o.order_id = i.order_id
    GROUP BY c.customer_unique_id
    ORDER BY revenue DESC
    LIMIT 20
""").df()

st.dataframe(
    customers.style.format({
        "revenue": "R$ {:,.2f}",
        "avg_order_value": "R$ {:,.2f}",
        "orders": "{:,.0f}",
    }),
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# 5. Delivery & Operational Performance
# ============================================================

st.header("5. Delivery & Operational Performance")
st.caption(
    "Where are delays occurring in the order lifecycle?"
)

ops = con.sql("""
    SELECT
        AVG(purchase_to_approval_hours)
            AS purchase_to_approval_hours,
        AVG(approval_to_carrier_hours)
            AS approval_to_carrier_hours,
        AVG(carrier_to_customer_hours)
            AS carrier_to_customer_hours,
        AVG(purchase_to_customer_days)
            AS purchase_to_customer_days,
        AVG(purchase_to_estimated_days)
            AS purchase_to_estimated_days,
        COUNT(*) AS completed_orders
    FROM fact_orders
    WHERE purchase_to_customer_days IS NOT NULL
""").df().iloc[0]

o1, o2, o3, o4 = st.columns(4)

o1.metric(
    "Purchase → Approval",
    f"{ops['purchase_to_approval_hours']:.1f} hrs"
)

o2.metric(
    "Approval → Carrier",
    f"{ops['approval_to_carrier_hours']:.1f} hrs"
)

o3.metric(
    "Carrier → Customer",
    f"{ops['carrier_to_customer_hours']:.1f} hrs"
)

o4.metric(
    "Purchase → Delivery",
    f"{ops['purchase_to_customer_days']:.1f} days"
)

delivery = con.sql("""
    SELECT
        order_status,
        COUNT(*) AS orders
    FROM fact_orders
    GROUP BY order_status
    ORDER BY orders DESC
""").df()

st.subheader("Order Status")

st.bar_chart(
    delivery.set_index("order_status")[["orders"]]
)


# ============================================================
# Footer
# ============================================================

st.divider()

st.caption(
    "NorthStar Retail | Gold Layer | DuckDB | "
    "Executive Decision Support"
)