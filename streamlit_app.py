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


# ── Title & Sidebar ──────────────────────────────────────────────────────────
st.title("📈 Autonomous Investment Adviser Desk")
st.markdown("---")

# Setup sidebar controls
st.sidebar.header("Agent Configuration")
st.sidebar.markdown(f"**Stance:** `{config.portfolio.risk_tolerance.upper()}`")
st.sidebar.markdown(f"**Optimization:** `{config.portfolio.optimization_method}`")

watchlist = config.watchlist.all_tickers
selected_tickers = st.sidebar.multiselect("Watchlist Assets", watchlist, default=watchlist)


# ── Operational Actions ──────────────────────────────────────────────────────
if st.sidebar.button("Run Full Market Scan", type="primary"):
    with st.spinner("Executing sequential multi-agent LangGraph scan..."):
        try:
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
    st.info("🚨 **LangGraph approval interrupt reached**: Review allocations below before proceeding.")
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
                    
                    st.session_state.analysis_results = final_state
                    st.session_state.approval_pending = False
                    st.success(f"Approved! Report saved to: {rep_paths.get('html')}")
                except Exception as e:
                    st.error(f"Error resuming graph: {str(e)}")
                    
    with col_app2:
        if st.button("Reject & Stop Pipeline", type="secondary", use_container_width=True):
            try:
                resume_with_approval(
                    st.session_state.graph, st.session_state.thread_id, "reject"
                )
                st.session_state.approval_pending = False
                st.session_state.analysis_results = None
                st.warning("Recommendation rejected. Execution halted.")
            except Exception as e:
                st.error(f"Error: {str(e)}")


# ── Render Analytics Panels ──────────────────────────────────────────────────
if st.session_state.analysis_results:
    state = st.session_state.analysis_results
    
    tab1, tab2, tab3 = st.tabs(["📊 Target Allocations", "🔍 Asset Analysis", "📈 Backtesting Validation"])
    
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
                    st.markdown(f"- **[{article.get('source')}]** [{article.get('title')}]({article.get('url')})")
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
