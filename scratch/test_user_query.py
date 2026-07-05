import os
import sys

# Desactivar CUDA/GPU para evitar que PyTorch intente inicializar CUDA y crashe el intérprete en Windows
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Configurar encoding UTF-8 en salida para evitar UnicodeEncodeError en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Pre-cargar sentence_transformers de primero absoluto para evitar conflictos de DLL en Windows
try:
    from sentence_transformers import SentenceTransformer
    print("DEBUG TEST_USER: SentenceTransformer pre-cargado con éxito.")
except Exception as e:
    print(f"DEBUG TEST_USER: Error pre-cargando SentenceTransformer: {e}")

# Agregar directorio del proyecto a sys.path
sys.path.append(r"c:\Users\Edwin\Desktop\Nueva carpeta\OtakuDescriptor")

# Importar los demás módulos
from database import Database
from search_system import SearchEngine
from search_system.bert_helper import BERTEmbedder
from utils import normalizar_texto
import numpy as np
from database import db

def test_query(query_text):
    print(f"\n--- Probando Query: '{query_text}' ---")
    vector = BERTEmbedder.get_embedding(normalizar_texto(query_text))
    results = SearchEngine.search(vector, query_text=query_text, top_k=10)
    
    # Buscar Naruto en el resultado
    naruto_rank = -1
    naruto_score = 0.0
    for idx, anime in enumerate(results):
        if "naruto" in anime.get('main_title', '').lower():
            naruto_rank = idx + 1
            naruto_score = anime.get('similarity_score', 0)
            break
            
    print("Top 5 Resultados:")
    for idx, anime in enumerate(results[:5]):
        score = anime.get('similarity_score', 0)
        title = anime.get('main_title', 'Unknown')
        print(f"  {idx+1}. {title} (Similitud: {score:.2f}%)")
        
    if naruto_rank != -1:
        print(f"⭐ Naruto encontrado en Rango {naruto_rank} con Similitud {naruto_score:.2f}%")
    else:
        # Calcular similitud directa
        naruto_doc = db.db.animes.find_one({"main_title": "Naruto"})
        if not naruto_doc:
            naruto_doc = db.db.animes.find_one({"title.english": "Naruto"})
        if naruto_doc:
            text_parts = []
            titles = [naruto_doc.get('main_title', '')]
            title_obj = naruto_doc.get('title') or {}
            for key in ['romaji', 'english', 'native']:
                val = title_obj.get(key)
                if val and val not in titles:
                    titles.append(val)
            text_parts.append("Títulos: " + ", ".join(titles))
            from utils import limpiar_descripcion
            desc_clean = limpiar_descripcion(naruto_doc.get('description', ''))
            if desc_clean:
                text_parts.append(desc_clean)
            text = " ".join(text_parts)
            norm_text = normalizar_texto(text)
            
            anime_emb = BERTEmbedder.get_embedding(norm_text)
            q_vec = np.array(vector[0])
            a_vec = np.array(anime_emb)
            sim = np.dot(q_vec, a_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(a_vec))
            print(f"❌ Naruto NO entró en el Top 10. Su Similitud directa es {sim*100:.2f}%")

def run():
    try:
        print("Inicializando Base de Datos...")
        Database.init_db()
        
        print("Cargando Motor de Búsqueda...")
        SearchEngine.load_data()
        
        # Probar con "boy" (correcto) y "bow" (con typo)
        test_query("a boy who want to become a hokage")
        test_query("a bow who want to become a hokage")
        
    except Exception as e:
        import traceback
        print(f"Error en run: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run()
