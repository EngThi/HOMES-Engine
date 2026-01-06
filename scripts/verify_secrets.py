import os
from pathlib import Path

def verify():
    print("--- 🛡️ HOMES SECRET AUDIT ---")
    secrets_path = Path(".secrets")
    
    if not secrets_path.exists():
        print("❌ Arquivo .secrets não encontrado!")
        return

    keys_to_check = [
        "GITHUB_USER",
        "GITHUB_TOKEN",
        "GIT_AUTH_URL",
        "GEMINI_API_KEY"
    ]
    
    with open(secrets_path, "r") as f:
        content = f.read()
        
    for key in keys_to_check:
        if f"{key}=" in content:
            # Check if it has a value other than placeholder
            val = [line for line in content.split("\n") if line.startswith(f"{key}=")][0].split("=")[1]
            if val and "COLE_SUA_CHAVE" not in val and "sua_chave" not in val:
                print(f"✅ {key}: CONFIGURADO")
            else:
                print(f"⚠️ {key}: PENDENTE (Placeholder)")
        else:
            print(f"❌ {key}: NÃO ENCONTRADO")

if __name__ == "__main__":
    verify()
