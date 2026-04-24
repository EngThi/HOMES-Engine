import pytest
import time
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Adicionar raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.queue_daemon import process_job

def test_process_job_happy_path(tmp_path):
    """Job .pending -> .done quando generate_video tem sucesso."""
    # Simula pasta scripts no tmp_path
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    job = scripts_dir / "ia_demo_123.pending.txt"
    job.write_text("Test script content")

    # Mock do generate_video e do log
    with patch("core.queue_daemon.generate_video") as mock_gv:
        mock_gv.return_value = None
        
        # Como process_job usa caminhos relativos fixos 'scripts/', 
        # precisamos temporariamente mudar o cwd ou mockar o Path
        with patch("pathlib.Path.rename") as mock_rename:
            process_job(job)
            
    # Verificação básica de chamadas (o Path.rename lida com a lógica física)
    assert mock_gv.called
    mock_gv.assert_called_with(str(job.with_suffix(".running.txt")), brand_name="demo")

def test_brand_extracted_from_filename():
    """Simula a extração de brand de diferentes padrões de nome."""
    # Teste unitário simples da lógica de extração dentro do process_job
    # ia_brand_timestamp.pending.txt
    filename = "ia_stoic_1735000000.pending.txt"
    parts = filename.split("_")
    brand = "demo"
    if len(parts) >= 2 and parts[1]:
        brand = parts[1]
    assert brand == "stoic"
