# Devlog - Session 4: Pipeline Integration & Farming

**Data:** 6 Janeiro 2026  
**Foco:** Consolidação de Ferramentas CLI e Pipeline Automático

---

## 🚜 Farming & Polishing

Para garantir a robustez do sistema antes da integração com o Backend, realizamos uma sessão de "farming" (polimento e automação).

### ✅ Tarefas Realizadas

1.  **Pipeline de Automação (`run_full_pipeline.sh`)**
    -   Criado script Bash para orquestrar todo o fluxo: `Topic -> AI Script -> TTS -> FFmpeg`.
    -   Suporte a fallback automático (Gemini TTS -> Edge TTS).
    -   Geração automática de legendas (VTT) e placeholder de áudio.

2.  **CLI Support nos Módulos Core**
    -   **`core/ai_writer.py`**: Adicionado suporte a `argparse` para execução direta via terminal (`--topic`, `--out`).
    -   **`core/google_tts.py`**: Adicionado suporte a `argparse` (`--input`, `--out`, `--voice`).
    -   Isso permite que esses módulos sejam testados isoladamente ou chamados por scripts shell.

3.  **Validação**
    -   Execução de testes de configuração: `python3 -m tests.test_config` (PASSOU).
    -   Verificação de permissões de execução.

### 📝 Mudanças no Código

-   `run_full_pipeline.sh`: Novo arquivo.
-   `core/ai_writer.py`: Adicionado bloco `if __name__ == "__main__":`.
-   `core/google_tts.py`: Adicionado bloco `if __name__ == "__main__":`.

---

## 🚀 Próximos Passos

-   Testar `run_full_pipeline.sh` com um tópico real.
-   Iniciar integração com NestJS.

---
*Assinado: Homes Architect*
