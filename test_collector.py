"""
Basic test script for the generalized network collector.
This demonstrates how to use the collector framework.
"""

import json
from collectors.network_collector import NetworkCollector


def test_collector():
    """Test the network collector with a sample configuration"""
    # Sample configuration for testing
    db_config = {
        'host': 'localhost',  # Update with your database host
        'database': 'network_collector_db',  # Update with your database name
        'user': 'collector_user',  # Update with your database user
        'password': 'your_secure_password',  # Update with your database password
        'port': 5432
    }
    
    source_config = {
        'name': 'test_collector',
        'description': 'Test network information collection',
        'sudo_password_path': '~/.env',  # Path to file containing SUDO_PASSWORD=your_password
        'ssh_directories': [
            '/home/youruser/.ssh',  # Update with actual SSH directory
        ]
    }
    
    print("Initializing network collector...")
    collector = NetworkCollector(db_config, source_config)
    
    print("Connecting to database...")
    if collector.connect_to_db():
        print("✓ Database connection successful")
        
        print("Running collection...")
        success = collector.collect()
        
        if success:
            print("✓ Collection completed successfully")
        else:
            print("✗ Collection failed")
    else:
        print("✗ Database connection failed")
    
    collector.close_connection()
    print("Test completed.")


if __name__ == "__main__":
    test_collector()