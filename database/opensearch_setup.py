#!/usr/bin/env python3
"""
OpenSearch setup script for HR AI Assistant

This script sets up OpenSearch indices, mappings, and sample documents
for the HR AI Assistant's RAG (Retrieval Augmented Generation) system.
"""

import os
import sys
import json
import time
from typing import Dict, Any, List
from opensearchpy import OpenSearch, RequestError, ConnectionError
from sentence_transformers import SentenceTransformer

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class OpenSearchSetup:
    """OpenSearch setup and configuration class"""
    
    def __init__(self):
        # OpenSearch configuration
        self.host = os.getenv("OPENSEARCH_HOST", "localhost")
        self.port = int(os.getenv("OPENSEARCH_PORT", "9200"))
        self.username = os.getenv("OPENSEARCH_USERNAME", "admin")
        self.password = os.getenv("OPENSEARCH_PASSWORD", "admin")
        self.use_ssl = os.getenv("OPENSEARCH_USE_SSL", "False").lower() == "true"
        self.verify_certs = os.getenv("OPENSEARCH_VERIFY_CERTS", "False").lower() == "true"
        self.index_name = os.getenv("OPENSEARCH_INDEX_NAME", "hr_documents")
        
        # Initialize OpenSearch client
        self.client = None
        self.embedding_model = None
        
        print(f"OpenSearch Setup Configuration:")
        print(f"  Host: {self.host}:{self.port}")
        print(f"  Index: {self.index_name}")
        print(f"  SSL: {self.use_ssl}")
    
    def connect(self) -> bool:
        """
        Connect to OpenSearch cluster
        
        Returns:
            bool: True if connection successful
        """
        try:
            config = {
                'hosts': [{'host': self.host, 'port': self.port}],
                'use_ssl': self.use_ssl,
                'verify_certs': self.verify_certs,
                'ssl_show_warn': False,
                'timeout': 30
            }
            
            if self.username and self.password:
                config['http_auth'] = (self.username, self.password)
            
            self.client = OpenSearch(**config)
            
            # Test connection
            info = self.client.info()
            print(f"✓ Connected to OpenSearch cluster: {info['cluster_name']}")
            print(f"  Version: {info['version']['number']}")
            return True
            
        except ConnectionError as e:
            print(f"✗ Failed to connect to OpenSearch: {e}")
            return False
        except Exception as e:
            print(f"✗ Unexpected error connecting to OpenSearch: {e}")
            return False
    
    def wait_for_cluster(self, max_wait_time: int = 60) -> bool:
        """
        Wait for OpenSearch cluster to be ready
        
        Args:
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            bool: True if cluster is ready
        """
        print("Waiting for OpenSearch cluster to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                if self.connect():
                    health = self.client.cluster.health()
                    if health['status'] in ['green', 'yellow']:
                        print(f"✓ Cluster is ready (status: {health['status']})")
                        return True
                    else:
                        print(f"  Cluster status: {health['status']}, waiting...")
                
            except Exception:
                pass
            
            time.sleep(5)
        
        print(f"✗ Cluster not ready after {max_wait_time} seconds")
        return False
    
    def create_index(self) -> bool:
        """
        Create the main document index with proper mappings
        
        Returns:
            bool: True if index created successfully
        """
        try:
            # Check if index already exists
            if self.client.indices.exists(index=self.index_name):
                print(f"ℹ Index '{self.index_name}' already exists")
                return True
            
            # Define index settings and mappings
            index_config = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "hr_analyzer": {
                                "type": "standard",
                                "stopwords": "_english_"
                            },
                            "hr_search_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "stop",
                                    "stemmer"
                                ]
                            }
                        },
                        "filter": {
                            "stemmer": {
                                "type": "stemmer",
                                "language": "english"
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "analyzer": "hr_analyzer",
                            "search_analyzer": "hr_search_analyzer",
                            "boost": 2.0
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "hr_analyzer",
                            "search_analyzer": "hr_search_analyzer"
                        },
                        "document_type": {
                            "type": "keyword"
                        },
                        "file_path": {
                            "type": "keyword"
                        },
                        "file_name": {
                            "type": "keyword"
                        },
                        "file_size": {
                            "type": "long"
                        },
                        "created_at": {
                            "type": "date",
                            "format": "strict_date_optional_time||epoch_millis"
                        },
                        "updated_at": {
                            "type": "date",
                            "format": "strict_date_optional_time||epoch_millis"
                        },
                        "tags": {
                            "type": "keyword"
                        },
                        "keywords": {
                            "type": "text",
                            "analyzer": "hr_analyzer"
                        },
                        "embedding": {
                            "type": "dense_vector",
                            "dims": 384,  # For all-MiniLM-L6-v2
                            "index": True,
                            "similarity": "cosine"
                        },
                        "chunk_id": {
                            "type": "integer"
                        },
                        "chunk_text": {
                            "type": "text",
                            "analyzer": "hr_analyzer",
                            "search_analyzer": "hr_search_analyzer"
                        },
                        "document_id": {
                            "type": "integer"
                        },
                        "access_level": {
                            "type": "keyword"
                        },
                        "author_id": {
                            "type": "integer"
                        },
                        "status": {
                            "type": "keyword"
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "file_name": {"type": "keyword"},
                                "file_extension": {"type": "keyword"},
                                "mime_type": {"type": "keyword"},
                                "version": {"type": "keyword"},
                                "language": {"type": "keyword"},
                                "word_count": {"type": "integer"},
                                "page_count": {"type": "integer"}
                            }
                        }
                    }
                }
            }
            
            # Create the index
            response = self.client.indices.create(
                index=self.index_name,
                body=index_config
            )
            
            if response.get('acknowledged'):
                print(f"✓ Index '{self.index_name}' created successfully")
                return True
            else:
                print(f"✗ Failed to create index '{self.index_name}'")
                return False
                
        except RequestError as e:
            if e.error == 'resource_already_exists_exception':
                print(f"ℹ Index '{self.index_name}' already exists")
                return True
            else:
                print(f"✗ Error creating index: {e}")
                return False
        except Exception as e:
            print(f"✗ Unexpected error creating index: {e}")
            return False
    
    def load_embedding_model(self) -> bool:
        """
        Load the sentence transformer model for embeddings
        
        Returns:
            bool: True if model loaded successfully
        """
        try:
            print("Loading sentence transformer model...")
            model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            self.embedding_model = SentenceTransformer(model_name)
            print(f"✓ Loaded embedding model: {model_name}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to load embedding model: {e}")
            return False
    
    def index_sample_documents(self) -> bool:
        """
        Index sample HR documents for testing
        
        Returns:
            bool: True if documents indexed successfully
        """
        try:
            if not self.embedding_model:
                if not self.load_embedding_model():
                    return False
            
            # Sample HR documents
            sample_documents = [
                {
                    "title": "Employee Handbook 2024",
                    "content": """
                    Welcome to our company! This employee handbook contains important information about our company policies, 
                    procedures, and benefits. Please read it carefully and keep it for future reference.
                    
                    Working Hours: Our standard working hours are 9:00 AM to 6:00 PM, Monday through Friday. 
                    We offer flexible working arrangements including remote work options.
                    
                    Leave Policy: Employees are entitled to 21 days of annual leave, 12 days of sick leave, 
                    and 12 days of casual leave per year. Maternity leave is 180 days and paternity leave is 15 days.
                    
                    Code of Conduct: We expect all employees to maintain high standards of professional conduct, 
                    treat colleagues with respect, and follow company policies and procedures.
                    
                    Benefits: We provide comprehensive health insurance, dental coverage, retirement savings plan, 
                    and professional development opportunities.
                    """,
                    "document_type": "handbook",
                    "file_name": "employee_handbook_2024.pdf",
                    "access_level": "internal",
                    "author_id": 1,
                    "tags": ["handbook", "policies", "benefits", "guidelines"],
                    "keywords": "employee handbook policies benefits working hours leave policy code of conduct"
                },
                {
                    "title": "Leave Policy Guidelines",
                    "content": """
                    Leave Policy and Procedures
                    
                    Annual Leave: All employees are entitled to 21 days of annual leave per year. 
                    Annual leave can be carried forward up to 5 days to the next year.
                    
                    Sick Leave: Employees receive 12 days of sick leave annually. Medical certificates 
                    may be required for sick leave exceeding 3 consecutive days.
                    
                    Casual Leave: 12 days of casual leave are provided for personal emergencies and short-term needs.
                    
                    Maternity Leave: Female employees are entitled to 180 days of maternity leave with full pay.
                    
                    Paternity Leave: Male employees are entitled to 15 days of paternity leave.
                    
                    Application Process: All leave requests must be submitted through the HR system at least 
                    3 days in advance (except for emergency situations). Manager approval is required for all leave.
                    
                    Public Holidays: The company observes national and regional public holidays as per local regulations.
                    """,
                    "document_type": "policy",
                    "file_name": "leave_policy_2024.pdf",
                    "access_level": "internal",
                    "author_id": 1,
                    "tags": ["leave", "policy", "annual", "sick", "maternity", "paternity"],
                    "keywords": "leave policy annual sick maternity paternity casual emergency application process"
                },
                {
                    "title": "IT Security Guidelines",
                    "content": """
                    Information Security Guidelines
                    
                    Password Policy: All passwords must be at least 8 characters long and contain uppercase letters, 
                    lowercase letters, numbers, and special characters. Passwords must be changed every 90 days.
                    
                    Email Security: Do not open suspicious email attachments or click on unknown links. 
                    Report phishing attempts to the IT security team immediately.
                    
                    Data Protection: Company data should not be stored on personal devices or cloud services. 
                    Use only approved company storage solutions.
                    
                    Access Control: Access to systems and data should be granted on a need-to-know basis. 
                    Report any unauthorized access attempts immediately.
                    
                    Remote Work Security: When working remotely, ensure you are using secure Wi-Fi connections 
                    and VPN access for company resources.
                    
                    Software Updates: Keep all software and operating systems updated with the latest security patches.
                    
                    Incident Reporting: Report any security incidents or suspected breaches to the IT security team 
                    within 2 hours of discovery.
                    """,
                    "document_type": "policy",
                    "file_name": "it_security_guidelines.pdf",
                    "access_level": "internal",
                    "author_id": 4,
                    "tags": ["security", "IT", "password", "email", "data protection"],
                    "keywords": "IT security password policy email security data protection access control remote work"
                },
                {
                    "title": "Performance Review Process",
                    "content": """
                    Annual Performance Review Process
                    
                    Overview: All employees participate in an annual performance review process to assess 
                    performance, set goals, and plan career development.
                    
                    Review Cycle: Performance reviews are conducted annually, typically in January/February 
                    for the previous calendar year.
                    
                    Self-Assessment: Employees complete a self-assessment form evaluating their achievements, 
                    challenges, and goals for the upcoming year.
                    
                    Manager Review: Direct managers provide feedback on employee performance, achievements, 
                    and areas for improvement.
                    
                    Goal Setting: Collaborative goal setting for the upcoming year, including professional 
                    development objectives.
                    
                    Rating Scale: Performance is rated on a 5-point scale:
                    - Exceeds Expectations (5)
                    - Meets Expectations (4)
                    - Partially Meets Expectations (3)
                    - Below Expectations (2)
                    - Significantly Below Expectations (1)
                    
                    Career Development: Discussion of career aspirations, training needs, and development opportunities.
                    
                    Documentation: All reviews are documented in the HR system and accessible to the employee.
                    """,
                    "document_type": "procedure",
                    "file_name": "performance_review_process.pdf",
                    "access_level": "internal",
                    "author_id": 1,
                    "tags": ["performance", "review", "evaluation", "goals", "development"],
                    "keywords": "performance review annual assessment goals development rating career"
                },
                {
                    "title": "Remote Work Policy",
                    "content": """
                    Remote Work Policy and Guidelines
                    
                    Eligibility: Remote work is available to employees whose roles can be performed effectively 
                    from a remote location, subject to manager approval.
                    
                    Application Process: Employees must submit a remote work request through the HR system, 
                    including justification and proposed work arrangements.
                    
                    Equipment: The company provides necessary equipment for remote work, including laptop, 
                    monitor, and other essential tools.
                    
                    Communication: Remote employees must maintain regular communication with their team and 
                    manager through approved communication channels.
                    
                    Working Hours: Remote employees are expected to maintain standard working hours and 
                    be available for meetings and collaboration.
                    
                    Productivity Standards: Performance and productivity standards remain the same for 
                    remote and office-based employees.
                    
                    Security Requirements: Remote workers must follow all IT security guidelines and 
                    use VPN for accessing company resources.
                    
                    Office Access: Remote employees may access office facilities when needed with 
                    advance notice.
                    
                    Review Process: Remote work arrangements are reviewed quarterly to ensure effectiveness.
                    """,
                    "document_type": "policy",
                    "file_name": "remote_work_policy.pdf",
                    "access_level": "internal",
                    "author_id": 1,
                    "tags": ["remote work", "policy", "WFH", "flexible work"],
                    "keywords": "remote work policy work from home flexible arrangements equipment communication"
                }
            ]
            
            indexed_count = 0
            
            for i, doc in enumerate(sample_documents):
                try:
                    # Create chunks from the content
                    chunks = self._chunk_text(doc["content"])
                    
                    for chunk_id, chunk_text in enumerate(chunks):
                        # Generate embedding for the chunk
                        embedding = self.embedding_model.encode(chunk_text).tolist()
                        
                        # Create document for indexing
                        doc_body = {
                            "title": doc["title"],
                            "content": doc["content"],
                            "document_type": doc["document_type"],
                            "file_path": f"documents/{doc['file_name']}",
                            "file_name": doc["file_name"],
                            "file_size": len(doc["content"]),
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": "2024-01-01T00:00:00Z",
                            "tags": doc["tags"],
                            "keywords": doc["keywords"],
                            "embedding": embedding,
                            "chunk_id": chunk_id,
                            "chunk_text": chunk_text,
                            "document_id": i + 1,
                            "access_level": doc["access_level"],
                            "author_id": doc["author_id"],
                            "status": "published",
                            "metadata": {
                                "file_name": doc["file_name"],
                                "file_extension": ".pdf",
                                "mime_type": "application/pdf",
                                "version": "1.0",
                                "language": "en",
                                "word_count": len(chunk_text.split()),
                                "page_count": 1
                            }
                        }
                        
                        # Index the document chunk
                        doc_id = f"doc_{i+1}_chunk_{chunk_id}"
                        response = self.client.index(
                            index=self.index_name,
                            id=doc_id,
                            body=doc_body
                        )
                        
                        if response.get("result") in ["created", "updated"]:
                            indexed_count += 1
                        
                except Exception as e:
                    print(f"✗ Error indexing document {i+1}: {e}")
                    continue
            
            # Refresh the index to make documents searchable
            self.client.indices.refresh(index=self.index_name)
            
            print(f"✓ Indexed {indexed_count} document chunks successfully")
            return True
            
        except Exception as e:
            print(f"✗ Error indexing sample documents: {e}")
            return False
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to chunk
            chunk_size: Maximum chunk size
            overlap: Overlap between chunks
            
        Returns:
            List[str]: Text chunks
        """
        # Clean the text
        text = " ".join(text.split())
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size * 0.5:
                    end = sentence_end + 1
                else:
                    # Try word boundary
                    word_end = text.rfind(' ', start, end)
                    if word_end > start + chunk_size * 0.5:
                        end = word_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def test_search_functionality(self) -> bool:
        """
        Test the search functionality with sample queries
        
        Returns:
            bool: True if search tests pass
        """
        try:
            print("\nTesting search functionality...")
            
            # Test queries
            test_queries = [
                "leave policy",
                "password requirements",
                "performance review",
                "remote work",
                "maternity leave"
            ]
            
            for query in test_queries:
                # Test text search
                search_body = {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^2", "chunk_text", "keywords"],
                            "type": "best_fields"
                        }
                    },
                    "size": 3,
                    "_source": {"excludes": ["embedding"]}
                }
                
                response = self.client.search(
                    index=self.index_name,
                    body=search_body
                )
                
                hits = response["hits"]["total"]["value"]
                print(f"  Query '{query}': {hits} results")
                
                if hits == 0:
                    print(f"  ⚠ No results for query: {query}")
            
            # Test semantic search if embedding model is available
            if self.embedding_model:
                print("\nTesting semantic search...")
                query_text = "How many vacation days do I get?"
                query_embedding = self.embedding_model.encode(query_text).tolist()
                
                semantic_search = {
                    "query": {
                        "script_score": {
                            "query": {"match_all": {}},
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                "params": {"query_vector": query_embedding}
                            }
                        }
                    },
                    "size": 3,
                    "_source": {"excludes": ["embedding"]}
                }
                
                response = self.client.search(
                    index=self.index_name,
                    body=semantic_search
                )
                
                hits = response["hits"]["total"]["value"]
                print(f"  Semantic query '{query_text}': {hits} results")
            
            print("✓ Search functionality tests completed")
            return True
            
        except Exception as e:
            print(f"✗ Error testing search functionality: {e}")
            return False
    
    def get_index_info(self) -> Dict[str, Any]:
        """
        Get information about the created index
        
        Returns:
            Dict: Index information
        """
        try:
            # Get index stats
            stats = self.client.indices.stats(index=self.index_name)
            
            # Get index mapping
            mapping = self.client.indices.get_mapping(index=self.index_name)
            
            # Get some sample documents
            sample_docs = self.client.search(
                index=self.index_name,
                body={"query": {"match_all": {}}, "size": 5},
                _source_excludes=["embedding"]
            )
            
            info = {
                "index_name": self.index_name,
                "document_count": stats["indices"][self.index_name]["total"]["docs"]["count"],
                "index_size_bytes": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
                "mapping_properties": list(mapping[self.index_name]["mappings"]["properties"].keys()),
                "sample_documents": [
                    {
                        "id": hit["_id"],
                        "title": hit["_source"].get("title"),
                        "document_type": hit["_source"].get("document_type"),
                        "chunk_id": hit["_source"].get("chunk_id")
                    }
                    for hit in sample_docs["hits"]["hits"]
                ]
            }
            
            return info
            
        except Exception as e:
            print(f"Error getting index info: {e}")
            return {}
    
    def cleanup_index(self) -> bool:
        """
        Delete the index (for testing/cleanup purposes)
        
        Returns:
            bool: True if cleanup successful
        """
        try:
            if self.client.indices.exists(index=self.index_name):
                response = self.client.indices.delete(index=self.index_name)
                if response.get('acknowledged'):
                    print(f"✓ Index '{self.index_name}' deleted successfully")
                    return True
            else:
                print(f"ℹ Index '{self.index_name}' does not exist")
                return True
                
        except Exception as e:
            print(f"✗ Error deleting index: {e}")
            return False


def main():
    """Main setup function"""
    print("=" * 60)
    print("HR AI Assistant - OpenSearch Setup")
    print("=" * 60)
    
    setup = OpenSearchSetup()
    
    # Wait for cluster to be ready
    if not setup.wait_for_cluster():
        return False
    
    # Create index
    if not setup.create_index():
        return False
    
    # Index sample documents
    if not setup.index_sample_documents():
        return False
    
    # Test search functionality
    if not setup.test_search_functionality():
        return False
    
    # Display index information
    print("\n" + "=" * 60)
    print("INDEX INFORMATION")
    print("=" * 60)
    
    info = setup.get_index_info()
    if info:
        print(f"Index Name: {info['index_name']}")
        print(f"Document Count: {info['document_count']}")
        print(f"Index Size: {info['index_size_bytes']:,} bytes")
        print(f"Mapping Properties: {', '.join(info['mapping_properties'])}")
        print(f"\nSample Documents:")
        for doc in info['sample_documents']:
            print(f"  - {doc['title']} (Type: {doc['document_type']}, Chunk: {doc['chunk_id']})")
    
    print("\n" + "=" * 60)
    print("✓ OpenSearch setup completed successfully!")
    print("✓ You can now start the HR AI Assistant application")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    import sys
    
    # Check for cleanup argument
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        print("Cleaning up OpenSearch index...")
        setup = OpenSearchSetup()
        if setup.connect():
            setup.cleanup_index()
        sys.exit(0)
    
    # Run main setup
    success = main()
    sys.exit(0 if success else 1)