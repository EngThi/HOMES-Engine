# ⚡ HOMES-Engine - Quick Reference

## 🎯 Missão Rápida (TL;DR)

```
Você está aqui → HOMES-Engine está 60% pronto
Faltam → Requirements.txt, config.py, setup.sh, documentação
Tempo → 2-3 horas
Meta → 100% funcional + pronto pra integração
```

---

## 📋 TODO List (4 Fases)

### ✅ FASE 1: Setup Files (30 min)
```bash
[ ] Criar requirements.txt (todas as libs com versões)
[ ] Criar config.py (centralizar configurações)
[ ] Criar .env.example (template de variáveis)
```

**Arquivos a criar:**
```
requirements.txt (50 linhas)
config.py (120 linhas)
.env.example (20 linhas)
```

### ✅ FASE 2: Refactor (45 min)
```bash
[ ] Atualizar main.py (integrar config.py)
[ ] Atualizar core/ai_writer.py (integrar config)
[ ] Atualizar core/video_maker.py (integrar config)
[ ] Atualizar core/tts_engine.py (integrar config)
[ ] Testar imports (python -c "import config")
```

### ✅ FASE 3: Automation (30 min)
```bash
[ ] Criar setup.sh (script Termux)
[ ] Chmod +x setup.sh
[ ] Testar em simulador Termux
```

**Arquivo a criar:**
```
setup.sh (80 linhas)
```

### ✅ FASE 4: Documentation (30 min)
```bash
[ ] Criar docs/SETUP_TERMUX.md (guia completo)
[ ] Atualizar README.md (quick start)
[ ] Criar devlog/Session-2.md (progress log)
```

**Arquivos a criar:**
```
docs/SETUP_TERMUX.md (200 linhas)
devlog/Session-2.md (150 linhas)
```

---

## 🔧 Arquivos a Criar/Modificar

### CRIAR (5 novos):
```
✨ requirements.txt       (NOVO)
✨ config.py              (NOVO)
✨ .env.example           (NOVO)
✨ setup.sh               (NOVO)
✨ docs/SETUP_TERMUX.md   (NOVO)
✨ devlog/Session-2.md    (NOVO)
```

### MODIFICAR (4 existentes):
```
🔄 main.py               (adicionar imports config)
🔄 core/ai_writer.py     (adicionar imports config)
🔄 core/video_maker.py   (adicionar imports config)
🔄 core/tts_engine.py    (adicionar imports config)
🔄 README.md             (adicionar quick start)
```

---

## 🎬 Sequência Exata de Comandos

```bash
# 1. Entrar no repo
cd ~/HOMES-Engine
git status

# 2. CRIAR requirements.txt
cat > requirements.txt << 'EOF'
google-generativeai==0.7.2
moviepy==1.0.3
opencv-python==4.8.1.78
Pillow==10.1.0
numpy==1.24.3
google-cloud-texttospeech==2.14.1
pydub==0.25.1
requests==2.31.0
python-dotenv==1.0.0
EOF
git add requirements.txt
git commit -m "feat(setup): add requirements.txt with all dependencies"

# 3. CRIAR config.py
# [Copiar conteúdo do HANDOFF.md - FASE 1 - Tarefa 1.2]
git add config.py
git commit -m "feat(config): add centralized configuration management"

# 4. CRIAR .env.example
# [Copiar conteúdo do HANDOFF.md - FASE 1 - Tarefa 1.3]
git add .env.example
git commit -m "docs: add .env.example template"

# 5. MODIFICAR main.py
# [Adicionar: from config import validate_config, THEMES, etc]
git add main.py
git commit -m "refactor(main): integrate centralized config system"

# 6. MODIFICAR core/*.py
# [Adicionar imports de config em cada arquivo]
git add core/
git commit -m "refactor(core): update imports to use centralized config"

# 7. CRIAR setup.sh
# [Copiar conteúdo do HANDOFF.md - FASE 3 - Tarefa 3.1]
chmod +x setup.sh
git add setup.sh
git commit -m "feat(setup): add automated Termux installation script"

# 8. CRIAR docs/SETUP_TERMUX.md
mkdir -p docs
# [Copiar conteúdo do HANDOFF.md - FASE 4 - Tarefa 4.1]
git add docs/SETUP_TERMUX.md
git commit -m "docs(setup): add detailed Termux installation guide"

# 9. CRIAR devlog/Session-2.md
# [Copiar conteúdo do HANDOFF.md - FASE 4 - Tarefa 4.2]
git add devlog/Session-2.md
git commit -m "docs: add Session-2 devlog with completion metrics"

# 10. MODIFICAR README.md
# [Adicionar quick start section]
git add README.md
git commit -m "docs(readme): add quick start sections"

# 11. PUSH final
git push origin master
```

---

## ✅ Checklist de Conclusão

```
ANTES (Diagnóstico - EngThi em 6/jan/2026 12:07):
├── [ ] requirements.txt
├── [ ] config.py
├── [ ] setup.sh
├── [ ] docs/SETUP_TERMUX.md
├── [ ] devlog/Session-2.md
└── Commits: 0 (hoje)

DEPOIS (Esperado após HANDOFF):
├── [x] requirements.txt ✅
├── [x] config.py ✅
├── [x] setup.sh ✅
├── [x] docs/SETUP_TERMUX.md ✅
├── [x] devlog/Session-2.md ✅
└── Commits: 8-10 ✅

VALIDAÇÃO:
├── [x] python -c "import config" (sem erro)
├── [x] python main.py (roda com menu)
├── [x] Todos os arquivos commitados
└── [x] Push no master
```

---

## 🚨 Erros Comuns & Soluções

### ❌ "ModuleNotFoundError: No module named 'config'"
```bash
# Solução: Certifique-se que config.py está no mesmo nível de main.py
ls -la config.py main.py
# Devem estar lado a lado no raiz do projeto
```

### ❌ "No module named 'google'"
```bash
# Solução: Instalar requirements
pip install -r requirements.txt

# Ou instalar isolado
pip install google-generativeai
```

### ❌ "ffmpeg: command not found"
```bash
# Solução: Instalar ffmpeg
# Linux:
sudo apt install ffmpeg

# Termux:
pkg install ffmpeg

# Mac:
brew install ffmpeg
```

### ❌ "GEMINI_API_KEY not configured"
```bash
# Solução: Criar .env e adicionar chave
cp .env.example .env
nano .env
# Adicionar sua chave GEMINI_API_KEY
```

---

## 📊 Tempo por Fase

```
Fase 1 (Requirements + Config)   → 30 min  ⏱️
Fase 2 (Refactoring)             → 45 min  ⏱️
Fase 3 (Setup Script)            → 30 min  ⏱️
Fase 4 (Documentação)            → 30 min  ⏱️
                                  ─────────
TOTAL                            → 2h 15m  ⏱️
(+ 15 min buffer para troubleshooting)
```

---

## 🎯 Commits Esperados (8-10)

1. `feat(setup): add requirements.txt with all dependencies`
2. `feat(config): add centralized configuration management`
3. `docs: add .env.example template`
4. `refactor(main): integrate centralized config system`
5. `refactor(core): update imports to use centralized config`
6. `feat(setup): add automated Termux installation script`
7. `docs(setup): add detailed Termux installation guide`
8. `docs: add Session-2 devlog with completion metrics`
9. `docs(readme): add quick start sections`
10. `docs: add HANDOFF guide for next development session`

---

## 🚀 Próximas Etapas (Após HOMES-Engine)

1. **Backend NestJS** (ai-video-factory) → 5-8 horas
2. **Frontend React** (homes-prompt-manager) → 3-5 horas
3. **Integração completa** → 2-3 horas
4. **Deploy** (Docker + Railway) → 1-2 horas

---

## 📞 Dúvidas Frequentes

**P: Por que criar config.py?**  
R: Centralizar todas as configurações, facilita manutenção e evita hardcodes.

**P: Posso pular alguma fase?**  
R: Não recomendo. Cada fase depende da anterior.

**P: Quanto tempo vai levar?**  
R: 2-3 horas se seguir o guia exatamente.

**P: E se eu ficar preso?**  
R: Veja HANDOFF.md seção "SE ALGO DER ERRADO"

---

## 🏆 Vitória Final

Quando você terminar:
- ✅ HOMES-Engine 100% funcional
- ✅ Setup automático Termux
- ✅ Documentação completa
- ✅ Pronto para integração Backend
- ✅ Commits rastreados no Hackatime

**Então você começa o Backend NestJS!** 🎉

---

**Preparado? Execute:**
```bash
cd ~/HOMES-Engine
# Leia este arquivo novamente
cat QUICK_REFERENCE.md

# Depois, siga HANDOFF.md
cat HANDOFF.md

# E comece!
# FASE 1: criar requirements.txt
```

Good luck! 🚀
