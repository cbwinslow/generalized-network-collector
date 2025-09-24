-- Generalized Schema for Multiple Data Types (PostgreSQL Compatible)
-- This schema can store file system information, configuration data, inventory, and more

-- Table 1: Data Sources (to track where our data comes from)
CREATE TABLE IF NOT EXISTS data_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'filesystem', 'configuration', 'inventory', 'monitoring'
    description TEXT,
    connection_info JSONB, -- JSON for connection details
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table 2: Root Entities (top-level containers for different data types)
CREATE TABLE IF NOT EXISTS root_entities (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES data_sources(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL, -- 'filesystem', 'config_root', 'inventory_root'
    path VARCHAR(1024), -- For filesystem-like data
    metadata JSONB, -- Additional data-specific metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table 3: Generic Hierarchy (for directories, config groups, inventory groups, etc.)
CREATE TABLE IF NOT EXISTS hierarchy_nodes (
    id SERIAL PRIMARY KEY,
    path_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA256 hash of the path for efficiency
    path TEXT NOT NULL,
    parent_id INTEGER REFERENCES hierarchy_nodes(id),
    root_entity_id INTEGER REFERENCES root_entities(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    node_type VARCHAR(50) NOT NULL, -- 'directory', 'config_group', 'inventory_group', etc.
    depth INTEGER NOT NULL,
    properties JSONB, -- Node-specific properties
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(root_entity_id, path)
);

-- Table 4: Generic Entity Types (for file types, config types, etc.)
CREATE TABLE IF NOT EXISTS entity_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL, -- 'file_extension', 'config_type', 'inventory_item'
    mime_type VARCHAR(255), -- MIME type where applicable
    description TEXT,
    metadata_template JSONB, -- Schema for expected metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(name, category)
);

-- Table 5: Generic Entities (files, config items, inventory items, etc.)
CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY,
    path_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA256 hash of the path for efficiency
    path TEXT NOT NULL,
    parent_node_id INTEGER REFERENCES hierarchy_nodes(id) NOT NULL,
    root_entity_id INTEGER REFERENCES root_entities(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    entity_type_id INTEGER REFERENCES entity_types(id),
    size BIGINT, -- in bytes for files, size indicator for other entities
    content_hash VARCHAR(64), -- SHA256 hash of content (for files) or identifier (for other entities)
    content_type VARCHAR(50), -- 'file', 'config', 'inventory_item', 'metric'
    content JSONB, -- Actual content if needed as JSON
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(parent_node_id, name)
);

-- Table 6: Generic Permissions (for entities that need access control)
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('hierarchy_node', 'entity')), -- node or entity
    entity_id INTEGER NOT NULL, -- references either hierarchy_nodes.id or entities.id
    scope VARCHAR(50), -- 'user', 'group', 'role', 'service'
    scope_identifier VARCHAR(255), -- username, group name, role name
    permissions_mask INTEGER DEFAULT 0, -- Bitmask for permissions
    custom_permissions JSONB, -- Additional permission details
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(entity_type, entity_id, scope, scope_identifier)
);

-- Table 7: Generic Metadata (key-value pairs for any entity)
CREATE TABLE IF NOT EXISTS metadata (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('data_source', 'root_entity', 'hierarchy_node', 'entity')),
    entity_id INTEGER NOT NULL, -- references the appropriate table
    key VARCHAR(255) NOT NULL, -- metadata key
    value TEXT, -- metadata value (JSON or string)
    data_type VARCHAR(20) DEFAULT 'string', -- 'string', 'number', 'boolean', 'json'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(entity_type, entity_id, key)
);

-- Table 8: Relationships (for linking entities across hierarchies)
CREATE TABLE IF NOT EXISTS relationships (
    id SERIAL PRIMARY KEY,
    from_entity_type VARCHAR(20) NOT NULL CHECK (from_entity_type IN ('hierarchy_node', 'entity')),
    from_entity_id INTEGER NOT NULL,
    to_entity_type VARCHAR(20) NOT NULL CHECK (to_entity_type IN ('hierarchy_node', 'entity')),
    to_entity_id INTEGER NOT NULL,
    relationship_type VARCHAR(50) NOT NULL, -- 'depends_on', 'part_of', 'similar_to', 'duplicate_of'
    metadata JSONB, -- Additional relationship details
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(from_entity_type, from_entity_id, to_entity_type, to_entity_id, relationship_type)
);

-- Table 9: Data Collection Jobs (for tracking automated data collection)
CREATE TABLE IF NOT EXISTS collection_jobs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    source_id INTEGER REFERENCES data_sources(id) NOT NULL,
    job_type VARCHAR(50) NOT NULL, -- 'filesystem_scan', 'config_pull', 'inventory_sync'
    schedule VARCHAR(100), -- Cron expression
    last_run TIMESTAMP WITH TIME ZONE,
    next_run TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    config JSONB, -- Job-specific configuration
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table 10: Collection Job Results (for tracking what was collected)
CREATE TABLE IF NOT EXISTS collection_results (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES collection_jobs(id) NOT NULL,
    entity_id INTEGER REFERENCES entities(id),
    node_id INTEGER REFERENCES hierarchy_nodes(id),
    status VARCHAR(20) DEFAULT 'processed', -- 'processed', 'skipped', 'error'
    message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes after table creation
CREATE INDEX IF NOT EXISTS idx_root_entities_source_id ON root_entities(source_id);
CREATE INDEX IF NOT EXISTS idx_hierarchy_nodes_parent_id ON hierarchy_nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_hierarchy_nodes_root_entity_id ON hierarchy_nodes(root_entity_id);
CREATE INDEX IF NOT EXISTS idx_hierarchy_nodes_path_hash ON hierarchy_nodes(path_hash);
CREATE INDEX IF NOT EXISTS idx_entities_parent_node_id ON entities(parent_node_id);
CREATE INDEX IF NOT EXISTS idx_entities_root_entity_id ON entities(root_entity_id);
CREATE INDEX IF NOT EXISTS idx_entities_entity_type_id ON entities(entity_type_id);
CREATE INDEX IF NOT EXISTS idx_entities_path_hash ON entities(path_hash);
CREATE INDEX IF NOT EXISTS idx_entities_content_hash ON entities(content_hash);
CREATE INDEX IF NOT EXISTS idx_permissions_entity ON permissions(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_metadata_entity ON metadata(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_metadata_key ON metadata(key);
CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_entity_type, from_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_entity_type, to_entity_id);
CREATE INDEX IF NOT EXISTS idx_collection_jobs_source_id ON collection_jobs(source_id);
CREATE INDEX IF NOT EXISTS idx_collection_jobs_status ON collection_jobs(status);
CREATE INDEX IF NOT EXISTS idx_collection_results_job_id ON collection_results(job_id);
CREATE INDEX IF NOT EXISTS idx_collection_results_entity_id ON collection_results(entity_id);

-- Triggers to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_data_sources_updated_at 
    BEFORE UPDATE ON data_sources 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_root_entities_updated_at 
    BEFORE UPDATE ON root_entities 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_hierarchy_nodes_updated_at 
    BEFORE UPDATE ON hierarchy_nodes 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entities_updated_at 
    BEFORE UPDATE ON entities 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_permissions_updated_at 
    BEFORE UPDATE ON permissions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_metadata_updated_at 
    BEFORE UPDATE ON metadata 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collection_jobs_updated_at 
    BEFORE UPDATE ON collection_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default data source types
INSERT INTO entity_types (name, category, description) 
SELECT 'folder', 'hierarchy_node', 'Directory or folder'
WHERE NOT EXISTS (SELECT 1 FROM entity_types WHERE name = 'folder' AND category = 'hierarchy_node');

INSERT INTO entity_types (name, category, mime_type, description) 
SELECT 'txt', 'file_extension', 'text/plain', 'Plain text file'
WHERE NOT EXISTS (SELECT 1 FROM entity_types WHERE name = 'txt' AND category = 'file_extension');

INSERT INTO entity_types (name, category, mime_type, description) 
SELECT 'py', 'file_extension', 'text/x-python', 'Python source code'
WHERE NOT EXISTS (SELECT 1 FROM entity_types WHERE name = 'py' AND category = 'file_extension');

INSERT INTO entity_types (name, category, mime_type, description) 
SELECT 'json', 'file_extension', 'application/json', 'JSON data'
WHERE NOT EXISTS (SELECT 1 FROM entity_types WHERE name = 'json' AND category = 'file_extension');