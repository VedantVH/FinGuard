import os
from google.cloud import bigquery
from app.config import config

def ensure_dataset(client: bigquery.Client):
    ds_id = f"{config.project_id}.{config.bigquery_dataset}"
    try:
        client.get_dataset(ds_id)
        print("Dataset exists:", ds_id)
    except Exception:
        ds = bigquery.Dataset(ds_id)
        ds.location = "US"
        client.create_dataset(ds)
        print("Created dataset:", ds_id)

def ensure_sources_table(client: bigquery.Client, csv_path: str):
    table_id = f"{config.project_id}.{config.bigquery_dataset}.{config.bq_table_sources}"
    schema = [
        bigquery.SchemaField("topic", "STRING"),
        bigquery.SchemaField("region", "STRING"),
        bigquery.SchemaField("source_name", "STRING"),
        bigquery.SchemaField("url", "STRING"),
        bigquery.SchemaField("source_type", "STRING"),
        bigquery.SchemaField("credibility_score", "FLOAT"),
    ]
    try:
        client.get_table(table_id)
        print("Sources table exists:", table_id)
    except Exception:
        table = bigquery.Table(table_id, schema=schema)
        client.create_table(table)
        print("Created sources table:", table_id)

    # Load CSV
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV, skip_leading_rows=1, autodetect=False, write_disposition="WRITE_TRUNCATE"
    )
    with open(csv_path, "rb") as f:
        load_job = client.load_table_from_file(f, table_id, job_config=job_config)
    load_job.result()
    print("Loaded sources from CSV")

def ensure_logs_table(client: bigquery.Client):
    table_id = f"{config.project_id}.{config.bigquery_dataset}.{config.bq_table_logs}"
    schema = [
        bigquery.SchemaField("ts", "TIMESTAMP"),
        bigquery.SchemaField("user_id", "STRING"),
        bigquery.SchemaField("phone", "STRING"),
        bigquery.SchemaField("message", "STRING"),
        bigquery.SchemaField("response", "STRING"),
        bigquery.SchemaField("verdict", "STRING"),
        bigquery.SchemaField("topics", "STRING", mode="REPEATED"),
        bigquery.SchemaField("risk_level", "STRING"),
        bigquery.SchemaField("sources", "STRING", mode="REPEATED"),
        bigquery.SchemaField("latency_ms", "INT64"),
        bigquery.SchemaField("model", "STRING"),
        bigquery.SchemaField("region", "STRING"),
        bigquery.SchemaField("action", "STRING"),
        bigquery.SchemaField("confidence", "FLOAT"),
    ]
    try:
        client.get_table(table_id)
        print("Logs table exists:", table_id)
    except Exception:
        table = bigquery.Table(table_id, schema=schema)
        client.create_table(table)
        print("Created logs table:", table_id)

if __name__ == "__main__":
    client = bigquery.Client(project=config.project_id)
    ensure_dataset(client)
    csv_path = os.path.join("data", "trusted_sources.csv")
    ensure_sources_table(client, csv_path)
    ensure_logs_table(client)
    print("BigQuery setup complete.")