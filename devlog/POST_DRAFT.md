# 📝 RASCUNHO DE POST - DEVLOG (HACKATHON)

**Plataforma Alvo:** LinkedIn / Discord / Twitter
**Limite:** ~2000 caracteres
**Mídia:** 8 Slots (Vídeo + Imagens)

---

## 🚀 Título: Transformei meu Celular em uma Fábrica de Vídeos com Python & IA (No Termux!)

Sempre me disseram que para programar coisas complexas eu precisava de um PC gamer de R$ 5.000. Eu discordei. 📱💻

Nas últimas 5 horas, transformei meu Android em uma estação de engenharia de software completa para o Hackathon. Apresento a **v3.0 do HOMES Engine**: um pipeline de automação de vídeo "Absolute Cinema" rodando 100% via terminal.

### 🛠️ O Que Eu Construí (A Engenharia por Trás)

Não é só um script. É uma arquitetura modular.

1.  **Cérebro (Google Gemini 2.5):** O sistema gera roteiros otimizados para retenção usando a API REST do Gemini. Nada de bibliotecas pesadas.
2.  **Voz (Neural TTS):** Integrei o novo modelo de áudio do Google para narrações ultra-realistas.
3.  **Editor (FFmpeg Modular):** Aqui a mágica acontece. Criei um motor que aplica zoom dinâmico (Ken Burns), corrige cores e mixa o áudio automaticamente.

**[MÍDIA 1: VÍDEO DO RESULTADO FINAL - "IA NO TERMUX"]**
*(Legenda: Olha o resultado saindo direto da pasta output!)*

### 🎨 O Desafio das Cores (Engenharia Reversa)

O FFmpeg usa um padrão de cor bizarro chamado ASS (não ria!) que inverte RGB para BGR. Em vez de hardcodar strings mágicas, escrevi um módulo `color_utils.py` que converte tuplas Python `(255, 165, 0)` para o hexadecimal correto.

**[MÍDIA 2: PRINT DO CÓDIGO color_utils.py]**
*(Legenda: Clean Code até no celular. Modularização é vida.)*

### 📉 Engenharia de Áudio: Sidechain Compression

Sabe quando o YouTuber fala e a música abaixa sozinha? Isso se chama "Ducking". Implementei um filtro complexo no FFmpeg que analisa a onda sonora da voz e comprime a música em tempo real.

**[MÍDIA 3: PRINT DO TERMINAL RODANDO O LAB_SESSION DA AULA 2]**
*(Legenda: Simulador de áudio rodando no terminal para testes.)*

### 🧩 Por Que Modular?

Poderia ter feito um "arquivo linguiça" de 1000 linhas. Mas dividi em:
- `core/ai_writer.py` (Roteiro)
- `core/video_maker.py` (Render)
- `core/ffmpeg_engine.py` (Processamento)

Isso permite que eu plugue novas IAs (como Pollinations para imagens) sem quebrar o resto.

**[MÍDIA 4: PRINT DO COMANDO TREE MOSTRANDO A ESTRUTURA DE PASTAS]**

### 🔮 Próximos Passos

O motor está pronto. Agora vou conectá-lo a um Backend NestJS para criar uma API real. O objetivo? Permitir que qualquer um crie vídeos virais pelo celular.

Obrigado por acompanhar essa jornada de código, café e Termux! ☕🚀

#Python #Termux #Hackathon #AI #FFmpeg #Engineering #CodingOnMobile #BuildInPublic

---

### 📸 CHECKLIST DE MÍDIAS PARA ANEXAR

1.  🎥 **Vídeo Final:** `HOMES_v1.4_....mp4` (O que renderizamos com o tema Yellow Punch).
2.  🖼️ **Print Código:** `core/color_utils.py` (Mostra a função rgb_to_ass).
3.  🖼️ **Print Terminal:** O simulador de áudio do `lab_session.py` (as barrinhas se movendo).
4.  🖼️ **Print Estrutura:** O comando `ls -R` ou `tree` mostrando a organização das pastas.
5.  🖼️ **Print Git:** O comando `git log --oneline` mostrando os commits semânticos ("feat:", "refactor:").
