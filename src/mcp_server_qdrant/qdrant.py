import logging
import re
import uuid
from typing import Any
from datetime import datetime

from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient, models

from mcp_server_qdrant.embeddings.base import EmbeddingProvider
from mcp_server_qdrant.settings import METADATA_PATH

logger = logging.getLogger(__name__)

Metadata = dict[str, Any]
ArbitraryFilter = dict[str, Any]


class Entry(BaseModel):
    """
    A single entry in the Qdrant collection with enhanced metadata support.
    """

    content: str
    metadata: Metadata | None = None
    similarity_score: float | None = Field(default=None, description="Vector similarity score from Qdrant search")
    platform: str | None = Field(default=None, description="Detected social media platform")
    date: str | None = Field(default=None, description="Extracted or inferred date")
    
    def detect_platform(self) -> str:
        """
        Detect social media platform from content hashtags and keywords.
        """
        content_lower = self.content.lower()
        
        # Platform-specific hashtag patterns
        if any(tag in content_lower for tag in ['#twitter', '#tweet', '@']):
            return 'Twitter/X'
        elif any(tag in content_lower for tag in ['#instagram', '#insta', '#ig']):
            return 'Instagram'
        elif any(tag in content_lower for tag in ['#facebook', '#fb']):
            return 'Facebook'
        elif any(tag in content_lower for tag in ['#linkedin', '#in']):
            return 'LinkedIn'
        elif any(tag in content_lower for tag in ['#tiktok', '#fyp', '#foryou']):
            return 'TikTok'
        elif any(tag in content_lower for tag in ['#youtube', '#yt']):
            return 'YouTube'
        elif any(tag in content_lower for tag in ['#reddit', '/r/']):
            return 'Reddit'
        elif 'http' in content_lower:
            return 'Web/Blog'
        else:
            return 'Social Media'
    
    def extract_date(self) -> str | None:
        """
        Extract date information from content or metadata.
        """
        # Try to extract from metadata first
        if self.metadata:
            if 'date' in self.metadata:
                return str(self.metadata['date'])
            if 'timestamp' in self.metadata:
                return str(self.metadata['timestamp'])
            if 'created_at' in self.metadata:
                return str(self.metadata['created_at'])
        
        # Try to extract date patterns from content
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # M/D/YY or MM/DD/YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, self.content)
            if match:
                return match.group()
        
        return None
    
    def enrich_metadata(self) -> "Entry":
        """
        Enrich entry with platform and date detection if not already set.
        """
        if not self.platform:
            self.platform = self.detect_platform()
        
        if not self.date:
            self.date = self.extract_date()
            
        return self


class QdrantConnector:
    """
    Encapsulates the connection to a Qdrant server and all the methods to interact with it.
    :param qdrant_url: The URL of the Qdrant server.
    :param qdrant_api_key: The API key to use for the Qdrant server.
    :param collection_name: The name of the default collection to use. If not provided, each tool will require
                            the collection name to be provided.
    :param embedding_provider: The embedding provider to use.
    :param qdrant_local_path: The path to the storage directory for the Qdrant client, if local mode is used.
    """

    def __init__(
        self,
        qdrant_url: str | None,
        qdrant_api_key: str | None,
        collection_name: str | None,
        embedding_provider: EmbeddingProvider,
        qdrant_local_path: str | None = None,
        field_indexes: dict[str, models.PayloadSchemaType] | None = None,
    ):
        self._qdrant_url = qdrant_url.rstrip("/") if qdrant_url else None
        self._qdrant_api_key = qdrant_api_key
        self._default_collection_name = collection_name
        self._embedding_provider = embedding_provider
        self._client = AsyncQdrantClient(
            location=qdrant_url, api_key=qdrant_api_key, path=qdrant_local_path
        )
        self._field_indexes = field_indexes

    async def get_collection_names(self) -> list[str]:
        """
        Get the names of all collections in the Qdrant server.
        :return: A list of collection names.
        """
        response = await self._client.get_collections()
        return [collection.name for collection in response.collections]

    async def store(self, entry: Entry, *, collection_name: str | None = None):
        """
        Store some information in the Qdrant collection, along with the specified metadata.
        :param entry: The entry to store in the Qdrant collection.
        :param collection_name: The name of the collection to store the information in, optional. If not provided,
                                the default collection is used.
        """
        collection_name = collection_name or self._default_collection_name
        assert collection_name is not None
        await self._ensure_collection_exists(collection_name)

        # Embed the document
        # ToDo: instead of embedding text explicitly, use `models.Document`,
        # it should unlock usage of server-side inference.
        embeddings = await self._embedding_provider.embed_documents([entry.content])

        # Add to Qdrant
        vector_name = self._embedding_provider.get_vector_name()
        payload = {"document": entry.content, METADATA_PATH: entry.metadata}
        await self._client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=uuid.uuid4().hex,
                    vector={vector_name: embeddings[0]},
                    payload=payload,
                )
            ],
        )

    async def search(
        self,
        query: str,
        *,
        collection_name: str | None = None,
        limit: int = 10,
        query_filter: models.Filter | None = None,
    ) -> list[Entry]:
        """
        Find points in the Qdrant collection with similarity scores and enhanced metadata.
        :param query: The query to use for the search.
        :param collection_name: The name of the collection to search in, optional. If not provided,
                                the default collection is used.
        :param limit: The maximum number of entries to return.
        :param query_filter: The filter to apply to the query, if any.

        :return: A list of entries found with similarity scores and enhanced metadata.
        """
        collection_name = collection_name or self._default_collection_name
        assert collection_name is not None, "Collection name must be provided"
        
        collection_exists = await self._client.collection_exists(collection_name)
        if not collection_exists:
            return []

        # Embed the query
        # ToDo: instead of embedding text explicitly, use `models.Document`,
        # it should unlock usage of server-side inference.

        query_vector = await self._embedding_provider.embed_query(query)
        vector_name = self._embedding_provider.get_vector_name()

        # Search in Qdrant
        search_results = await self._client.query_points(
            collection_name=collection_name,
            query=query_vector,
            using=vector_name,
            limit=limit,
            query_filter=query_filter,
        )

        entries = []
        for result in search_results.points:
            # Handle potential None payload
            payload = result.payload or {}
            
            # Extract content with fallback
            content = payload.get("document") or payload.get("text", "")
            metadata = payload.get("metadata")
            
            # Create entry with similarity score
            entry = Entry(
                content=content,
                metadata=metadata,
                similarity_score=float(result.score) if result.score is not None else None,
            )
            
            # Enrich with platform and date detection
            entry = entry.enrich_metadata()
            entries.append(entry)

        return entries

    async def _ensure_collection_exists(self, collection_name: str):
        """
        Ensure that the collection exists, creating it if necessary.
        :param collection_name: The name of the collection to ensure exists.
        """
        collection_exists = await self._client.collection_exists(collection_name)
        if not collection_exists:
            # Create the collection with the appropriate vector size
            vector_size = self._embedding_provider.get_vector_size()

            # Use the vector name as defined in the embedding provider
            vector_name = self._embedding_provider.get_vector_name()
            await self._client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    vector_name: models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    )
                },
            )

            # Create payload indexes if configured

            if self._field_indexes:
                for field_name, field_type in self._field_indexes.items():
                    await self._client.create_payload_index(
                        collection_name=collection_name,
                        field_name=field_name,
                        field_schema=field_type,
                    )
