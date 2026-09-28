"""Regenerate the bundled sample datasets.

Run with:  python tools/make_samples.py

Every file is synthetic but statistically realistic, and each one carries
deliberate imperfections - missing values, duplicate rows, untrimmed text,
outliers - so all five workflow stages have something real to do.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "sample_data"
OUT.mkdir(exist_ok=True)


def dirty(df: pd.DataFrame, rng, missing: dict[str, int] | None = None, dupes: int = 0) -> pd.DataFrame:
    """Punch holes and duplicates into a clean frame."""
    for column, count in (missing or {}).items():
        df.loc[rng.choice(len(df), count, replace=False), column] = np.nan
    if dupes:
        df = pd.concat([df, df.iloc[rng.choice(len(df), dupes, replace=False)]], ignore_index=True)
    return df.sample(frac=1, random_state=11).reset_index(drop=True)


def save(df: pd.DataFrame, name: str) -> None:
    path = OUT / name
    df.to_csv(path, index=False)
    print(f"{name:<34} {df.shape[0]:>5} rows x {df.shape[1]:>2} cols")


# ---------------------------------------------------------------- 1. titanic
def titanic(rng) -> pd.DataFrame:
    n = 891
    pclass = rng.choice([1, 2, 3], n, p=[0.24, 0.21, 0.55])
    sex = rng.choice(["male", "female"], n, p=[0.65, 0.35])
    age = np.round(np.clip(rng.normal(29.7, 14.5, n), 0.5, 80), 1)
    fare = np.round(np.where(pclass == 1, rng.gamma(4, 21, n), np.where(pclass == 2, rng.gamma(4, 5, n), rng.gamma(3, 4, n))), 2)
    # Survival follows the historical pattern: women and first class fared far better.
    odds = -1.1 + 1.0 * (pclass == 1) + 0.35 * (pclass == 2) + 2.5 * (sex == "female") - 0.012 * age
    survived = (rng.random(n) < 1 / (1 + np.exp(-odds))).astype(int)
    df = pd.DataFrame({
        "PassengerId": np.arange(1, n + 1),
        "Survived": survived,
        "Pclass": pclass,
        "Sex": sex,
        "Age": age,
        "SibSp": rng.choice([0, 1, 2, 3, 4], n, p=[0.68, 0.23, 0.05, 0.02, 0.02]),
        "Parch": rng.choice([0, 1, 2, 3], n, p=[0.76, 0.13, 0.09, 0.02]),
        "Fare": fare,
        "Embarked": rng.choice(["S", "C", "Q"], n, p=[0.72, 0.19, 0.09]),
        "Cabin": np.where(rng.random(n) < 0.23, [f"C{i}" for i in rng.integers(1, 148, n)], None),
    })
    return dirty(df, rng, missing={"Age": 177, "Embarked": 2, "Fare": 3}, dupes=5)


# ------------------------------------------------------------------- 2. tips
def tips(rng) -> pd.DataFrame:
    n = 244
    size = rng.choice([1, 2, 3, 4, 5, 6], n, p=[0.02, 0.64, 0.15, 0.15, 0.03, 0.01])
    total_bill = np.round(np.clip(rng.gamma(4.5, 1.3, n) * size * 1.6, 3, None), 2)
    tip = np.round(np.clip(total_bill * rng.normal(0.16, 0.04, n), 1, None), 2)
    df = pd.DataFrame({
        "total_bill": total_bill,
        "tip": tip,
        "sex": rng.choice(["Male", "Female"], n, p=[0.64, 0.36]),
        "smoker": rng.choice(["No", "Yes"], n, p=[0.62, 0.38]),
        "day": rng.choice(["Thur", "Fri", "Sat", "Sun"], n, p=[0.25, 0.08, 0.36, 0.31]),
        "time": rng.choice(["Lunch", "Dinner"], n, p=[0.28, 0.72]),
        "size": size,
    })
    return dirty(df, rng, missing={"tip": 6}, dupes=3)


# -------------------------------------------------------------- 3. ecommerce
def ecommerce(rng) -> pd.DataFrame:
    n = 1200
    categories = ["Electronics", "Apparel", "Home & Kitchen", "Beauty", "Sports", "Books"]
    category = rng.choice(categories, n, p=[0.24, 0.26, 0.18, 0.14, 0.11, 0.07])
    base = {"Electronics": 240, "Apparel": 45, "Home & Kitchen": 70, "Beauty": 28, "Sports": 90, "Books": 16}
    unit_price = np.round([max(2, rng.normal(base[c], base[c] * 0.35)) for c in category], 2)
    quantity = rng.choice([1, 2, 3, 4, 5], n, p=[0.55, 0.24, 0.12, 0.06, 0.03])
    discount = np.round(rng.choice([0, 0.05, 0.1, 0.15, 0.25], n, p=[0.5, 0.18, 0.16, 0.1, 0.06]), 2)
    revenue = np.round(unit_price * quantity * (1 - discount), 2)
    shipping_days = np.clip(rng.poisson(4, n) + 1, 1, None)
    rating = np.round(np.clip(5 - shipping_days * 0.18 + rng.normal(0.6, 0.8, n), 1, 5), 1)
    df = pd.DataFrame({
        "Order ID": [f"EC-{i:06d}" for i in range(1, n + 1)],
        "Order Date": (pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 540, n), unit="D")).strftime("%Y-%m-%d"),
        "Category": category,
        "Unit Price": unit_price,
        "Quantity": quantity,
        "Discount": discount,
        "Revenue": revenue,
        "Shipping Days": shipping_days,
        "Customer Rating": rating,
        "Country": rng.choice(["Pakistan", "UAE", "UK", "USA", "Canada", "Germany"], n, p=[0.34, 0.16, 0.14, 0.2, 0.09, 0.07]),
        "Payment Method": rng.choice(["Card", "COD", "Wallet", "Bank transfer"], n, p=[0.42, 0.3, 0.19, 0.09]),
        "Returned": rng.choice(["No", "Yes"], n, p=[0.91, 0.09]),
    })
    spikes = rng.choice(n, 8, replace=False)
    df.loc[spikes, "Revenue"] = df.loc[spikes, "Revenue"] * rng.uniform(6, 11, 8)
    df.loc[rng.choice(n, 40, replace=False), "Category"] = "  Apparel  "
    return dirty(df, rng, missing={"Customer Rating": 95, "Discount": 30, "Country": 14}, dupes=15)


# ------------------------------------------------------------ 4. agriculture
def agriculture(rng) -> pd.DataFrame:
    n = 900
    crops = ["Wheat", "Rice", "Cotton", "Sugarcane", "Maize"]
    crop = rng.choice(crops, n, p=[0.3, 0.24, 0.18, 0.14, 0.14])
    rainfall = np.round(np.clip(rng.normal(620, 180, n), 80, None), 1)
    temperature = np.round(rng.normal(27.5, 4.2, n), 1)
    fertilizer = np.round(np.clip(rng.normal(145, 42, n), 10, None), 1)
    pesticide = np.round(np.clip(rng.normal(3.1, 1.1, n), 0.2, None), 2)
    irrigation = np.round(np.clip(rng.normal(55, 18, n), 5, 100), 1)
    # Yield genuinely depends on rainfall, fertiliser and irrigation.
    crop_base = {"Wheat": 3.1, "Rice": 3.8, "Cotton": 2.2, "Sugarcane": 62.0, "Maize": 4.6}
    scale = np.array([crop_base[c] for c in crop])
    yield_t = np.round(
        scale * (0.55 + rainfall / 1400 + fertilizer / 900 + irrigation / 420 - np.abs(temperature - 26) / 90)
        * rng.normal(1.0, 0.09, n),
        2,
    )
    df = pd.DataFrame({
        "District": rng.choice(["Multan", "Faisalabad", "Sukkur", "Peshawar", "Quetta", "Sahiwal"], n),
        "Crop": crop,
        "Season": rng.choice(["Kharif", "Rabi"], n),
        "Year": rng.integers(2016, 2025, n),
        "Area Hectares": np.round(np.clip(rng.gamma(3, 14, n), 1, None), 1),
        "Rainfall mm": rainfall,
        "Avg Temp C": temperature,
        "Fertilizer kg per ha": fertilizer,
        "Pesticide kg per ha": pesticide,
        "Irrigation Coverage %": irrigation,
        "Yield tons per ha": yield_t,
    })
    return dirty(df, rng, missing={"Rainfall mm": 55, "Pesticide kg per ha": 70, "Irrigation Coverage %": 25}, dupes=10)


# ----------------------------------------------------------------- 5. crypto
def crypto(rng) -> pd.DataFrame:
    coins = {"Bitcoin": 62000, "Ethereum": 3100, "Solana": 145, "Cardano": 0.58, "Ripple": 0.62, "Dogecoin": 0.14}
    days = 220
    dates = pd.date_range("2025-01-01", periods=days, freq="D")
    frames = []
    for coin, start_price in coins.items():
        # Correlated random walk: the whole market drifts together.
        market = np.cumsum(rng.normal(0, 0.012, days))
        idio = np.cumsum(rng.normal(0, 0.018, days))
        price = start_price * np.exp(market + idio)
        volume = np.round(price * rng.gamma(4, 18000, days), 0)
        frames.append(pd.DataFrame({
            "Date": dates.strftime("%Y-%m-%d"),
            "Coin": coin,
            "Price USD": np.round(price, 4),
            "Market Cap USD": np.round(price * rng.uniform(1.4e7, 2.1e7, days), 0),
            "Volume 24h USD": volume,
            "Change 24h %": np.round(np.concatenate([[0], np.diff(price) / price[:-1] * 100]), 2),
            "Circulating Supply": np.round(rng.uniform(1.4e7, 2.1e7, days), 0),
        }))
    df = pd.concat(frames, ignore_index=True)
    return dirty(df, rng, missing={"Volume 24h USD": 60, "Change 24h %": 12}, dupes=18)


# -------------------------------------------------------------------- 6. hr
def hr(rng) -> pd.DataFrame:
    n = 700
    departments = ["Engineering", "Sales", "Marketing", "Operations", "Finance", "HR"]
    department = rng.choice(departments, n, p=[0.32, 0.22, 0.13, 0.17, 0.09, 0.07])
    experience = np.round(np.clip(rng.gamma(2.4, 2.6, n), 0, 35), 1)
    base = {"Engineering": 95, "Sales": 68, "Marketing": 66, "Operations": 58, "Finance": 78, "HR": 55}
    salary = np.round([max(28, rng.normal(base[d] + 4.8 * e, 12)) for d, e in zip(department, experience)], 0) * 1000
    satisfaction = np.round(np.clip(rng.normal(3.5, 0.9, n) + experience * 0.02, 1, 5), 2)
    overtime = rng.choice(["No", "Yes"], n, p=[0.72, 0.28])
    odds = 1.6 - 0.55 * satisfaction - 0.06 * experience + 0.8 * (overtime == "Yes")
    df = pd.DataFrame({
        "Employee ID": [f"EMP-{i:04d}" for i in range(1, n + 1)],
        "Department": department,
        "Age": np.round(np.clip(22 + experience + rng.normal(4, 3, n), 21, 64), 0),
        "Gender": rng.choice(["Male", "Female"], n, p=[0.61, 0.39]),
        "Years Experience": experience,
        "Annual Salary": salary,
        "Satisfaction Score": satisfaction,
        "Training Hours": np.round(np.clip(rng.normal(28, 12, n), 0, None), 0),
        "Overtime": overtime,
        "Remote Days per Week": rng.choice([0, 1, 2, 3, 5], n, p=[0.3, 0.2, 0.24, 0.16, 0.1]),
        "Attrition": np.where(rng.random(n) < 1 / (1 + np.exp(-odds)), "Yes", "No"),
    })
    return dirty(df, rng, missing={"Satisfaction Score": 38, "Training Hours": 24}, dupes=8)


# --------------------------------------------------------------- 7. students
def students(rng) -> pd.DataFrame:
    n = 650
    study = np.round(np.clip(rng.normal(14, 5.5, n), 0, 40), 1)
    attendance = np.round(np.clip(rng.normal(82, 12, n), 30, 100), 1)
    previous = np.round(np.clip(rng.normal(64, 14, n), 10, 100), 1)
    sleep = np.round(np.clip(rng.normal(6.9, 1.1, n), 3, 11), 1)
    final = np.round(np.clip(
        0.42 * previous + 1.15 * study + 0.22 * attendance + 1.8 * sleep + rng.normal(0, 6, n) - 12, 0, 100), 1)
    df = pd.DataFrame({
        "Student ID": [f"STU-{i:04d}" for i in range(1, n + 1)],
        "Gender": rng.choice(["Male", "Female"], n, p=[0.52, 0.48]),
        "Study Hours per Week": study,
        "Attendance %": attendance,
        "Previous Score": previous,
        "Sleep Hours": sleep,
        "Tutoring Sessions": rng.choice([0, 1, 2, 3, 4], n, p=[0.42, 0.26, 0.17, 0.1, 0.05]),
        "Internet Access": rng.choice(["Yes", "No"], n, p=[0.86, 0.14]),
        "Parental Education": rng.choice(["High school", "Bachelor", "Master", "None"], n, p=[0.38, 0.32, 0.14, 0.16]),
        "Extracurricular": rng.choice(["Yes", "No"], n, p=[0.45, 0.55]),
        "Final Score": final,
    })
    return dirty(df, rng, missing={"Previous Score": 31, "Sleep Hours": 18, "Parental Education": 22}, dupes=6)


# ----------------------------------------------------------------- 8. health
def health(rng) -> pd.DataFrame:
    n = 768
    age = np.round(np.clip(rng.normal(45, 14, n), 18, 88), 0)
    bmi = np.round(np.clip(rng.normal(28.4, 6.1, n), 14, None), 1)
    glucose = np.round(np.clip(rng.normal(112, 32, n) + bmi * 0.9, 50, None), 0)
    systolic = np.round(np.clip(rng.normal(124, 16, n) + age * 0.22, 80, None), 0)
    cholesterol = np.round(np.clip(rng.normal(198, 41, n), 90, None), 0)
    odds = -8.2 + 0.035 * glucose + 0.06 * bmi + 0.022 * age
    df = pd.DataFrame({
        "Patient ID": [f"PT-{i:04d}" for i in range(1, n + 1)],
        "Age": age,
        "Sex": rng.choice(["Male", "Female"], n, p=[0.48, 0.52]),
        "BMI": bmi,
        "Glucose mg/dL": glucose,
        "Systolic BP": systolic,
        "Diastolic BP": np.round(np.clip(systolic * 0.63 + rng.normal(0, 6, n), 50, None), 0),
        "Cholesterol mg/dL": cholesterol,
        "Smoker": rng.choice(["No", "Yes"], n, p=[0.74, 0.26]),
        "Physical Activity hrs/wk": np.round(np.clip(rng.gamma(2, 1.8, n), 0, None), 1),
        "Diabetes": np.where(rng.random(n) < 1 / (1 + np.exp(-odds)), "Yes", "No"),
    })
    return dirty(df, rng, missing={"Glucose mg/dL": 44, "Cholesterol mg/dL": 62, "BMI": 21}, dupes=9)


# ---------------------------------------------------------------- 9. weather
def weather(rng) -> pd.DataFrame:
    cities = {"Karachi": 27.5, "Lahore": 24.8, "Islamabad": 21.9, "Peshawar": 24.1, "Quetta": 16.2}
    days = 365
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    seasonal = -np.cos(np.linspace(0, 2 * np.pi, days)) * 9
    frames = []
    for city, mean_temp in cities.items():
        temp = np.round(mean_temp + seasonal + rng.normal(0, 2.6, days), 1)
        humidity = np.round(np.clip(78 - (temp - mean_temp) * 1.6 + rng.normal(0, 9, days), 12, 100), 1)
        rain = np.round(np.where(rng.random(days) < 0.17, rng.gamma(2, 7, days), 0), 1)
        frames.append(pd.DataFrame({
            "Date": dates.strftime("%Y-%m-%d"),
            "City": city,
            "Temp C": temp,
            "Humidity %": humidity,
            "Wind kmh": np.round(np.clip(rng.gamma(3, 4, days), 0, None), 1),
            "Rainfall mm": rain,
            "Pressure hPa": np.round(rng.normal(1010, 6, days), 1),
            "Condition": np.where(rain > 4, "Rain", np.where(humidity > 72, "Cloudy", "Clear")),
        }))
    df = pd.concat(frames, ignore_index=True)
    return dirty(df, rng, missing={"Humidity %": 70, "Pressure hPa": 40}, dupes=20)


# ---------------------------------------------------------------- 10. housing
def housing(rng) -> pd.DataFrame:
    n = 820
    area = np.round(np.clip(rng.gamma(5, 320, n), 350, None), 0)
    bedrooms = np.clip((area / 620 + rng.normal(0, 0.7, n)).round(), 1, 7).astype(int)
    bathrooms = np.clip((bedrooms * 0.7 + rng.normal(0, 0.5, n)).round(), 1, 5).astype(int)
    age_years = np.round(np.clip(rng.gamma(2, 6, n), 0, 60), 0)
    location = rng.choice(["DHA", "Gulberg", "Bahria Town", "Model Town", "Johar Town"], n, p=[0.22, 0.2, 0.24, 0.16, 0.18])
    premium = {"DHA": 1.55, "Gulberg": 1.32, "Bahria Town": 1.1, "Model Town": 1.2, "Johar Town": 1.0}
    price = np.round(
        (area * 9200 + bedrooms * 850000 + bathrooms * 420000 - age_years * 145000)
        * np.array([premium[loc] for loc in location]) * rng.normal(1.0, 0.11, n), -3)
    df = pd.DataFrame({
        "Property ID": [f"PR-{i:04d}" for i in range(1, n + 1)],
        "Location": location,
        "Area sqft": area,
        "Bedrooms": bedrooms,
        "Bathrooms": bathrooms,
        "Age Years": age_years,
        "Floors": rng.choice([1, 2, 3], n, p=[0.42, 0.46, 0.12]),
        "Parking Spaces": rng.choice([0, 1, 2, 3], n, p=[0.12, 0.44, 0.34, 0.1]),
        "Furnished": rng.choice(["No", "Semi", "Yes"], n, p=[0.48, 0.34, 0.18]),
        "Price PKR": np.clip(price, 1_500_000, None),
    })
    spikes = rng.choice(n, 7, replace=False)
    df.loc[spikes, "Price PKR"] = df.loc[spikes, "Price PKR"] * rng.uniform(3.5, 6, 7)
    return dirty(df, rng, missing={"Age Years": 29, "Parking Spaces": 18}, dupes=11)


# -------------------------------------------------------------- 11. retail
def retail(rng) -> pd.DataFrame:
    n = 400
    dates = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D")
    units = rng.poisson(28, n) + rng.integers(0, 12, n)
    unit_price = np.round(rng.normal(52, 11, n).clip(8, None), 2)
    revenue = units * unit_price * rng.normal(1.0, 0.04, n)
    spikes = rng.choice(n, 6, replace=False)
    revenue[spikes] *= rng.uniform(4, 7, 6)
    revenue = np.round(revenue, 2)
    df = pd.DataFrame({
        "Order ID": [f"ORD-{i:05d}" for i in range(1, n + 1)],
        "Order Date": [d.strftime("%Y-%m-%d") for d in dates],
        "Region": rng.choice(["North", "South", "East", "West", "Central"], n, p=[0.28, 0.22, 0.2, 0.18, 0.12]),
        "Channel": rng.choice(["Online", "Retail", "Wholesale"], n, p=[0.5, 0.35, 0.15]),
        "Units Sold": units,
        "Unit Price": unit_price,
        "Revenue": revenue,
        "Marketing Spend": np.round(revenue * rng.normal(0.11, 0.02, n).clip(0.03, None), 2),
        "Customer Satisfaction": np.round((units / units.max() * 2.0 + rng.normal(3.0, 0.5, n)).clip(1, 5), 2),
        "Currency": "USD",
        "Internal Note": [None] * n,
    })
    df.loc[rng.choice(n, 20, replace=False), "Channel"] = "  Online  "
    return dirty(df, rng, missing={"Marketing Spend": 34, "Customer Satisfaction": 18, "Region": 12}, dupes=9)


BUILDERS = [
    (titanic, "titanic_passengers.csv"),
    (tips, "restaurant_tips.csv"),
    (ecommerce, "ecommerce_orders.csv"),
    (agriculture, "agriculture_crop_yield.csv"),
    (crypto, "crypto_coin_prices.csv"),
    (hr, "employee_attrition.csv"),
    (students, "student_performance.csv"),
    (health, "patient_health.csv"),
    (weather, "weather_daily.csv"),
    (housing, "housing_prices.csv"),
    (retail, "retail_sales_sample.csv"),
]

if __name__ == "__main__":
    for index, (builder, filename) in enumerate(BUILDERS):
        save(builder(np.random.default_rng(100 + index)), filename)
    print(f"\n{len(BUILDERS)} datasets written to {OUT}")
