import psycopg2
import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional


class BaseCollector(ABC):
    """
    Abstract base class for all data collectors.
    Provides common functionality for connecting to the database and inserting data.
    """
    
    def __init__(self, db_config: Dict[str, str], source_config: Dict[str, Any]):
        self.db_config = db_config
        self.source_config = source_config
        self.connection = None
        self.data_source_id = None
        
    def connect_to_db(self):
        """Connect to the PostgreSQL database"""
        try:
            self.connection = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config.get('port', 5432),
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            return True
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return False
    
    def initialize_data_source(self, source_name: str, source_type: str, description: str) -> int:
        """Initialize a data source in the database"""
        cursor = self.connection.cursor()
        
        # Insert or get data source
        cursor.execute("""
            INSERT INTO data_sources (name, source_type, description, connection_info)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                source_type = EXCLUDED.source_type,
                description = EXCLUDED.description,
                connection_info = EXCLUDED.connection_info,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
        """, (source_name, source_type, description, json.dumps(self.source_config)))
        
        self.data_source_id = cursor.fetchone()[0]
        self.connection.commit()
        cursor.close()
        
        return self.data_source_id
    
    def initialize_root_entity(self, name: str, entity_type: str, path: Optional[str] = None, metadata: Optional[Dict] = None) -> int:
        """Initialize a root entity in the database"""
        cursor = self.connection.cursor()
        
        cursor.execute("""
            INSERT INTO root_entities (source_id, name, entity_type, path, metadata)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (source_id, name) DO UPDATE SET
                entity_type = EXCLUDED.entity_type,
                path = EXCLUDED.path,
                metadata = EXCLUDED.metadata,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
        """, (self.data_source_id, name, entity_type, path, json.dumps(metadata) if metadata else None))
        
        root_entity_id = cursor.fetchone()[0]
        self.connection.commit()
        cursor.close()
        
        return root_entity_id
    
    def get_or_create_hierarchy_node(self, path: str, parent_id: Optional[int], 
                                   root_entity_id: int, name: str, node_type: str, 
                                   depth: int, properties: Optional[Dict] = None) -> int:
        """Get or create a hierarchy node"""
        cursor = self.connection.cursor()
        
        path_hash = hashlib.sha256(path.encode()).hexdigest()
        
        cursor.execute("""
            INSERT INTO hierarchy_nodes (path_hash, path, parent_id, root_entity_id, name, node_type, depth, properties)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (root_entity_id, path) DO UPDATE SET
                parent_id = EXCLUDED.parent_id,
                name = EXCLUDED.name,
                node_type = EXCLUDED.node_type,
                depth = EXCLUDED.depth,
                properties = EXCLUDED.properties,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
        """, (path_hash, path, parent_id, root_entity_id, name, node_type, depth, json.dumps(properties) if properties else None))
        
        node_id = cursor.fetchone()[0]
        self.connection.commit()
        cursor.close()
        
        return node_id
    
    def get_or_create_entity_type(self, name: str, category: str, mime_type: Optional[str] = None, 
                                description: Optional[str] = None) -> int:
        """Get or create an entity type"""
        cursor = self.connection.cursor()
        
        cursor.execute("""
            INSERT INTO entity_types (name, category, mime_type, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name, category) DO UPDATE SET
                mime_type = EXCLUDED.mime_type,
                description = EXCLUDED.description
            RETURNING id;
        """, (name, category, mime_type, description))
        
        entity_type_id = cursor.fetchone()[0]
        self.connection.commit()
        cursor.close()
        
        return entity_type_id
    
    def get_or_create_entity(self, path: str, parent_node_id: int, root_entity_id: int, name: str,
                           entity_type_id: Optional[int] = None, size: Optional[int] = None,
                           content_hash: Optional[str] = None, content_type: str = 'file',
                           content: Optional[Dict] = None) -> int:
        """Get or create an entity"""
        cursor = self.connection.cursor()
        
        path_hash = hashlib.sha256(path.encode()).hexdigest()
        
        cursor.execute("""
            INSERT INTO entities (path_hash, path, parent_node_id, root_entity_id, name, entity_type_id, size, content_hash, content_type, content)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (parent_node_id, name) DO UPDATE SET
                path_hash = EXCLUDED.path_hash,
                path = EXCLUDED.path,
                root_entity_id = EXCLUDED.root_entity_id,
                entity_type_id = EXCLUDED.entity_type_id,
                size = EXCLUDED.size,
                content_hash = EXCLUDED.content_hash,
                content_type = EXCLUDED.content_type,
                content = EXCLUDED.content,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
        """, (path_hash, path, parent_node_id, root_entity_id, name, entity_type_id, size, content_hash, content_type, json.dumps(content) if content else None))
        
        entity_id = cursor.fetchone()[0]
        self.connection.commit()
        cursor.close()
        
        return entity_id
    
    def add_metadata(self, entity_type: str, entity_id: int, key: str, value: str, data_type: str = 'string'):
        """Add metadata to an entity"""
        cursor = self.connection.cursor()
        
        cursor.execute("""
            INSERT INTO metadata (entity_type, entity_id, key, value, data_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (entity_type, entity_id, key) DO UPDATE SET
                value = EXCLUDED.value,
                data_type = EXCLUDED.data_type,
                updated_at = CURRENT_TIMESTAMP;
        """, (entity_type, entity_id, key, value, data_type))
        
        self.connection.commit()
        cursor.close()
    
    @abstractmethod
    def collect(self):
        """Abstract method that must be implemented by subclasses"""
        pass
    
    def close_connection(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()