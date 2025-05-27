import os
import mimetypes
from datetime import datetime, timedelta, UTC
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

def upload_to_azure_storage(file_path):
    """
    Upload a file to Azure Blob Storage and return a presigned URL.
    
    Args:
        file_path (str): Path to the file to upload
        
    Returns:
        str: Presigned URL for the uploaded file
    """
    # Get Azure Storage credentials from environment variables
    connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.environ.get('AZURE_STORAGE_CONTAINER')
    
    if not connection_string or not container_name:
        raise ValueError("Azure Storage credentials not found in environment variables")
    
    # Create the BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    
    # Get file name and content type
    file_name = os.path.basename(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    
    # Upload the file
    with open(file_path, "rb") as data:
        blob_client = container_client.upload_blob(
            name=file_name,
            data=data,
            overwrite=True,
            content_type=content_type
        )
    
    # Generate SAS token for the blob
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=container_name,
        blob_name=file_name,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(UTC) + timedelta(hours=1)
    )
    
    # Generate the presigned URL
    presigned_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{file_name}?{sas_token}"
    
    return presigned_url 