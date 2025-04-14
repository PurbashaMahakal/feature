import logging
import pandas as pd
from datetime import datetime
from flask import Flask, jsonify, request

from utils import filter_data, process_downtime_data
from db_utils import fetch_downtime_data, fetch_top_products_from_mpo, fetch_recommended_rate_data, fetch_mpo_data
from logic_utils import aggregate_specific_downtime, aggregate_specific_product, process_downtime_pareto, aggregate_top_downtimes, aggregate_top_products, aggregate_top_products, calculate_recommended_rate, calculate_changeovers

# Configure logging to log to file and console
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("script_log.log"),
                        logging.StreamHandler()
                    ])

# Flask API Setup
app = Flask(__name__)

@app.route("/downtimepareto", methods=["POST"])
def get_downtime_pareto():
    try:
        logging.info(f"Full Request URL: {request.url}")
        logging.info(f"Base URL: {request.base_url}")

        data = request.get_json()
        site_id = data.get("SiteID")
        if not site_id:
            return jsonify({"error": "Missing required parameter: SiteID"}), 400
        site_ids = [int(site_id)]  # Ensure it's an integer for filtering

        fromdatetime = data.get("fromdatetime")
        todatetime = data.get("todatetime")
        resource_ids = data.get("ResourceIDs")
        shifts = data.get("Shifts")

        if not all([fromdatetime, todatetime]):
            logging.warning("Missing required parameters")
            return jsonify({"error": "Missing required parameters"}), 400

        fromdatetime = datetime.strptime(fromdatetime, "%Y%m%d%H%M%S")
        todatetime = datetime.strptime(todatetime, "%Y%m%d%H%M%S")

        data = fetch_downtime_data(fromdatetime, todatetime, site_ids, resource_ids, shifts)
        results = process_downtime_pareto(data)

        if not results:
            logging.info("No data found")
            return jsonify({"message": "No data found"}), 404

        return jsonify(results)

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/topdowntimes", methods=["POST"])
def get_top_downtimes():
    try:
        logging.info(f"Full Request URL: {request.url}")
        logging.info(f"Base URL: {request.base_url}")

        data = request.get_json()
        site_id = data.get("SiteID")
        if not site_id:
            return jsonify({"error": "Missing required parameter: SiteID"}), 400
        site_ids = [int(site_id)]  # Ensure it's an integer for filtering

        fromdatetime = data.get("fromdatetime")
        todatetime = data.get("todatetime")
        resource_ids = data.get("ResourceIDs")
        shifts = data.get("Shifts")

        if not all([fromdatetime, todatetime]):
            logging.warning("Missing required parameters")
            return jsonify({"error": "Missing required parameters"}), 400

        fromdatetime = datetime.strptime(fromdatetime, "%Y%m%d%H%M%S")
        todatetime = datetime.strptime(todatetime, "%Y%m%d%H%M%S")

        logging.info(f"Querying data from {fromdatetime} to {todatetime} (Python Datetime)")

        data = fetch_downtime_data(fromdatetime, todatetime, site_ids, resource_ids, shifts)
        df = pd.DataFrame(data)

        if df.empty:
            logging.warning("No downtime data found")
            return jsonify({"message": "No data found"}), 404

        top_by_occurrences = aggregate_top_downtimes(df, "Occurrences")
        top_by_downtime = aggregate_top_downtimes(df, "TotalDowntimeDuration")

        logging.info("Successfully aggregated top downtime data")
        return jsonify({
            "top_by_occurrences": top_by_occurrences,
            "top_by_duration": top_by_downtime
        })

    except Exception as e:
        logging.error(f"Error in /topdowntimes: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/topdtproducts", methods=["POST"])
def get_top_dt_products():
    try:
        logging.info(f"Full Request URL: {request.url}")
        logging.info(f"Base URL: {request.base_url}")

        data = request.get_json()
        site_id = data.get("SiteID")
        if not site_id:
            return jsonify({"error": "Missing required parameter: SiteID"}), 400
        site_ids = [int(site_id)]  # Ensure it's an integer for filtering

        fromdatetime = data.get("fromdatetime")
        todatetime = data.get("todatetime")
        resource_ids = data.get("ResourceIDs")
        shifts = data.get("Shifts")

        if not all([fromdatetime, todatetime]):
            logging.warning("Missing required parameters")
            return jsonify({"error": "Missing required parameters"}), 400

        fromdatetime = datetime.strptime(fromdatetime, "%Y%m%d%H%M%S")
        todatetime = datetime.strptime(todatetime, "%Y%m%d%H%M%S")

        logging.info(f"Querying data from {fromdatetime} to {todatetime} (Python Datetime)")

        data = fetch_downtime_data(fromdatetime, todatetime, site_ids, resource_ids, shifts)
        df = pd.DataFrame(data)

        if df.empty:
            logging.warning("No downtime data found")
            return jsonify({"message": "No data found"}), 404

        top_by_occurrences = aggregate_top_products(df, "Occurrences")
        top_by_downtime = aggregate_top_products(df, "TotalDowntimeDuration")

        logging.info("Successfully aggregated top product data")
        return jsonify({
            "top_by_occurrences": top_by_occurrences,
            "top_by_duration": top_by_downtime
        })

    except Exception as e:
        logging.error(f"Error in /topdtproducts: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/specificdt", methods=["POST"])
def get_specific_dt_plot():
    try:
        logging.info(f"Full Request URL: {request.url}")
        logging.info(f"Base URL: {request.base_url}")

        data = request.get_json()
        site_id = data.get("SiteID")
        if not site_id:
            return jsonify({"error": "Missing required parameter: SiteID"}), 400
        site_ids = [site_id]  # wrap in list to match Mongo query structure

        fromdatetime = data.get("fromdatetime")
        todatetime = data.get("todatetime")
        resource_ids = data.get("ResourceIDs")
        shifts = data.get("Shifts")
        downtime_names = data.get("DowntimeNames")  # Updated to accept multiple values

        if not all([fromdatetime, todatetime, downtime_names]):
            logging.warning("Missing required parameters")
            return jsonify({"error": "Missing required parameters"}), 400

        fromdatetime = datetime.strptime(fromdatetime, "%Y%m%d%H%M%S")
        todatetime = datetime.strptime(todatetime, "%Y%m%d%H%M%S")

        logging.info(f"Querying data from {fromdatetime} to {todatetime} (Python Datetime)")

        data = fetch_downtime_data(fromdatetime, todatetime, site_ids, resource_ids, shifts, downtime_names)
        df = pd.DataFrame(data)

        if df.empty:
            logging.warning("No downtime data found")
            return jsonify({"message": "No data found"}), 404

        top_by_occurrences = aggregate_specific_downtime(df, "Occurrences")
        top_by_downtime = aggregate_specific_downtime(df, "TotalDowntimeDuration")

        logging.info("Successfully aggregated specific downtime data")
        return jsonify({
            "top_by_occurrences": top_by_occurrences,
            "top_by_duration": top_by_downtime
        })

    except Exception as e:
        logging.error(f"Error in /specificdt: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/specificproduct", methods=["POST"])
def get_specific_product_plot():
    try:
        logging.info(f"Full Request URL: {request.url}")
        logging.info(f"Base URL: {request.base_url}")

        data = request.get_json()
        site_id = data.get("SiteID")
        if not site_id:
            return jsonify({"error": "Missing required parameter: SiteID"}), 400
        site_ids = [site_id]  # wrap in list to match Mongo query structure
        
        fromdatetime = data.get("fromdatetime")
        todatetime = data.get("todatetime")
        resource_ids = data.get("ResourceIDs")
        shifts = data.get("Shifts")
        product_ids = data.get("ProductIDs")  # Updated to accept multiple values

        if not all([fromdatetime, todatetime, product_ids]):
            logging.warning("Missing required parameters")
            return jsonify({"error": "Missing required parameters"}), 400

        fromdatetime = datetime.strptime(fromdatetime, "%Y%m%d%H%M%S")
        todatetime = datetime.strptime(todatetime, "%Y%m%d%H%M%S")

        logging.info(f"Querying data from {fromdatetime} to {todatetime} (Python Datetime)")

        data = fetch_downtime_data(fromdatetime, todatetime, site_ids, resource_ids, shifts, product_ids=product_ids)
        df = pd.DataFrame(data)

        if df.empty:
            logging.warning("No downtime data found")
            return jsonify({"message": "No data found"}), 404

        top_by_occurrences = aggregate_specific_product(df, "Occurrences")
        top_by_downtime = aggregate_specific_product(df, "TotalDowntimeDuration")

        logging.info("Successfully aggregated specific product data")
        return jsonify({
            "top_by_occurrences": top_by_occurrences,
            "top_by_duration": top_by_downtime
        })

    except Exception as e:
        logging.error(f"Error in /specificproduct: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/timevariabledt", methods=["POST"])
def get_timevariable_dt():
    try:
        logging.info(f"Full Request URL: {request.url}")
        logging.info(f"Base URL: {request.base_url}")

        data = request.get_json()
        site_id = data.get("SiteID")
        if not site_id:
            return jsonify({"error": "Missing required parameter: SiteID"}), 400
        site_ids = [site_id]  # wrap in list to match Mongo query structure

        fromdatetime = data.get("fromdatetime")
        todatetime = data.get("todatetime")
        resource_ids = data.get("ResourceIDs")
        shifts = data.get("Shifts")
        downtime_names = data.get("DowntimeNames")
        product_ids = data.get("ProductIDs")
        monthwise = data.get("monthwise", True)  # Default is month-wise

        if not all([fromdatetime, todatetime]):
            logging.warning("Missing required parameters")
            return jsonify({"error": "Missing required parameters"}), 400

        # Convert date strings to datetime objects
        fromdatetime = datetime.strptime(fromdatetime, "%Y%m%d%H%M%S")
        todatetime = datetime.strptime(todatetime, "%Y%m%d%H%M%S")
        
        logging.info(f"Querying data from {fromdatetime} to {todatetime} (Python Datetime)")

        # Fetch filtered downtime data
        data = fetch_downtime_data(fromdatetime, todatetime, site_ids, resource_ids, shifts)
        # Convert to DataFrame
        df = pd.DataFrame(data)

        if df.empty:
            logging.warning("No data found")
            return jsonify({"message": "No data found"}), 404

        # Apply additional filtering
        df = filter_data(df, resource_ids, shifts, product_ids)

        if downtime_names:
            df = df[df["FDOWNTIMENAME"].isin(downtime_names)]

        if df.empty:
            logging.warning("No data found after filtering")
            return jsonify({"message": "No data found after filtering"}), 404

        # Convert FACTUALSTARTDATETIME to datetime format
        df["FACTUALSTARTDATETIME"] = pd.to_datetime(df["FACTUALSTARTDATETIME"])

        # Generate proper time period labels
        if monthwise:
            df["TimePeriod"] = df["FACTUALSTARTDATETIME"].dt.strftime("%B %Y")  # Ex: "March 2024"
        else:
            df["TimePeriod"] = df["FACTUALSTARTDATETIME"].dt.to_period("W").apply(
                lambda x: x.start_time.strftime("%b %d, %Y")
            )  # Ex: "Mar 24, 2024"

        # Aggregate occurrences and downtime duration per time period
        aggregated_df = df.groupby("TimePeriod").agg(
            TotalDowntimeDuration=("FDURATION", "sum"),
            Occurrences=("FDURATION", "count")
        ).reset_index()

        # Convert to JSON-friendly format
        response_data = {
            "TimePeriods": aggregated_df["TimePeriod"].tolist(),
            "Occurrences": aggregated_df["Occurrences"].astype(int).tolist(),
            "TotalDowntimeDuration": aggregated_df["TotalDowntimeDuration"].astype(float).tolist()
        }

        logging.info("Successfully aggregated time variable data")
        return jsonify(response_data)

    except Exception as e:
        logging.error(f"Error in /timevariabledt: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/topproducts", methods=["POST"])
def get_top_products():
    try:
        logging.info(f"Full Request URL: {request.url}")
        logging.info(f"Base URL: {request.base_url}")

        data = request.get_json()
        site_id = data.get("SiteID")
        if not site_id:
            return jsonify({"error": "Missing required parameter: SiteID"}), 400
        site_ids = [int(site_id)]  # Ensure it's an integer for filtering

        # Ensure the date-time strings are converted to datetime objects
        fromdatetime = datetime.strptime(data.get("fromdatetime"), "%Y%m%d%H%M%S")
        todatetime = datetime.strptime(data.get("todatetime"), "%Y%m%d%H%M%S")
        resource_ids = data.get("ResourceIDs")

        logging.info(f"Querying MPO data from {fromdatetime} to {todatetime} (Python Datetime)")

        mpo_data = fetch_top_products_from_mpo(fromdatetime, todatetime, site_ids, resource_ids)
        
        if not data:
            logging.warning("No data found for products")
            return jsonify({"message": "No data found"}), 404

        # Convert data to DataFrame and aggregate by product ID (FIDHID) and count occurrences
        df = pd.DataFrame(mpo_data)
        aggregated_df = df.groupby("FIDHID").size().reset_index(name="Occurrences")
        aggregated_df = aggregated_df.sort_values(by="Occurrences", ascending=False).head(5)

        logging.info("Successfully aggregated top products data")

        response = {
            "ProductIDs": aggregated_df["FIDHID"].tolist(),
            "Occurrences": [int(val) for val in aggregated_df["Occurrences"].tolist()]
        }

        return jsonify(response)

    except Exception as e:
        logging.error(f"Error in /topproducts: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/recommendedrate", methods=["POST"])
def get_recommended_rate():
    try:
        logging.info(f"Full Request URL: {request.url}")
        logging.info(f"Base URL: {request.base_url}")

        data = request.get_json()
        site_id = data.get("SiteID")
        if not site_id:
            return jsonify({"error": "Missing required parameter: SiteID"}), 400
        site_ids = [site_id]  # wrap in list to match Mongo query structure

        fromdatetime = data.get("fromdatetime")
        todatetime = data.get("todatetime")
        resource_ids = data.get("ResourceIDs")

        if not all([fromdatetime, todatetime]):
            logging.warning("Missing required parameters")
            return jsonify({"error": "Missing required parameters"}), 400

        fromdatetime = datetime.strptime(fromdatetime, "%Y%m%d%H%M%S")
        todatetime = datetime.strptime(todatetime, "%Y%m%d%H%M%S")

        logging.info(f"Querying data from {fromdatetime} to {todatetime} (Python Datetime)")

        # Fetch data from MongoDB using the refactored function, passing site_ids for filtering
        data = fetch_recommended_rate_data(fromdatetime, todatetime, site_ids, resource_ids)

        if not data:
            logging.warning("No data found for recommended rate")
            return jsonify({"message": "No data found"}), 404

        # Calculate recommended rate using the refactored function
        recommended_rates = calculate_recommended_rate(data)

        logging.info(f"Successfully calculated recommended rates for {len(recommended_rates)} products")

        return jsonify(recommended_rates)

    except Exception as e:
        logging.error(f"Error in /recommendedrate: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/changeovers", methods=["POST"])
def get_changeovers():
    try:
        logging.info("Received request for /changeovers")
        data = request.get_json()
        logging.info(f"Request Payload: {data}")

        site_id = data.get("SiteID")
        if not site_id:
            return jsonify({"error": "Missing required parameter: SiteID"}), 400
        site_ids = [int(site_id)]  # Ensure it's an integer for filtering

        fromdatetime = data.get("fromdatetime")
        todatetime = data.get("todatetime")
        resource_ids = data.get("ResourceIDs")

        if not all([fromdatetime, todatetime]):
            logging.warning("Missing required parameters")
            return jsonify({"error": "Missing required parameters"}), 400

        # Check if fromdatetime and todatetime are already datetime objects
        if isinstance(fromdatetime, str):
            fromdatetime = datetime.strptime(fromdatetime, "%Y%m%d%H%M%S")
        if isinstance(todatetime, str):
            todatetime = datetime.strptime(todatetime, "%Y%m%d%H%M%S")
        
        logging.info(f"Filtering data from {fromdatetime} to {todatetime} (Python Datetime)")

        # Fetch MPO and Downtime data, passing site_ids for filtering
        mpo_data = fetch_mpo_data(fromdatetime, todatetime, site_ids, resource_ids)
        dt_data = fetch_downtime_data(fromdatetime, todatetime, site_ids, resource_ids)

        if not mpo_data or not dt_data:
            logging.warning("No data found")
            return jsonify({"message": "No data found"}), 404

        # Process Downtime data
        dt_df = process_downtime_data(dt_data, fromdatetime, todatetime)

        # Calculate changeovers
        all_changeovers = calculate_changeovers(mpo_data, dt_df, fromdatetime, todatetime)

        return jsonify(all_changeovers)

    except Exception as e:
        logging.error(f"Error in /changeovers: {str(e)}")
        return jsonify({"error": str(e)}), 500

# "0.0.0.0" is used to expose the API to the network - takes all incoming requests
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)