"""The bundled sample dataset library.

Every file is synthetic but statistically realistic, and each one carries
deliberate imperfections so all five workflow stages have real work to do.
Regenerate them with `python tools/make_samples.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


@dataclass(frozen=True)
class Sample:
    key: str
    name: str
    filename: str
    icon: str
    domain: str
    summary: str
    good_for: str

    @property
    def path(self) -> Path:
        return SAMPLE_DIR / self.filename

    @property
    def exists(self) -> bool:
        return self.path.exists()


LIBRARY: list[Sample] = [
    Sample(
        key="titanic",
        name="Titanic passengers",
        filename="titanic_passengers.csv",
        icon=":material/directions_boat:",
        domain="Classic",
        summary="891 passengers with class, sex, age, fare and survival. Age is 20% missing, exactly like the original.",
        good_for="Classification, missing-value strategy, survival rates by group.",
    ),
    Sample(
        key="tips",
        name="Restaurant tips",
        filename="restaurant_tips.csv",
        icon=":material/restaurant:",
        domain="Classic",
        summary="244 restaurant bills with tip, party size, day and time. Small and easy to reason about.",
        good_for="Your first run — correlation between bill and tip is strong and obvious.",
    ),
    Sample(
        key="ecommerce",
        name="E-commerce orders",
        filename="ecommerce_orders.csv",
        icon=":material/shopping_cart:",
        domain="Business",
        summary="1,200 orders across six categories with price, discount, shipping days, rating and returns.",
        good_for="Revenue by category, how shipping delay drags ratings down, messy text and outliers.",
    ),
    Sample(
        key="agriculture",
        name="Agriculture crop yield",
        filename="agriculture_crop_yield.csv",
        icon=":material/agriculture:",
        domain="Science",
        summary="900 field records: rainfall, temperature, fertiliser, irrigation and the yield they produced.",
        good_for="Multi-driver analysis — yield genuinely depends on three inputs at once.",
    ),
    Sample(
        key="crypto",
        name="Crypto coin prices",
        filename="crypto_coin_prices.csv",
        icon=":material/currency_bitcoin:",
        domain="Finance",
        summary="Six coins over 220 days with price, market cap, volume and daily change.",
        good_for="Time-series trends, volatility, and how a whole market moves together.",
    ),
    Sample(
        key="hr",
        name="Employee attrition",
        filename="employee_attrition.csv",
        icon=":material/badge:",
        domain="Business",
        summary="700 employees with department, salary, experience, satisfaction, overtime and who left.",
        good_for="Why people quit — satisfaction and overtime carry the signal.",
    ),
    Sample(
        key="students",
        name="Student performance",
        filename="student_performance.csv",
        icon=":material/school:",
        domain="Education",
        summary="650 students with study hours, attendance, sleep, tutoring and their final score.",
        good_for="Clean, strong relationships — the easiest dataset to explain to a class.",
    ),
    Sample(
        key="health",
        name="Patient health records",
        filename="patient_health.csv",
        icon=":material/monitor_heart:",
        domain="Science",
        summary="768 patients with BMI, glucose, blood pressure, cholesterol and a diabetes outcome.",
        good_for="Health screening logic, and why correlation must not be read as cause.",
    ),
    Sample(
        key="weather",
        name="Daily weather",
        filename="weather_daily.csv",
        icon=":material/wb_sunny:",
        domain="Science",
        summary="A full year across five cities: temperature, humidity, wind, rainfall and condition.",
        good_for="Seasonality — the clearest time-series charts in the library.",
    ),
    Sample(
        key="housing",
        name="Housing prices",
        filename="housing_prices.csv",
        icon=":material/home_work:",
        domain="Business",
        summary="820 properties with area, bedrooms, age, location and price, including a few wild listings.",
        good_for="Price drivers, location premiums, and spotting outlier listings.",
    ),
    Sample(
        key="retail",
        name="Retail sales",
        filename="retail_sales_sample.csv",
        icon=":material/storefront:",
        domain="Business",
        summary="400 orders with region, channel, units, revenue and marketing spend. Has an empty and a constant column.",
        good_for="Showing off preprocessing — every cleaning step finds something to do.",
    ),
]

BY_KEY = {sample.key: sample for sample in LIBRARY}
DOMAINS = ["All", *dict.fromkeys(sample.domain for sample in LIBRARY)]


@st.cache_data(show_spinner=False, ttl="4h")
def load(key: str) -> pd.DataFrame:
    """Read one bundled sample into a dataframe."""
    sample = BY_KEY[key]
    if not sample.exists:
        raise FileNotFoundError(
            f"{sample.filename} is missing. Regenerate it with: python tools/make_samples.py"
        )
    return pd.read_csv(sample.path)


@st.cache_data(show_spinner=False, ttl="4h")
def shape_of(key: str) -> tuple[int, int]:
    """Row and column count, for the library cards."""
    try:
        frame = load(key)
    except FileNotFoundError:
        return (0, 0)
    return frame.shape


def available() -> list[Sample]:
    return [sample for sample in LIBRARY if sample.exists]
