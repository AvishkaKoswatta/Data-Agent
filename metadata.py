import os
import json
import pandas as pd
import boto3
from io import BytesIO
import s3fs
import re
from dotenv import load_dotenv

# =========================
# LOAD ENV VARIABLES
# =========================
load_dotenv()

# =========================
# AWS S3 CLIENT
# =========================
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="ap-south-1"
)

# =========================
# CONFIG
# =========================
CSV_FILES = {
    "orders": "List_of_Orders.csv",
    "order_details": "Order_Details.csv"
}

# =========================
# STEP 1: GET LATEST FOLDER
# =========================
def get_latest_folder(bucket):
    fs = s3fs.S3FileSystem()
    paths = fs.ls(bucket)

    pattern = r"\d{4}_\d{2}_\d{2}"
    folders = []

    for p in paths:
        name = p.split("/")[-1]
        if re.match(pattern, name):
            folders.append(name)

    if not folders:
        raise Exception("No valid date folders found in S3")

    return sorted(folders, reverse=True)[0]

# =========================
# STEP 2: LOAD CSVs FROM S3
# =========================
def load_csvs(bucket, folder):
    dfs = {}
    fs = s3fs.S3FileSystem()

    base_path = f"s3://{bucket}/{folder}"

    for name, file in CSV_FILES.items():
        s3_path = f"{base_path}/{file}"

        if not fs.exists(s3_path):
            raise FileNotFoundError(f"{s3_path} not found in S3")

        print(f"Reading from {s3_path}...")
        dfs[name] = pd.read_csv(s3_path, low_memory=False)

    return dfs

# =========================
# STEP 3: PREPROCESS DATA
# =========================
def preprocess_data(dfs):
    if "Order Date" in dfs["orders"].columns:
        dfs["orders"]["Order Date"] = pd.to_datetime(
            dfs["orders"]["Order Date"], format="%d-%m-%Y"
        )
    return dfs

# =========================
# STEP 4: CREATE MASTER TABLE
# =========================
def create_master_table(dfs):
    return dfs["orders"].merge(dfs["order_details"], on="Order ID")

# =========================
# STEP 5: SAVE PICKLE TO S3
# =========================
def save_pickle(df, bucket, folder):
    buffer = BytesIO()
    df.to_pickle(buffer)
    buffer.seek(0)

    key = f"{folder}/master.pkl"

    s3.upload_fileobj(buffer, bucket, key)

    print(f"Saved master → s3://{bucket}/{key}")

# =========================
# STEP 6: GENERATE METADATA (ROBUST)
# =========================
def generate_metadata(df, table_name="master"):

    def safe(val):
        if pd.isna(val):
            return None
        if isinstance(val, pd.Timestamp):
            return val.isoformat()
        return val

    columns = []
    hints = []

    for col in df.columns:
        col_data = df[col]

        columns.append({
            "name": col,
            "dtype": str(col_data.dtype)
        })

        c = col.lower()

        if "customer" in c:
            hints.append(f"{col} identifies customers")
        elif "date" in c:
            hints.append(f"{col} is a datetime field")
        elif "amount" in c or "price" in c:
            hints.append(f"{col} represents monetary value")
        elif "profit" in c:
            hints.append(f"{col} can be negative or positive")
        elif "quantity" in c:
            hints.append(f"{col} represents count of items")
        elif "category" in c:
            hints.append(f"{col} is a product dimension")

    hints = list(set(hints))

    sample = df.head(3).copy()
    sample = sample.apply(lambda col: col.map(safe))
    sample = sample.to_dict(orient="records")

    metadata = {
        table_name: {
            "columns": columns,
            "row_count": len(df),
            "sample": sample,
            "description": f"Dataset containing {len(df)} rows and {len(df.columns)} columns for analytical processing.",
            "hints": hints
        }
    }

    return metadata

# =========================
# STEP 7: SAVE REGISTRY TO S3
# =========================
def save_registry_s3(metadata, bucket, folder):
    key = f"{folder}/df_registry.json"

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(metadata, indent=4),
        ContentType="application/json"
    )

    print(f"Saved registry → s3://{bucket}/{key}")

# =========================
# MAIN PIPELINE
# =========================
def main():
    bucket = os.getenv("S3_BUCKET_NAME")

    if not bucket:
        raise ValueError("S3_BUCKET_NAME not set")

    print("Getting latest folder...")
    latest_folder = get_latest_folder(bucket)

    print("Loading CSV files...")
    dfs = load_csvs(bucket, latest_folder)

    print("Preprocessing...")
    dfs = preprocess_data(dfs)

    print("Creating master table...")
    master_df = create_master_table(dfs)

    print("Saving pickle...")
    save_pickle(master_df, bucket, latest_folder)

    print("Generating metadata...")
    registry = generate_metadata(master_df)

    print("Saving registry...")
    save_registry_s3(registry, bucket, latest_folder)

    print("Done ✅")

if __name__ == "__main__":
    main()