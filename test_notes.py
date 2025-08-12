#!/usr/bin/env python3
"""Test script to check notes field in Paperless NGX."""

import requests
from src.paperless_ngx.infrastructure.config import get_settings
from src.paperless_ngx.infrastructure.paperless import PaperlessApiClient

settings = get_settings()
base_url = settings.paperless_base_url
token = settings.get_secret_value("paperless_api_token")

# Get API schema for documents
headers = {
    "Authorization": f"Token {token}",
    "Accept": "application/json"
}

# Try to get any document with notes
url = f"{base_url}/documents/?format=json&page_size=100"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    docs = response.json()["results"]
    found_with_notes = False
    
    for doc in docs:
        notes = doc.get("notes")
        if notes and len(notes) > 0:
            print(f"Found document with notes:")
            print(f"ID: {doc['id']}")
            print(f"Title: {doc['title']}")
            print(f"Notes: {notes}")
            print(f"Notes type: {type(notes)}")
            found_with_notes = True
            break
    
    if not found_with_notes:
        print("No documents found with notes")
        print("\nChecking first few documents:")
        for doc in docs[:3]:
            print(f"\nDocument {doc['id']}:")
            print(f"  Title: {doc['title']}")
            print(f"  Notes field: {doc.get('notes')}")
            print(f"  Notes type: {type(doc.get('notes'))}")

# Now test creating a note
print("\n" + "="*50)
print("Testing note creation...")

client = PaperlessApiClient()

# Test with the notes field as a list of note objects
test_doc_id = 447

# Paperless NGX notes are stored as an array of note objects
# Each note object has: note (text), created (timestamp), user (user id)
import datetime

note_object = {
    "note": "Dies ist eine Test-Notiz vom automatischen System",
    "created": datetime.datetime.now().isoformat(),
}

print(f"\nTrying to update document {test_doc_id} with note object...")
try:
    # Try with single note object
    update_data = {"notes": [note_object]}
    result = client.update_document(test_doc_id, update_data)
    print(f"Success! Notes: {result.get('notes')}")
except Exception as e:
    print(f"Failed with note object: {e}")
    
    # Try with just string in array
    print("\nTrying with simple string in array...")
    try:
        update_data = {"notes": ["Test-Notiz als einfacher String"]}
        result = client.update_document(test_doc_id, update_data)
        print(f"Result: {result.get('notes')}")
    except Exception as e2:
        print(f"Failed with string array: {e2}")