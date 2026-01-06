"""
🎓 LAB SESSION: AULA 4.5 - COLOR CONVERTER (RGB -> ASS/BGR)
-----------------------------------------------------------
Ferramenta para criar cores compatíveis com FFmpeg sem dor de cabeça.

CONCEITO:
Input: (255, 165, 0) [Laranja RGB]
Processo: Inverte para BGR -> Converte para Hex -> Adiciona &H
Output: &H0000A5FF
"""

def rgb_to_ass(r, g, b, alpha=0):
    """
    Converte RGB (0-255) para formato ASS Hex.
    alpha: 0 (opaco) a 255 (transparente)
    """
    # Garante que os valores estão entre 0 e 255
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    a = max(0, min(255, alpha))

    # Formatação BGR (Blue-Green-Red)
    # :02X significa: 2 dígitos, Hexadecimal Maiúsculo
    ass_code = f"&H{a:02X}{b:02X}{g:02X}{r:02X}"
    return ass_code

def testar_cores():
    print("🎨 CONVERSOR DE PALETAS (RGB -> ASS)")
    print("-" * 60)
    
    paleta = {
        "Netflix Orange": (229, 9, 20),
        "Spotify Green":  (29, 185, 84),
        "Discord Blurple":(88, 101, 242),
        "Cyber Yellow":   (255, 211, 0),
        "Deep Shadow (50%)": (0, 0, 0, 128) # Com Alpha
    }

    print(f"{'NOME':<20} | {'RGB INPUT':<15} | {'ASS OUTPUT':<12}")
    print("-" * 60)

    for nome, values in paleta.items():
        if len(values) == 4:
            r, g, b, a = values
        else:
            r, g, b = values
            a = 0
            
        codigo = rgb_to_ass(r, g, b, a)
        print(f"{nome:<20} | {str(values):<15} | {codigo:<12}")

    print("-" * 60)
    print("✅ Agora você pode copiar esses códigos para o video_maker.py!")

if __name__ == "__main__":
    testar_cores()