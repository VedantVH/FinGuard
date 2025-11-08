from typing import List
from google.cloud import bigquery
from .gcp import get_bigquery
from .config import config
from .schemas import SourceItem
import csv
import os

def get_sources(topics: List[str], region: str | None) -> List[SourceItem]:
    client: bigquery.Client = get_bigquery()
    dataset = config.bigquery_dataset
    table = config.bq_table_sources
    topics = [t.lower() for t in topics if t]
    topics_param = topics or ["general"]

    query = f"""
    SELECT source_name, url, source_type, topic, region
    FROM `{config.project_id}.{dataset}.{table}`
    WHERE LOWER(topic) IN UNNEST(@topics)
       OR topic = 'general'
       OR (LOWER(topic) IN UNNEST(@topics) AND region = @region)
    LIMIT 12
    """
    job = client.query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("topics", "STRING", topics_param),
                bigquery.ScalarQueryParameter("region", "STRING", (region or "").upper()),
            ]
        ),
    )
    rows = list(job.result())
    items: List[SourceItem] = []
    for r in rows:
        items.append(SourceItem(
            source_name=r["source_name"],
            url=r["url"],
            source_type=r["source_type"],
            topic=r["topic"],
            region=r["region"]
        ))
    # Fallback to bundled CSV if BQ empty
    if not items:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "trusted_sources.csv")
        if os.path.exists(csv_path):
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("topic", "").lower() in topics_param or row.get("topic", "").lower() == "general":
                        items.append(SourceItem(
                            source_name=row["source_name"],
                            url=row["url"],
                            source_type=row.get("source_type",""),
                            topic=row.get("topic","general"),
                            region=row.get("region") or None
                        ))
                        if len(items) >= 10:
                            break
    return items[:10]