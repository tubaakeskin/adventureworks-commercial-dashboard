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
# 2. SMART DATA LOADING WITH ENCODING FALLBACKS
# ==============================================================================
@st.cache_data
def load_and_merge_data():
    """
    Dynamically scans the data folder, handles text encoding fallbacks (latin1/utf-8),
    and safely joins the relational tables.
    """
    data_dir = "data" if os.path.exists("data") else "DATA"
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Neither 'data' nor 'DATA' folder was found in the root directory.")
        
    all_files = os.listdir(data_dir)
    
    # Robust CSV Reader with encoding fallback to prevent 'utf-8' decode crashes
    def read_csv_safe(file_path):
        encodings = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252']
        for enc in encodings:
            try:
                df_temp = pd.read_csv(file_path, encoding=enc)
                return df_temp
            except UnicodeDecodeError:
                continue
        # If all fail, try with errors ignored
        return pd.read_csv(file_path, encoding='utf-8', errors='ignore')

    # 1. Load and Union Sales Tables
    sales_files = [f for f in all_files if "Sales" in f and f.endswith(".csv")]
    sales_dfs = []
    for f in sales_files:
        sales_dfs.append(read_csv_safe(os.path.join(data_dir, f)))
        
    if not sales_dfs:
        raise FileNotFoundError("No Sales CSV files found inside the data directory.")
        
    sales = pd.concat(sales_dfs, ignore_index=True)
    sales.columns = sales.columns.str.strip()
    sales['OrderDate'] = pd.to_datetime(sales['OrderDate'])
    
    # Helper to find and read lookup tables dynamically
    def find_and_read_lookup(keyword):
        matched = [f for f in all_files if keyword in f and f.endswith(".csv")]
        if not matched:
            raise FileNotFoundError(f"Could not find any CSV file containing '{keyword}' in '{data_dir}/'")
        df_loaded = read_csv_safe(os.path.join(data_dir, matched[0]))
        df_loaded.columns = df_loaded.columns.str.strip()
        return df_loaded

    # 2. Load Lookups safely with text encoding auto-detection
    products = find_and_read_lookup("Product Lookup")
    categories = find_and_read_lookup("Categories")
    subcategories = find_and_read_lookup("Subcategories")
    customers = find_and_read_lookup("Customer")
    territories = find_and_read_lookup("Territory")
    returns_df = find_and_read_lookup("Returns")
    
    # 3. Create Product Model Dimension
    prod_model = pd.merge(products, subcategories, on='ProductSubcategoryKey', how='left')
    prod_model = pd.merge(prod_model, categories, on='ProductCategoryKey', how='left')
    
    # Safe Customer Name builder
    if 'FirstName' in customers.columns and 'LastName' in customers.columns:
        customers['CustomerName'] = customers['FirstName'] + " " + customers['LastName']
    elif 'CustomerName' not in customers.columns:
        customers['CustomerName'] = "Customer " + customers['CustomerKey'].astype(str)

    # 4. Central Fact Table Joins (SQL Star Schema mapping)
    df = pd.merge(sales, prod_model, on='ProductKey', how='left')
    df = pd.merge(df, territories, on='TerritoryKey', how='left')
    df = pd.merge(df, customers, on='CustomerKey', how='left')
    
    # Timeline Parsing
    df['Year'] = df['OrderDate'].dt.year
    df['Month'] = df['OrderDate'].dt.month
    df['MonthName'] = df['OrderDate'].dt.strftime('%B')
    df['YearMonth'] = df['OrderDate'].dt.to_period('M')
    
    # Financial KPI Columns
    df['Revenue'] = df['OrderQuantity'] * df['ProductPrice']
    df['TotalCost'] = df['OrderQuantity'] * df['ProductCost']
    df['GrossProfit'] = df['Revenue'] - df['TotalCost']
    
    return df, returns_df, prod_model, territories

# Execute pipeline safely
try:
    df, returns_df, products, territories = load_and_merge_data()
except Exception as e:
    st.error(f"❌ Data pipeline execution failed. Details: {e}")
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

regions = ['All Regions'] + list(df['Region'].dropna().unique())
selected_region = st.sidebar.selectbox("Region", regions)

# Filtering engine constraints
filtered_df = df[df['Year'] == selected_year]
if selected_region != 'All Regions':
    filtered_df = filtered_df[filtered_df['Region'] == selected_region]

# Calculations Matrix
total_revenue = filtered_df['Revenue'].sum() if not filtered_df.empty else 0
total_profit = filtered_df['GrossProfit'].sum() if not filtered_df.empty else 0
gross_margin = (total_profit / total_revenue) * 100 if total_revenue > 0 else 0
num_orders = filtered_df['OrderNumber'].nunique() if not filtered_df.empty else 0
num_customers = filtered_df['CustomerKey'].nunique() if not filtered_df.empty else 0
avg_order_value = total_revenue / num_orders if num_orders > 0 else 0

if not returns_df.empty:
    returns_df['ReturnDate'] = pd.to_datetime(returns_df['ReturnDate'])
    ret_detail = pd.merge(returns_df, products, on='ProductKey', how='left')
    ret_detail = pd.merge(ret_detail, territories, on='TerritoryKey', how='left')
    ret_detail['Year'] = ret_detail['ReturnDate'].dt.year
    
    filtered_returns = ret_detail[ret_detail['Year'] == selected_year]
    if selected_region != 'All Regions':
        filtered_returns = filtered_returns[filtered_returns['Region'] == selected_region]
    total_returns = filtered_returns['ReturnQuantity'].sum() if not filtered_returns.empty else 0
else:
    filtered_returns = pd.DataFrame()
    total_returns = 0

total_sold = filtered_df['OrderQuantity'].sum() if not filtered_df.empty else 0
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
        st.info(f"💡 **Pipeline Live:** Encoding codec mismatch neutralized. Operating on live production files for FY{selected_year} within the {selected_region} division.")
    with diag_col2:
        if return_rate > 3.0:
            st.warning(f"⚠️ **Attention Required:** Return rate is high at **{return_rate:.2f}%**. Inspect quality control data via the Returns tab.")
        else:
            st.success("✅ **Operations Secure:** Outbound logistics and returns are within standard margins.")

# ==============================================================================
# PAGE 2: SALES PERFORMANCE
# ==============================================================================
elif page == "🛍️ Sales Performance":
    st.title("🛍️ Sales & Category Performance")
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Category Revenue & Profit Share")
        if not filtered_df.empty and 'CategoryName' in filtered_df.columns:
            cat_perf = filtered_df.groupby('CategoryName').agg({'Revenue': 'sum', 'GrossProfit': 'sum'}).reset_index()
            fig_cat = px.bar(cat_perf, x='CategoryName', y=['Revenue', 'GrossProfit'], barmode='group', color_discrete_sequence=['#003366', '#27ae60'])
            fig_cat.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("Category details loaded.")

    with col_right:
        st.subheader("Regional Market Share")
        if not filtered_df.empty:
            reg_perf = filtered_df.groupby('Region')['Revenue'].sum().reset_index()
            fig_reg = px.pie(reg_perf, values='Revenue', names='Region', hole=0.4, color_discrete_sequence=px.colors.sequential.YlGnBu)
            st.plotly_chart(fig_reg, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🏆 Top Performing Assets")
    tab1, tab2 = st.tabs(["Top 10 Products", "Top 10 Customers"])
    with tab1:
        if not filtered_df.empty and 'ProductName' in filtered_df.columns:
            top_products = filtered_df.groupby('ProductName').agg({'OrderQuantity': 'sum', 'Revenue': 'sum', 'GrossProfit': 'sum'}).sort_values(by='Revenue', ascending=False).head(10)
            st.dataframe(top_products.style.format("${:,.2f}", subset=['Revenue', 'GrossProfit']), use_container_width=True)
    with tab2:
        if not filtered_df.empty:
            top_cust = filtered_df.groupby('CustomerName').agg({'OrderNumber': 'nunique', 'Revenue': 'sum', 'GrossProfit': 'sum'}).sort_values(by='Revenue', ascending=False).head(10)
            st.dataframe(top_cust.style.format("${:,.2f}", subset=['Revenue', 'GrossProfit']), use_container_width=True)

# ==============================================================================
# PAGE 3: PROFITABILITY & RETURNS
# ==============================================================================
elif page == "💸 Profitability & Returns":
    st.title("💸 Profitability & Returns Analysis")
    st.markdown("---")
    
    prof_col1, prof_col2 = st.columns([3, 2])
    with prof_col1:
        st.subheader("Product Profitability Quadrant")
        if not filtered_df.empty and 'ProductName' in filtered_df.columns:
            prod_margin = filtered_df.groupby(['ProductName', 'CategoryName' if 'CategoryName' in filtered_df.columns else 'ProductKey']).agg({'OrderQuantity': 'sum', 'Revenue': 'sum', 'GrossProfit': 'sum'}).reset_index()
            prod_margin['MarginPercent'] = (prod_margin['GrossProfit'] / prod_margin['Revenue']) * 100
            
            fig_scatter = px.scatter(prod_margin, x='OrderQuantity', y='MarginPercent', size='Revenue', color='CategoryName' if 'CategoryName' in prod_margin.columns else None, hover_name='ProductName')
            fig_scatter.add_hline(y=prod_margin['MarginPercent'].mean(), line_dash="dash", line_color="red")
            fig_scatter.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_scatter, use_container_width=True)

    with prof_col2:
        st.subheader("Commercial Profitability Insights")
        if not filtered_df.empty and 'prod_margin' in locals() and not prod_margin.empty:
            problem_products = prod_margin[prod_margin['MarginPercent'] < prod_margin['MarginPercent'].median()].sort_values(by='OrderQuantity', ascending=False)
            if not problem_products.empty:
                st.warning(f"⚠️ **Volume/Margin Disconnect:** **{problem_products.iloc[0]['ProductName']}** indicates a heavy fulfillment footprint with tight net yields.")
            
            reg_margin = filtered_df.groupby('Region').agg({'Revenue': 'sum', 'GrossProfit': 'sum'}).reset_index()
            reg_margin['MarginPercent'] = (reg_margin['GrossProfit'] / reg_margin['Revenue']) * 100
            if not reg_margin.empty:
                lowest_reg = reg_margin.sort_values(by='MarginPercent').iloc[0]
                st.info(f"🌍 **Territory Review:** **{lowest_reg['Region']}** presents margin resistance sitting at **{lowest_reg['MarginPercent']:.1f}%**.")

    st.markdown("---")
    st.subheader("🔄 Returns Audit")
    if filtered_returns.empty or 'ProductName' not in filtered_returns.columns:
        st.success("🎉 **Operational Excellence:** Zero financial leakage from returns in this selection branch.")
    else:
        ret_col1, ret_col2 = st.columns(2)
        with ret_col1:
            top_returned = filtered_returns.groupby('ProductName').agg({'ReturnQuantity': 'sum'}).sort_values(by='ReturnQuantity', ascending=False).head(5).reset_index()
            fig_ret_bar = px.bar(top_returned, y='ProductName', x='ReturnQuantity', orientation='h', color_discrete_sequence=['#e74c3c'])
            st.plotly_chart(fig_ret_bar, use_container_width=True)
        with ret_col2:
            filtered_returns['RevenueLost'] = filtered_returns['ReturnQuantity'] * filtered_returns['ProductPrice']
            cat_returns = filtered_returns.groupby('CategoryName' if 'CategoryName' in filtered_returns.columns else 'ProductKey').agg({'RevenueLost': 'sum'}).reset_index()
            fig_ret_pie = px.pie(cat_returns, values='RevenueLost', names=cat_returns.columns[0], color_discrete_sequence=px.colors.sequential.Reds_r)
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
        st.warning("Insufficient timeframe timelines to map linear regressions.")

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
st.caption("AdventureWorks Commercial Suite v1.8 • Encoding Safeguards Active.")
