"""
RAG (Retrieval Augmented Generation) service for the HR AI Assistant.

This service handles document indexing, semantic search, and context retrieval
for AI-powered responses using OpenSearch and sentence transformers.
"""

import os
import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError, RequestError

from app.config.opensearch import get_opensearch_client, opensearch_config
from app.models.document import Document
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RAGService:
    """
    Retrieval Augmented Generation service for document processing and search
    """
    
    def __init__(self):
        # Initialize embedding model
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "384"))
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "500"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "50"))
        
        # Initialize sentence transformer
        try:
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None
        
        # OpenSearch client
        self.client = None
        self.index_name = opensearch_config.index_name
    
    def _get_client(self) -> OpenSearch:
        """Get OpenSearch client instance"""
        if self.client is None:
            self.client = get_opensearch_client()
        return self.client
    
    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """
        Split text into overlapping chunks for better context retrieval
        
        Args:
            text: Text to chunk
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            List[str]: List of text chunks
        """
        if chunk_size is None:
            chunk_size = self.chunk_size
        if overlap is None:
            overlap = self.chunk_overlap
        
        # Clean and normalize text
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If we're not at the end, try to break at a sentence or word boundary
            if end < len(text):
                # Look for sentence boundary
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size * 0.5:
                    end = sentence_end + 1
                else:
                    # Look for word boundary
                    word_end = text.rfind(' ', start, end)
                    if word_end > start + chunk_size * 0.5:
                        end = word_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - overlap
            
            # Avoid infinite loop
            if start >= len(text):
                break
        
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks
        
        Args:
            texts: List of text strings
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        if not self.embedding_model:
            logger.error("Embedding model not available")
            return []
        
        try:
            embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []
    
    def index_document(self, document: Document, content: str) -> bool:
        """
        Index a document with its content and metadata
        
        Args:
            document: Document model instance
            content: Document text content
            
        Returns:
            bool: True if indexing successful, False otherwise
        """
        try:
            client = self._get_client()
            
            # Chunk the document content
            chunks = self.chunk_text(content)
            
            # Generate embeddings for chunks
            embeddings = self.generate_embeddings(chunks)
            
            if not embeddings:
                logger.error(f"Failed to generate embeddings for document {document.id}")
                return False
            
            # Index each chunk as a separate document
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_body = {
                    "title": document.title,
                    "content": content,
                    "document_type": document.document_type.value if document.document_type else "unknown",
                    "file_path": document.file_path,
                    "file_size": document.file_size,
                    "created_at": document.created_at.isoformat() if document.created_at else None,
                    "updated_at": document.updated_at.isoformat() if document.updated_at else None,
                    "tags": document.tags,
                    "embedding": embedding,
                    "chunk_id": i,
                    "chunk_text": chunk,
                    "document_id": document.id,
                    "access_level": document.access_level.value if document.access_level else "internal",
                    "author_id": document.author_id,
                    "metadata": {
                        "file_name": document.file_name,
                        "file_extension": document.file_extension,
                        "mime_type": document.mime_type,
                        "version": document.version,
                        "language": document.language
                    }
                }
                
                # Index the chunk
                doc_id = f"{document.id}_{i}"
                response = client.index(
                    index=self.index_name,
                    id=doc_id,
                    body=doc_body
                )
                
                if response.get("result") not in ["created", "updated"]:
                    logger.warning(f"Unexpected response for document {doc_id}: {response}")
            
            logger.info(f"Successfully indexed document {document.id} with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing document {document.id}: {e}")
            return False
    
    def remove_document_from_index(self, document_id: int) -> bool:
        """
        Remove a document and all its chunks from the index
        
        Args:
            document_id: Document ID to remove
            
        Returns:
            bool: True if removal successful, False otherwise
        """
        try:
            client = self._get_client()
            
            # Search for all chunks of this document
            search_body = {
                "query": {
                    "term": {
                        "document_id": document_id
                    }
                },
                "size": 1000  # Assuming no document has more than 1000 chunks
            }
            
            response = client.search(index=self.index_name, body=search_body)
            
            # Delete each chunk
            for hit in response["hits"]["hits"]:
                client.delete(index=self.index_name, id=hit["_id"])
            
            logger.info(f"Removed document {document_id} from index")
            return True
            
        except NotFoundError:
            logger.warning(f"Document {document_id} not found in index")
            return True
        except Exception as e:
            logger.error(f"Error removing document {document_id} from index: {e}")
            return False
    
    def semantic_search(self, query: str, limit: int = 5, min_score: float = 0.5, 
                       document_types: Optional[List[str]] = None,
                       access_levels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search using query embeddings
        
        Args:
            query: Search query
            limit: Maximum number of results
            min_score: Minimum similarity score
            document_types: Filter by document types
            access_levels: Filter by access levels
            
        Returns:
            List[Dict]: Search results with relevance scores
        """
        try:
            client = self._get_client()
            
            # Generate query embedding
            query_embedding = self.generate_embeddings([query])
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            query_vector = query_embedding[0]
            
            # Build search query
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": query_vector,
                                        "k": limit * 2  # Get more results for filtering
                                    }
                                }
                            }
                        ]
                    }
                },
                "size": limit * 2,
                "_source": {
                    "excludes": ["embedding"]  # Don't return embedding vectors
                }
            }
            
            # Add filters
            filters = []
            
            if document_types:
                filters.append({
                    "terms": {
                        "document_type": document_types
                    }
                })
            
            if access_levels:
                filters.append({
                    "terms": {
                        "access_level": access_levels
                    }
                })
            
            if filters:
                search_body["query"]["bool"]["filter"] = filters
            
            # Perform search
            response = client.search(index=self.index_name, body=search_body)
            
            # Process results
            results = []
            seen_documents = set()
            
            for hit in response["hits"]["hits"]:
                score = hit["_score"]
                source = hit["_source"]
                document_id = source.get("document_id")
                
                # Skip if score is too low
                if score < min_score:
                    continue
                
                # Avoid duplicate documents (prefer highest scoring chunk)
                if document_id in seen_documents:
                    continue
                
                seen_documents.add(document_id)
                
                results.append({
                    "document_id": document_id,
                    "title": source.get("title"),
                    "chunk_text": source.get("chunk_text"),
                    "chunk_id": source.get("chunk_id"),
                    "document_type": source.get("document_type"),
                    "file_name": source.get("metadata", {}).get("file_name"),
                    "relevance_score": score,
                    "metadata": source.get("metadata", {}),
                    "created_at": source.get("created_at")
                })
                
                if len(results) >= limit:
                    break
            
            logger.info(f"Semantic search returned {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []
    
    def hybrid_search(self, query: str, limit: int = 5, 
                     semantic_weight: float = 0.7,
                     keyword_weight: float = 0.3) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword search
        
        Args:
            query: Search query
            limit: Maximum number of results
            semantic_weight: Weight for semantic search results
            keyword_weight: Weight for keyword search results
            
        Returns:
            List[Dict]: Combined search results
        """
        try:
            # Get semantic search results
            semantic_results = self.semantic_search(query, limit * 2)
            
            # Get keyword search results
            keyword_results = self.keyword_search(query, limit * 2)
            
            # Combine and re-rank results
            combined_results = {}
            
            # Add semantic results
            for result in semantic_results:
                doc_id = result["document_id"]
                combined_results[doc_id] = result.copy()
                combined_results[doc_id]["combined_score"] = result["relevance_score"] * semantic_weight
                combined_results[doc_id]["semantic_score"] = result["relevance_score"]
                combined_results[doc_id]["keyword_score"] = 0
            
            # Add keyword results
            for result in keyword_results:
                doc_id = result["document_id"]
                if doc_id in combined_results:
                    # Update existing result
                    combined_results[doc_id]["combined_score"] += result["relevance_score"] * keyword_weight
                    combined_results[doc_id]["keyword_score"] = result["relevance_score"]
                else:
                    # Add new result
                    combined_results[doc_id] = result.copy()
                    combined_results[doc_id]["combined_score"] = result["relevance_score"] * keyword_weight
                    combined_results[doc_id]["semantic_score"] = 0
                    combined_results[doc_id]["keyword_score"] = result["relevance_score"]
            
            # Sort by combined score and return top results
            sorted_results = sorted(
                combined_results.values(),
                key=lambda x: x["combined_score"],
                reverse=True
            )
            
            return sorted_results[:limit]
            
        except Exception as e:
            logger.error(f"Error performing hybrid search: {e}")
            return self.semantic_search(query, limit)  # Fallback to semantic search
    
    def keyword_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform keyword-based search using full-text search
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List[Dict]: Search results
        """
        try:
            client = self._get_client()
            
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title^3",  # Boost title matches
                            "chunk_text^2",  # Boost content matches
                            "content",
                            "tags"
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                },
                "size": limit,
                "_source": {
                    "excludes": ["embedding"]
                }
            }
            
            response = client.search(index=self.index_name, body=search_body)
            
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                results.append({
                    "document_id": source.get("document_id"),
                    "title": source.get("title"),
                    "chunk_text": source.get("chunk_text"),
                    "chunk_id": source.get("chunk_id"),
                    "document_type": source.get("document_type"),
                    "file_name": source.get("metadata", {}).get("file_name"),
                    "relevance_score": hit["_score"],
                    "metadata": source.get("metadata", {}),
                    "created_at": source.get("created_at")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing keyword search: {e}")
            return []
    
    def get_relevant_context(self, query: str, max_context_length: int = 2000) -> Dict[str, Any]:
        """
        Get relevant context for a query to use in AI responses
        
        Args:
            query: User query
            max_context_length: Maximum length of context text
            
        Returns:
            Dict: Context information including text and metadata
        """
        try:
            # Perform hybrid search
            search_results = self.hybrid_search(query, limit=5)
            
            if not search_results:
                return {
                    "context_text": "",
                    "sources": [],
                    "relevance_score": 0,
                    "has_context": False
                }
            
            # Build context text from top results
            context_parts = []
            sources = []
            total_score = 0
            context_length = 0
            
            for result in search_results:
                chunk_text = result.get("chunk_text", "")
                
                # Check if adding this chunk exceeds max length
                if context_length + len(chunk_text) > max_context_length:
                    # Try to fit partial chunk
                    remaining_length = max_context_length - context_length
                    if remaining_length > 100:  # Only add if meaningful length remains
                        chunk_text = chunk_text[:remaining_length] + "..."
                        context_parts.append(chunk_text)
                    break
                
                context_parts.append(chunk_text)
                context_length += len(chunk_text)
                
                # Add source information
                sources.append({
                    "document_id": result.get("document_id"),
                    "title": result.get("title"),
                    "file_name": result.get("file_name"),
                    "document_type": result.get("document_type"),
                    "relevance_score": result.get("combined_score", result.get("relevance_score", 0))
                })
                
                total_score += result.get("combined_score", result.get("relevance_score", 0))
            
            # Calculate average relevance score
            avg_score = total_score / len(sources) if sources else 0
            
            return {
                "context_text": "\n\n".join(context_parts),
                "sources": sources,
                "relevance_score": avg_score,
                "has_context": len(context_parts) > 0,
                "num_sources": len(sources)
            }
            
        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return {
                "context_text": "",
                "sources": [],
                "relevance_score": 0,
                "has_context": False
            }
    
    def suggest_related_queries(self, query: str, limit: int = 5) -> List[str]:
        """
        Suggest related queries based on document content
        
        Args:
            query: Original query
            limit: Maximum number of suggestions
            
        Returns:
            List[str]: List of suggested queries
        """
        try:
            # Get relevant documents
            search_results = self.semantic_search(query, limit=10)
            
            # Extract key phrases from relevant documents
            suggestions = []
            seen_suggestions = set()
            
            for result in search_results:
                chunk_text = result.get("chunk_text", "")
                title = result.get("title", "")
                
                # Simple key phrase extraction (can be improved with NLP)
                phrases = self._extract_key_phrases(chunk_text, title)
                
                for phrase in phrases:
                    if phrase.lower() not in seen_suggestions and len(phrase) > 3:
                        suggestions.append(phrase)
                        seen_suggestions.add(phrase.lower())
                        
                        if len(suggestions) >= limit:
                            break
                
                if len(suggestions) >= limit:
                    break
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating query suggestions: {e}")
            return []
    
    def _extract_key_phrases(self, text: str, title: str = "") -> List[str]:
        """
        Extract key phrases from text for query suggestions
        
        Args:
            text: Text content
            title: Document title
            
        Returns:
            List[str]: Key phrases
        """
        phrases = []
        
        # Add title as a phrase
        if title:
            phrases.append(title)
        
        # Simple pattern-based phrase extraction
        # Look for phrases like "How to...", "What is...", etc.
        patterns = [
            r"(?:how to|what is|when should|where can|why does|which) [^.?!]+",
            r"[A-Z][a-z]+ (?:policy|procedure|process|guideline|requirement)",
            r"(?:annual|sick|vacation|maternity|paternity) leave",
            r"(?:employee|performance|salary|benefits|training) [a-z]+",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            phrases.extend(matches)
        
        # Clean and filter phrases
        cleaned_phrases = []
        for phrase in phrases:
            phrase = re.sub(r'[^\w\s]', '', phrase).strip()
            if 3 <= len(phrase) <= 50:
                cleaned_phrases.append(phrase)
        
        return cleaned_phrases[:10]  # Return top 10 phrases
    
    def get_index_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the document index
        
        Returns:
            Dict: Index statistics
        """
        try:
            client = self._get_client()
            
            # Get index stats
            stats = client.indices.stats(index=self.index_name)
            
            # Get document count by type
            type_aggregation = {
                "query": {"match_all": {}},
                "aggs": {
                    "document_types": {
                        "terms": {
                            "field": "document_type",
                            "size": 20
                        }
                    }
                },
                "size": 0
            }
            
            type_response = client.search(index=self.index_name, body=type_aggregation)
            
            return {
                "total_documents": stats["indices"][self.index_name]["total"]["docs"]["count"],
                "index_size_bytes": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
                "document_types": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in type_response["aggregations"]["document_types"]["buckets"]
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting index statistics: {e}")
            return {
                "total_documents": 0,
                "index_size_bytes": 0,
                "document_types": {},
                "last_updated": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def reindex_all_documents(self, documents: List[Document], contents: List[str]) -> Dict[str, Any]:
        """
        Reindex all documents (useful for index updates or migrations)
        
        Args:
            documents: List of document objects
            contents: List of document contents (same order as documents)
            
        Returns:
            Dict: Reindexing results
        """
        results = {
            "total": len(documents),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        for doc, content in zip(documents, contents):
            try:
                if self.index_document(doc, content):
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to index document {doc.id}")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Error indexing document {doc.id}: {str(e)}")
        
        logger.info(f"Reindexing completed: {results['successful']}/{results['total']} successful")
        return results

# Global RAG service instance
rag_service = RAGService()