"""
R2 Storage Service for Cloudflare R2 object storage.
Provides basic upload/download functionality with error handling.
"""

import boto3
import os
import base64
import io
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
from utils.logging import get_logger
from utils.config import settings

logger = get_logger(__name__)

class R2StorageService:
    """Service for interacting with Cloudflare R2 storage."""
    
    def __init__(self):
        """Initialize R2 client with credentials from environment."""
        self.account_id = os.getenv("R2_ACCOUNT_ID")
        self.access_key_id = os.getenv("R2_ACCESS_KEY_ID") 
        self.secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("R2_BUCKET_NAME_STAGING", "narratix-staging")
        
        if not all([self.account_id, self.access_key_id, self.secret_access_key]):
            logger.warning("R2 credentials not fully configured - storage operations will fail")
            logger.warning(f"Missing credentials - account_id: {'✓' if self.account_id else '✗'}, access_key: {'✓' if self.access_key_id else '✗'}, secret_key: {'✓' if self.secret_access_key else '✗'}")
            self.client = None
            return
            
        # Create S3 client configured for Cloudflare R2
        # Updated configuration to fix signature mismatch issues
        self.client = boto3.client(
            's3',
            endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name='auto',  # R2 uses 'auto' as region
            config=Config(
                signature_version='s3v4',
                # Fix for R2 compatibility issues with boto3 checksum behavior  
                s3={
                    'addressing_style': 'virtual'
                },
                # Disable automatic checksums that cause signature issues with R2
                disable_request_compression=True,
                parameter_validation=False
            )
        )
        
        logger.info(f"R2StorageService initialized for bucket: {self.bucket_name}")
    
    def upload_file(self, file_path: str, object_key: str, content_type: str = None) -> bool:
        """
        Upload a file to R2 storage.
        
        Args:
            file_path: Local path to the file
            object_key: Key to store the object under in R2
            content_type: MIME type of the file
            
        Returns:
            True if upload succeeded, False otherwise
        """
        if not self.client:
            logger.error("R2 client not initialized - check credentials")
            return False
            
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
                
            self.client.upload_file(file_path, self.bucket_name, object_key, ExtraArgs=extra_args)
            logger.info(f"Successfully uploaded {file_path} to {object_key}")
            return True
            
        except FileNotFoundError:
            logger.error(f"Local file not found: {file_path}")
            return False
        except NoCredentialsError:
            logger.error("R2 credentials not configured")
            return False
        except ClientError as e:
            logger.error(f"Failed to upload {file_path} to R2: {e}")
            return False
    
    def upload_bytes(self, data: bytes, object_key: str, content_type: str = None) -> bool:
        """
        Upload bytes data to R2 storage.
        
        Args:
            data: Bytes data to upload
            object_key: Key to store the object under in R2  
            content_type: MIME type of the data
            
        Returns:
            True if upload succeeded, False otherwise
        """
        if not self.client:
            logger.error("R2 client not initialized - check credentials")
            return False
            
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
                
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=data,
                **extra_args
            )
            logger.info(f"Successfully uploaded {len(data)} bytes to {object_key}")
            return True
            
        except NoCredentialsError:
            logger.error("R2 credentials not configured")
            return False
        except ClientError as e:
            logger.error(f"Failed to upload bytes to R2: {e}")
            return False
    
    def download_file(self, object_key: str, local_path: str) -> bool:
        """
        Download a file from R2 storage to local path.
        
        Args:
            object_key: Key of the object in R2
            local_path: Local path to save the file
            
        Returns:
            True if download succeeded, False otherwise
        """
        if not self.client:
            logger.error("R2 client not initialized - check credentials")
            return False
            
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.client.download_file(self.bucket_name, object_key, local_path)
            logger.info(f"Successfully downloaded {object_key} to {local_path}")
            return True
            
        except NoCredentialsError:
            logger.error("R2 credentials not configured")
            return False
        except ClientError as e:
            logger.error(f"Failed to download {object_key} from R2: {e}")
            return False
    
    def download_bytes(self, object_key: str) -> Optional[bytes]:
        """
        Download an object from R2 storage as bytes.
        
        Args:
            object_key: Key of the object in R2
            
        Returns:
            Bytes data if download succeeded, None otherwise
        """
        if not self.client:
            logger.error("R2 client not initialized - check credentials")
            return None
            
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=object_key)
            data = response['Body'].read()
            logger.info(f"Successfully downloaded {len(data)} bytes from {object_key}")
            return data
            
        except NoCredentialsError:
            logger.error("R2 credentials not configured")
            return None
        except ClientError as e:
            logger.error(f"Failed to download {object_key} from R2: {e}")
            return None
    
    def delete_object(self, object_key: str) -> bool:
        """
        Delete an object from R2 storage.
        
        Args:
            object_key: Key of the object to delete
            
        Returns:
            True if deletion succeeded, False otherwise
        """
        if not self.client:
            logger.error("R2 client not initialized - check credentials")
            return False
            
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info(f"Successfully deleted {object_key} from R2")
            return True
            
        except NoCredentialsError:
            logger.error("R2 credentials not configured")
            return False
        except ClientError as e:
            logger.error(f"Failed to delete {object_key} from R2: {e}")
            return False
    
    def list_objects(self, prefix: str = "") -> Optional[list]:
        """
        List objects in R2 bucket with optional prefix filter.
        
        Args:
            prefix: Optional prefix to filter objects
            
        Returns:
            List of object keys if successful, None otherwise
        """
        if not self.client:
            logger.error("R2 client not initialized - check credentials")
            return None
            
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                objects = [obj['Key'] for obj in response['Contents']]
                logger.info(f"Found {len(objects)} objects with prefix '{prefix}'")
                return objects
            else:
                logger.info(f"No objects found with prefix '{prefix}'")
                return []
                
        except NoCredentialsError:
            logger.error("R2 credentials not configured")
            return None
        except ClientError as e:
            logger.error(f"Failed to list objects in R2: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test connection to R2 bucket.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.client:
            logger.error("R2 client not initialized - check credentials")
            return False
            
        try:
            # Try to list objects to test connection
            self.client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            logger.info("R2 connection test successful")
            return True
            
        except NoCredentialsError:
            logger.error("R2 credentials not configured")
            return False
        except ClientError as e:
            logger.error(f"R2 connection test failed: {e}")
            return False

# Global instance for easy access
r2_storage = R2StorageService() 