import os

def criar_prompt_homes():
        print("--- HOMES: Gerador de Roteiros Faceless ---")
        tema = input("Digite o tema do vídeo: ")
                
                    # Suas diretrizes de "Absolute Cinema" e Retenção
                        prompt_estruturado = f"""
                            [DIRETRIZES DE BRANDING HOMES]
                                Atue como um roteirista sênior de canais Faceless.
                                    TEMA: {tema}
                                        ESTILO: Ritmo dinâmico, ganchos de retenção a cada 30 segundos.
                                            ESTÉTICA: Cinematográfica e futurista.
                                                REQUISITO: Gere um roteiro pronto para narração (TTS) e sugestões de prompts de imagem para o pipeline.
                                                    """
                                                        
                                                            # Criar nome de arquivo amigável
                                                                nome_arquivo = f"roteiro_{tema.replace(' ', '_').lower()}.txt"
                                                                    
                                                                        with open(nome_arquivo, "w", encoding="utf-8") as f:
                                                                                    f.write(prompt_estruturado)
                                                                                        
                                                                                            print(f"\n✅ Sucesso! Prompt salvo em: {nome_arquivo}")

                                                                                            if __name__ == "__main__":
                                                                                                    criar_prompt_homes()

