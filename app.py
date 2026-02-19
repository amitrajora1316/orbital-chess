import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt import risk_models, expected_returns

# --- VANGUARD CSS THEME ---
st.set_page_config(page_title="Vanguard | Tactical Reallocator", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050508; color: #dcd9d0; font-family: 'Georgia', serif; }
    .stTable { border: 2px ridge #c5a059; background: #0d0d12; }
    h1, h2, h3 { color: #c5a059; letter-spacing: 2px; text-transform: uppercase; border-bottom: 1px solid #c5a059; }
    .stButton>button { background-color: #c5a059; color: black; font-weight: 900; border-radius: 0px; border: 1px solid #fff; }
    </style>
    """, unsafe_allow_stdio=True)

st.title("🏛️ Portfolio Reallocator V3.2")
st.caption("Strategic Mean-Variance Optimization Frame with Risk-Reward Visualization")

# --- USER INPUT SIDEBAR ---
with st.sidebar:
    st.header("Deployment Parameters")
    symbols_raw = st.text_input("Ticker Symbols (Commas)", "AAPL, MSFT, TSLA, GLD, BTC-USD")
    tickers = [s.strip().upper() for s in symbols_raw.split(",")]
    
    st.markdown("---")
    st.subheader("Current Weights")
    current_weights = {}
    for t in tickers:
        current_weights[t] = st.number_input(f"Current % for {t}", value=100.0/len(tickers))

# --- CALCULATION ENGINE ---
if st.button("EXECUTE ANALYSIS & CHART"):
    with st.spinner("Calculating Variance and Mapping Frontier..."):
        try:
            # 1. Fetch historical data
            prices = yf.download(tickers, period="3y")['Adj Close']
            
            # 2. Markowitz Calculations
            mu = expected_returns.mean_historical_return(prices)
            S = risk_models.sample_cov(prices)
            volatility = pd.Series(np.sqrt(np.diag(S)), index=S.index) # Individual risk
            
            # 3. Optimize for Max Sharpe Ratio
            ef = EfficientFrontier(mu, S)
            weights = ef.max_sharpe()
            cleaned_weights = ef.clean_weights()
            
            # --- LAYOUT: 4-COLUMN TABLE ---
            st.subheader("Tactical Reallocation Matrix")
            display_data = []
            for t in tickers:
                index_map = "Equity/Bond" if "USD" not in t else "Digital Asset"
                display_data.append({
                    "Share Symbol": t,
                    "Primary Index": index_map,
                    "Current Allocation": f"{current_weights[t]:.2f}%",
                    "Recommended Allocation": f"{cleaned_weights.get(t, 0)*100:.2f}%"
                })
            st.table(pd.DataFrame(display_data))

            # --- THE CHART: RISK VS REWARD ---
            st.subheader("Efficient Frontier Analysis")
            
            # Prepare data for Plotly
            chart_df = pd.DataFrame({
                'Ticker': mu.index,
                'Expected Return (%)': (mu.values * 100).round(2),
                'Risk/Volatility (%)': (volatility.values * 100).round(2)
            })

            fig = px.scatter(
                chart_df, 
                x='Risk/Volatility (%)', 
                y='Expected Return (%)', 
                text='Ticker',
                title="Asset Risk-Reward Profile"
            )

            # Vanguard Styling for Chart
            fig.update_traces(marker=dict(size=12, color='#c5a059', line=dict(width=2, color='white')), selector=dict(mode='markers'))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(13,13,18,0.8)',
                font_color='#dcd9d0',
                xaxis=dict(gridcolor='#33333c', title="RISK (Annual Volatility)"),
                yaxis=dict(gridcolor='#33333c', title="RETURN (Annualized)"),
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("Visual Guide: Assets in the top-left provide higher returns for lower risk. The Markowitz framework reallocates capital away from high-risk/low-return assets.")

        except Exception as e:
            st.error(f"Logic Error: {e}")