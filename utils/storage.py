import os
import uuid
import mimetypes
from datetime import datetime, timedelta, UTC
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from urllib.parse import urlparse, parse_qs, quote
from azure.core.exceptions import AzureError
import time
from tqdm import tqdm


def _mask(value, keep=8):
    """Mask a secret for debug output, showing only the first `keep` characters."""
    if not value:
        return None
    return value[:keep] + "..." if len(value) > keep else "***"

def upload_to_azure_storage(file_path, debug=False):
    """
    Upload a file to Azure Blob Storage and return a presigned URL.
    
    Args:
        file_path (str): Path to the file to upload
        debug (bool): Whether to show debug information
        
    Returns:
        str: Presigned URL for the uploaded file
    """
    # Get Azure Storage credentials from environment variables
    sas_token = os.environ.get('AZURE_SAS_TOKEN')
    container_name = os.environ.get('AZURE_STORAGE_CONTAINER')
    account_name = os.environ.get('AZURE_STORAGE_ACCOUNT')
    
    if debug:
        print("\nEnvironment Variables:")
        print("FIREFLY_SERVICES_CLIENT_ID:", _mask(os.environ.get('FIREFLY_SERVICES_CLIENT_ID')))
        print("FIREFLY_SERVICES_CLIENT_SECRET:", _mask(os.environ.get('FIREFLY_SERVICES_CLIENT_SECRET'), keep=4))
        print("STORAGE_TYPE:", os.environ.get('STORAGE_TYPE'))
        print("AZURE_SAS_TOKEN:", _mask(sas_token, keep=20))
        print("AZURE_STORAGE_CONTAINER:", container_name)
        print("AZURE_STORAGE_ACCOUNT:", account_name)
        print("THROTTLE_LIMIT_FIREFLY:", os.environ.get('THROTTLE_LIMIT_FIREFLY'))
    
    if not sas_token or not container_name or not account_name:
        raise ValueError("Azure Storage credentials not found in environment variables")
    
    try:
        # Create the BlobServiceClient using the account URL and SAS token
        account_url = f"https://{account_name}.blob.core.windows.net"
        if debug:
            print(f"Creating BlobServiceClient with account URL: {account_url}")
        
        # Create the client with the SAS token
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=sas_token
        )
        
        if debug:
            print("BlobServiceClient created successfully")
        
        try:
            container_client = blob_service_client.get_container_client(container_name)
            if debug:
                print(f"Container Client Created: {container_name}")
        except Exception as e:
            if debug:
                print(f"Error creating container client: {str(e)}")
            raise
        
        # Get file name and content type. Prefix the blob name with a UUID so two
        # files sharing a basename in different folders don't overwrite each other.
        original_name = os.path.basename(file_path)
        ext = os.path.splitext(original_name)[1]
        blob_name = f"{uuid.uuid4().hex}{ext}"
        content_type, _ = mimetypes.guess_type(file_path)

        if debug:
            print(f"\nPreparing to upload file:")
            print(f"File path: {file_path}")
            print(f"Original name: {original_name}")
            print(f"Blob name: {blob_name}")
            print(f"Content Type: {content_type}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file size
        file_size = os.path.getsize(file_path)
        if debug:
            print(f"File size: {file_size} bytes")
        
        # Upload the file using upload_blob_from_path
        try:
            if debug:
                print("\nStarting file upload...")
            
            start_time = time.time()

            # Create a blob client
            blob_client = container_client.get_blob_client(blob_name)

            # Upload the file with progress bar. No SDK-level timeout — large media
            # files on slow connections need to be allowed to finish.
            with open(file_path, "rb") as data:
                with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"Uploading {original_name}") as pbar:
                    blob_client.upload_blob(
                        data,
                        overwrite=True,
                        content_type=content_type,
                        max_concurrency=1,  # Sequential upload for accurate progress
                        progress_hook=lambda current, total: pbar.update(current - pbar.n)
                    )
            
            if debug:
                print("Blob uploaded successfully")
                print(f"Upload completed in {time.time() - start_time:.2f} seconds")
            
        except AzureError as e:
            if debug:
                print(f"Azure Error during upload: {str(e)}")
                print(f"Error details: {e.error_code if hasattr(e, 'error_code') else 'No error code'}")
            raise
        except Exception as e:
            if debug:
                print(f"Error during file upload: {str(e)}")
                print(f"Error type: {type(e).__name__}")
            raise
        
        if debug:
            print("\nGenerating URL for the blob...")
        
        # Generate the URL with the SAS token
        url = f"https://{account_name}.blob.core.windows.net/{container_name}/{quote(blob_name)}?{sas_token}"
        
        if debug:
            print("URL generated successfully")
            print(f"Generated URL (first 50 chars): {url[:50]}...")
        
        return url
        
    except Exception as e:
        if debug:
            print(f"\nError in upload_to_azure_storage:")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            import traceback
            print("\nFull traceback:")
            print(traceback.format_exc())
        raise 