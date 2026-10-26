import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv
load_dotenv()
import uuid

client=QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

from qdrant_client import models

COLLECTION_NAME = "medical_documents"
VECTOR_SIZE = 384


def initialize_collection():
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        )

    # Index patient_id for filtered searches
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="patient_id",
        field_schema=models.PayloadSchemaType.INTEGER,
        wait=True,
    )

def store_document_chunks(
    document_id: int,
    patient_id: int,
    chunks: list,
    embeddings,
):
    initialize_collection()

    points = []

    for index, chunk in enumerate(chunks):
        point_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"niramaya:{document_id}:{index}",
            )
        )

        points.append(
            models.PointStruct(
                id=point_id,
                vector=embeddings[index].tolist(),
                payload={
                    "document_id": document_id,
                    "patient_id": patient_id,
                    "chunk_index": index,
                    "text": chunk,
                },
            )
        )

    if points:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )

    return len(points)

def search_document_chunks(query_embedding,patient_id: int,limit: int = 5,):
    initialize_collection()
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding.tolist(),
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="patient_id",
                    match=models.MatchValue(value=patient_id),
                )
            ]
        ),
        limit=limit,
        with_payload=True,
    ).points

    return [
        {
            "document_id": point.payload["document_id"],
            "patient_id": point.payload["patient_id"],
            "chunk_index": point.payload["chunk_index"],
            "text": point.payload["text"],
            "score": point.score,
        }
        for point in results
    ]