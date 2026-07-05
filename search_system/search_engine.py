import json
import os
import numpy as np
import faiss
from config import Config
from utils import normalizar_texto, limpiar_html
from database import Database, db

class SearchEngine:
    ids = []  # Lista de IDs que corresponde índice por índice con FAISS
    index = None
    dim = 0

    @classmethod
    def load_data(cls):
        print("Inicializando motor de busqueda (conectado a MongoDB)...")
        try:
            Database.init_db()
            
            # 1. Cargar SOLO los IDs de los animes que tienen embeddings
            # DEBEN estar ordenados por 'id' igual que como se generó embeddings.npy
            cursor = db.db.animes.find(
                {"embedding": {"$exists": True}},
                {"id": 1} 
            ).sort("id", 1)
            
            cls.ids = [doc['id'] for doc in cursor]
            
            if not cls.ids:
                print("! No se encontraron animes con embeddings en MongoDB.")
                return

            # 2. Cargar embeddings (FAISS)
            if not os.path.exists("embeddings.npy"):
                print("ERROR: 'embeddings.npy' no existe. Ejecuta generate_embeddings.py primero.")
                return

            embeddings = np.load("embeddings.npy")
            
            # NORMALIZAR los embeddings para usar Inner Product como similitud coseno
            # Los embeddings ya vienen normalizados, pero lo aseguramos
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms
            
            cls.dim = embeddings.shape[1]
            
            # Verificación de consistencia
            if len(cls.ids) != embeddings.shape[0]:
                print(f"! ADVERTENCIA: Discrepancia entre IDs en DB ({len(cls.ids)}) y embeddings ({embeddings.shape[0]}).")
                # Ajustar al mínimo
                min_len = min(len(cls.ids), embeddings.shape[0])
                cls.ids = cls.ids[:min_len]
                embeddings = embeddings[:min_len]
            
            # Crear índice FAISS con INNER PRODUCT (similitud coseno con vectores normalizados)
            print("Creando indice FAISS con similitud coseno...")
            cls.index = faiss.IndexFlatIP(cls.dim)  # IP = Inner Product
            cls.index.add(embeddings.astype('float32'))
            print(f"✓ Motor de busqueda listo. Indice contiene {len(cls.ids)} vectores usando cosine similarity.")
            
        except Exception as e:
            print(f"X Error cargando motor de busqueda: {e}")

    @classmethod
    def search(cls, vector, query_text=None, top_k=10, threshold=None):
        if not cls.index or not cls.ids:
            return []
            
        top_k = max(1, min(int(top_k), len(cls.ids)))
        
        # Normalizar el vector de búsqueda también
        vector = np.array([vector], dtype="float32")
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        # D contiene las similitudes (más alto = más similar con IndexFlatIP)
        D, I = cls.index.search(vector, k=top_k)
        
        # Obtener los IDs correspondientes a los vecinos más cercanos
        found_indices = I[0]
        similarities = D[0]  # Ya son similitudes (no distancias), más alto = mejor
        
        target_ids = []
        score_map = {}
        
        for similarity, idx in zip(similarities, found_indices):
            if idx < len(cls.ids):
                anime_id = cls.ids[idx]
                target_ids.append(anime_id)
                # Convertir a un score entre 0-100 (similarity está entre -1 y 1, típicamente 0-1 para vectores positivos)
                score_map[anime_id] = float(similarity * 100)
        
        # CONSULTA A MONGODB: Traer detalles de estos IDs
        cursor = db.db.animes.find({"id": {"$in": target_ids}})
        
        results = []
        # Mongo no garantiza orden en $in, así que reordenamos manual
        fetched_animes = {anime['id']: anime for anime in cursor}
        
        for anime_id in target_ids:
            anime = fetched_animes.get(anime_id)
            if anime:
                # Procesar para salida
                if '_id' in anime:
                    anime['_id'] = str(anime['_id'])
                anime['similarity_score'] = score_map.get(anime_id, 0.0)
                anime['description_clean'] = limpiar_html(anime.get('description', ''))
                
                # Opcional: eliminar el vector embedding del resultado para no enviarlo al frontend
                if 'embedding' in anime:
                    del anime['embedding']
                    
                results.append(anime)
        
        # Refinar con BERT si hay coincidencia superior al threshold
        if query_text and results:
            if threshold is None:
                threshold = getattr(Config, 'BERT_RERANK_THRESHOLD', 60.0)
            
            candidates = [a for a in results if a['similarity_score'] >= threshold]
            if candidates:
                from search_system.bert_helper import BERTEmbedder
                from utils import limpiar_descripcion
                
                texts_to_embed = []
                for anime in candidates:
                    # Usar la descripción limpia (sin HTML ni fuentes/ruido)
                    text_desc = limpiar_descripcion(anime.get('description', ''))
                    
                    text_to_compare = normalizar_texto(text_desc)
                    if not text_to_compare:
                        text_to_compare = normalizar_texto(anime.get('main_title', ''))
                    
                    texts_to_embed.append(text_to_compare)
                
                # Obtener embeddings en lote
                desc_embeddings = BERTEmbedder.get_embeddings_batch(texts_to_embed)
                
                # Calcular similitud coseno directa con el query
                for idx, anime in enumerate(candidates):
                    emb = np.array(desc_embeddings[idx], dtype="float32")
                    emb_norm = np.linalg.norm(emb)
                    if emb_norm > 0:
                        emb = emb / emb_norm
                    
                    # Calcular similitud
                    sim = float(np.dot(vector[0], emb))
                    new_score = sim * 100
                    anime['similarity_score'] = new_score
                    anime['refined_by_bert'] = True
                
                # Re-ordenar la lista completa de resultados basada en el nuevo score
                results.sort(key=lambda x: x['similarity_score'], reverse=True)
                
        return results

    @classmethod
    def get_by_id(cls, anime_id):
        # Consulta directa a MongoDB
        try:
            query = {
                "$or": [
                    {"id": anime_id},
                    {"idMal": anime_id}
                ]
            }
            anime = db.db.animes.find_one(query)
            
            if anime:
                if '_id' in anime:
                    anime['_id'] = str(anime['_id'])
                if 'embedding' in anime:
                    del anime['embedding']
                anime['description_clean'] = limpiar_html(anime.get('description', ''))
                return anime
        except Exception as e:
            print(f"Error en get_by_id: {e}")
            pass
            
        return None
