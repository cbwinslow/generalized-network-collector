# Generalized Network Information Collector
# 
# This project provides a flexible, extensible system for collecting and storing
# network information from various sources (ZeroTier, Tailscale, SSH, etc.)
# in a PostgreSQL database with support for multiple data types.
#
# Features:
# - Modular collector framework
# - Generalized database schema for multiple data types
# - Support for ZeroTier, Tailscale, and SSH information collection
# - Ansible playbooks for deployment
# - Extensible design for additional collectors
# 
# Installation:
# 1. Install dependencies: pip install psycopg2-binary pydantic
# 2. Set up PostgreSQL database
# 3. Configure config.json with your database credentials
# 4. Run: python collect_network_data.py --config config.json