import logging
import pymongo
import json
from datetime import datetime
from utils import format_datetime

# Load MongoDB configuration from downtime_query.json
CONFIG_PATH = "C:\\service-oee\\vMaxTranslator\\downtime_query.json"

def load_config():
    with open(CONFIG_PATH, "r") as file:
        config = json.load(file)
    return config["mongodb_config"]

# MongoDB connection setup (configured earlier)
config = load_config()
client = pymongo.MongoClient(config["mongodb_uri"])
db = client[config["database_name"]]
dt_collection = db["vMax_DowntimeRecords"]
mpo_collection = db["vMax_MPORecords"]

def fetch_downtime_data(start_date, end_date, site_ids=None, resource_ids=None, shifts=None, downtime_names=None, product_ids=None):
    start_dt = format_datetime(start_date)
    end_dt = format_datetime(end_date)

    logging.info(f"Querying from: {start_dt} to {end_dt}")

    query = {
        "FACTUALSTARTDATETIME": {"$gte": start_dt, "$lt": end_dt}
    }

    if site_ids:
        query["SITEID"] = {"$in": site_ids}  
        logging.info(f"Filtering by SiteIDs: {site_ids}")

    if resource_ids:
        query["FRESOURCEID"] = {"$in": resource_ids}
        logging.info(f"Filtering by ResourceIDs: {resource_ids}")

    if shifts:
        query["Shift"] = {"$in": shifts}
        logging.info(f"Filtering by Shifts: {shifts}")

    if downtime_names:
        query["FDOWNTIMENAME"] = {"$in": downtime_names}  
        logging.info(f"Filtering by Downtime Names: {downtime_names}")

    if product_ids:
        if isinstance(product_ids, list):
            query["FIDHID"] = {"$in": product_ids}
        else:
            query["FIDHID"] = product_ids
        logging.info(f"Filtering by Product IDs: {product_ids}")

    logging.info(f"Executing MongoDB Query: {query}")
    data = list(dt_collection.find(query).sort("FACTUALSTARTDATETIME", pymongo.ASCENDING))
    logging.info(f"Fetched {len(data)} records after filtering")
    return data

def fetch_top_products_from_mpo(fromdatetime, todatetime, site_ids, resource_ids=None):
    """
    Fetches the top 5 most occurring products from vMax_MPORecords.

    Args:
        fromdatetime (datetime): Start date-time.
        todatetime (datetime): End date-time.
        site_ids (list): List of Site IDs (SITEID) to filter by.
        resource_ids (list): List of resource IDs to filter by.

    Returns:
        list: List of top products with their occurrences.
    """
    logging.info(f"Querying MPO data from {fromdatetime} to {todatetime} (Python Datetime)")

    # Ensure datetime objects are used directly
    query = {
        "FPOSTARTDATETIME": {"$gte": fromdatetime},
        "FPOENDDATETIME": {"$lte": todatetime},
        "SITEID": {"$in": site_ids}  # Filter by SiteID (FSITEID)
    }

    if resource_ids:
        query["FRESOURCEID"] = {"$in": resource_ids}

    logging.info(f"Executing MongoDB Query: {query}")

    # Fetch data from MPO collection
    data = list(mpo_collection.find(query))

    if not data:
        logging.warning("No data found for products")
        return []

    logging.info(f"Fetched {len(data)} records for products from MPO")
    return data


def fetch_recommended_rate_data(fromdatetime, todatetime, site_ids, resource_ids=None):
    query = {
        "FPOSTARTDATETIME": {"$gte": fromdatetime},
        "FPOENDDATETIME": {"$lte": todatetime},
        "Availability": {"$gt": 0.85},
        "Performance": {"$gt": 0.85},
        "Quality": {"$gt": 0.85},
        "SITEID": {"$in": site_ids}  # **New line added to filter by SiteID (SITEID)**
    }

    if resource_ids:
        query["FRESOURCEID"] = {"$in": resource_ids}

    logging.info(f"Querying MPO data for recommended rates with query: {query}")

    data = list(mpo_collection.find(query))

    if not data:
        logging.warning("No data found for recommended rate")
        return None

    return data

def fetch_mpo_data(fromdatetime, todatetime, site_ids, resource_ids=None):
    """ Fetch MPO data from MongoDB for the specified date range, site IDs, and resource IDs """
    
    # Ensure fromdatetime and todatetime are datetime objects
    if isinstance(fromdatetime, str):
        fromdatetime = datetime.strptime(fromdatetime, "%Y%m%d%H%M%S")
    if isinstance(todatetime, str):
        todatetime = datetime.strptime(todatetime, "%Y%m%d%H%M%S")
    
    # Log the dates to verify correct parsing
    logging.info(f"From datetime: {fromdatetime}")
    logging.info(f"To datetime: {todatetime}")

    # MongoDB expects ISO 8601 format (without timezone adjustment, if not needed)
    query = {
        "FPOSTARTDATETIME": {"$gte": fromdatetime},
        "FPOENDDATETIME": {"$lte": todatetime},
        "SITEID": {"$in": site_ids}  # Ensure SITEID is used correctly
    }

    if resource_ids:
        query["FRESOURCEID"] = {"$in": resource_ids}
    
    logging.info(f"Fetching MPO data with query: {query}")
    mpo_data = list(mpo_collection.find(query))

    if not mpo_data:
        logging.warning("No MPO data found")
        return None

    # Debugging: Log a sample of fetched MPO data
    logging.info(f"Fetched {len(mpo_data)} MPO records from MongoDB")
    logging.debug(f"Sample MPO data: {mpo_data[:5]}")  # Log the first few records

    return mpo_data