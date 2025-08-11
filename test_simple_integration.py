#!/usr/bin/env python3
"""
Einfacher Integrationstest für Email-Abruf und Paperless-Verarbeitung
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# Füge src zum Python-Pfad hinzu
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def test_email_connections():
    """Test 1: Email-Verbindungen testen"""
    print("\n" + "="*60)
    print("TEST 1: EMAIL-VERBINDUNGEN")
    print("="*60)
    
    try:
        from paperless_ngx.infrastructure.config import get_settings
        from paperless_ngx.application.services import EmailFetcherService
        
        # Konfiguration laden
        settings = get_settings()
        print("✅ Konfiguration geladen")
        
        # Email-Service initialisieren
        email_service = EmailFetcherService()
        account_count = len(email_service._clients) if hasattr(email_service, '_clients') else 0
        print(f"✅ Email-Service initialisiert mit {account_count} Konten")
        
        # Verbindungen testen
        results = email_service.test_all_connections()
        
        for account_name, is_connected in results.items():
            status = "✅" if is_connected else "❌"
            print(f"   {status} {account_name}: {'Verbunden' if is_connected else 'Fehler'}")
        
        # Statistiken anzeigen
        print("\n📊 Email-Statistiken:")
        account_names = list(results.keys())
        for account_name in account_names:
            stats = email_service.get_account_statistics(account_name)
            print(f"   {account_name}:")
            print(f"      - Verarbeitete Emails: {stats.get('processed_emails', 0)}")
            print(f"      - Heruntergeladene Anhänge: {stats.get('downloaded_attachments', 0)}")
        
        return all(results.values())
        
    except Exception as e:
        print(f"❌ Fehler beim Email-Test: {e}")
        return False


def test_paperless_connection():
    """Test 2: Paperless API-Verbindung testen"""
    print("\n" + "="*60)
    print("TEST 2: PAPERLESS API-VERBINDUNG")
    print("="*60)
    
    try:
        from paperless_ngx.infrastructure.config import get_settings
        from paperless_ngx.infrastructure.paperless import PaperlessApiClient
        
        # Konfiguration laden
        settings = get_settings()
        api_url = settings.paperless_base_url
        api_token = settings.get_secret_value('paperless_api_token')
        
        print(f"📄 Verbinde zu Paperless API: {api_url}")
        
        # API-Client erstellen
        client = PaperlessApiClient(
            base_url=api_url,
            api_token=api_token
        )
        
        # Dokumente abrufen (nur erste Seite)
        response = client.get_documents(page_size=5)
        
        if response:
            doc_count = response.get('count', 0)
            print(f"✅ Verbindung erfolgreich")
            print(f"   - Dokumente gefunden: {doc_count}")
            
            # Erste 3 Dokumente anzeigen
            docs = response.get('results', [])[:3]
            if docs:
                print(f"\n📑 Beispiel-Dokumente (erste {len(docs)}):")
                for doc in docs:
                    print(f"   - ID {doc['id']}: {doc.get('title', 'Kein Titel')}")
                    if doc.get('correspondent_name'):
                        print(f"     Korrespondent: {doc['correspondent_name']}")
                    if doc.get('document_type_name'):
                        print(f"     Typ: {doc['document_type_name']}")
            
            return True
        else:
            print("❌ Keine Antwort von Paperless API")
            return False
            
    except Exception as e:
        print(f"❌ Fehler beim Paperless-Test: {e}")
        return False


def test_metadata_extraction():
    """Test 3: Metadaten-Extraktion mit LLM testen"""
    print("\n" + "="*60)
    print("TEST 3: METADATEN-EXTRAKTION MIT LLM")
    print("="*60)
    
    try:
        from paperless_ngx.infrastructure.config import get_settings
        from paperless_ngx.infrastructure.paperless import PaperlessApiClient
        from paperless_ngx.application.use_cases import MetadataExtractionUseCase
        
        # Konfiguration laden
        settings = get_settings()
        api_url = settings.paperless_base_url
        api_token = settings.get_secret_value('paperless_api_token')
        
        # API-Client erstellen
        client = PaperlessApiClient(
            base_url=api_url,
            api_token=api_token
        )
        
        # Dokumente abrufen
        print("📄 Suche Dokumente zum Testen...")
        response = client.get_documents(page_size=10)
        
        if not response or not response.get('results'):
            print("❌ Keine Dokumente gefunden")
            return False
        
        docs = response.get('results', [])
        
        # Dokument mit OCR-Text finden
        test_doc = None
        for doc in docs:
            doc_detail = client.get_document(doc['id'])
            ocr_text = doc_detail.get('content') or doc_detail.get('ocr', '')
            if ocr_text and len(ocr_text) > 100:
                test_doc = doc_detail
                break
        
        if not test_doc:
            print("❌ Kein Dokument mit OCR-Text gefunden")
            return False
        
        print(f"✅ Test-Dokument gefunden: ID {test_doc['id']}")
        print(f"   Titel: {test_doc.get('title', 'Kein Titel')}")
        print(f"   OCR-Text-Länge: {len(test_doc.get('content', ''))} Zeichen")
        
        # Metadaten extrahieren
        print("\n🤖 Extrahiere Metadaten mit LLM...")
        
        metadata_extractor = MetadataExtractionUseCase()
        ocr_text = test_doc.get('content') or test_doc.get('ocr', '')
        
        try:
            metadata = metadata_extractor.extract_metadata(
                ocr_text=ocr_text[:2000],  # Nur erste 2000 Zeichen für Test
                filename=test_doc.get('original_filename', 'test.pdf'),
                validate=True
            )
            
            print("✅ Metadaten erfolgreich extrahiert:")
            print(f"   - Korrespondent: {metadata.get('correspondent', 'N/A')}")
            print(f"   - Dokumenttyp: {metadata.get('document_type', 'N/A')}")
            print(f"   - Tags: {', '.join(metadata.get('tags', []))}")
            print(f"   - Datum: {metadata.get('date', 'N/A')}")
            
            # Beschreibung anzeigen (gekürzt)
            desc = metadata.get('description', '')
            if desc:
                print(f"   - Beschreibung: {desc[:100]}...")
            
            return True
            
        except Exception as e:
            print(f"⚠️ LLM-Extraktion fehlgeschlagen: {e}")
            print("   (Dies kann normal sein, wenn Ollama/OpenAI nicht konfiguriert ist)")
            return False
            
    except Exception as e:
        print(f"❌ Fehler beim Metadaten-Test: {e}")
        return False


def main():
    """Hauptfunktion für alle Tests"""
    print("\n" + "="*60)
    print("PAPERLESS NGX - INTEGRATIONSTESTS")
    print("="*60)
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Test 1: Email-Verbindungen
    results['email'] = test_email_connections()
    
    # Test 2: Paperless API
    results['paperless'] = test_paperless_connection()
    
    # Test 3: Metadaten-Extraktion
    results['metadata'] = test_metadata_extraction()
    
    # Zusammenfassung
    print("\n" + "="*60)
    print("TESTERGEBNISSE")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ BESTANDEN" if passed else "❌ FEHLGESCHLAGEN"
        print(f"{test_name.upper()}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALLE TESTS BESTANDEN!")
    else:
        print("⚠️ EINIGE TESTS FEHLGESCHLAGEN - Bitte Konfiguration prüfen")
    print("="*60)
    
    # Ergebnisse in JSON speichern
    results_file = Path("test_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'all_passed': all_passed
        }, f, indent=2)
    
    print(f"\nErgebnisse gespeichert in: {results_file}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())