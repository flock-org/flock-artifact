from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import (
    ContainerGroup, Container, ContainerGroupIdentity, ResourceRequirements, ResourceRequests, 
    OperatingSystemTypes, ContainerGroupRestartPolicy, ImageRegistryCredential, IpAddress, Port, ContainerPort
)
from azure.mgmt.subscription import SubscriptionClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import VirtualNetwork, AddressSpace, Subnet
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.storage.models import StorageAccountCreateParameters, Sku, Kind
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.msi import ManagedServiceIdentityClient
from azure.mgmt.msi.models import Identity

import uuid

CONTAINER_IMAGE = "sijuntan/flock"
CONTAINER_NAME = "flock"
CONTAINER_GROUP_NAME = "flock-container-group"
VNET_NAME="flock-vnet"
SUBNET_NAME="flock-subnet"
IDENTITY_NAME="flock-identity"
STORAGE_ACCOUNT_NAME = "flockstorage"

LOCATION="westus"

def list_azure_subscriptions():
    # Create the SubscriptionClient
    credential = DefaultAzureCredential()
    # credential = InteractiveBrowserCredential()
    subscription_client = SubscriptionClient(credential)

    # List all the subscriptions available under the account
    subscriptions = list(subscription_client.subscriptions.list())
    for subscription in subscriptions:
        print(f"Subscription Name: {subscription.display_name}, Subscription ID: {subscription.subscription_id}")
    return subscriptions


def list_resource_groups(subscription_id: str):
    # Create the ResourceManagementClient
    credential = DefaultAzureCredential()
    resource_client = ResourceManagementClient(credential, subscription_id)

    # List all the resource groups in the subscription
    resource_groups = list(resource_client.resource_groups.list())
    for rg in resource_groups:
        print(f"Resource Group: {rg.name}, Location: {rg.location}")
    return resource_groups



class AzureManager:
    def __init__(self, subscription_id: str, resource_group: str):
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.credential = DefaultAzureCredential()
        self.container_instance_client = ContainerInstanceManagementClient(self.credential, self.subscription_id)
        self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)
        self.network_client = NetworkManagementClient(self.credential, self.subscription_id)
        self.storage_client = StorageManagementClient(self.credential, self.subscription_id)
        self.authorization_client = AuthorizationManagementClient(self.credential, self.subscription_id)
        self.msi_client = ManagedServiceIdentityClient(self.credential, self.subscription_id)

    def start_azure_container_instance(self, container_group_name: str, container_name: str, image: str, port: int = 5000,
                                       cpu: float = 1.0, memory: str = '1.5G', os_type: str = OperatingSystemTypes.linux,
                                       restart_policy: str = ContainerGroupRestartPolicy.always, location: str = 'eastus',
                                       image_registry_login_server: str = None, image_registry_username: str = None,
                                       image_registry_password: str = None):
        
        ports = [ContainerPort(port=p) for p in range(port, port + 100)]
        
        container = Container(
            name=container_name,
            image=image,
            resources=ResourceRequirements(
                requests=ResourceRequests(
                    cpu=cpu,
                    memory_in_gb=float(memory[:-1])
                )
            ),
            ports=ports
        )

        if image_registry_login_server and image_registry_username and image_registry_password:
            container.image_registry_credentials = [
                ImageRegistryCredential(
                    server=image_registry_login_server,
                    username=image_registry_username,
                    password=image_registry_password
                )
            ]

        container_group = ContainerGroup(
            location=location,
            containers=[container],
            os_type=os_type,
            restart_policy=restart_policy,
            ip_address=IpAddress(ports=[Port(protocol='TCP', port=p) for p in range(port, port+5)], type='Public'),
            identity=ContainerGroupIdentity(type="SystemAssigned")
        )

        self.container_instance_client.container_groups.begin_create_or_update(self.resource_group, container_group_name,
                                                                              container_group)
        print(f"Container Group '{container_group_name}' is created or updated successfully.")

    def get_default_subscription_and_resource_group(self):
        subscriptions = list(self.subscription_client.subscriptions.list())
        if not subscriptions:
            raise Exception("No subscriptions are available.")

        default_subscription = subscriptions[0]
        print(f"Default Subscription: {default_subscription.subscription_id}, Display Name: {default_subscription.display_name}")

        resource_groups = list(self.resource_client.resource_groups.list())
        if not resource_groups:
            raise Exception("No resource groups are available in the default subscription.")

        default_resource_group = resource_groups[0]
        print(f"Default Resource Group: {default_resource_group.name}, Location: {default_resource_group.location}")

    def stop_container_instance(self, container_group_name: str):
        self.container_instance_client.container_groups.begin_delete(self.resource_group, container_group_name).result()
        print(f"Container instance {container_group_name} stopped.")

    def get_container_group(self, container_group_name: str) -> str:
        container_group = self.container_instance_client.container_groups.get(self.resource_group, container_group_name)
        return container_group

    def create_vnet(self, vnet_name: str, subnet_name: str, location='eastus'):
        vnet_params = VirtualNetwork(
            location=location,
            address_space=AddressSpace(
                address_prefixes=['10.0.0.0/16']
            ),
            subnets=[Subnet(name=subnet_name, address_prefix='10.0.0.0/24')]
        )

        self.network_client.virtual_networks.begin_create_or_update(self.resource_group, vnet_name, vnet_params).result()
        print(f"VNet {vnet_name} created successfully.")

    def list_vnets_and_subnets(self):
        vnets = self.network_client.virtual_networks.list(self.resource_group)
        for vnet in vnets:
            print(f"VNet Name: {vnet.name}, ID: {vnet.id}")
            for subnet in vnet.subnets:
                print(f"  Subnet Name: {subnet.name}, ID: {subnet.id}")


    def grant_blob_access(self, container_group_name: str, storage_account_name: str, identity):
        """
        Grant blob access to a container instance by assigning a role to its managed identity.

        :param container_group_name: str, Name of the container group.
        :param storage_account_name: str, Name of the storage account.
        :param identity_id: str, ID of the managed identity to assign the role to.
        """
        # Assign managed identity to the container instance
        self.container_instance_client.container_groups.update(
            resource_group_name=self.resource_group,
            container_group_name=container_group_name,
            resource={
                'identity': {
                    'type': 'UserAssigned',
                    'user_assigned_identities': {identity.id: {}}
                }
            }
        )

        # Get the storage account id
        storage_account_id = self.storage_client.storage_accounts.get_properties(
            account_name=storage_account_name,
            resource_group_name=self.resource_group
        ).id

        # Assign the "Storage Blob Data Contributor" role to the managed identity
        # self.authorization_client.role_assignments.create_for_object_by_id(
        #     object_id=storage_account_id,
        #     role_assignment_name=identity_id,  # Extracting the name from the ID
        #     parameters={
        #         "role_definition_id": "/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/ba92f5b4-2d11-453d-a403-e96b0029c9fe".format(subscription_id=self.subscription_id),
        #         "principal_id": identity_id
        #     }
        # )

        self.authorization_client.role_assignments.create(
            scope=storage_account_id,
            role_assignment_name=uuid.uuid4(),  # Generating a new UUID for the role assignment name
            parameters={
                "role_definition_id": "/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/ba92f5b4-2d11-453d-a403-e96b0029c9fe".format(subscription_id=self.subscription_id),
                "principal_id": identity.principal_id
            }
        )

    def list_storage_accounts(self):
        """
        List all storage accounts in the resource group.

        :return: List of storage accounts.
        """
        return list(self.storage_client.storage_accounts.list_by_resource_group(self.resource_group))


    def create_storage_account(self, account_name: str, location: str, sku_name='Standard_LRS', kind=Kind.storage_v2):
        """
        Create a new storage account.

        :param account_name: str, Name of the new storage account.
        :param location: str, Azure region to create the storage account in.
        :param sku_name: str, Type of the storage account. Default: 'Standard_LRS'.
        :param kind: Kind, Kind of the storage account. Default: Kind.storage_v2.
        :return: Storage account properties.
        """
        storage_account_params = StorageAccountCreateParameters(
            sku=Sku(name=sku_name),
            kind=kind,
            location=location
        )
        return self.storage_client.storage_accounts.begin_create(
            resource_group_name=self.resource_group,
            account_name=account_name,
            parameters=storage_account_params
        ).result()
    
    def get_storage_account_by_name(self, storage_account_name: str):
        """
        Get a storage account by its name.

        :param storage_account_name: str, Name of the storage account.
        :return: Storage account properties if found, else None.
        """
        try:
            # Get and return the storage account properties
            return self.storage_client.storage_accounts.get_properties(
                account_name=storage_account_name,
                resource_group_name=self.resource_group
            )
        except Exception as e:
            print(f"Error: {str(e)}")
            return None
    
    def create_managed_identity(self, identity_name: str, location: str):
        """
        Create a new managed identity.

        :param identity_name: str, Name of the new managed identity.
        :param location: str, Azure region to create the managed identity in.
        :return: Managed identity properties.
        """
        identity_params = Identity(location=location)
        return self.msi_client.user_assigned_identities.create_or_update(
            resource_group_name=self.resource_group,
            resource_name=identity_name,
            parameters=identity_params
        )
    
    def get_identity(self, identity_name: str):
        """
        Get the ID of a managed identity by its name.

        :param identity_name: str, Name of the managed identity.
        :return: str, ID of the managed identity if found, else None.
        """
        try:
            # Get and return the managed identity ID
            identity = self.msi_client.user_assigned_identities.get(
                resource_group_name=self.resource_group,
                resource_name=identity_name
            )
            return identity
        except Exception as e:
            print(f"Error: {str(e)}")
            return None


# def init():
#     # create_managed_identity()
#  create_storage_account()
   # storage_account = azure_manager.create_storage_account(STORAGE_ACCOUNT_NAME, LOCATION)
#    azure_manager.grant_blob_access(CONTAINER_GROUP_NAME, STORAGE_ACCOUNT_NAME, identity)

if __name__ == "__main__":
    subs = list_azure_subscriptions()
    sub = subs[0].subscription_id
    rgs = list_resource_groups(sub)
    rg = rgs[0].name

    azure_manager = AzureManager(sub, rg)
    
    # identity = azure_manager.get_identity(IDENTITY_NAME)
    # print(identity)
    # storage_account = azure_manager.list_storage_accounts()[0]
    # storage_account_name = storage_account.name

    azure_manager.stop_container_instance(CONTAINER_GROUP_NAME)
    azure_manager.start_azure_container_instance(
        container_group_name=CONTAINER_GROUP_NAME,
        container_name=CONTAINER_NAME,
        image=CONTAINER_IMAGE,
    )
    container_group = azure_manager.get_container_group(CONTAINER_GROUP_NAME)




    # print(azure_manager.get_storage_account_by_name(STORAGE_ACCOUNT_NAME))