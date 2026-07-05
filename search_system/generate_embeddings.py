print("DEBUG: 1. Iniciando script...")
import os
import sys

# Desactivar CUDA/GPU para evitar que PyTorch intente inicializar la RTX 5060 y crashe el intérprete
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
print("DEBUG: 2. CUDA desactivado.")

# Asegurar que el directorio raíz está en sys.path para los imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("DEBUG: 3. Importando BERTEmbedder (primero)...")
from search_system.bert_helper import BERTEmbedder

import time
import numpy as np
print("DEBUG: 4. Numpy cargado.")
print("DEBUG: 5. Importando Database...")
from database import Database, db
print("DEBUG: 6. Importando Config...")
from config import Config
print("DEBUG: 7. Importando Utils...")
from utils import normalizar_texto, limpiar_descripcion
print("DEBUG: 8. Importando tqdm...")
from tqdm import tqdm
print("DEBUG: 9. Todos los imports listos.")

# Inicializar conexión a DB
Database.init_db()

class EmbeddingGenerator:
    def __init__(self):
        self.collection = db.db.animes
        self.model = Config.BERT_MODEL
        
    def generate_embedding(self, text):
        """Genera embedding para un texto"""
        try:
            text = text.replace("\n", " ")
            return BERTEmbedder.get_embedding(text)
        except Exception as e:
            print(f"Error generando embedding: {e}")
            return None

    def process_all(self, batch_size=100, force_regenerate=False):
        """Genera embeddings para todos los animes en la DB"""
        print(f"🚀 Iniciando generación de embeddings usando {self.model}...")
        
        # Filtro: solo los que no tienen embedding o todos si force_regenerate
        query = {} if force_regenerate else {"embedding": {"$exists": False}}
        total_to_process = self.collection.count_documents(query)
        
        print(f"📊 Animes a procesar: {total_to_process}")
        
        if total_to_process == 0:
            print("✅ Todos los animes ya tienen embeddings.")
            self.export_numpy()
            return

        cursor = self.collection.find(query)
        batch = []
        
        # Barra de progreso
        pbar = tqdm(total=total_to_process)
        
        for anime in cursor:
            text_parts = []
            
            # Incluir títulos y sinónimos para asegurar coincidencia exacta
            titles = []
            main_title = anime.get('main_title')
            if main_title:
                titles.append(main_title)
                
            title_obj = anime.get('title') or {}
            for key in ['romaji', 'english', 'native']:
                val = title_obj.get(key)
                if val and val not in titles:
                    titles.append(val)
                    
            if titles:
                text_parts.append("Títulos: " + ", ".join(titles))
            
            # Incluir descripción limpia (sin HTML ni fuentes/ruido)
            desc_clean = limpiar_descripcion(anime.get('description', ''))
            if desc_clean:
                text_parts.append(desc_clean)
                
            if not text_parts:
                text = anime.get('main_title', '')
            else:
                text = ' '.join(text_parts)
            
            # NORMALIZAR TEXTO (Importante para coincidir con la búsqueda)
            text = normalizar_texto(text)
            
            if not text:
                pbar.update(1)
                continue
                
            batch.append({
                'id': anime['id'],
                'text': text
            })
            
            if len(batch) >= batch_size:
                self.process_batch(batch)
                pbar.update(len(batch))
                batch = []
                time.sleep(0.1) # Rate limiting
        
        # Procesar remanente
        if batch:
            self.process_batch(batch)
            pbar.update(len(batch))
            
        pbar.close()
        self.export_numpy()

    def process_batch(self, batch):
        """Procesa un lote de animes"""
        try:
            texts = [item['text'] for item in batch]
            embeddings = BERTEmbedder.get_embeddings_batch(texts)
            
            for i, embedding in enumerate(embeddings):
                anime_id = batch[i]['id']
                
                # Guardar en MongoDB
                self.collection.update_one(
                    {'id': anime_id},
                    {'$set': {'embedding': embedding}}
                )
                
        except Exception as e:
            print(f"❌ Error en batch: {e}")
            # Fallback: intentar uno por uno si falla el batch
            for item in batch:
                # Ya está normalizado en process_all
                embedding = self.generate_embedding(item['text'])
                if embedding:
                    self.collection.update_one(
                        {'id': item['id']},
                        {'$set': {'embedding': embedding}}
                    )
                else:
                    print(f"⚠️ Falló embedding para anime {item['id']}")
 
    def export_numpy(self):
        """Exporta todos los embeddings a un archivo .npy para FAISS"""
        print("\n💾 Exportando embeddings a archivo numpy...")
        
        # Obtener todos los animes con embeddings ordenados por algún criterio estable si es necesario
        # IMPORTANTE: search_engine asume que el índice del array corresponde al índice en la lista de animes loaded
        # Por lo tanto, necesitamos asegurarnos de que el orden sea consistente.
        # En la implementación de search_engine modificada, cargaremos TODO de Mongo.
        
        # Para ser consistentes, recuperamos todo y guardamos en orden de ID
        cursor = self.collection.find(
            {"embedding": {"$exists": True}},
            {"embedding": 1}
        ).sort('id', 1)
        
        embeddings_list = []
        count = 0
        
        for doc in cursor:
            embeddings_list.append(doc['embedding'])
            count += 1
            
        if not embeddings_list:
            print("⚠️ No hay embeddings para exportar.")
            return

        embeddings_array = np.array(embeddings_list, dtype='float32')
        np.save("embeddings.npy", embeddings_array)
        print(f"✅ Archivo 'embeddings.npy' guardado con {count} vectores.")

def main():
    generator = EmbeddingGenerator()
    # Forzar regeneración para aplicar normalización y usar el nuevo modelo BERT
    generator.process_all(force_regenerate=True)

if __name__ == "__main__":
    main()
