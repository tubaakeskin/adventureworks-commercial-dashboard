import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==============================================================================
# 1. PAGE CONFIGURATION & THEME
# ==============================================================================
st.set_page_config(
    page_title="AdventureWorks Commercial Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for executive look
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
# 2. DATA LOADING & INTEGRATION (SQL JOIN LOGIC)
# ==============================================================================
@st.cache_data
def load_and_merge_data():
    """
    Loads AdventureWorks tables and merges them into a single analytical data model.
    Equivalent to SQL JOINs.
    """
    np.random.seed(42)
    n_rows = 1000
    
    # Calendar Table
    calendar = pd.DataFrame({
        'DateKey': pd.date_range(start='2024-01-01', periods=365*2, freq='D')
    })
    calendar['Year'] = calendar['DateKey'].dt.year
    calendar['Month'] = calendar['DateKey'].dt.month
    calendar['MonthName'] = calendar['DateKey'].dt.strftime('%B')
    
    # Product Table
    products = pd.DataFrame({
        'ProductKey': range(1, 21),
        'ProductName': [f"Product {i}" for i in range(1, 21)],
        'Category': ['Bikes', 'Components', 'Clothing', 'Accessories'] * 5,
        'Subcategory': ['Road Bikes', 'Mountain Bikes', 'Helmets', 'Tires', 'Chains'] * 4,
        'ProductCost': np.random.uniform(10, 500, 20),
        'ProductPrice': np.random.uniform(20, 1000, 20)
    })
    products['ProductPrice'] = products['ProductCost'] + np.random.uniform(10, 200, 20)
    
    # Territory Table
    territories = pd.DataFrame({
        'TerritoryKey': range(1, 6),
        'Region': ['Northwest', 'Northeast', 'Southwest', 'Southeast', 'Canada'],
        'Country': ['United States', 'United States', 'United States', 'United States', 'Canada']
    })
    
    # Customer Table
    customers = pd.DataFrame({
        'CustomerKey': range(100, 200),
        'CustomerName': [f"Customer {i}" for i in range(100, 200)]
    })
    
    # Sales Table
    sales = pd.DataFrame({
        'OrderDate': np.random.choice(calendar['DateKey'], n_rows),
        'ProductKey': np.random.choice(products['ProductKey'], n_rows),
        'CustomerKey': np.random.choice(customers['CustomerKey'], n_rows),
        'TerritoryKey': np.random.choice(territories['TerritoryKey'], n_rows),
        'OrderQuantity': np.random.randint(1, 5, n_rows),
        'OrderNumber': [f"SO{i}" for i in range(10000, 10000 + n_rows)]
    })
    
    # Returns Table
    returns_df = pd.DataFrame({
        'ReturnDate': np.random.choice(calendar['DateKey'], 100),
        'ProductKey': np.random.choice(products['ProductKey'], 100),
        'TerritoryKey': np.random.choice(territories['TerritoryKey'], 100),
        'ReturnQuantity': np.random.randint(1, 2, 100)
    })
    
    # SQL-LIKE MERGE (JOIN)
    df = pd.merge(sales, products, on='ProductKey', how='left')
    df = pd.merge(df, territories, on='TerritoryKey', how='left')
    df = pd.merge(df, customers, on='CustomerKey', how='left')
    
    df['Year'] = df['OrderDate'].dt.year
    df['Month'] = df['OrderDate'].dt.month
    df['MonthName'] = df['OrderDate'].dt.strftime('%B')
    df['YearMonth'] = df['OrderDate'].dt.to_period('M')
    
    df['Revenue'] = df['OrderQuantity'] * df['ProductPrice']
    df['TotalCost'] = df['OrderQuantity'] * df['ProductCost']
    df['GrossProfit'] = df['Revenue'] - df['TotalCost']
    
    return df, returns_df, products, territories

# Load data
df, returns_df, products, territories = load_and_merge_data()

# ==============================================================================
# 3. SIDEBAR NAVIGATION & FILTER PANEL
# ==============================================================================
st.sidebar.image("https://img.icons8.com/color/96/dashboard.png", width=80)
st.sidebar.title("Commercial Control Room")
st.sidebar.markdown("---")

# 1. NAVIGATION MULTIPAGE MENU
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

# Date Filters
years = sorted(df['Year'].unique())
selected_year = st.sidebar.selectbox("Fiscal Year", years, index=len(years)-1)

# Region Filters
regions = ['All Regions'] + list(df['Region'].unique())
selected_region = st.sidebar.selectbox("Region", regions)

# Filter Data Model based on selection
filtered_df = df[df['Year'] == selected_year]
if selected_region != 'All Regions':
    filtered_df = filtered_df[filtered_df['Region'] == selected_region]

# Global Calculations (Available on all pages)
total_revenue = filtered_df['Revenue'].sum() if not filtered_df.empty else 0
total_profit = filtered_df['GrossProfit'].sum() if not filtered_df.empty else 0
gross_margin = (total_profit / total_revenue) * 100 if total_revenue > 0 else 0
num_orders = filtered_df['OrderNumber'].nunique() if not filtered_df.empty else 0
num_customers = filtered_df['CustomerKey'].nunique() if not filtered_df.empty else 0
avg_order_value = total_revenue / num_orders if num_orders > 0 else 0

# Safe Returns mapping
if not returns_df.empty:
    ret_detail = pd.merge(returns_df, products, on='ProductKey', how='left')
    ret_detail = pd.merge(ret_detail, territories, on='TerritoryKey', how='left')
    ret_detail['Year'] = pd.to_datetime(ret_detail['ReturnDate']).dt.year
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
    
    # 4 Core KPI Cards
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        st.markdown(f"""
        <div class="metric-card">
            <p style='color:#7f8c8d; font-size:14px; margin-bottom:5px;'>TOTAL REVENUE</p>
            <h2 style='color:#2c3e50; margin:0;'>${total_revenue:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col2:
        st.markdown(f"""
        <div class="metric-card">
            <p style='color:#7f8c8d; font-size:14px; margin-bottom:5px;'>GROSS MARGIN</p>
            <h2 style='color:#27ae60; margin:0;'>{gross_margin:.2f}%</h2>
            <p style='color:#7f8c8d; font-size:12px; margin:0;'>Profit: ${total_profit:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col3:
        st.markdown(f"""
        <div class="metric-card">
            <p style='color:#7f8c8d; font-size:14px; margin-bottom:5px;'>VOLUME & BASKET</p>
            <h2 style='color:#2c3e50; margin:0;'>{num_orders:,} Orders</h2>
            <p style='color:#7f8c8d; font-size:12px; margin:0;'>Avg Ticket: ${avg_order_value:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col4:
        st.markdown(f"""
        <div class="metric-card">
            <p style='color:#7f8c8d; font-size:14px; margin-bottom:5px;'>RETURN RATE</p>
            <h2 style='color:#c0392b; margin:0;'>{return_rate:.2f}%</h2>
            <p style='color:#7f8c8d; font-size:12px; margin:0;'>Total Returns: {total_returns}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Quick Summary Cards
    st.markdown("### Quick Diagnostic")
    diag_col1, diag_col2 = st.columns(2)
    with diag_col1:
        st.info(f"💡 **Selected Filters Status:** You are currently viewing data for the fiscal period **{selected_year}** filtering for the region **{selected_region}**. Change selection in the sidebar menu to update dynamically.")
    with diag_col2:
        if return_rate > 3.0:
            st.warning(f"⚠️ **Attention Needed:** Return rate is currently high (**{return_rate:.2f}%**). Please navigate to the **Profitability & Returns** page to inspect the leakage source.")
        else:
            st.success("✅ **Operations Stable:** Return margins are well within the 3.0% control boundaries. Great job in product fulfillment.")

# ==============================================================================
# PAGE 2: SALES Performance
# ==============================================================================
elif page == "🛍️ Sales Performance":
    st.title("🛍️ Sales & Category Performance")
    st.subheader(f"Category analysis and regional market shares for FY{selected_year}")
    st.markdown("---")
    
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Category Revenue & Profit Share")
        if not filtered_df.empty:
            cat_perf = filtered_df.groupby('Category').agg({
                'Revenue': 'sum',
                'GrossProfit': 'sum'
            }).reset_index()
            
            fig_cat = px.bar(
                cat_perf, 
                x='Category', 
                y=['Revenue', 'GrossProfit'],
                barmode='group',
                title="Revenue vs. Profit by Product Category",
                color_discrete_sequence=['#003366', '#27ae60']
            )
            fig_cat.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.write("No transaction data available.")

    with col_right:
        st.subheader("Regional Market Share")
        if not filtered_df.empty:
            reg_perf = filtered_df.groupby('Region')['Revenue'].sum().reset_index()
            
            fig_reg = px.pie(
                reg_perf, 
                values='Revenue', 
                names='Region', 
                hole=0.4,
                title="Revenue Distribution by Sales Territory",
                color_discrete_sequence=px.colors.sequential.YlGnBu
            )
            st.plotly_chart(fig_reg, use_container_width=True)
        else:
            st.write("No regional distribution available.")

    st.markdown("---")
    st.markdown("### 🏆 Top Performing Assets")
    tab1, tab2 = st.tabs(["Top 10 Products", "Top 10 Customers"])

    with tab1:
        if not filtered_df.empty:
            top_products = filtered_df.groupby('ProductName').agg({
                'OrderQuantity': 'sum',
                'Revenue': 'sum',
                'GrossProfit': 'sum'
            }).sort_values(by='Revenue', ascending=False).head(10)
            top_products['Revenue'] = top_products['Revenue'].apply(lambda x: f"${x:,.2f}")
            top_products['GrossProfit'] = top_products['GrossProfit'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(top_products, use_container_width=True)

    with tab2:
        if not filtered_df.empty:
            top_cust = filtered_df.groupby('CustomerName').agg({
                'OrderNumber': 'nunique',
                'Revenue': 'sum',
                'GrossProfit': 'sum'
            }).sort_values(by='Revenue', ascending=False).head(10).rename(columns={'OrderNumber': 'Total Orders'})
            top_cust['Revenue'] = top_cust['Revenue'].apply(lambda x: f"${x:,.2f}")
            top_cust['GrossProfit'] = top_cust['GrossProfit'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(top_cust, use_container_width=True)

# ==============================================================================
# PAGE 3: PROFITABILITY & RETURNS
# ==============================================================================
elif page == "💸 Profitability & Returns":
    st.title("💸 Profitability & Returns Analysis")
    st.subheader(f"Performance quadrants and leakage audits — FY{selected_year}")
    st.markdown("---")
    
    prof_col1, prof_col2 = st.columns([3, 2])

    with prof_col1:
        st.subheader("Product Profitability Quadrant")
        if not filtered_df.empty:
            prod_margin = filtered_df.groupby(['ProductName', 'Category']).agg({
                'OrderQuantity': 'sum',
                'Revenue': 'sum',
                'GrossProfit': 'sum'
            }).reset_index()
            prod_margin['MarginPercent'] = (prod_margin['GrossProfit'] / prod_margin['Revenue']) * 100
            
            fig_scatter = px.scatter(
                prod_margin,
                x='OrderQuantity',
                y='MarginPercent',
                size='Revenue',
                color='Category',
                hover_name='ProductName',
                title="Volume vs. Margin Matrix (Bubble size represents Revenue)",
                labels={
                    'OrderQuantity': 'Units Sold (Volume)',
                    'MarginPercent': 'Gross Margin (%)',
                    'Revenue': 'Total Revenue ($)'
                },
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            avg_margin_line = prod_margin['MarginPercent'].mean() if not prod_margin.empty else 0
            avg_qty_line = prod_margin['OrderQuantity'].median() if not prod_margin.empty else 0
            
            fig_scatter.add_hline(y=avg_margin_line, line_dash="dash", line_color="red", annotation_text="Avg Margin")
            fig_scatter.add_vline(x=avg_qty_line, line_dash="dash", line_color="gray", annotation_text="Median Volume")
            
            fig_scatter.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("ℹ️ No transaction data available.")

    with prof_col2:
        st.subheader("Commercial Profitability Insights")
        if not filtered_df.empty and 'prod_margin' in locals() and not prod_margin.empty:
            low_margin_threshold = prod_margin['MarginPercent'].quantile(0.3)
            high_volume_threshold = prod_margin['OrderQuantity'].quantile(0.7)
            
            problem_products = prod_margin[
                (prod_margin['MarginPercent'] <= low_margin_threshold) & 
                (prod_margin['OrderQuantity'] >= high_volume_threshold)
            ].sort_values(by='Revenue', ascending=False)
            
            high_margin_threshold = prod_margin['MarginPercent'].quantile(0.7)
            low_volume_threshold = prod_margin['OrderQuantity'].quantile(0.3)
            
            champion_products = prod_margin[
                (prod_margin['MarginPercent'] >= high_margin_threshold) & 
                (prod_margin['OrderQuantity'] <= low_volume_threshold)
            ].sort_values(by='GrossProfit', ascending=False)
            
            st.markdown("**⚠️ High Volume but Low Margin (Requires Cost Review):**")
            if not problem_products.empty:
                for idx, row in problem_products.head(2).iterrows():
                    st.warning(f"**{row['ProductName']}** ({row['Category']}): Sold {row['OrderQuantity']} units, margin: **{row['MarginPercent']:.1f}%**.")
            else:
                st.write("No major high-volume/low-margin outliers detected.")
                
            st.markdown("**💎 High Margin but Low Volume (Niche / Growth Candidates):**")
            if not champion_products.empty:
                for idx, row in champion_products.head(2).iterrows():
                    st.success(f"**{row['ProductName']}** ({row['Category']}): Margin of **{row['MarginPercent']:.1f}%** but only sold {row['OrderQuantity']} units.")
            else:
                st.write("No major niche high-margin products detected.")
        else:
            st.write("Insufficient data for insights.")

    st.markdown("---")
    st.subheader("🔄 Returns Audit")
    
    # UI Control for Returns Section
    if filtered_returns.empty or 'ProductName' not in filtered_returns.columns:
        st.success(f"🎉 **Excellent Operations for FY{selected_year}!** There are absolutely no returns registered in **{selected_region}** for this period. Profit leakage is at 0%.")
    else:
        ret_col1, ret_col2 = st.columns(2)

        with ret_col1:
            st.subheader("Top 5 Most Returned Products")
            top_returned = filtered_returns.groupby('ProductName').agg({
                'ReturnQuantity': 'sum'
            }).sort_values(by='ReturnQuantity', ascending=False).head(5).reset_index()
            
            fig_ret_bar = px.bar(
                top_returned,
                y='ProductName',
                x='ReturnQuantity',
                orientation='h',
                title="Returned Units by Product Name",
                color_discrete_sequence=['#e74c3c']
            )
            fig_ret_bar.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_ret_bar, use_container_width=True)

        with ret_col2:
            st.subheader("Financial Impact of Returns")
            filtered_returns['RevenueLost'] = filtered_returns['ReturnQuantity'] * filtered_returns['ProductPrice']
            total_lost_rev = filtered_returns['RevenueLost'].sum()
            
            cat_returns = filtered_returns.groupby('Category').agg({
                'ReturnQuantity': 'sum',
                'RevenueLost': 'sum'
            }).reset_index()
            
            fig_ret_pie = px.pie(
                cat_returns,
                values='RevenueLost',
                names='Category',
                title=f"Revenue Lost (${total_lost_rev:,.2f}) by Category",
                color_discrete_sequence=px.colors.sequential.Reds_r
            )
            st.plotly_chart(fig_ret_pie, use_container_width=True)

# ==============================================================================
# PAGE 4: FORECASTING & STRATEGY
# ==============================================================================
elif page == "🔮 Forecasting & Strategy":
    st.title("🔮 Forecasting & Executive Strategy")
    st.subheader(f"Extrapolations and decision briefs based on historical trends")
    st.markdown("---")
    
    # 12-Month Forecasting Module
    monthly_sales = df.groupby('YearMonth')['Revenue'].sum().reset_index()
    monthly_sales['YearMonth_Str'] = monthly_sales['YearMonth'].astype(str)

    if len(monthly_sales) > 1:
        x = np.arange(len(monthly_sales))
        y = monthly_sales['Revenue'].values
        slope, intercept = np.polyfit(x, y, 1)
        
        last_idx = x[-1]
        next_month_pred = max(0, slope * (last_idx + 1) + intercept)
        next_quarter_pred = max(0, (slope * np.array([last_idx+1, last_idx+2, last_idx+3]) + intercept).sum())
        next_year_pred = max(0, (slope * np.arange(last_idx+1, last_idx+13) + intercept).sum())
        
        fore_col1, fore_col2, fore_col3 = st.columns(3)
        with fore_col1:
            st.metric(label="🎯 Next Month Forecast", value=f"${next_month_pred:,.2f}")
        with fore_col2:
            st.metric(label="📊 Next Quarter Forecast (3M)", value=f"${next_quarter_pred:,.2f}")
        with fore_col3:
            st.metric(label="📅 Next 12 Months Forecast", value=f"${next_year_pred:,.2f}")
            
        future_months = [df['OrderDate'].max() + pd.DateOffset(months=i) for i in range(1, 13)]
        future_periods = [d.strftime('%Y-%m') for d in future_months]
        future_revenues = [max(0, slope * (last_idx + i) + intercept) for i in range(1, 13)]
        
        forecast_df = pd.DataFrame({'YearMonth_Str': future_periods, 'Revenue': future_revenues, 'Type': 'Forecast'})
        historical_df = monthly_sales[['YearMonth_Str', 'Revenue']].copy()
        historical_df['Type'] = 'Historical'
        
        combined_forecast = pd.concat([historical_df, forecast_df], ignore_index=True)
        
        fig_forecast = px.line(
            combined_forecast,
            x='YearMonth_Str',
            y='Revenue',
            color='Type',
            color_discrete_map={'Historical': '#003366', 'Forecast': '#ff7f0e'},
            title="Revenue Trend Line & 12-Month Forecast Path"
        )
        fig_forecast.update_traces(line=dict(width=3))
        fig_forecast.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_forecast, use_container_width=True)
    else:
        st.warning("⚠️ Insufficient historical data to generate predictive models.")

    st.markdown("---")
    st.subheader("🧠 Executive AI Recommendation & Insights")
    
    if not filtered_df.empty:
        cat_revs = filtered_df.groupby('Category')['Revenue'].sum()
        total_rev = cat_revs.sum()
        top_cat = cat_revs.idxmax()
        top_cat_share = (cat_revs.max() / total_rev) * 100
        cat_margins = (filtered_df.groupby('Category')['GrossProfit'].sum() / cat_revs) * 100
        top_cat_margin = cat_margins.get(top_cat, 0)
        avg_total_margin = (filtered_df['GrossProfit'].sum() / total_rev) * 100
        
        reg_perf = filtered_df.groupby('Region')['Revenue'].sum()
        lowest_region = reg_perf.idxmin()
        
        rec_col1, rec_col2 = st.columns(2)
        with rec_col1:
            st.markdown("#### 🎯 Performance Highlights")
            st.info(f"⚡ **{top_cat}** represents the dominant share of your business, generating **{top_cat_share:.1f}%** of total revenue. However, its profit margin is currently sitting at **{top_cat_margin:.1f}%** (overall average margin is **{avg_total_margin:.1f}%**).")
            
            highest_margin_cat = cat_margins.idxmax()
            highest_margin_val = cat_margins.max()
            st.success(f"💎 **{highest_margin_cat}** has outstanding profitability with a **{highest_margin_val:.1f}%** gross margin. Commercial team should scale marketing efforts to push volume.")

        with rec_col2:
            st.markdown("#### ⚠️ Operational Threats & Strategy")
            st.error(f"🚨 **{lowest_region}** region is underperforming compared to other territories, showing the lowest revenue intake this cycle. Country Managers should review distributor channels immediately.")
            
            if not filtered_returns.empty and 'Category' in filtered_returns.columns:
                cat_returns = filtered_returns.groupby('Category').agg({'ReturnQuantity': 'sum'}).reset_index()
                if not cat_returns.empty:
                    top_ret_category = cat_returns.sort_values(by='ReturnQuantity', ascending=False).iloc[0]['Category']
                    st.warning(f"🔄 Returns are concentrated heavily in **{top_ret_category}**. This indicates potential product quality issues or descriptive discrepancies. Operations team must audit this group.")
            else:
                st.success("✅ **Zero-Defect Streak:** No major return waves recorded. Customer satisfaction and logistical quality metrics are exceeding target boundaries.")

# ==============================================================================
# PAGE 5: SCENARIO SIMULATION (WHAT-IF ANALYSIS)
# ==============================================================================
elif page == "🎛️ Scenario Simulation":
    st.title("🎛️ Strategic Commercial Simulator")
    st.subheader(f"Interactive 'What-If' planning tool for FY{selected_year} — Simulation base: ({selected_region})")
    st.markdown("---")
    
    # 2-Column layout: Sliders on left, results on right
    sim_col_left, sim_col_right = st.columns([1, 2])
    
    with sim_col_left:
        st.subheader("Adjust Commercial Levers")
        st.markdown("Simulate different pricing, volume, and operational changes to see the immediate bottom-line impact.")
        
        # Lever 1: Price Change
        price_slider = st.slider(
            "Average Price Modification (%)", 
            min_value=-20.0, 
            max_value=20.0, 
            value=0.0, 
            step=1.0,
            help="Simulate increasing or decreasing product prices. Affects total revenue without altering costs."
        )
        
        # Lever 2: Sales Volume Change
        volume_slider = st.slider(
            "Transaction Volume Delta (%)", 
            min_value=-20.0, 
            max_value=50.0, 
            value=0.0, 
            step=1.0,
            help="Simulate scaling marketing efforts or expansion resulting in a growth/decline of units sold."
        )
        
        # Lever 3: Return Rate Optimization
        return_reduction = st.slider(
            "Target Return Reduction (%)", 
            min_value=0, 
            max_value=100, 
            value=0, 
            step=5,
            help="Simulate operational optimization to reduce return rates (e.g., higher quality checks, better web descriptions)."
        )
        
        st.markdown("---")
        st.markdown("##### Simulation Presets:")
        if st.button("🚀 Aggressive Growth Plan"):
            st.info("💡 Try setting Price to **+5%**, Volume to **+25%**, and Returns Reduction to **30%** manually to see the optimal mix.")
            
    with sim_col_right:
        st.subheader("Simulated Business Impact")
        
        # Calculations based on sliders
        # 1. Base Metrics
        base_rev = total_revenue
        base_cost = filtered_df['TotalCost'].sum() if not filtered_df.empty else 0
        base_profit = total_profit
        base_margin = gross_margin
        
        # 2. Simulated Metrics
        # Price adjustment affects unit price -> affects revenue directly.
        # Volume adjustment affects quantity -> affects both revenue and total production cost.
        sim_volume_factor = (1 + (volume_slider / 100))
        sim_price_factor = (1 + (price_slider / 100))
        
        sim_rev = base_rev * sim_volume_factor * sim_price_factor
        sim_cost = base_cost * sim_volume_factor
        sim_profit = sim_rev - sim_cost
        sim_margin = (sim_profit / sim_rev) * 100 if sim_rev > 0 else 0
        
        # Calculate Returns Financial Recoveries
        base_return_lost = 0
        if not filtered_returns.empty and 'ProductPrice' in filtered_returns.columns:
            filtered_returns['RevenueLost'] = filtered_returns['ReturnQuantity'] * filtered_returns['ProductPrice']
            base_return_lost = filtered_returns['RevenueLost'].sum()
            
        saved_from_returns = base_return_lost * (return_reduction / 100)
        final_sim_profit = sim_profit + saved_from_returns
        final_sim_margin = (final_sim_profit / sim_rev) * 100 if sim_rev > 0 else 0
        
        # Display side-by-side metric updates
        sim_m1, sim_m2, sim_m3 = st.columns(3)
        
        with sim_m1:
            st.metric(
                label="Simulated Revenue",
                value=f"${sim_rev:,.2f}",
                delta=f"${(sim_rev - base_rev):+,.2f}"
            )
        with sim_m2:
            st.metric(
                label="Simulated Gross Margin",
                value=f"{final_sim_margin:.2f}%",
                delta=f"{(final_sim_margin - base_margin):+.2f}%"
            )
        with sim_m3:
            st.metric(
                label="Simulated Net Profit",
                value=f"${final_sim_profit:,.2f}",
                delta=f"${(final_sim_profit - base_profit):+,.2f}"
            )
            
        st.markdown("---")
        
        # Comparison Chart (Current vs. Simulated)
        comp_df = pd.DataFrame({
            'Metric': ['Revenue', 'Gross Profit', 'Returns Loss'],
            'Current State': [base_rev, base_profit, base_return_lost],
            'Simulated State': [sim_rev, final_sim_profit, (base_return_lost - saved_from_returns)]
        })
        
        fig_comp = px.bar(
            comp_df,
            x='Metric',
            y=['Current State', 'Simulated State'],
            barmode='group',
            title="Operational Scenario Comparison",
            color_discrete_sequence=['#003366', '#ff7f0e']
        )
        fig_comp.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_comp, use_container_width=True)
        
        # Decision Analysis text
        st.markdown("#### Simulator Strategic Brief:")
        if final_sim_profit > base_profit:
            st.success(
                f"📈 This specific combination would result in a profit increase of **${(final_sim_profit - base_profit):,.2f}** "
                f"for FY{selected_year}. Gross margins would scale from **{base_margin:.1f}%** to **{final_sim_margin:.1f}%**."
            )
        elif final_sim_profit < base_profit:
            st.error(
                f"📉 **Warning:** This scenario leads to a net profit leakage of **${(base_profit - final_sim_profit):,.2f}**. "
                f"The price or volume cuts cannot be offset by current cost structures."
            )
        else:
            st.info("Move the levers on the left to see dynamic scenario modeling.")

# Footer
st.markdown("---")
st.caption("AdventureWorks Commercial Suite v1.2 • Advanced Scenario Engine Active.")