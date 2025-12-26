from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import os
import io
import json

# Your Google Drive folder IDs
DRIVE_FOLDERS = {
    'notes': '1nKTDQFB1A5clU49-umH_L3neUrBTlWHL',
    'pyq': '1udxVk0O41nnHU4h1kJcHzAz2Vn6_TrFW',
    'semester': '1PvL0t92eV3H6eQyeO7ypv74tFgu3HJ9O'
}

def get_drive_service():
    """Get Google Drive service using Service Account"""
    # Try to get service account from environment variable (Render)
    service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    
    if service_account_json:
        # Load from environment variable
        try:
            service_account_info = json.loads(service_account_json)
        except:
            # If it's a path string
            if os.path.exists(service_account_json):
                with open(service_account_json, 'r') as f:
                    service_account_info = json.load(f)
            else:
                raise Exception("Invalid service account JSON")
    else:
        # Try local file (development)
        service_account_file = 'service_account.json'
        if os.path.exists(service_account_file):
            with open(service_account_file, 'r') as f:
                service_account_info = json.load(f)
        else:
            raise Exception("No service account credentials found")
    
    # Create credentials
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    
    # Build service
    return build('drive', 'v3', credentials=credentials)

def upload_to_my_drive(file_storage, filename, resource_type):
    """Upload file to Google Drive"""
    service = get_drive_service()
    
    # Get folder ID
    folder_id = DRIVE_FOLDERS.get(resource_type.lower(), DRIVE_FOLDERS['notes'])
    
    # File metadata
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    # Read file content
    file_content = file_storage.read()
    media = MediaIoBaseUpload(
        io.BytesIO(file_content),
        mimetype=file_storage.content_type or 'application/octet-stream'
    )
    
    # Upload file
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink, webContentLink'
    ).execute()
    
    # Make file publicly accessible
    service.permissions().create(
        fileId=file['id'],
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()
    
    return {
        'file_id': file['id'],
        'view_link': file['webViewLink'],
        'download_link': file['webContentLink'].replace('&export=download', '')
    }