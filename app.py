# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

st.set_page_config(page_title="Simulació DCA", layout="wide")

currency_symbol = "$"

st.title("Simulació DCA amb reequilibri opcional")

# --- Inputs ---
st.header("1️⃣ Configuració de la simulació")

# Any d'inici
start_2015 = st.radio("Vols començar la simulació al 2015?", ("Sí", "No"))
if start_2015 == "Sí":
    start_year = 2015
else:
    st.warning("⚠️ Bitcoin (BTC-USD) no té dades abans del 2015.")
    start_year = st.number_input("Introdueix l'any d'inici (1980-2025):", min_value=1980, max_value=2025, value=2015)

start_date = f"{start_year}-01-01"
end_date = datetime.today().strftime("%Y-%m-%d")

# Quantitat mensual
monthly_investment = st.number_input("Quant vols invertir cada mes ($)?", min_value=1, max_value=100000, value=100)

# Tick­ers
default_tickers = ["BTC-USD", "QQQ", "SPY", "GLD"]
use_default = st.radio(f"Vols fer servir els tickers per defecte {default_tickers}?", ("Sí", "No"))

if use_default == "Sí":
    tickers = default_tickers
else:
    n_tickers = st.number_input("Entre quants tickers vols repartir (1 a 5)?", min_value=1, max_value=5, value=4)
    tickers = []
    for i in range(n_tickers):
        tickers.append(st.text_input(f"Introdueix el ticker {i+1}", value=""))

# Reequilibri anual
rebalance = st.checkbox("Vols rebalancejar anualment?")

# Repartiment equitatiu o percentatges
equal_allocation = st.checkbox("Vols repartir equitativament el capital entre tots els actius?")

allocations = []
if equal_allocation:
    allocations = [1/len(tickers)]*len(tickers)
else:
    st.subheader("Introdueix el percentatge mensual i al reequilibri per cada actiu (0-100%)")
    while True:
        allocations = []
        for t in tickers:
            p = st.number_input(f"Percentatge per {t}", min_value=0.0, max_value=100.0, value=25.0)
            allocations.append(p)
        total_pct = sum(allocations)
        st.write(f"La suma de percentatges és {total_pct}%")
        if total_pct == 100:
            allocations = [p/100 for p in allocations]  # normalitzar a decimals
            break
        else:
            st.warning("La suma dels percentatges ha de ser 100%. Torna-ho a introduir.")

st.write("✅ Configuració completada.")
st.write("Tickers:", tickers)
st.write("Percentatges:", [round(a*100,2) for a in allocations])

# --- Descarregar dades ---
st.header("2️⃣ Descàrrega de dades")
data_load_state = st.text("Descarregant dades...")
data = yf.download(tickers, start=start_date, end=end_date, interval="1mo")["Close"]
data.dropna(how="all", inplace=True)
data = data[tickers]
data_load_state.text("Dades descarregades amb èxit!")

# --- Funció DCA ---
def simulate_dca(data, monthly_investment, allocations, rebalance=False):
    units = pd.DataFrame(index=data.index, columns=data.columns)
    value = pd.DataFrame(index=data.index, columns=data.columns)
    holdings = {t:0 for t in data.columns}
    
    for i, (date, prices) in enumerate(data.iterrows()):
        for t, alloc in zip(data.columns, allocations):
            price = prices[t]
            if pd.notna(price):
                holdings[t] += (monthly_investment * alloc) / price
        if rebalance and date.month ==1 and i != 0:
            total_value = sum(holdings[t]*prices[t] for t in data.columns if pd.notna(prices[t]))
            for t, alloc in zip(data.columns, allocations):
                price = prices[t]
                if pd.notna(price):
                    holdings[t] = (total_value * alloc)/price
        for t in data.columns:
            price = prices[t]
            if pd.notna(price):
                units.loc[date, t] = holdings[t]
                value.loc[date, t] = holdings[t]*price
    return value

# --- Simulació ---
value_user = simulate_dca(data, monthly_investment, allocations, rebalance=rebalance)
portfolio_user = value_user.sum(axis=1)

# --- Taula resum ---
final_value = value_user.iloc[-1].astype(float)
months = len(data)
invested_per_asset = [monthly_investment * months * a for a in allocations]
portfolio_final_value = float(portfolio_user.iloc[-1])
percent_over_portfolio = ((final_value / portfolio_final_value) * 100).round(2)


summary = pd.DataFrame({
    f"Valor final ({currency_symbol})": final_value.round(2),
    f"Aportat total ({currency_symbol})": invested_per_asset,
    "Benefici (%)": ((final_value/invested_per_asset-1)*100).round(2),
    "% sobre portfoli final": percent_over_portfolio
}, index=tickers)

st.header("3️⃣ Resultats de la simulació")
st.dataframe(summary)

# --- Gràfiques ---
st.header("4️⃣ Gràfiques del portfoli")
fig, axs = plt.subplots(2,2, figsize=(16,10))
axs = axs.flatten()

# Lineal
axs[0].plot(portfolio_user.index, portfolio_user.values, lw=2, label="Portfoli")
axs[0].set_title("Escala lineal")
axs[0].set_ylabel(f"Valor total ({currency_symbol})")
axs[0].grid(True)
axs[0].yaxis.set_major_formatter(mticker.StrMethodFormatter(f"{currency_symbol}{{x:,.0f}}"))
axs[0].legend()

# Logarítmica
axs[1].plot(portfolio_user.index, portfolio_user.values, lw=2, label="Portfoli")
axs[1].set_yscale("log")
axs[1].set_title("Escala logarítmica")
axs[1].set_ylabel(f"Valor total ({currency_symbol})")
axs[1].grid(True, which="both", ls="--")
axs[1].yaxis.set_major_formatter(mticker.StrMethodFormatter(f"{currency_symbol}{{x:,.0f}}"))
axs[1].legend()

# Comparació amb/sense reequilibri
if rebalance:
    value_no_rebalance = simulate_dca(data, monthly_investment, allocations, rebalance=False)
    portfolio_no_rebalance = value_no_rebalance.sum(axis=1)
    axs[2].plot(portfolio_user.index, portfolio_user.values, lw=2, label="Amb reequilibri")
    axs[2].plot(portfolio_no_rebalance.index, portfolio_no_rebalance.values, lw=2, label="Sense reequilibri")
    axs[2].set_title("Comparació lineal")
    axs[2].set_ylabel(f"Valor total ({currency_symbol})")
    axs[2].grid(True)
    axs[2].yaxis.set_major_formatter(mticker.StrMethodFormatter(f"{currency_symbol}{{x:,.0f}}"))
    axs[2].legend()
    
    axs[3].plot(portfolio_user.index, portfolio_user.values, lw=2, label="Amb reequilibri")
    axs[3].plot(portfolio_no_rebalance.index, portfolio_no_rebalance.values, lw=2, label="Sense reequilibri")
    axs[3].set_yscale("log")
    axs[3].set_title("Comparació logarítmica")
    axs[3].set_ylabel(f"Valor total ({currency_symbol})")
    axs[3].grid(True, which="both", ls="--")
    axs[3].yaxis.set_major_formatter(mticker.StrMethodFormatter(f"{currency_symbol}{{x:,.0f}}"))
    axs[3].legend()
else:
    for i in [2,3]:
        axs[i].axis('off')

# Percentatge al final de la línia
for t, pct in zip(value_user.columns, percent_over_portfolio):
    axs[0].text(portfolio_user.index[-1], value_user[t].iloc[-1], f"{t}: {pct:.1f}%", fontsize=9, va='bottom')

plt.tight_layout()
st.pyplot(fig)

