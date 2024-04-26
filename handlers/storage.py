import boto3
import os
import shutil
from botocore.exceptions import ClientError
from google.cloud import storage
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, ContentSettings
from azure.identity import DefaultAzureCredential
from botocore.exceptions import NoCredentialsError

AWS_REGION = "us-west-1"
GCP_REGION = "us-west2"
AZURE_STORAGE_ACCOUNT_NAME = "flockstorage"
CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=flockstorage;AccountKey=FuvNVJlKPBWzZK9yUuwbURU11ViF+VgNhsmKK8GUHQo4EI61lynq6igUTy7l95vcEbggrVF9g0fe+ASt1cJgsg==;EndpointSuffix=core.windows.net"

class LocalStorage:
    def __init__(self, bucket_name, username):
        self.bucket_name = bucket_name
        self.local_path = f"./{self.bucket_name}"
        self.username = username
        
        # Create the local directory if it doesn't exist
        if not os.path.exists(self.local_path):
            os.makedirs(self.local_path)
            print(f"Successfully created local directory {self.bucket_name}.")
        else:
            print(f"Local directory {self.bucket_name} already exists.")

    def _get_prefixed_key(self, file_key):
        return f"{self.username}_{file_key}"
    
    def get_object(self, file_key):
        file_key = self._get_prefixed_key(file_key)
        try:
            file_path = os.path.join(self.local_path, file_key)
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            return file_content
        except Exception as e:
            print(f"Error getting object {file_key} from local directory {self.bucket_name}. Exception: {e}")
            raise e
    
    def store_object(self, file_key, content, content_type='text/plain'):
        file_key = self._get_prefixed_key(file_key)
        try:
            file_path = os.path.join(self.local_path, file_key)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Successfully stored object {file_key} in local directory {self.bucket_name}.")
        except Exception as e:
            print(f"Error storing object {file_key} to local directory {self.bucket_name}. Exception: {e}")
            raise e
    
    def create_bucket(self):
        try:
            if not os.path.exists(self.local_path):
                os.makedirs(self.local_path)
                print(f"Successfully created local directory {self.bucket_name}.")
            else:
                print(f"Local directory {self.bucket_name} already exists.")
        except Exception as e:
            print(f"Error creating local directory {self.bucket_name}. Exception: {e}")
            raise e


class AWSStorage:
    def __init__(self, bucket_name, username):
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name
        self.username = username

    def _get_prefixed_key(self, file_key):
        return f"{self.username}_{file_key}"

    def get_object(self, file_key):
        file_key = self._get_prefixed_key(file_key)
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            file_content = response['Body'].read().decode('utf-8')
            return file_content
        except Exception as e:
            print(f"Error getting object {file_key} from bucket {self.bucket_name}. Exception: {e}")
            raise e

    def store_object(self, file_key, content, content_type='text/plain'):
        file_key = self._get_prefixed_key(file_key)
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=content,
                ContentType=content_type
            )
            print(f"Successfully stored object {file_key} in bucket {self.bucket_name}.")
        except Exception as e:
            print(f"Error storing object {file_key} to bucket {self.bucket_name}. Exception: {e}")
            raise e
        
    def create_bucket(self):
        try:
            self.s3_client.create_bucket(
                Bucket=self.bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': AWS_REGION
                }
            )
            print(f"Successfully created bucket {self.bucket_name}.")
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                print(f"Bucket {self.bucket_name} already exists.")
            else:
                print(f"Error creating bucket {self.bucket_name}. Exception: {e}")
                raise e
            
    def check_object_exists(self, file_key):
        file_key = self._get_prefixed_key(file_key)
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except self.s3_client.exceptions.ClientError as e:
            # Handle a 404 error specifically
            if e.response['Error']['Code'] == '404':
                return False
            else:
                print(f"An error occurred while checking for object {file_key}. Exception: {e}")
                raise
        except NoCredentialsError as e:
            print(f"No credentials available to access S3: {e}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise

    def delete_bucket(self):
        bucket_name = self.bucket_name
        s3 = boto3.client('s3')
        try:
            s3.delete_bucket(Bucket=bucket_name)
            print(f'Bucket {bucket_name} deleted successfully.')
        except Exception as e:
            print(f'An error occurred: {e}')

    def delete_all_objects(self):
        bucket_name = self.bucket_name
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucket_name)
        for obj in bucket.objects.all():
            obj.delete()
        print(f'All objects in bucket {bucket_name} deleted.')


class GCPStorage:
    def __init__(self, bucket_name, username):
        self.storage_client = storage.Client()
        self.bucket_name = bucket_name
        self.username = username

    def _get_prefixed_key(self, file_key):
        return f"{self.username}_{file_key}"
        
    def create_bucket(self):
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            if not bucket.exists():
                bucket.create(location=GCP_REGION)
                print(f"Bucket {self.bucket_name} created.")
        except Exception as e:
            print(f"Error creating bucket {self.bucket_name}. Exception: {e}")
            raise e

    def get_object(self, file_key):
        file_key = self._get_prefixed_key(file_key)
        try:
            bucket = self.storage_client.get_bucket(self.bucket_name)
            blob = storage.Blob(file_key, bucket)
            file_content = blob.download_as_text()
            return file_content
        except Exception as e:
            print(f"Error getting object {file_key} from bucket {self.bucket_name}. Exception: {e}")
            raise e

    def store_object(self, file_key, content, content_type='text/plain'):
        file_key = self._get_prefixed_key(file_key)
        try:
            bucket = self.storage_client.get_bucket(self.bucket_name)
            blob = storage.Blob(file_key, bucket)
            blob.upload_from_string(content, content_type=content_type)
            print(f"Successfully stored object {file_key} in bucket {self.bucket_name}.")
        except Exception as e:
            print(f"Error storing object {file_key} to bucket {self.bucket_name}. Exception: {e}")
            raise e
    
    def check_object_exists(self, file_key):
        file_key = self._get_prefixed_key(file_key)
        try:
            bucket = self.storage_client.get_bucket(self.bucket_name)
            blob = storage.Blob(file_key, bucket)
            return blob.exists()
        except Exception as e:
            print(f"An error occurred while checking for object {file_key}. Exception: {e}")
            raise e


class AzureStorage:
    def __init__(self, container_name, username):
        # TODO: move this into an .env file
        self.connection_string = CONNECTION_STRING
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self.username = username

    def _get_prefixed_key(self, file_key):
        return f"{self.username}_{file_key}"
        
    # Note that this is creating a container but we are calling it create_bucket for consistency with toher APIs
    def create_bucket(self):
        try:
            container_client = self.blob_service_client.create_container(self.container_name)
            print(f"Container {self.container_name} created.")
        except Exception as e:
            if "ContainerAlreadyExists" in str(e):
                print(f"Container {self.container_name} already exists.")
            else:
                print(f"Error creating container {self.container_name}. Exception: {e}")
                raise e
    
    def get_object(self, file_key):
        file_key = self._get_prefixed_key(file_key)
        try:
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=file_key)
            file_content = blob_client.download_blob().content_as_text()
            return file_content
        except Exception as e:
            print(f"Error getting object {file_key} from container {self.container_name}. Exception: {e}")
            raise e
    
    def store_object(self, file_key, content, content_type='text/plain'):
        file_key = self._get_prefixed_key(file_key)
        try:
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=file_key)
            content_settings = ContentSettings(content_type=content_type, cache_control=None)
            blob_client.upload_blob(content, content_settings=content_settings, overwrite=True)
            print(f"Successfully stored object {file_key} in container {self.container_name}.")
        except Exception as e:
            print(f"Error storing object {file_key} to container {self.container_name}. Exception: {e}")
            raise e
        
    def check_object_exists(self, file_key):
        """
        Check whether the specified object (blob) exists in the container.

        :param file_key: str, name/path of the blob to check for existence
        :return: bool, True if exists, False otherwise
        """
        file_key = self._get_prefixed_key(file_key)
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=file_key)
        try:
            blob_client.get_blob_properties()
            return True  # Blob exists
        except Exception as e:
            return False
        

def delete_bucket_and_all_objects(bucket_name):
    # Delete all objects in the bucket
    objects = s3_client.list_objects_v2(Bucket=bucket_name)
    if 'Contents' in objects:
        for obj in objects['Contents']:
            s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])

    # Delete the bucket
    s3_client.delete_bucket(Bucket=bucket_name)


if __name__ == "__main__":

    # Initialize the boto3 S3 client
    # s3_client = boto3.client('s3')

    # try:
    #     # List all buckets
    #     all_buckets = s3_client.list_buckets()
    #     for bucket in all_buckets['Buckets']:
    #         # Check if bucket name starts with the desired prefix
    #         if bucket['Name'].startswith("on-demand"):
    #             delete_bucket_and_all_objects(bucket['Name'])
    # except Exception as e:
    #     print(e)

    for i in range(16):
        try:
            username = f"user{i}"
            # for party_int in ["1"]:
            bucket_name = f"flock-baseline-storage-{username}-1"
            print(bucket_name)
            storage = AWSStorage(bucket_name)
            storage.create_bucket()
            # storage.delete_all_objects()
            # storage.delete_bucket()
        except Exception as e:
            print(e)

    # for i in range(20, 21):
    #     try:
    #         username = f"user{i}"
    #         for party_int in ["0"]:
    #             bucket_name = f"flock-storage-{username}-{party_int}"

    #         # bucket_name = f"dotme-aws-lambda-storage-{username}"
    #         # print(bucket_name)
    #         s = GCPStorage(bucket_name)
    #         s.create_bucket()

    #         # storage.delete_all_objects()
    #         # storage.delete_bucket()
    #     except Exception as e:
    #         print(e)