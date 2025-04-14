import logging
import pandas as pd
from datetime import datetime

def parse_datetime(dt_string, dt_format="%Y%m%d%H%M%S"):
    """
    Parse a datetime string into a datetime object.
    
    Args:
        dt_string (str): The datetime string.
        dt_format (str): The expected format of the datetime string. Default: "%Y%m%d%H%M%S".
    
    Returns:
        datetime: The parsed datetime object.
    """
    try:
        return datetime.strptime(dt_string, dt_format)
    except Exception as e:
        logging.error(f"Error parsing datetime: {str(e)}")
        raise ValueError("Invalid datetime format")

def format_datetime(dt):
    """
    Convert Python datetime to MongoDB datetime format for querying.
    Returns datetime object to be used in MongoDB queries.
    """
    return dt

def filter_data(df, resource_ids=None, shifts=None, product_ids=None):
    """
    Filters data based on the provided conditions.
    
    Args:
        df (pd.DataFrame): DataFrame to filter.
        resource_ids (list): List of resource IDs to filter by.
        shifts (list): List of shifts to filter by.
        product_ids (list): List of product IDs to filter by.
    
    Returns:
        pd.DataFrame: Filtered DataFrame.
    """
    if resource_ids:
        df = df[df["FRESOURCEID"].isin(resource_ids)]
    if shifts:
        df = df[df["Shift"].isin(shifts)]
    if product_ids:
        df = df[df["FIDHID"].isin(product_ids)]
    
    return df

def process_downtime_data(dt_data, fromdatetime, todatetime):
    """ Filter and convert downtime data to a usable format """
    if not dt_data:
        return pd.DataFrame()

    # Convert to DataFrame
    dt_df = pd.DataFrame(dt_data)

    # Convert string timestamps to datetime objects
    dt_df["FACTUALSTARTDATETIME"] = pd.to_datetime(dt_df["FACTUALSTARTDATETIME"], format="%Y-%b-%d %I:%M:%S %p", errors="coerce")
    dt_df["FACTUALFINISHDATETIME"] = pd.to_datetime(dt_df["FACTUALFINISHDATETIME"], format="%Y-%b-%d %I:%M:%S %p", errors="coerce")
    dt_df.dropna(subset=["FACTUALSTARTDATETIME", "FACTUALFINISHDATETIME"], inplace=True)

    # Apply Python-based filtering
    dt_df = dt_df[(dt_df["FACTUALSTARTDATETIME"] >= fromdatetime) & (dt_df["FACTUALFINISHDATETIME"] <= todatetime)]
    
    logging.info(f"Filtered downtime records: {len(dt_df)}")
    return dt_df
