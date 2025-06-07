"""
OpenSearch configuration for document indexing and search functionality.

This module handles OpenSearch connectivity and configuration for the
HR AI Assistant's RAG (Retrieval Augmented Generation) system.
"""

import os
from typing import Dict, Any, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import ConnectionError, RequestError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenSearch configuration
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))
OPENSEARCH_USERNAME = os.getenv("OPENSEARCH_USERNAME", "admin")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD", "admin")
OPENSEARCH_USE_SSL = os.getenv("OPENSEARCH_USE_SSL", "False").lower() == "true"
OPENSEARCH_VERIFY_CERTS = os.getenv("OPENSEARCH_VERIFY_CERTS", "False").lower() == "true"
OPENSEARCH_INDEX_NAME = os.getenv("OPENSEARCH_INDEX_NAME", "hr_documents")

class OpenSearchConfig:
    """OpenSearch configuration class"""
    
    def __init__(self):
        self.host = OPENSEARCH_HOST
        self.port = OPENSEARCH_PORT
        self.username = OPENSEARCH_USERNAME
        self.password = OPENSEARCH_PASSWORD
        self.use_ssl = OPENSEARCH_USE_SSL
        self.verify_certs = OPENSEARCH_VERIFY_CERTS
        self.index_name = OPENSEARCH_INDEX_NAME
        self.client = None
    
    def get_client_config(self) -> Dict[str, Any]:
        """Get OpenSearch client configuration"""
        config = {
            'hosts': [{'host': self.host, 'port': self.port}],
            'connection_class': RequestsHttpConnection,
            'use_ssl': self.use_ssl,
            'verify_certs': self.verify_certs,
            'ssl_show_warn': False,
            'timeout': 30,
            'max_retries': 3,
            'retry_on_timeout': True
        }
        
        if self.username and self.password:
            config['http_auth'] = (self.username, self.password)
        
        return config

# Global configuration instance
opensearch_config = OpenSearchConfig()

def get_opensearch_client() -> OpenSearch:
    """
    Get OpenSearch client instance.
    
    Returns:
        OpenSearch: Configured OpenSearch client
    """
    if opensearch_config.client is None:
        try:
            client_config = opensearch_config.get_client_config()
            opensearch_config.client = OpenSearch(**client_config)
            
            # Test connection
            if not opensearch_config.client.ping():
                raise ConnectionError("Failed to connect to OpenSearch")
                
            print("OpenSearch client initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize OpenSearch client: {e}")
            raise e
    
    return opensearch_config.client

def check_opensearch_connection() -> bool:
    """
    Check if OpenSearch connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        client = get_opensearch_client()
        return client.ping()
    except Exception as e:
        print(f"OpenSearch connection failed: {e}")
        return False

async def opensearch_health_check() -> Dict[str, Any]:
    """
    Perform OpenSearch health check for monitoring.
    
    Returns:
        dict: Health check status and details
    """
    try:
        client = get_opensearch_client()
        
        # Check cluster health
        health = client.cluster.health()
        
        # Check if index exists
        index_exists = client.indices.exists(index=opensearch_config.index_name)
        
        return {
            "status": "healthy" if health["status"] in ["green", "yellow"] else "unhealthy",
            "message": "OpenSearch connection successful",
            "cluster_status": health["status"],
            "cluster_name": health["cluster_name"],
            "number_of_nodes": health["number_of_nodes"],
            "index_exists": index_exists,
            "index_name": opensearch_config.index_name,
            "host": opensearch_config.host,
            "port": opensearch_config.port
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"OpenSearch connection failed: {str(e)}",
            "host": opensearch_config.host,
            "port": opensearch_config.port
        }

def create_document_index() -> bool:
    """
    Create the main document index for HR documents.
    
    Returns:
        bool: True if index was created successfully, False otherwise
    """
    try:
        client = get_opensearch_client()
        
        # Check if index already exists
        if client.indices.exists(index=opensearch_config.index_name):
            print(f"Index '{opensearch_config.index_name}' already exists")
            return True
        
        # Define index mapping
        index_mapping = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "hr_analyzer": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "title": {
                        "type": "text",
                        "analyzer": "hr_analyzer"
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "hr_analyzer"
                    },
                    "document_type": {
                        "type": "keyword"
                    },
                    "file_path": {
                        "type": "keyword"
                    },
                    "file_size": {
                        "type": "long"
                    },
                    "created_at": {
                        "type": "date"
                    },
                    "updated_at": {
                        "type": "date"
                    },
                    "tags": {
                        "type": "keyword"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 384  # For all-MiniLM-L6-v2 model
                    },
                    "chunk_id": {
                        "type": "integer"
                    },
                    "chunk_text": {
                        "type": "text",
                        "analyzer": "hr_analyzer"
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": False
                    }
                }
            }
        }
        
        # Create index
        response = client.indices.create(
            index=opensearch_config.index_name,
            body=index_mapping
        )
        
        if response.get('acknowledged'):
            print(f"Index '{opensearch_config.index_name}' created successfully")
            return True
        else:
            print(f"Failed to create index '{opensearch_config.index_name}'")
            return False
            
    except RequestError as e:
        if e.error == 'resource_already_exists_exception':
            print(f"Index '{opensearch_config.index_name}' already exists")
            return True
        else:
            print(f"Error creating index: {e}")
            return False
    except Exception as e:
        print(f"Error creating index: {e}")
        return False

def delete_document_index() -> bool:
    """
    Delete the document index (use with caution).
    
    Returns:
        bool: True if index was deleted successfully, False otherwise
    """
    try:
        client = get_opensearch_client()
        
        if not client.indices.exists(index=opensearch_config.index_name):
            print(f"Index '{opensearch_config.index_name}' does not exist")
            return True
        
        response = client.indices.delete(index=opensearch_config.index_name)
        
        if response.get('acknowledged'):
            print(f"Index '{opensearch_config.index_name}' deleted successfully")
            return True
        else:
            print(f"Failed to delete index '{opensearch_config.index_name}'")
            return False
            
    except Exception as e:
        print(f"Error deleting index: {e}")
        return False

# Initialize index on module import
def init_opensearch():
    """Initialize OpenSearch connection and create index if needed"""
    try:
        if check_opensearch_connection():
            create_document_index()
            print("OpenSearch initialized successfully")
        else:
            print("OpenSearch connection failed during initialization")
    except Exception as e:
        print(f"Error initializing OpenSearch: {e}")