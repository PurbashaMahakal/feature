import pandas as pd
import logging
from datetime import datetime, timedelta
def process_downtime_pareto(data):
    """
    Processes downtime data to generate a Pareto chart.

    Args:
        data (list): List of downtime records.

    Returns:
        list: Processed data for Pareto chart.
    """
    df = pd.DataFrame(data)
    if df.empty:
        return []

    grouped_df = df.groupby(["FRESOURCEID", "Shift", "FDOWNTIMENAME"]).agg({
        "FDURATION": ["sum", "count"]
    }).reset_index()

    grouped_df.columns = ["ResourceID", "Shift", "DowntimeNames", "TotalDowntimeDuration", "Occurrences"]

    grouped_df["TotalDowntimeDuration"] = grouped_df["TotalDowntimeDuration"].astype(float)
    grouped_df["Occurrences"] = grouped_df["Occurrences"].astype(int)

    processed_data = []

    for (resource, shift), group in grouped_df.groupby(["ResourceID", "Shift"]):
        sorted_data = sorted(
            group.to_dict(orient="records"),
            key=lambda x: x["Occurrences"],
            reverse=True
        )

        occurrences = [entry["Occurrences"] for entry in sorted_data]
        downtime_names = [entry["DowntimeNames"] for entry in sorted_data]
        total_durations = [entry["TotalDowntimeDuration"] for entry in sorted_data]

        total_occurrences = sum(occurrences) if occurrences else 1
        cumulative_percentages = [
            round(sum(occurrences[:i + 1]) / total_occurrences * 100, 2) for i in range(len(occurrences))
        ]

        processed_data.append({
            "ResourceID": int(resource),
            "Shift": shift,
            "DowntimeNames": downtime_names,
            "Occurrences": occurrences,
            "TotalDowntimeDuration": total_durations,
            "cumulative %": cumulative_percentages
        })

    return processed_data

def aggregate_top_downtimes(df, sort_by):
    if df.empty:
        logging.warning("DataFrame is empty in aggregate_top_downtimes")
        return {}

    aggregated_df = df.groupby("FDOWNTIMENAME").agg(
        TotalDowntimeDuration=("FDURATION", "sum"),
        Occurrences=("FDOWNTIMENAME", "count")
    ).reset_index()

    aggregated_df = aggregated_df.sort_values(by=sort_by, ascending=False).head(5)

    logging.info(f"Aggregated top downtime data by {sort_by}: {aggregated_df.head()}")
    
    return {
        "DowntimeNames": aggregated_df["FDOWNTIMENAME"].tolist(),
        "Occurrences": [int(val) for val in aggregated_df["Occurrences"].tolist()],
        "TotalDowntimeDuration": [float(val) for val in aggregated_df["TotalDowntimeDuration"].tolist()]
    }

def aggregate_top_products(df, sort_by):
    """
    Aggregates the top products based on the specified sorting criteria.

    Args:
        df (pd.DataFrame): DataFrame containing downtime records.
        sort_by (str): Column name to sort by, either "Occurrences" or "TotalDowntimeDuration".

    Returns:
        dict: Aggregated data with product IDs, occurrences, and total downtime duration.
    """
    if df.empty:
        logging.warning("DataFrame is empty in aggregate_top_products")
        return {}

    aggregated_df = df.groupby("FIDHID").agg(
        TotalDowntimeDuration=("FDURATION", "sum"),
        Occurrences=("FIDHID", "count")
    ).reset_index()

    aggregated_df = aggregated_df.sort_values(by=sort_by, ascending=False).head(5)

    logging.info(f"Aggregated top products data by {sort_by}: {aggregated_df.head()}")
    
    return {
        "ProductIDs": aggregated_df["FIDHID"].tolist(),
        "Occurrences": [int(val) for val in aggregated_df["Occurrences"].tolist()],
        "TotalDowntimeDuration": [float(val) for val in aggregated_df["TotalDowntimeDuration"].tolist()]
    }

def aggregate_specific_downtime(df, sort_by):
    """ Aggregates downtime occurrences for specific downtime names across products (FIDHID) """
    if df.empty:
        logging.warning("DataFrame is empty in aggregate_specific_downtime")
        return {}

    aggregated_df = df.groupby("FIDHID").agg(
        TotalDowntimeDuration=("FDURATION", "sum"),
        Occurrences=("FIDHID", "count")
    ).reset_index()

    aggregated_df = aggregated_df.sort_values(by=sort_by, ascending=False).head(10)

    logging.info(f"Aggregated specific downtime data by {sort_by}: {aggregated_df.head()}")

    return {
        "ProductIDs": aggregated_df["FIDHID"].tolist(),
        "Occurrences": [int(val) for val in aggregated_df["Occurrences"].tolist()],
        "TotalDowntimeDuration": [float(val) for val in aggregated_df["TotalDowntimeDuration"].tolist()]
    }

def aggregate_specific_product(df, sort_by):
    """ Aggregates downtime occurrences for specific product IDs across downtimes. """
    if df.empty:
        logging.warning("DataFrame is empty in aggregate_specific_product")
        return {}

    aggregated_df = df.groupby("FDOWNTIMENAME").agg(
        TotalDowntimeDuration=("FDURATION", "sum"),
        Occurrences=("FDOWNTIMENAME", "count")
    ).reset_index()

    aggregated_df = aggregated_df.sort_values(by=sort_by, ascending=False).head(10)

    logging.info(f"Aggregated specific product data by {sort_by}: {aggregated_df.head()}")
    
    return {
        "DowntimeNames": aggregated_df["FDOWNTIMENAME"].tolist(),
        "Occurrences": [int(val) for val in aggregated_df["Occurrences"].tolist()],
        "TotalDowntimeDuration": [float(val) for val in aggregated_df["TotalDowntimeDuration"].tolist()]
    }

def calculate_recommended_rate(data):
    """
    Calculates the recommended rate for products based on total quantity (finished + rejected).
    
    Args:
        data (list): List of MPO records containing product data.
    
    Returns:
        list: List of dictionaries containing the product ID, order number, and recommended rate.
    """
    df = pd.DataFrame(data)

    if df.empty:
        logging.warning("No data to calculate recommended rates")
        return []

    # Calculate total quantity
    df["TotalQty"] = df["FTOTALFINISHEDQTY"] + abs(df["FTOTALREJECTQTY"])

    recommended_rates = []
    for product_id, group_df in df.groupby("FIDHID"):
        # Find row with maximum TotalQty
        best_row = group_df.loc[group_df["TotalQty"].idxmax()]
        recommended_rates.append({
            "ProductID": product_id,
            "FAUFNR": best_row["FAUFNR"],
            "RecommendedRate": best_row["FACTUALRATE_WITH_DT"]
        })

    return recommended_rates

def calculate_changeovers(mpo_data, dt_data, fromdatetime, todatetime):
    """ Calculate the changeovers by comparing MPO and downtime data """
    all_changeovers = []
    manufacture_df = pd.DataFrame(mpo_data)
    dt_df = pd.DataFrame(dt_data)
    
    # Ensure FPOSTARTDATETIME and FPOENDDATETIME are in datetime format
    manufacture_df["FPOSTARTDATETIME"] = pd.to_datetime(manufacture_df["FPOSTARTDATETIME"], errors="coerce")
    manufacture_df["FPOENDDATETIME"] = pd.to_datetime(manufacture_df["FPOENDDATETIME"], errors="coerce")

    # Log the filtering action
    logging.info(f"Filtering MPO data from {fromdatetime} to {todatetime}")

    # Filter MPO data based on the provided date range
    manufacture_res = manufacture_df[
        (manufacture_df["FPOSTARTDATETIME"] >= fromdatetime) & 
        (manufacture_df["FPOENDDATETIME"] <= todatetime)
    ].sort_values(by="FPOSTARTDATETIME").reset_index(drop=True)

    logging.info(f"Filtered MPO data: {manufacture_res[['FAUFNR', 'FPOSTARTDATETIME', 'FPOENDDATETIME']].head()}")

    if manufacture_res.empty:
        logging.warning(f"No MPO data found within the date range {fromdatetime} to {todatetime}")
    
    resource_ids = manufacture_df["FRESOURCEID"].unique()
    logging.info(f"Processing {len(resource_ids)} unique resources")
    
    for resource_id in resource_ids:
        logging.info(f"Processing Resource: {resource_id}")
        manufacture_res_resource = manufacture_res[manufacture_res["FRESOURCEID"] == resource_id]
        dt_res = dt_df[dt_df["FRESOURCEID"] == resource_id]

        # Ensure FACTUALSTARTDATETIME and FACTUALFINISHDATETIME are in datetime format
        dt_res["FACTUALSTARTDATETIME"] = pd.to_datetime(dt_res["FACTUALSTARTDATETIME"], errors="coerce")
        dt_res["FACTUALFINISHDATETIME"] = pd.to_datetime(dt_res["FACTUALFINISHDATETIME"], errors="coerce")

        for i in range(len(manufacture_res_resource) - 1):
            before_po = manufacture_res_resource.iloc[i]["FAUFNR"]
            after_po = manufacture_res_resource.iloc[i + 1]["FAUFNR"]
            before_end = manufacture_res_resource.iloc[i]["FPOENDDATETIME"]
            after_start = manufacture_res_resource.iloc[i + 1]["FPOSTARTDATETIME"]

            logging.info(f"Before PO: {before_po}, After PO: {after_po}")
            logging.info(f"Before End: {before_end}, After Start: {after_start}")

            # Skip conversion if the variables are already datetime objects
            if isinstance(before_end, str):
                before_end = datetime.strptime(before_end, "%Y-%b-%d %I:%M:%S %p")
            if isinstance(after_start, str):
                after_start = datetime.strptime(after_start, "%Y-%b-%d %I:%M:%S %p")

            # Check if the variables are already datetime objects
            if not isinstance(before_end, datetime):
                logging.error(f"Expected datetime object for before_end but got {type(before_end)}")
                continue
            if not isinstance(after_start, datetime):
                logging.error(f"Expected datetime object for after_start but got {type(after_start)}")
                continue

            # Calculate the gap between orders in minutes
            gap_minutes = int(round((after_start - before_end).total_seconds() / 60))
            logging.info(f"Gap between orders: {gap_minutes} minutes")

            if gap_minutes <= 0:
                logging.warning(f"Invalid gap between orders: {gap_minutes} minutes (Before PO: {before_po}, After PO: {after_po})")
                continue  # Skip this changeover if the gap is invalid

            # Check if the gap is valid and there is downtime in the range
            if after_start > before_end:
                relevant_downtimes = dt_res[
                    (dt_res["FACTUALFINISHDATETIME"] >= before_end) & 
                    (dt_res["FACTUALSTARTDATETIME"] <= after_start)
                ].copy()

                logging.info(f"Relevant Downtimes: {relevant_downtimes[['FDOWNTIMENAME', 'FACTUALSTARTDATETIME', 'FACTUALFINISHDATETIME']].head()}")

                if not relevant_downtimes.empty:
                    all_changeovers.append({
                        "resource_id": int(resource_id),
                        "before_po": str(before_po),
                        "after_po": str(after_po),
                        "before_end": before_end.isoformat(),
                        "after_start": after_start.isoformat(),
                        "gap_minutes": gap_minutes,
                        "downtime_names": relevant_downtimes["FDOWNTIMENAME"].tolist(),
                        "downtime_durations": int(relevant_downtimes["FDURATION"].sum()),
                        "FDEPARTMENT": relevant_downtimes["FDEPARTMENT"].unique().tolist()
                    })
                else:
                    all_changeovers.append({
                        "resource_id": int(resource_id),
                        "before_po": str(before_po),
                        "after_po": str(after_po),
                        "before_end": before_end.isoformat(),
                        "after_start": after_start.isoformat(),
                        "gap_minutes": gap_minutes,
                        "downtime_names": ["No Downtime"],
                        "downtime_durations": 0,
                        "FDEPARTMENT": ["N/A"]
                    })

    logging.info(f"Processed {len(all_changeovers)} changeovers")
    return all_changeovers