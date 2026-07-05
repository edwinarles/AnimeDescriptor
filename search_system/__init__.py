print("DEBUG INIT: 1. Iniciando __init__.py...")
import os
# Desactivar CUDA a nivel de paquete para evitar crasheos de PyTorch con tarjetas gráficas incompatibles
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

print("DEBUG INIT: 2. Importando sentence_transformers...")
# Pre-cargar sentence_transformers para evitar conflictos de DLL en Windows (DLL Hell) al importar numpy/faiss
try:
    from sentence_transformers import SentenceTransformer
    print("DEBUG INIT: 3. SentenceTransformer importado.")
except ImportError:
    print("DEBUG INIT: 3 (Error). SentenceTransformer falló.")
    pass

print("DEBUG INIT: 4. Importando SearchEngine...")
from .search_engine import SearchEngine
print("DEBUG INIT: 5. SearchEngine importado exitosamente en __init__.py.")

__all__ = ['SearchEngine']


