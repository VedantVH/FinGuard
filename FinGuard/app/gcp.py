from typing import Optional
import vertexai
from google.cloud import firestore, bigquery
from .config import config

_vertex_initialized = False
_firestore_client: Optional[firestore.Client] = None
_bigquery_client: Optional[bigquery.Client] = None

def init_vertex():
    global _vertex_initialized
    if not _vertex_initialized:
        vertexai.init(project=config.project_id, location=config.vertex_location)
        _vertex_initialized = True

def get_firestore() -> firestore.Client:
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.Client(project=config.project_id)
    return _firestore_client

def get_bigquery() -> bigquery.Client:
    global _bigquery_client
    if _bigquery_client is None:
        _bigquery_client = bigquery.Client(project=config.project_id)
    return _bigquery_client