from typing import Optional, List, Dict

def build_payload(text: Optional[str], files: Optional[List[str]]) -> Dict:
    """Формирует payload для API"""
    payload = {}
    if text:
        payload["text"] = text
    if files:
        payload["attachments"] = files
    return payload
