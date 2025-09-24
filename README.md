# Generalized Network Information Collector

A flexible, extensible system for collecting and storing network information from various sources (ZeroTier, Tailscale, SSH, etc.) in a PostgreSQL database with support for multiple data types.

## Features

- **Modular collector framework** - Easy to extend with new collector types
- **Generalized database schema** - Supports multiple data types (filesystem, config, network, etc.)
- **Network information collection** - ZeroTier, Tailscale, and SSH information gathering
- **Ansible playbooks** - For automated deployment
- **Extensible design** - Add custom collectors for your specific needs

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/cbwinslow/generalized-network-collector.git
   cd generalized-network-collector
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   # or
   pip install psycopg2-binary pydantic
   ```

3. Set up PostgreSQL database:
   ```bash
   # Create database and user
   sudo -u postgres psql
   CREATE DATABASE network_collector_db;
   CREATE USER collector_user WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE network_collector_db TO collector_user;
   \q

   # Apply the schema
   sudo -u postgres psql -d network_collector_db -f schema.sql
   ```

4. Configure the collector by updating `config.json` with your database credentials

## Usage

Run the network collector:

```bash
python collect_network_data.py --config config.json
```

## Configuration

The `config.json` file contains the following settings:

- `db_host`: Database host (default: localhost)
- `db_name`: Database name (default: network_collector_db)
- `db_user`: Database user (default: collector_user)
- `db_password`: Database password
- `db_port`: Database port (default: 5432)
- `source_config`: Collector-specific configuration

## Customization

### Adding SSH Directories
You can customize which SSH directories to scan by adding an `ssh_directories` key to your config:

```json
{
  "source_config": {
    "ssh_directories": [
      "/home/youruser/.ssh",
      "/root/.ssh"
    ]
  }
}
```

### Creating Custom Collectors
Extend the `BaseCollector` class to create new collectors for your specific data sources.

## Security Notes

- Store database credentials securely
- Use strong passwords for database users
- Consider using SSH key-based authentication for server connections
- Store sudo password in a secure file with appropriate permissions

## Architecture

The system uses a generalized database schema with the following main tables:

- `data_sources` - Tracks data sources
- `root_entities` - Top-level containers
- `hierarchy_nodes` - Hierarchical structures
- `entities` - Individual data items
- `metadata` - Key-value pairs for additional information

## Troubleshooting

- If you get authentication errors, verify your database credentials in config.json
- If sudo commands fail, ensure your sudo password file is correctly configured
- Check that PostgreSQL is running and accessible
- Verify that required CLI tools (ZeroTier, Tailscale) are installed if needed

## Contributing

Contributions are welcome! Please submit issues and pull requests with improvements.

## License

This project is licensed under the MIT License.