import sys
import os

ROOT_DIR = r"c:\Users\atona\Documents\GitHub\model"
sys.path.insert(0, ROOT_DIR)

print("--- Testing Imports ---")
try:
    from core.settings import ADMIN_TOKEN
    print(f"OK: settings (ADMIN_TOKEN length: {len(ADMIN_TOKEN)})")
    
    from core.bd import inicjalizuj
    print("OK: core.bd")
    
    from core.wyszukiwarka import Wyszukiwarka
    print("OK: core.wyszukiwarka")
    
    from infrastructure.container import Container
    print("OK: infrastructure.container")
    
    from domain.services.ask_question import execute_ask_question
    print("OK: domain.services.ask_question")
    
    print("\n--- Testing Knowledge Loading ---")
    DATA_DIR = os.path.join(ROOT_DIR, "data")
    from infrastructure.knowledge_loader import utworz_wyszukiwarke
    w = utworz_wyszukiwarke(DATA_DIR)
    print(f"OK: Wyszukiwarka loaded with {len(w.fragmenty)} fragments")
    
    print("\n--- Testing Search Logic ---")
    wyniki = w.szukaj("ile razy mozna zdawac egzamin")
    if wyniki:
        print(f"OK: Search returned: {wyniki[0].tytul} (sim: {wyniki[0].podobienstwo})")
    else:
        print("FAIL: Search returned no results")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\nFAILED: {e}")
