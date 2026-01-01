from google.cloud import storage

def download_image(bucket_name, blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    return blob.download_as_bytes()