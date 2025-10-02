import asyncio
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from ..utils.config import settings
import logging
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import (
    VirtualMachine,
    HardwareProfile,
    StorageProfile,
    OSDisk,
    DiskCreateOptionTypes,
    OSProfile,
    NetworkProfile,
    NetworkInterfaceReference,
    LinuxConfiguration,
    SshConfiguration,
    SshPublicKey,
    VirtualMachinePriorityTypes,
    VirtualMachineEvictionPolicyTypes,
    ResourceIdentityType,
    VirtualMachineIdentity,
    ImageReference
)
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import (
    VirtualNetwork,
    AddressSpace,
    Subnet,
    PublicIPAddress,
    PublicIPAddressSkuName,
    NetworkInterface,
    NetworkInterfaceIPConfiguration,
    NetworkSecurityGroup,
    SecurityRule,
    SecurityRuleProtocol,
    SecurityRuleAccess,
    SecurityRuleDirection
)
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.core.exceptions import AzureError
import json
import base64

logger = logging.getLogger(__name__)

class AzureGPUManager:
    """Manages GPU instances on Azure"""
    
    GPU_SPECS = {
        "T4": {
            "azure_size": "Standard_NC4as_T4_v3",
            "vcpus": 4,
            "memory_gb": 28,
            "gpu_memory_gb": 16,
            "cost_per_hour": 0.99,
            "spot_discount": 0.70,
            "image": {
                "publisher": "microsoft-dsvm",
                "offer": "ubuntu-hpc",
                "sku": "2004-gen2",
                "version": "latest"
            }
        },
        "A10G": {
            "azure_size": "Standard_NV36ads_A10_v5",
            "vcpus": 36,
            "memory_gb": 440,
            "gpu_memory_gb": 24,
            "cost_per_hour": 1.99,
            "spot_discount": 0.70,
            "image": {
                "publisher": "microsoft-dsvm",
                "offer": "ubuntu-hpc",
                "sku": "2004-gen2",
                "version": "latest"
            }
        },
        "A100": {
            "azure_size": "Standard_NC24ads_A100_v4",
            "vcpus": 24,
            "memory_gb": 220,
            "gpu_memory_gb": 80,
            "cost_per_hour": 3.99,
            "spot_discount": 0.70,
            "image": {
                "publisher": "microsoft-dsvm",
                "offer": "ubuntu-hpc",
                "sku": "2004-gen2",
                "version": "latest"
            }
        }
    }
    
    def __init__(self):
        self.resource_group = "gpu-cloud-platform"
        self.location = "eastus"
        
        # Initialize Azure clients
        self.credential = ClientSecretCredential(
            tenant_id=settings.AZURE_TENANT_ID,
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET
        )
        
        self.compute_client = ComputeManagementClient(
            self.credential,
            settings.AZURE_SUBSCRIPTION_ID
        )
        
        self.network_client = NetworkManagementClient(
            self.credential,
            settings.AZURE_SUBSCRIPTION_ID
        )
        
        self.resource_client = ResourceManagementClient(
            self.credential,
            settings.AZURE_SUBSCRIPTION_ID
        )
        
        self.monitor_client = MonitorManagementClient(
            self.credential,
            settings.AZURE_SUBSCRIPTION_ID
        )
    
    async def _ensure_resource_group(self):
        """Ensure the resource group exists"""
        try:
            self.resource_client.resource_groups.create_or_update(
                self.resource_group,
                {"location": self.location}
            )
            logger.info(f"Resource group {self.resource_group} ready")
        except Exception as e:
            logger.error(f"Failed to create resource group: {e}")
    
    async def _create_vnet(self, vnet_name: str, subnet_name: str) -> VirtualNetwork:
        """Create Virtual Network and Subnet"""
        vnet_params = VirtualNetwork(
            location=self.location,
            address_space=AddressSpace(address_prefixes=["10.0.0.0/16"]),
            subnets=[Subnet(name=subnet_name, address_prefix="10.0.0.0/24")]
        )
        
        async_vnet = self.network_client.virtual_networks.begin_create_or_update(
            self.resource_group, vnet_name, vnet_params
        )
        return async_vnet.result()
    
    async def _create_nsg(self, nsg_name: str, gpu_type: str) -> NetworkSecurityGroup:
        """Create Network Security Group with appropriate rules"""
        nsg_params = NetworkSecurityGroup(
            location=self.location,
            security_rules=[
                SecurityRule(
                    name="SSH",
                    priority=100,
                    direction=SecurityRuleDirection.INBOUND,
                    access=SecurityRuleAccess.ALLOW,
                    protocol=SecurityRuleProtocol.TCP,
                    source_port_range="*",
                    destination_port_range="22",
                    source_address_prefix="*",
                    destination_address_prefix="*"
                ),
                SecurityRule(
                    name="Jupyter",
                    priority=110,
                    direction=SecurityRuleDirection.INBOUND,
                    access=SecurityRuleAccess.ALLOW,
                    protocol=SecurityRuleProtocol.TCP,
                    source_port_range="*",
                    destination_port_range="8888",
                    source_address_prefix="*",
                    destination_address_prefix="*"
                ),
                SecurityRule(
                    name="API",
                    priority=120,
                    direction=SecurityRuleDirection.INBOUND,
                    access=SecurityRuleAccess.ALLOW,
                    protocol=SecurityRuleProtocol.TCP,
                    source_port_range="*",
                    destination_port_range="8000",
                    source_address_prefix="*",
                    destination_address_prefix="*"
                ),
                SecurityRule(
                    name="HTTP",
                    priority=130,
                    direction=SecurityRuleDirection.INBOUND,
                    access=SecurityRuleAccess.ALLOW,
                    protocol=SecurityRuleProtocol.TCP,
                    source_port_range="*",
                    destination_port_range="80",
                    source_address_prefix="*",
                    destination_address_prefix="*"
                ),
                SecurityRule(
                    name="HTTPS",
                    priority=140,
                    direction=SecurityRuleDirection.INBOUND,
                    access=SecurityRuleAccess.ALLOW,
                    protocol=SecurityRuleProtocol.TCP,
                    source_port_range="*",
                    destination_port_range="443",
                    source_address_prefix="*",
                    destination_address_prefix="*"
                )
            ]
        )
        
        async_nsg = self.network_client.network_security_groups.begin_create_or_update(
            self.resource_group, nsg_name, nsg_params
        )
        return async_nsg.result()
    
    async def _create_public_ip(self, public_ip_name: str) -> PublicIPAddress:
        """Create Public IP Address"""
        public_ip_params = PublicIPAddress(
            location=self.location,
            sku={"name": PublicIPAddressSkuName.STANDARD},
            public_ip_allocation_method="Static",
            public_ip_address_version="IPv4"
        )
        
        async_ip = self.network_client.public_ip_addresses.begin_create_or_update(
            self.resource_group, public_ip_name, public_ip_params
        )
        return async_ip.result()
    
    async def _create_nic(
        self, 
        nic_name: str, 
        vnet_name: str, 
        subnet_name: str,
        public_ip_name: str,
        nsg_name: str
    ) -> NetworkInterface:
        """Create Network Interface"""
        subnet = self.network_client.subnets.get(
            self.resource_group, vnet_name, subnet_name
        )
        public_ip = self.network_client.public_ip_addresses.get(
            self.resource_group, public_ip_name
        )
        nsg = self.network_client.network_security_groups.get(
            self.resource_group, nsg_name
        )
        
        nic_params = NetworkInterface(
            location=self.location,
            ip_configurations=[
                NetworkInterfaceIPConfiguration(
                    name="ipconfig1",
                    subnet={"id": subnet.id},
                    public_ip_address={"id": public_ip.id}
                )
            ],
            network_security_group={"id": nsg.id}
        )
        
        async_nic = self.network_client.network_interfaces.begin_create_or_update(
            self.resource_group, nic_name, nic_params
        )
        return async_nic.result()
    
    def _get_startup_script(self, docker_image: str = None) -> str:
        """Generate startup script for the VM"""
        script = """#!/bin/bash
# Update system
apt-get update
apt-get install -y docker.io nvidia-docker2 python3-pip

# Start Docker
systemctl start docker
systemctl enable docker

# Install NVIDIA drivers if not present
if ! command -v nvidia-smi &> /dev/null; then
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.0-1_all.deb
    dpkg -i cuda-keyring_1.0-1_all.deb
    apt-get update
    apt-get -y install cuda-drivers
fi

# Pull and run Docker container if specified
"""
        if docker_image:
            script += f"""
docker pull {docker_image}
docker run -d --gpus all -p 8888:8888 -p 8000:8000 {docker_image}
"""
        else:
            # Default: Install Jupyter
            script += """
pip3 install jupyterlab torch torchvision torchaudio transformers
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root &
"""
        
        return base64.b64encode(script.encode()).decode('utf-8')
    
    async def _deploy_azure_vm(
        self,
        name: str,
        gpu_type: str,
        nic_name: str,
        use_spot: bool = True,
        docker_image: str = None
    ) -> VirtualMachine:
        """Deploy the actual Azure VM with GPU"""
        
        spec = self.GPU_SPECS[gpu_type]
        nic = self.network_client.network_interfaces.get(
            self.resource_group, nic_name
        )
        
        # VM parameters
        vm_params = VirtualMachine(
            location=self.location,
            hardware_profile=HardwareProfile(vm_size=spec["azure_size"]),
            storage_profile=StorageProfile(
                image_reference=ImageReference(
                    publisher=spec["image"]["publisher"],
                    offer=spec["image"]["offer"],
                    sku=spec["image"]["sku"],
                    version=spec["image"]["version"]
                ),
                os_disk=OSDisk(
                    name=f"{name}-osdisk",
                    create_option=DiskCreateOptionTypes.FROM_IMAGE,
                    managed_disk={"storage_account_type": "Premium_LRS"}
                )
            ),
            os_profile=OSProfile(
                computer_name=name,
                admin_username="gpuadmin",
                admin_password="GPUCloud2025!@#",  # In production, use SSH keys
                linux_configuration=LinuxConfiguration(
                    disable_password_authentication=False
                ),
                custom_data=self._get_startup_script(docker_image)
            ),
            network_profile=NetworkProfile(
                network_interfaces=[
                    NetworkInterfaceReference(id=nic.id, primary=True)
                ]
            ),
            identity=VirtualMachineIdentity(
                type=ResourceIdentityType.SYSTEM_ASSIGNED
            )
        )
        
        # Configure spot instance if requested
        if use_spot:
            vm_params.priority = VirtualMachinePriorityTypes.SPOT
            vm_params.eviction_policy = VirtualMachineEvictionPolicyTypes.DEALLOCATE
            vm_params.billing_profile = {"max_price": spec["cost_per_hour"]}
        
        # Create the VM
        async_vm = self.compute_client.virtual_machines.begin_create_or_update(
            self.resource_group, name, vm_params
        )
        
        return async_vm.result()
    
    async def create_instance(
        self,
        gpu_type: str,
        user_id: int,
        name: str = None,
        use_spot: bool = True,
        docker_image: str = None
    ) -> Dict[str, Any]:
        """Create a new GPU instance"""
        
        if gpu_type not in self.GPU_SPECS:
            raise ValueError(f"Invalid GPU type: {gpu_type}")
        
        # Ensure resource group exists
        await self._ensure_resource_group()
        
        instance_id = self._generate_instance_id()
        
        if name is None:
            name = f"gpu-{gpu_type.lower()}-{instance_id[:8]}"
        
        # Create network resources
        vnet_name = f"vnet-{instance_id}"
        subnet_name = f"subnet-{instance_id}"
        public_ip_name = f"pip-{instance_id}"
        nsg_name = f"nsg-{instance_id}"
        nic_name = f"nic-{instance_id}"
        
        try:
            # Create Virtual Network
            vnet = await self._create_vnet(vnet_name, subnet_name)
            
            # Create Network Security Group
            nsg = await self._create_nsg(nsg_name, gpu_type)
            
            # Create Public IP
            public_ip = await self._create_public_ip(public_ip_name)
            
            # Create Network Interface
            nic = await self._create_nic(nic_name, vnet_name, subnet_name, public_ip_name, nsg_name)
            
            # Deploy the VM
            vm = await self._deploy_azure_vm(
                name=name,
                gpu_type=gpu_type,
                nic_name=nic_name,
                use_spot=use_spot,
                docker_image=docker_image
            )
            
            # Get the public IP address
            public_ip_info = self.network_client.public_ip_addresses.get(
                self.resource_group, public_ip_name
            )
            
            instance_data = {
                "id": instance_id,
                "name": name,
                "gpu_type": gpu_type,
                "status": "running",
                "azure_resource_id": vm.id,
                "public_ip": public_ip_info.ip_address,
                "ssh_port": 22,
                "jupyter_url": f"http://{public_ip_info.ip_address}:8888",
                "api_endpoint": f"http://{public_ip_info.ip_address}:8000/api",
                "specs": self.GPU_SPECS[gpu_type],
                "is_spot": use_spot,
                "created_at": datetime.utcnow().isoformat(),
                "vm_name": name,
                "resource_ids": {
                    "vm": vm.id,
                    "nic": nic.id,
                    "public_ip": public_ip.id,
                    "nsg": nsg.id,
                    "vnet": vnet.id
                }
            }
            
            return instance_data
            
        except AzureError as e:
            logger.error(f"Azure deployment failed: {e}")
            raise Exception(f"Failed to deploy GPU instance: {str(e)}")
    
    async def stop_instance(self, vm_name: str) -> bool:
        """Stop (deallocate) a GPU instance"""
        try:
            async_operation = self.compute_client.virtual_machines.begin_deallocate(
                self.resource_group, vm_name
            )
            async_operation.result()
            return True
        except AzureError as e:
            logger.error(f"Failed to stop VM {vm_name}: {e}")
            return False
    
    async def start_instance(self, vm_name: str) -> bool:
        """Start a stopped GPU instance"""
        try:
            async_operation = self.compute_client.virtual_machines.begin_start(
                self.resource_group, vm_name
            )
            async_operation.result()
            return True
        except AzureError as e:
            logger.error(f"Failed to start VM {vm_name}: {e}")
            return False
    
    async def delete_instance(self, vm_name: str, resource_ids: Dict[str, str]) -> bool:
        """Delete a GPU instance and all associated resources"""
        try:
            # Delete VM first
            async_vm = self.compute_client.virtual_machines.begin_delete(
                self.resource_group, vm_name
            )
            async_vm.result()
            
            # Delete other resources
            # Note: In production, parse resource IDs properly
            # This is simplified for the MVP
            
            return True
        except AzureError as e:
            logger.error(f"Failed to delete VM {vm_name}: {e}")
            return False
    
    async def get_instance_status(self, vm_name: str) -> Optional[Dict[str, Any]]:
        """Get current status of a VM"""
        try:
            vm = self.compute_client.virtual_machines.get(
                self.resource_group, vm_name, expand='instanceView'
            )
            
            # Parse status from instance view
            status = "unknown"
            if vm.instance_view and vm.instance_view.statuses:
                for s in vm.instance_view.statuses:
                    if s.code.startswith('PowerState/'):
                        status = s.code.split('/')[-1]
                        break
            
            return {
                "status": status,
                "vm_size": vm.hardware_profile.vm_size,
                "location": vm.location
            }
        except AzureError as e:
            logger.error(f"Failed to get VM status {vm_name}: {e}")
            return None
    
    async def get_instance_metrics(self, vm_name: str) -> Dict[str, Any]:
        """Get metrics for a VM"""
        try:
            vm = self.compute_client.virtual_machines.get(
                self.resource_group, vm_name
            )
            
            # Query metrics from Azure Monitor
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=5)
            
            metrics_data = self.monitor_client.metrics.list(
                vm.id,
                timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                interval='PT1M',
                metricnames='Percentage CPU,Network In,Network Out',
                aggregation='Average'
            )
            
            metrics = {
                "cpu_utilization": 0,
                "network_in_bytes": 0,
                "network_out_bytes": 0
            }
            
            for item in metrics_data.value:
                for timeseries in item.timeseries:
                    for data in timeseries.data:
                        if item.name.value == 'Percentage CPU':
                            metrics["cpu_utilization"] = data.average or 0
                        elif item.name.value == 'Network In':
                            metrics["network_in_bytes"] = data.average or 0
                        elif item.name.value == 'Network Out':
                            metrics["network_out_bytes"] = data.average or 0
            
            # Note: GPU metrics would require additional setup with custom metrics
            # For MVP, we'll simulate GPU metrics based on CPU
            metrics["gpu_utilization"] = min(metrics["cpu_utilization"] * 1.2, 100)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics for {vm_name}: {e}")
            return {
                "cpu_utilization": 0,
                "gpu_utilization": 0,
                "network_in_bytes": 0,
                "network_out_bytes": 0
            }
    
    def calculate_spot_price(self, gpu_type: str) -> float:
        """Calculate current spot price for GPU type"""
        if gpu_type not in self.GPU_SPECS:
            return 0
        
        base_price = self.GPU_SPECS[gpu_type]["cost_per_hour"]
        spot_discount = self.GPU_SPECS[gpu_type]["spot_discount"]
        
        # In production, query Azure for actual spot prices
        # For now, apply the discount
        spot_price = base_price * (1 - spot_discount)
        
        return spot_price
    
    def _generate_instance_id(self) -> str:
        """Generate unique instance ID"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))