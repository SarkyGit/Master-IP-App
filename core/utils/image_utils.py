import base64
from fastapi import UploadFile

async def file_to_data_uri(file: UploadFile) -> str:
    data = await file.read()
    encoded = base64.b64encode(data).decode()
    return f"data:{file.content_type};base64,{encoded}"
