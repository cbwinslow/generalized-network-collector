import subprocess
import json
import re
from typing import Dict, List, Any, Optional
from collectors.base_collector import BaseCollector


class NetworkCollector(BaseCollector):
    """
    Collector for network information from ZeroTier and Tailscale.
    """
    
    def __init__(self, db_config: dict, source_config: dict):
        super().__init__(db_config, source_config)
        self.sudo_password_path = source_config.get('sudo_password_path', '~/.env')
        self.sudo_password = self._get_sudo_password()
        
    def _get_sudo_password(self) -> Optional[str]:
        """Read sudo password from file"""
        try:
            with open(self.sudo_password_path, 'r') as f:
                for line in f:
                    if line.startswith('SUDO_PASSWORD='):
                        return line.split('=', 1)[1].strip()
        except Exception as e:
            print(f"Error reading sudo password file: {e}")
        return None
    
    def _run_command_with_sudo(self, command: List[str]) -> Optional[str]:
        """Run a command with sudo, using the password from file"""
        if not self.sudo_password:
            print("Sudo password not available")
            return None
            
        try:
            # Use echo to pass password to sudo
            full_command = f'echo "{self.sudo_password}" | sudo -S {" ".join(command)}'
            result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"Command failed: {result.stderr}")
                return None
        except Exception as e:
            print(f"Error running command: {e}")
            return None
    
    def _run_command(self, command: List[str]) -> Optional[str]:
        """Run a command without sudo"""
        try:
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"Command failed: {result.stderr}")
                return None
        except Exception as e:
            print(f"Error running command: {e}")
            return None
    
    def collect(self):
        """Collect network information from ZeroTier and Tailscale"""
        if not self.connect_to_db():
            return False
        
        # Initialize data source
        self.initialize_data_source(
            source_name=self.source_config.get('name', 'network_collector'),
            source_type='network',
            description=self.source_config.get('description', 'Network information collector')
        )
        
        # Initialize root entity
        root_entity_id = self.initialize_root_entity(
            name='network_root',
            entity_type='network',
            path='network_root',
            metadata={'type': 'network_root'}
        )
        
        # Collect ZeroTier information
        self._collect_zerotier_info(root_entity_id)
        
        # Collect Tailscale information
        self._collect_tailscale_info(root_entity_id)
        
        # Collect SSH key information
        self._collect_ssh_info(root_entity_id)
        
        print("Network information collection completed")
        return True
    
    def _collect_zerotier_info(self, root_entity_id: int):
        """Collect ZeroTier network information"""
        print("Collecting ZeroTier information...")
        
        # Check if ZeroTier is installed
        result = self._run_command(['which', 'zerotier-cli'])
        if not result:
            print("ZeroTier not found, skipping")
            return
        
        # Get ZeroTier status
        status_output = self._run_command_with_sudo(['zerotier-cli', 'status'])
        if not status_output:
            print("Could not get ZeroTier status")
            return
        
        # Parse status
        status_lines = status_output.strip().split('\n')
        status_info = {}
        
        for line in status_lines:
            if 'Online' in line:
                status_info['online'] = True
            elif 'Offline' in line:
                status_info['online'] = False
            elif '200' in line and 'OK' in line:
                # This is the header line, skip
                continue
            else:
                parts = line.split()
                if len(parts) >= 3:
                    status_info['address'] = parts[0]
                    status_info['version'] = parts[1]
                    status_info['tcp_fallback_active'] = 'tcp' in line.lower()
        
        # Create ZeroTier root node
        zerotier_node_id = self.get_or_create_hierarchy_node(
            path='network_root/zerotier',
            parent_id=None,
            root_entity_id=root_entity_id,
            name='ZeroTier',
            node_type='network_service',
            depth=1,
            properties=status_info
        )
        
        # Add metadata for status
        self.add_metadata('hierarchy_node', zerotier_node_id, 'status', 
                         'online' if status_info.get('online', False) else 'offline')
        
        # Get ZeroTier networks
        networks_output = self._run_command_with_sudo(['zerotier-cli', 'listnetworks'])
        if networks_output:
            network_lines = networks_output.strip().split('\n')[1:]  # Skip header
            
            for line in network_lines:
                parts = line.split()
                if len(parts) >= 5:
                    network_id = parts[0]
                    status = parts[1]
                    type = parts[2]
                    name = parts[3]
                    mac = parts[4]
                    
                    # Get network details
                    details_output = self._run_command_with_sudo(['zerotier-cli', 'get', f'{network_id}'])
                    
                    network_details = {
                        'id': network_id,
                        'status': status,
                        'type': type,
                        'name': name,
                        'mac': mac
                    }
                    
                    # Parse IP addresses from details
                    if details_output:
                        ip_pattern = r'(\d+\.\d+\.\d+\.\d+)(?:/\d+)?'
                        ip_matches = re.findall(ip_pattern, details_output)
                        if ip_matches:
                            network_details['ips'] = ip_matches
                    
                    # Create network node
                    network_node_id = self.get_or_create_hierarchy_node(
                        path=f'network_root/zerotier/{network_id}',
                        parent_id=zerotier_node_id,
                        root_entity_id=root_entity_id,
                        name=name,
                        node_type='network',
                        depth=2,
                        properties=network_details
                    )
                    
                    # Add network entity
                    network_entity_id = self.get_or_create_entity(
                        path=f'network_root/zerotier/{network_id}',
                        parent_node_id=network_node_id,
                        root_entity_id=root_entity_id,
                        name=f'network_{network_id}',
                        content_type='zerotier_network',
                        content=network_details
                    )
                    
                    # Add IP addresses as metadata
                    if 'ips' in network_details:
                        for ip in network_details['ips']:
                            self.add_metadata('entity', network_entity_id, 'ip_address', ip)
    
    def _collect_tailscale_info(self, root_entity_id: int):
        """Collect Tailscale network information"""
        print("Collecting Tailscale information...")
        
        # Check if Tailscale is installed
        result = self._run_command(['which', 'tailscale'])
        if not result:
            print("Tailscale not found, skipping")
            return
        
        # Get Tailscale status
        status_output = self._run_command_with_sudo(['tailscale', 'status', '--json'])
        if not status_output:
            print("Could not get Tailscale status")
            return
        
        try:
            status_data = json.loads(status_output)
        except json.JSONDecodeError:
            print("Could not parse Tailscale status JSON")
            return
        
        # Create Tailscale root node
        tailscale_node_id = self.get_or_create_hierarchy_node(
            path='network_root/tailscale',
            parent_id=None,  # Will be linked to root
            root_entity_id=root_entity_id,
            name='Tailscale',
            node_type='network_service',
            depth=1,
            properties={
                'self': status_data.get('Self', {}),
                'backend_state': status_data.get('BackendState', 'unknown')
            }
        )
        
        # Add status metadata
        self.add_metadata('hierarchy_node', tailscale_node_id, 'backend_state', 
                         status_data.get('BackendState', 'unknown'))
        
        # Get Tailscale IP information
        ip_output = self._run_command_with_sudo(['tailscale', 'ip', '-4'])
        if ip_output:
            ip_address = ip_output.strip()
            self.add_metadata('hierarchy_node', tailscale_node_id, 'ipv4_address', ip_address)
        
        ip_output_v6 = self._run_command_with_sudo(['tailscale', 'ip', '-6'])
        if ip_output_v6:
            ipv6_address = ip_output_v6.strip()
            self.add_metadata('hierarchy_node', tailscale_node_id, 'ipv6_address', ipv6_address)
        
        # Create entity for Tailscale service
        tailscale_entity_id = self.get_or_create_entity(
            path='network_root/tailscale',
            parent_node_id=tailscale_node_id,
            root_entity_id=root_entity_id,
            name='tailscale_service',
            content_type='tailscale_service',
            content=status_data
        )
        
        # Add peer information
        if 'Peer' in status_data:
            for peer_id, peer_info in status_data['Peer'].items():
                # Create peer node
                peer_node_id = self.get_or_create_hierarchy_node(
                    path=f'network_root/tailscale/peer_{peer_id}',
                    parent_id=tailscale_node_id,
                    root_entity_id=root_entity_id,
                    name=peer_info.get('HostName', f'peer_{peer_id}'),
                    node_type='network_peer',
                    depth=2,
                    properties=peer_info
                )
                
                # Create peer entity
                peer_entity_id = self.get_or_create_entity(
                    path=f'network_root/tailscale/peer_{peer_id}',
                    parent_node_id=peer_node_id,
                    root_entity_id=root_entity_id,
                    name=f'peer_{peer_id}',
                    content_type='tailscale_peer',
                    content=peer_info
                )
                
                # Add IPs as metadata
                if 'TailscaleIPs' in peer_info:
                    for ip in peer_info['TailscaleIPs']:
                        self.add_metadata('entity', peer_entity_id, 'tailscale_ip', ip)
    
    def _collect_ssh_info(self, root_entity_id: int):
        """Collect SSH key information and related IP addresses"""
        print("Collecting SSH information...")
        
        ssh_node_id = self.get_or_create_hierarchy_node(
            path='network_root/ssh',
            parent_id=None,  # Will be linked to root
            root_entity_id=root_entity_id,
            name='SSH',
            node_type='security_service',
            depth=1,
            properties={'description': 'SSH key and connection information'}
        )
        
        # Look for SSH keys in common locations
        import os
        import stat
        from pathlib import Path
        
        ssh_dirs = [
            Path('/home/foomanchu8008/.ssh'),
            Path('/root/.ssh')
        ]
        
        for ssh_dir in ssh_dirs:
            try:
                if ssh_dir.exists():
                    # List SSH keys
                    for key_file in ssh_dir.glob('*'):
                        if key_file.is_file() and not key_file.name.endswith('.pub'):
                            # Skip some common non-key files
                            if key_file.name in ['known_hosts', 'config', 'authorized_keys']:
                                continue
                                
                            try:
                                # Get file stats
                                file_stat = os.stat(str(key_file))
                                permissions = oct(stat.S_IMODE(file_stat.st_mode))
                                
                                # Read key to get fingerprint
                                import hashlib
                                
                                with open(key_file, 'rb') as f:
                                    key_data = f.read()
                                    key_hash = hashlib.sha256(key_data).hexdigest()
                                
                                # Create key entity
                                key_entity_id = self.get_or_create_entity(
                                    path=f'network_root/ssh/{key_file.name}',
                                    parent_node_id=ssh_node_id,
                                    root_entity_id=root_entity_id,
                                    name=key_file.name,
                                    content_type='ssh_key',
                                    content={
                                        'path': str(key_file),
                                        'permissions': permissions,
                                        'size': file_stat.st_size,
                                        'created': file_stat.st_ctime,
                                        'modified': file_stat.st_mtime,
                                        'sha256': key_hash
                                    }
                                )
                                
                                # Add key metadata
                                self.add_metadata('entity', key_entity_id, 'key_type', 'private')
                                self.add_metadata('entity', key_entity_id, 'size_bytes', str(file_stat.st_size), 'number')
                                
                                # Also check for corresponding public key
                                pub_key_path = key_file.with_suffix(key_file.suffix + '.pub')
                                if pub_key_path.exists():
                                    pub_key_entity_id = self.get_or_create_entity(
                                        path=f'network_root/ssh/{pub_key_path.name}',
                                        parent_node_id=ssh_node_id,
                                        root_entity_id=root_entity_id,
                                        name=pub_key_path.name,
                                        content_type='ssh_public_key',
                                        content={'path': str(pub_key_path)}
                                    )
                                    
                                    # Add relationship between private and public key
                                    # This would require the relationships table from our schema
                                    # For now, we'll just link them via metadata
                                    self.add_metadata('entity', key_entity_id, 'public_key', pub_key_path.name)
                                    self.add_metadata('entity', pub_key_entity_id, 'private_key', key_file.name)
                                    
                            except Exception as e:
                                print(f"Error processing SSH key {key_file}: {e}")
            except PermissionError:
                print(f"Permission denied accessing {ssh_dir}, skipping...")
                continue
        
        # Add SSH service entity
        ssh_entity_id = self.get_or_create_entity(
            path='network_root/ssh',
            parent_node_id=ssh_node_id,
            root_entity_id=root_entity_id,
            name='ssh_service',
            content_type='ssh_service',
            content={'description': 'SSH service configuration'}
        )
        
        # Add system IP addresses
        try:
            import socket
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            
            # Filter out loopback addresses
            local_ips = [ip for ip in local_ips if not ip.startswith("127.")]
            
            for ip in local_ips:
                self.add_metadata('entity', ssh_entity_id, 'local_ip', ip)
            
        except Exception as e:
            print(f"Error getting local IP addresses: {e}")