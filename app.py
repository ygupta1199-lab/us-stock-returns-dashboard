import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------

st.set_page_config(
    page_title="US Stock Returns Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 US Stock Returns Dashboard")
st.caption("Historical monthly, quarterly, and annual returns")


# ---------------------------------------------------------
# DATA DOWNLOAD
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def download_stock_data(ticker, start_date, end_date):

    data = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        auto_adjust=False,
        progress=False
    )

    if data.empty:
        return None

    # yfinance can sometimes return MultiIndex columns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Use Adjusted Close
    if "Adj Close" in data.columns:
        price = data["Adj Close"].copy()
    else:
        price = data["Close"].copy()

    price = price.dropna()

    return price


# ---------------------------------------------------------
# RETURN CALCULATIONS
# ---------------------------------------------------------

def calculate_monthly_returns(price):

    # Month-end prices
    month_end = price.resample("ME").last()

    # Percentage change from previous month
    monthly_returns = month_end.pct_change() * 100

    # Convert to dataframe
    df = monthly_returns.to_frame("Return")

    df["Year"] = df.index.year
    df["Month"] = df.index.month

    # Pivot into Year x Month
    table = df.pivot(
        index="Year",
        columns="Month",
        values="Return"
    )

    # Ensure all months exist
    table = table.reindex(columns=range(1, 13))

    table.columns = [
        "Jan", "Feb", "Mar", "Apr",
        "May", "Jun", "Jul", "Aug",
        "Sep", "Oct", "Nov", "Dec"
    ]

    # Most recent year first
    table = table.sort_index(ascending=False)

    return table


def calculate_quarterly_returns(price):

    # Quarter-end prices
    quarter_end = price.resample("QE").last()

    # Percentage change
    quarterly_returns = quarter_end.pct_change() * 100

    df = quarterly_returns.to_frame("Return")

    df["Year"] = df.index.year
    df["Quarter"] = df.index.quarter

    # Pivot into Year x Quarter
    table = df.pivot(
        index="Year",
        columns="Quarter",
        values="Return"
    )

    table = table.reindex(columns=[1, 2, 3, 4])

    table.columns = [
        "Q1", "Q2", "Q3", "Q4"
    ]

    table = table.sort_index(ascending=False)

    return table


def calculate_annual_returns(price):

    # Year-end prices
    year_end = price.resample("YE").last()

    # Percentage change
    annual_returns = year_end.pct_change() * 100

    table = annual_returns.to_frame(
        "Annual Return"
    )

    table.index = table.index.year
    table.index.name = "Year"

    table = table.sort_index(ascending=False)

    return table


# ---------------------------------------------------------
# TABLE STYLING
# ---------------------------------------------------------

def format_returns(df):

    def color_returns(value):

        if pd.isna(value):
            return ""

        if value > 0:
            return (
                "color: #137333; "
                "background-color: #e6f4ea; "
                "font-weight: 500"
            )

        if value < 0:
            return (
                "color: #b3261e; "
                "background-color: #fce8e6; "
                "font-weight: 500"
            )

        return ""

    return (
        df.style
        .format("{:.2f}%", na_rep="—")
        .map(color_returns)
    )


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

st.sidebar.header("Stock Settings")

ticker = st.sidebar.text_input(
    "US Stock Ticker",
    value="AAPL",
    placeholder="e.g. AAPL, MSFT, NVDA"
).strip().upper()

years = st.sidebar.slider(
    "Years of history",
    min_value=5,
    max_value=20,
    value=15
)

load_stock = st.sidebar.button(
    "Load Stock",
    type="primary",
    use_container_width=True
)

st.sidebar.divider()

st.sidebar.info(
    """
    Examples:

    AAPL — Apple  
    MSFT — Microsoft  
    NVDA — NVIDIA  
    AMZN — Amazon  
    TSLA — Tesla  
    META — Meta  
    GOOGL — Alphabet
    """
)

# ---------------------------------------------------------
# INITIALIZE
# ---------------------------------------------------------

if "ticker" not in st.session_state:

    st.session_state.ticker = "AAPL"

if load_stock:

    if ticker:
        st.session_state.ticker = ticker

active_ticker = st.session_state.ticker


# ---------------------------------------------------------
# DATE RANGE
# ---------------------------------------------------------

today = date.today()

# Get one additional year of data.
# This is important because calculating the first displayed
# monthly/quarterly/annual return requires the previous period.
start_date = date(
    today.year - years - 1,
    today.month,
    today.day
)

end_date = today


# ---------------------------------------------------------
# DOWNLOAD DATA
# ---------------------------------------------------------

with st.spinner(
    f"Loading {active_ticker} historical data..."
):

    price = download_stock_data(
        active_ticker,
        start_date,
        end_date
    )


# ---------------------------------------------------------
# ERROR HANDLING
# ---------------------------------------------------------

if price is None or price.empty:

    st.error(
        f"""
        Could not find historical data for **{active_ticker}**.

        Please check that you entered a valid US stock ticker.
        """
    )

    st.stop()


# ---------------------------------------------------------
# LIMIT TO REQUESTED HISTORY
# ---------------------------------------------------------

display_start = pd.Timestamp(today) - pd.DateOffset(
    years=years
)

price_display = price[
    price.index >= display_start
]


# ---------------------------------------------------------
# COMPANY INFO
# ---------------------------------------------------------

try:

    info = yf.Ticker(active_ticker).info

    company_name = info.get(
        "longName",
        active_ticker
    )

except Exception:

    company_name = active_ticker


# ---------------------------------------------------------
# CALCULATE RETURNS
# ---------------------------------------------------------

monthly_returns = calculate_monthly_returns(
    price_display
)

quarterly_returns = calculate_quarterly_returns(
    price_display
)

annual_returns = calculate_annual_returns(
    price_display
)


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.header(
    f"{company_name} ({active_ticker})"
)

first_date = price_display.index.min().strftime(
    "%b %d, %Y"
)

last_date = price_display.index.max().strftime(
    "%b %d, %Y"
)


# ---------------------------------------------------------
# SUMMARY METRICS
# ---------------------------------------------------------

annual_values = (
    annual_returns["Annual Return"]
    .dropna()
)

if len(annual_values) > 0:

    positive_years = (
        annual_values > 0
    ).sum()

    best_year = annual_values.idxmax()
    best_return = annual_values.max()

    worst_year = annual_values.idxmin()
    worst_return = annual_values.min()

else:

    positive_years = 0
    best_year = "—"
    best_return = 0
    worst_year = "—"
    worst_return = 0


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Latest Price",
        f"${float(price.iloc[-1]):,.2f}"
    )


with col2:

    st.metric(
        "Positive Years",
        f"{positive_years}/{len(annual_values)}"
    )


with col3:

    if best_year != "—":

        st.metric(
            "Best Year",
            f"{best_year}: {best_return:.2f}%"
        )

    else:

        st.metric(
            "Best Year",
            "—"
        )


with col4:

    if worst_year != "—":

        st.metric(
            "Worst Year",
            f"{worst_year}: {worst_return:.2f}%"
        )

    else:

        st.metric(
            "Worst Year",
            "—"
        )


st.caption(
    f"Historical data shown: {first_date} → {last_date}"
)


# ---------------------------------------------------------
# TABS
# ---------------------------------------------------------

monthly_tab, quarterly_tab, annual_tab = st.tabs(
    [
        "📅 Monthly Returns",
        "📊 Quarterly Returns",
        "📈 Annual Returns"
    ]
)


# ---------------------------------------------------------
# MONTHLY TABLE
# ---------------------------------------------------------

with monthly_tab:

    st.subheader(
        "Monthly Percentage Change"
    )

    st.write(
        """
        Return from the previous month's
        adjusted closing price to the current
        month's adjusted closing price.
        """
    )

    st.dataframe(
        format_returns(monthly_returns),
        use_container_width=True,
        height=700
    )

    st.download_button(
        label="⬇️ Download Monthly CSV",

        data=monthly_returns.to_csv(),

        file_name=(
            f"{active_ticker}_monthly_returns.csv"
        ),

        mime="text/csv"
    )


# ---------------------------------------------------------
# QUARTERLY TABLE
# ---------------------------------------------------------

with quarterly_tab:

    st.subheader(
        "Quarterly Percentage Change"
    )

    st.write(
        """
        Return from the previous quarter-end
        adjusted closing price to the current
        quarter-end adjusted closing price.
        """
    )

    st.dataframe(
        format_returns(quarterly_returns),
        use_container_width=True,
        height=700
    )

    st.download_button(
        label="⬇️ Download Quarterly CSV",

        data=quarterly_returns.to_csv(),

        file_name=(
            f"{active_ticker}_quarterly_returns.csv"
        ),

        mime="text/csv"
    )


# ---------------------------------------------------------
# ANNUAL TABLE
# ---------------------------------------------------------

with annual_tab:

    st.subheader(
        "Annual Percentage Change"
    )

    st.write(
        """
        Return from the previous year-end
        adjusted closing price to the current
        year-end adjusted closing price.
        """
    )

    st.dataframe(
        format_returns(annual_returns),
        use_container_width=True,
        height=700
    )

    st.download_button(
        label="⬇️ Download Annual CSV",

        data=annual_returns.to_csv(),

        file_name=(
            f"{active_ticker}_annual_returns.csv"
        ),

        mime="text/csv"
    )


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    """
    Data retrieved using yfinance/Yahoo Finance.
    Returns use Adjusted Close when available.
    """
)