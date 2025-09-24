#!/usr/bin/env python3

import json
import argparse
from collectors.network_collector import NetworkCollector


def main():
    parser = argparse.ArgumentParser(description='Generalized Network Information Collector')
    parser.add_argument('--config', type=str, required=True, help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    # Database configuration
    db_config = {
        'host': config.get('db_host', 'localhost'),
        'database': config.get('db_name', 'network_collector_db'),
        'user': config.get('db_user', 'collector_user'),
        'password': config.get('db_password', 'your_secure_password'),
        'port': config.get('db_port', 5432)
    }
    
    # Collector configuration
    source_config = config.get('source_config', {})
    
    # Initialize and run network collector
    collector = NetworkCollector(db_config, source_config)
    
    # Run collection
    success = collector.collect()
    
    if success:
        print("Network data collection completed successfully")
    else:
        print("Network data collection failed")


if __name__ == "__main__":
    main()