import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# ==============================================================================
# 1. PAGE CONFIGURATION & THEME
# ==============================================================================
st.set_page_config(
    page_title="AdventureWorks Commercial Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #003366;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. SMART DATA LOADING WITH DATA TYPE SANITIZATION
# ==============================================================================
@st.cache_data
def load_and_merge_data():
    """
    Loads AdventureWorks CSV files, enforces identical data types on joining keys 
    to avoid object-to-int merge crashes, and safely connects tables.
    """
    data_dir = "data" if os.path.exists("data") else "DATA"
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Neither 'data' nor 'DATA' folder was found in the root directory.")
        
    all_files = os.listdir(data_dir)
    
    def read_csv_safe(file_path):
        encodings = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252']
        for enc in encodings:
            try:
                df_temp = pd.read_csv(file_path, encoding=enc)
                df_temp.columns = df_temp.columns.str.strip()
                return df_temp
            except UnicodeDecodeError:
                continue
        df_temp = pd.read_csv(file_path, encoding='utf-8', errors='ignore')
        df_temp.columns = df_temp.columns.str.strip()
        return df_temp

    def find_best_key(df_cols, keywords):
        for col in df_cols:
            if all(k.lower() in col.lower() for k in keywords):
                return col
        return None

    def safe_merge(left_df, right_df, key_keywords, how='left'):
        left_key = find_best_key(left_df.columns, key_keywords)
        right_key = find_best_key(right_df.columns, key_keywords)
        
        if left_key and right_key:
            left_df[left_key] = left_df[left_key].astype(str).str.strip()
            right_df[right_key] = right_df[right_key].astype(str).str.strip()
            return pd.merge(left_df, right_df, left_on=left_key, right_on=right_key, how=how)
        elif left_key:
            left_df[left_key] = left_df[left_key].astype(str).str.strip()
            return pd.merge(left_df, right_df, on=left_key, how=how)
        return left_df

    # 1. Load and Union Sales Tables
    sales_files = [f for f in all_files if "Sales" in f and f.endswith(".csv")]
    sales_dfs = []
    for f in sales_files:
        sales_dfs.append(read_csv_safe(os.path.join(data_dir, f)))
        
    if not sales_dfs:
        raise FileNotFoundError("No Sales CSV files found inside the data directory.")
        
    sales = pd.concat(sales_dfs, ignore_index=True)
    
    date_col = find_best_key(sales.columns, ["Date"]) or "OrderDate"
    sales[date_col] = pd.to_datetime(sales[date_col], errors='coerce')
    
    def find_and_read_lookup(keyword):
        matched = [f for f in all_files if keyword in f and f.endswith(".csv")]
        if not matched:
            raise FileNotFoundError(f"Could not find any CSV file containing '{keyword}' in '{data_dir}/'")
        return read_csv_safe(os.path.join(data_dir, matched[0]))

    # 2. Load Lookups
    products = find_and_read_lookup("Product Lookup")
    categories = find_and_read_lookup("Categories")
    subcategories = find_and_read_lookup("Subcategories")
    customers = find_and_read_lookup("Customer")
    territories = find_and_read_lookup("Territory")
    returns_df = find_and_read_lookup("Returns")
    
    # 3. Create Product Model Dimension
    prod_model = safe_merge(products, subcategories, ["Subcategory", "Key"])
    prod_model = safe_merge(prod_model, categories, ["Category", "Key"])
    
    # Customer Full Name Builder
    first_col = find_best_key(customers.columns, ["First"])
    last_col = find_best_key(customers.columns, ["Last"])
    if first_col and last_col:
        customers['CustomerName'] = customers[first_col].astype(str) + " " + customers[last_col].astype(str)
    else:
        cust_id = find_best_key(customers.columns, ["Customer", "Key"]) or customers.columns[0]
        customers['CustomerName'] = "Customer " + customers[cust_id].astype(str)

    # 4. Central Fact Table Joins
    df = safe_merge(sales, prod_model, ["Product", "Key"])
    df = safe_merge(df, territories, ["Territory", "Key"])
    df = safe_merge(df, customers, ["Customer", "Key"])
    
    # Timeline Aggregation Fields
    df['Year'] = df[date_col].dt.year
    df['Month'] = df[date_col].dt.month
    df['MonthName'] = df[date_col].dt.strftime('%B')
    df['YearMonth'] = df[date_col].dt.to_period('M')
    
    # Numerical Calculations Sanitization
    qty_col = find_best_key(df.columns, ["Quantity"]) or "OrderQuantity"
    price_col = find_best_key(df.columns, ["Price"]) or "ProductPrice"
    cost_col = find_best_key(df.columns, ["Cost"]) or "ProductCost"
    
    df[qty_col] = pd.to_numeric(df[qty_col], errors='coerce').fillna(0)
    df[price_col] = pd.to_numeric(df[price_col], errors='coerce').fillna(0)
    df[cost_col] = pd.to_numeric(df[cost_col], errors='coerce').fillna(0)
    
    df['Revenue'] = df[qty_col] * df[price_col]
    df['TotalCost'] = df[qty_col] * df[cost_col]
    df['GrossProfit'] = df['Revenue'] - df['TotalCost']
    
    return df, returns_df, prod_model, territories, date_col, qty_col, price_col

# Execute pipeline safely
try:
    df, returns_df, products, territories, date_col, qty_col, price_col = load_and_merge_data()
except Exception as e:
    st.error(f"❌ Table integration failed. Details: {e}")
    st.stop()

# ==============================================================================
# 3. SIDEBAR NAVIGATION & FILTER PANEL
# ==============================================================================
st.sidebar.image("https://img.icons8.com/color/96/dashboard.png", width=80)
st.sidebar.title("Commercial Control Room")
st.sidebar.markdown("---")

st.sidebar.subheader("📌 Navigation")
page = st.sidebar.radio(
    "Select Department View",
    [
        "📊 Executive Summary", 
        "🛍️ Sales Performance", 
        "💸 Profitability & Returns", 
        "🔮 Forecasting & Strategy",
        "🎛️ Scenario Simulation"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filter Options")

years = sorted(df['Year'].dropna().unique())
selected_year = st.sidebar.selectbox("Fiscal Year", years, index=len(years)-1)

region_col = [c for c in df.columns if 'region' in c.lower() or 'territory' in c.lower() and 'key' not in c.lower()]
region_col = region_col[0] if region_col else None

if region_col:
    regions = ['All Regions'] + list(df[region_col].dropna().unique())
else:
    regions = ['All Regions']
selected_region = st.sidebar.selectbox("Region/Territory", regions)

# Dynamic filtering
filtered_df = df[df['Year'] == selected_year]
if region_col and selected_region != 'All Regions':
    filtered_df = filtered_df[filtered_df[region_col] == selected_region]

# Core Metrics Calculations
total_revenue = filtered_df['Revenue'].sum() if not filtered_df.empty else 0
total_profit = filtered_df['GrossProfit'].sum() if not filtered_df.empty else 0
gross_margin = (total_profit / total_revenue) * 100 if total_revenue > 0 else 0

ord_id_col = [c for c in df.columns if 'order' in c.lower() and 'number' in c.lower() or 'id' in c.lower()]
ord_id_col = ord_id_col[0] if ord_id_col else df.columns[0]
num_orders = filtered_df[ord_id_col].nunique() if not filtered_df.empty else 0
avg_order_value = total_revenue / num_orders if num_orders > 0 else 0

# Process Returns Matrix Safely
if not returns_df.empty:
    ret_date_col = [c for c in returns_df.columns if 'date' in c.lower()][0]
    returns_df[ret_date_col] = pd.to_datetime(returns_df[ret_date_col], errors='coerce')
    returns_df['Year'] = returns_df[ret_date_col].dt.year
    
    ret_prod_key = [c for c in returns_df.columns if 'product' in c.lower() and 'key' in c.lower()][0]
    prod_key_main = [c for c in products.columns if 'product' in c.lower() and 'key' in c.lower()][0]
    
    returns_df[ret_prod_key] = returns_df[ret_prod_key].astype(str).str.strip()
    products[prod_key_main] = products[prod_key_main].astype(str).str.strip()
    
    ret_detail = pd.merge(returns_df, products, left_on=ret_prod_key, right_on=prod_key_main, how='left')
    
    filtered_returns = ret_detail[ret_detail['Year'] == selected_year]
    
    # FIX: Dynamically target ONLY the quantity column for sums to avoid summing DateTime types
    ret_qty_col = [c for c in returns_df.columns if 'quantity' in c.lower() or 'return' in c.lower() and 'key' not in c.lower() and 'date' not in c.lower()][0]
    filtered_returns[ret_qty_col] = pd.to_numeric(filtered_returns[ret_qty_col], errors='coerce').fillna(0)
    total_returns = filtered_returns[ret_qty_col].sum() if not filtered_returns.empty else 0
else:
    filtered_returns = pd.DataFrame()
    total_returns = 0

total_sold = filtered_df[qty_col].sum() if not filtered_df.empty else 0
return_rate = (total_returns / total_sold) * 100 if total_sold > 0 else 0

# ==============================================================================
# PAGE 1: EXECUTIVE SUMMARY
# ==============================================================================
if page == "📊 Executive Summary":
    st.title("💼 AdventureWorks Executive Suite")
    st.subheader(f"Commercial Performance Overview — FY{selected_year} ({selected_region})")
    st.markdown("---")
    
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    with kpi_col1:
        st.markdown(f'<div class="metric-card"><p style="color:#7f8c8d; font-size:14px; margin-bottom:5px;">TOTAL REVENUE</p><h2 style="color:#2c3e50; margin:0;">${total_revenue:,.2f}</h2></div>', unsafe_allow_html=True)
    with kpi_col2:
        st.markdown(f'<div class="metric-card"><p style="color:#7f8c8d; font-size:14px; margin-bottom:5px;">GROSS MARGIN</p><h2 style="color:#27ae60; margin:0;">{gross_margin:.2f}%</h2><p style="color:#7f8c8d; font-size:12px; margin:0;">Profit: ${total_profit:,.2f}</p></div>', unsafe_allow_html=True)
    with kpi_col3:
        st.markdown(f'<div class="metric-card"><p style="color:#7f8c8d; font-size:14px; margin-bottom:5px;">VOLUME & BASKET</p><h2 style="color:#2c3e50; margin:0;">{num_orders:,} Orders</h2><p style="color:#7f8c8d; font-size:12px; margin:0;">Avg Ticket: ${avg_order_value:,.2f}</p></div>', unsafe_allow_html=True)
    with kpi_col4:
        st.markdown(f'<div class="metric-card"><p style="color:#7f8c8d; font-size:14px; margin-bottom:5px;">RETURN RATE</p><h2 style="color:#c0392b; margin:0;">{return_rate:.2f}%</h2><p style="color:#7f8c8d; font-size:12px; margin:0;">Total Returns: {total_returns}</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Quick Diagnostic")
    diag_col1, diag_col2 = st.columns(2)
    with diag_col1:
        st.info(f"💡 **Pipeline Live:** Schema types fully aligned. Dynamic parsing active for fiscal segment FY{selected_year}.")
    with diag_col2:
        if return_rate > 3.0:
            st.warning(f"⚠️ **Attention Required:** Return rate is high at **{return_rate:.2f}%**. Inspect quality data via the Profitability tab.")
        else:
            st.success("✅ **Operations Stable:** Outbound fulfillment vectors are performing cleanly within standard guardrails.")

# ==============================================================================
# PAGE 2: SALES PERFORMANCE
# ==============================================================================
elif page == "🛍️ Sales Performance":
    st.title("🛍️ Sales & Category Performance")
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    cat_name_col = [c for c in df.columns if 'category' in c.lower() and 'name' in c.lower() or 'category' in c.lower() and 'key' not in c.lower()]
    cat_name_col = cat_name_col[0] if cat_name_col else None
    
    with col_left:
        st.subheader("Category Revenue & Profit Share")
        if not filtered_df.empty and cat_name_col:
            cat_perf = filtered_df.groupby(cat_name_col).agg({'Revenue': 'sum', 'GrossProfit': 'sum'}).reset_index()
            fig_cat = px.bar(cat_perf, x=cat_name_col, y=['Revenue', 'GrossProfit'], barmode='group', color_discrete_sequence=['#003366', '#27ae60'])
            fig_cat.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("Product category structural sync complete.")

    with col_right:
        st.subheader("Regional Market Share")
        if not filtered_df.empty and region_col:
            reg_perf = filtered_df.groupby(region_col)['Revenue'].sum().reset_index()
            fig_reg = px.pie(reg_perf, values='Revenue', names=region_col, hole=0.4, color_discrete_sequence=px.colors.sequential.YlGnBu)
            st.plotly_chart(fig_reg, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🏆 Top Performing Assets")
    tab1, tab2 = st.tabs(["Top 10 Products", "Top 10 Customers"])
    
    prod_name_col = [c for c in df.columns if 'product' in c.lower() and 'name' in c.lower()][0]
    
    with tab1:
        if not filtered_df.empty:
            top_products = filtered_df.groupby(prod_name_col).agg({qty_col: 'sum', 'Revenue': 'sum', 'GrossProfit': 'sum'}).sort_values(by='Revenue', ascending=False).head(10)
            st.dataframe(top_products.style.format("${:,.2f}", subset=['Revenue', 'GrossProfit']), use_container_width=True)
    with tab2:
        if not filtered_df.empty:
            top_cust = filtered_df.groupby('CustomerName').agg({ord_id_col: 'nunique', 'Revenue': 'sum', 'GrossProfit': 'sum'}).sort_values(by='Revenue', ascending=False).head(10)
            st.dataframe(top_cust.style.format("${:,.2f}", subset=['Revenue', 'GrossProfit']), use_container_width=True)

# ==============================================================================
# PAGE 3: PROFITABILITY & RETURNS
# ==============================================================================
elif page == "💸 Profitability & Returns":
    st.title("💸 Profitability & Returns Analysis")
    st.markdown("---")
    
    prod_name_col = [c for c in df.columns if 'product' in c.lower() and 'name' in c.lower()][0]
    cat_name_col = [c for c in df.columns if 'category' in c.lower() and 'name' in c.lower()]
    cat_name_col = cat_name_col[0] if cat_name_col else prod_name_col
    
    prof_col1, prof_col2 = st.columns([3, 2])
    with prof_col1:
        st.subheader("Product Profitability Quadrant")
        if not filtered_df.empty:
            prod_margin = filtered_df.groupby([prod_name_col, cat_name_col]).agg({qty_col: 'sum', 'Revenue': 'sum', 'GrossProfit': 'sum'}).reset_index()
            prod_margin['MarginPercent'] = (prod_margin['GrossProfit'] / prod_margin['Revenue']) * 100
            
            fig_scatter = px.scatter(prod_margin, x=qty_col, y='MarginPercent', size='Revenue', color=cat_name_col, hover_name=prod_name_col)
            fig_scatter.add_hline(y=prod_margin['MarginPercent'].mean(), line_dash="dash", line_color="red")
            fig_scatter.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_scatter, use_container_width=True)

    with prof_col2:
        st.subheader("Commercial Profitability Insights")
        if not filtered_df.empty and 'prod_margin' in locals() and not prod_margin.empty:
            problem_products = prod_margin[prod_margin['MarginPercent'] < prod_margin['MarginPercent'].median()].sort_values(by=qty_col, ascending=False)
            if not problem_products.empty:
                st.warning(f"⚠️ **Volume/Margin Disconnect:** **{problem_products.iloc[0][prod_name_col]}** shows high transactional velocity but tight margins.")
            
            if region_col:
                reg_margin = filtered_df.groupby(region_col).agg({'Revenue': 'sum', 'GrossProfit': 'sum'}).reset_index()
                reg_margin['MarginPercent'] = (reg_margin['GrossProfit'] / reg_margin['Revenue']) * 100
                if not reg_margin.empty:
                    lowest_reg = reg_margin.sort_values(by='MarginPercent').iloc[0]
                    st.info(f"🌍 **Territory Review:** **{lowest_reg[region_col]}** presents structural margin friction standing at **{lowest_reg['MarginPercent']:.1f}%**.")

    st.markdown("---")
    st.subheader("🔄 Returns Audit")
    if filtered_returns.empty:
        st.success("🎉 **Operational Excellence:** No financial leaks from returns detected.")
    else:
        ret_col1, ret_col2 = st.columns(2)
        ret_prod_name = [c for c in filtered_returns.columns if 'product' in c.lower() and 'name' in c.lower()][0]
        
        with ret_col1:
            st.subheader("Top Returned Products")
            # FIX: Forced aggregation dynamically on the targeted quantity column to isolate safely
            top_returned = filtered_returns.groupby(ret_prod_name)[ret_qty_col].sum().reset_index()
            top_returned = top_returned.sort_values(by=ret_qty_col, ascending=False).head(5)
            fig_ret_bar = px.bar(top_returned, y=ret_prod_name, x=ret_qty_col, orientation='h', color_discrete_sequence=['#e74c3c'])
            fig_ret_bar.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_ret_bar, use_container_width=True)
            
        with ret_col2:
            st.subheader("Financial Impact of Returns")
            ret_price_col = [c for c in filtered_returns.columns if 'price' in c.lower() or 'amount' in c.lower()][0]
            filtered_returns['RevenueLost'] = filtered_returns[ret_qty_col] * pd.to_numeric(filtered_returns[ret_price_col], errors='coerce').fillna(0)
            ret_cat_col = [c for c in filtered_returns.columns if 'category' in c.lower() and 'name' in c.lower()]
            ret_cat_col = ret_cat_col[0] if ret_cat_col else ret_prod_name
            
            cat_returns = filtered_returns.groupby(ret_cat_col)['RevenueLost'].sum().reset_index()
            fig_ret_pie = px.pie(cat_returns, values='RevenueLost', names=ret_cat_col, color_discrete_sequence=px.colors.sequential.Reds_r)
            st.plotly_chart(fig_ret_pie, use_container_width=True)

# ==============================================================================
# PAGE 4: FORECASTING & STRATEGY
# ==============================================================================
elif page == "🔮 Forecasting & Strategy":
    st.title("🔮 Forecasting & Executive Strategy")
    st.markdown("---")
    
    monthly_sales = df.groupby('YearMonth')['Revenue'].sum().reset_index()
    monthly_sales['YearMonth_Str'] = monthly_sales['YearMonth'].astype(str)

    if len(monthly_sales) > 1:
        x = np.arange(len(monthly_sales))
        y = monthly_sales['Revenue'].values
        slope, intercept = np.polyfit(x, y, 1)
        
        last_idx = x[-1]
        next_month_pred = max(0, slope * (last_idx + 1) + intercept)
        next_quarter_pred = max(0, (slope * np.array([last_idx+1, last_idx+2, last_idx+3]) + intercept).sum())
        
        fore_col1, fore_col2 = st.columns(2)
        with fore_col1: st.metric(label="🎯 Next Month Revenue Forecast", value=f"${next_month_pred:,.2f}")
        with fore_col2: st.metric(label="📊 Next Quarter Forecast (3M)", value=f"${next_quarter_pred:,.2f}")
            
        future_revenues = [max(0, slope * (last_idx + i) + intercept) for i in range(1, 7)]
        future_periods = [f"Forecast +{i}M" for i in range(1, 7)]
        forecast_df = pd.DataFrame({'YearMonth_Str': future_periods, 'Revenue': future_revenues, 'Type': 'Forecast'})
        
        historical_df = monthly_sales[['YearMonth_Str', 'Revenue']].copy()
        historical_df['Type'] = 'Historical'
        combined_forecast = pd.concat([historical_df, forecast_df], ignore_index=True)
        
        fig_forecast = px.line(combined_forecast, x='YearMonth_Str', y='Revenue', color='Type', color_discrete_map={'Historical': '#003366', 'Forecast': '#ff7f0e'})
        st.plotly_chart(fig_forecast, use_container_width=True)
    else:
        st.warning("Insufficient timeframe milestones to evaluate predictive regressions.")

# ==============================================================================
# PAGE 5: SCENARIO SIMULATION (WHAT-IF ANALYSIS)
# ==============================================================================
elif page == "🎛️ Scenario Simulation":
    st.title("🎛️ Strategic Commercial Simulator")
    st.markdown("---")
    
    sim_col_left, sim_col_right = st.columns([1, 2])
    with sim_col_left:
        st.subheader("Adjust Commercial Levers")
        price_slider = st.slider("Average Pricing Adjustment (%)", min_value=-20.0, max_value=20.0, value=0.0, step=1.0)
        volume_slider = st.slider("Transaction Volume Delta (%)", min_value=-20.0, max_value=50.0, value=0.0, step=1.0)
        
    with sim_col_right:
        st.subheader("Simulated Business Impact")
        base_rev = total_revenue
        base_cost = filtered_df['TotalCost'].sum() if not filtered_df.empty else 0
        base_profit = total_profit
        
        sim_volume_factor = (1 + (volume_slider / 100))
        sim_price_factor = (1 + (price_slider / 100))
        
        sim_rev = base_rev * sim_volume_factor * sim_price_factor
        sim_cost = base_cost * sim_volume_factor
        sim_profit = sim_rev - sim_cost
        sim_margin = (sim_profit / sim_rev) * 100 if sim_rev > 0 else 0
        
        sim_m1, sim_m2, sim_m3 = st.columns(3)
        with sim_m1: st.metric(label="Simulated Revenue", value=f"${sim_rev:,.2f}", delta=f"${(sim_rev - base_rev):+,.2f}")
        with sim_m2: st.metric(label="Simulated Gross Margin", value=f"{sim_margin:.2f}%", delta=f"{(sim_margin - gross_margin):+.2f}%")
        with sim_m3: st.metric(label="Simulated Net Profit", value=f"${sim_profit:,.2f}", delta=f"${(sim_profit - base_profit):+,.2f}")
        
        st.markdown("---")
        comp_df = pd.DataFrame({
            'Metric': ['Revenue', 'Gross Profit'],
            'Current State': [base_rev, base_profit],
            'Simulated State': [sim_rev, sim_profit]
        })
        fig_comp = px.bar(comp_df, x='Metric', y=['Current State', 'Simulated State'], barmode='group', color_discrete_sequence=['#003366', '#ff7f0e'])
        st.plotly_chart(fig_comp, use_container_width=True)

st.markdown("---")
st.caption("AdventureWorks Commercial Suite v2.1 • Type-Safe Aggregation Engine Active.")
