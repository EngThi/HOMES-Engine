from typing import Tuple

def rgb_to_ass_hex(rgb: Tuple[int, int, int], alpha: int = 0) -> str:
    """
    Converte uma tupla RGB (Red, Green, Blue) para o formato hexadecimal ASS (Advanced Substation Alpha).
    O formato ASS usa ordem BGR (Blue, Green, Red).

    Args:
        rgb (tuple): (R, G, B) inteiros de 0-255.
        alpha (int): Transparência de 0 (opaco) a 255 (invisível).

    Returns:
        str: String formatada '&H[Alpha][Blue][Green][Red]' (ex: '&H00FFFF00')
    """
    r, g, b = rgb
    # Clamp values to 0-255
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    a = max(0, min(255, alpha))

    return f"&H{a:02X}{b:02X}{g:02X}{r:02X}"

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Converte Hex HTML (#RRGGBB) para tupla RGB.
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
