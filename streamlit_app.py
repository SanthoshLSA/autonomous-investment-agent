"""
Streamlit Web Dashboard for the Autonomous Investment Research Agent.
"""

from __future__ import annotations

import os
from datetime import datetime
import pandas as pd
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="Investment Agent Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Imports from src package
from src.config import get_config, get_api_keys
from src.agents.graph import (
    build_investment_graph,
    run_investment_analysis,
    resume_with_approval,
)
from src.portfolio.backtester import Backtester
from src.portfolio.optimizer import PortfolioOptimizer
from src.portfolio.rebalancer import Rebalancer
from src.reports.charts import (
    build_price_candlestick,
    build_risk_heatmap,
    build_allocation_pie,
)
from src.reports.generator import generate_daily_report

# Initialize core variables
config = get_config()
api_keys = get_api_keys()

# Ensure keys exist in session state to handle page refreshes
if "graph" not in st.session_state:
    st.session_state.graph = build_investment_graph(config, api_keys)
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"dashboard-{datetime.now().strftime('%Y%m%d%H%M%S')}"
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "approval_pending" not in st.session_state:
    st.session_state.approval_pending = False
if "report_paths" not in st.session_state:
    st.session_state.report_paths = None


# Custom CSS to match santhoshlsa.vercel.app visual layout
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Outfit:wght@300;400;600;700&display=swap');

/* Main layout background & fonts */
.stApp {
    background: radial-gradient(circle at 10% 20%, rgba(168, 85, 247, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(56, 189, 248, 0.08) 0%, transparent 40%),
                #07040d !important;
    font-family: 'Outfit', sans-serif !important;
    color: #f8fafc !important;
}

/* Headings styling */
h1, h2, h3, h4, h5, h6, [data-testid="stHeader"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    text-transform: uppercase !important;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #0c0816 !important;
    border-right: 1px solid rgba(168, 85, 247, 0.15) !important;
}

/* Buttons styling */
.stButton>button {
    background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%) !important;
    color: white !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    border-radius: 12px !important;
    padding: 0.75rem 2rem !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 0 15px rgba(168, 85, 247, 0.25) !important;
    width: 100% !important;
}

.stButton>button:hover {
    transform: scale(1.02) !important;
    box-shadow: 0 0 25px rgba(168, 85, 247, 0.45) !important;
    border-color: rgba(168, 85, 247, 0.5) !important;
}

/* Glassmorphic Cards */
div[data-testid="stMetric"], .stAlert {
    background: rgba(12, 8, 22, 0.6) !important;
    border: 1px solid rgba(168, 85, 247, 0.15) !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
    backdrop-filter: blur(12px) !important;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4) !important;
}

/* Selectbox / Multiselect styling */
div[data-baseweb="select"] {
    background-color: rgba(12, 8, 22, 0.8) !important;
    border-radius: 12px !important;
}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background-color: transparent !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    background-color: rgba(255, 255, 255, 0.01) !important;
    border: 1px solid rgba(255, 255, 255, 0.03) !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
}

.stTabs [aria-selected="true"] {
    color: #a855f7 !important;
    border-bottom: 2px solid #a855f7 !important;
    background-color: rgba(168, 85, 247, 0.1) !important;
}

/* Text elements custom highlights */
.stMarkdown p {
    color: #cbd5e1 !important;
    font-size: 1rem !important;
    line-height: 1.6 !important;
}

/* Gradient heading highlight */
.gradient-header {
    background: linear-gradient(to right, #a855f7, #ffffff, #38bdf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 800;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ── Title & Sidebar ──────────────────────────────────────────────────────────
st.markdown(
    '<h1 class="gradient-header">📈 AUTONOMOUS INVESTMENT ADVISER DESK</h1>', unsafe_allow_html=True
)
st.markdown("---")

# Setup sidebar controls
st.sidebar.header("Agent Configuration")
st.sidebar.markdown(f"**Stance:** `{config.portfolio.risk_tolerance.upper()}`")
st.sidebar.markdown(f"**Optimization:** `{config.portfolio.optimization_method}`")

watchlist = list(config.watchlist.all_tickers)

# Allow user to dynamically add new assets directly in the UI
custom_ticker = (
    st.sidebar.text_input("➕ Add custom ticker (e.g. NVDA, TATAMOTORS.NS, SOL-USD)", "")
    .strip()
    .upper()
)
if custom_ticker:
    if custom_ticker not in watchlist:
        watchlist.append(custom_ticker)

selected_tickers = st.sidebar.multiselect("Watchlist Assets", watchlist, default=watchlist)


# ── Operational Actions ──────────────────────────────────────────────────────
if st.sidebar.button("Run Full Market Scan", type="primary"):
    with st.spinner("Executing sequential multi-agent LangGraph scan..."):
        try:
            # Rebuild the graph to ensure any updated API keys are loaded
            st.session_state.graph = build_investment_graph(config, get_api_keys())

            # Trigger LangGraph execution loop
            results = run_investment_analysis(
                st.session_state.graph, selected_tickers, st.session_state.thread_id
            )
            st.session_state.analysis_results = results
            st.session_state.approval_pending = True
            st.success("Scan completed. Awaiting portfolio allocation approval.")
        except Exception as e:
            st.error(f"Execution Error: {str(e)}")

# Add reset handler
if st.sidebar.button("Reset Session ID"):
    st.session_state.thread_id = f"dashboard-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    st.session_state.analysis_results = None
    st.session_state.approval_pending = False
    st.info("Session ID re-generated.")


# ── Human Approval Gate UI ──────────────────────────────────────────────────
if st.session_state.approval_pending and st.session_state.analysis_results:
    st.info(
        "🚨 **LangGraph approval interrupt reached**: Review allocations below before proceeding."
    )
    col_app1, col_app2 = st.columns(2)

    with col_app1:
        if st.button("Approve & Generate Reports", type="primary", use_container_width=True):
            with st.spinner("Resuming workflow pipeline..."):
                try:
                    final_state = resume_with_approval(
                        st.session_state.graph, st.session_state.thread_id, "approve"
                    )
                    # Generate daily report HTML
                    rep_paths = generate_daily_report(final_state)
                    st.session_state.report_paths = rep_paths

                    st.session_state.analysis_results = final_state
                    st.session_state.approval_pending = False
                    st.success("Approved! Daily HTML and PDF reports generated successfully.")
                except Exception as e:
                    st.error(f"Error resuming graph: {str(e)}")

    with col_app2:
        if st.button("Reject & Stop Pipeline", type="secondary", use_container_width=True):
            try:
                resume_with_approval(st.session_state.graph, st.session_state.thread_id, "reject")
                st.session_state.approval_pending = False
                st.session_state.analysis_results = None
                st.warning("Recommendation rejected. Execution halted.")
            except Exception as e:
                st.error(f"Error: {str(e)}")


# ── Render Analytics Panels ──────────────────────────────────────────────────
if st.session_state.analysis_results:
    state = st.session_state.analysis_results

    # Show error logs for debugging
    errors = state.get("error_log", [])
    if errors:
        with st.expander("⚠️ System Debug & Connection Logs"):
            for err in errors:
                st.error(err)
        st.markdown("---")

    # Downloadable PDF Report Button
    if st.session_state.report_paths and "pdf" in st.session_state.report_paths:
        pdf_path = st.session_state.report_paths["pdf"]
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label="📥 Download PDF Report Document",
                data=pdf_bytes,
                file_name=f"Daily_Investment_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.markdown("---")

    tab1, tab2, tab3 = st.tabs(
        ["📊 Target Allocations", "🔍 Asset Analysis", "📈 Backtesting Validation"]
    )

    # 1. Allocation Page
    with tab1:
        recomm = state.get("portfolio_recommendation", {})
        if recomm:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("Asset Breakdown")
                fig_pie = build_allocation_pie(recomm.get("allocations", {}))
                st.plotly_chart(fig_pie, use_container_width=True)
            with col2:
                st.subheader("Advisor Stance Summary")
                st.info(recomm.get("portfolio_summary", "No summary text."))

                st.subheader("Key Caveats / Warnings")
                for w in recomm.get("warnings", []):
                    st.warning(w)

            st.subheader("Execution Rationale per Asset")
            for ticker, text in recomm.get("rationale", {}).items():
                st.markdown(f"**{ticker}**: {text}")
        else:
            st.warning("No portfolio recommendations calculated.")

    # 2. Deep Dive Page
    with tab2:
        composite = state.get("composite_scores", {})
        if composite:
            fig_heat = build_risk_heatmap(composite)
            st.plotly_chart(fig_heat, use_container_width=True)

            selected_ticker = st.selectbox("Deep Dive Stock Ticker", list(composite.keys()))

            # Candlestick
            market = state.get("market_data", {}).get(selected_ticker, {})
            if market and market.get("prices"):
                fig_candle = build_price_candlestick(selected_ticker, market["prices"])
                st.plotly_chart(fig_candle, use_container_width=True)

                # News
                st.subheader("Sentiment Source News Headlines")
                for article in market.get("news", []):
                    st.markdown(
                        f"- **[{article.get('source')}]** [{article.get('title')}]({article.get('url')})"
                    )
        else:
            st.warning("Run a scan to check asset metrics.")

    # 3. Backtesting Page
    with tab3:
        st.subheader("Historical Backtest (5 Years)")
        st.write("Simulating calculated allocation against S&P 500 benchmark...")

        # Load price df from state to run backtest
        market = state.get("market_data", {})
        if market:
            price_series_dict = {}
            for ticker, bundle in market.items():
                prices = bundle.get("prices", [])
                if prices:
                    pdf = pd.DataFrame(prices)
                    pdf["date"] = pd.to_datetime(pdf["date"], utc=True)
                    pdf.set_index("date", inplace=True)
                    pdf.sort_index(inplace=True)
                    price_series_dict[ticker] = pdf["close"]

            prices_df = pd.DataFrame(price_series_dict).ffill().bfill()

            if not prices_df.empty:
                optimizer_weights = state.get("portfolio_recommendation", {}).get("allocations", {})

                bt = Backtester(config.backtest)
                metrics = bt.run_backtest(prices_df, optimizer_weights)

                if "error" not in metrics:
                    col_bt1, col_bt2, col_bt3 = st.columns(3)
                    col_bt1.metric("CAGR Return", f"{metrics['annual_return']:.2%}")
                    col_bt2.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
                    col_bt3.metric("Max Drawdown", f"{metrics['max_drawdown']:.2%}")

                    st.write(f"Benchmark Cumulative Return: **{metrics['benchmark_return']:.2%}**")
                    st.write(f"Strategy Cumulative Return: **{metrics['total_return']:.2%}**")
                else:
                    st.error(f"Backtesting error: {metrics['error']}")
            else:
                st.warning("Insufficient prices dataframe generated.")
        else:
            st.warning("No market data to backtest.")

else:
    st.info("Use the sidebar on the left to select assets and trigger the market scanner.")
