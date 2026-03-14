import pandas as pd

def load_data():

    df = pd.read_csv("data/traffic_data.csv")

    return df


def calculate_traffic_level(row):

    ratio = row["vehicles"] / row["capacity"]

    if ratio < 0.5:
        return "Low"

    elif ratio <= 1:
        return "Moderate"

    else:
        return "High"