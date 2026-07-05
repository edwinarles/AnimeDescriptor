import os
import sys

# Desactivar CUDA/GPU
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Configurar UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(r"c:\Users\Edwin\Desktop\Nueva carpeta\OtakuDescriptor")

from database import Database, db

def run():
    Database.init_db()
    # Buscar Tonikawa
    tonikawa = db.db.animes.find_one({"main_title": "TONIKAWA: Over The Moon For You"})
    if not tonikawa:
        tonikawa = db.db.animes.find_one({"title.romaji": "Tonikaku Kawaii"})
    
    if tonikawa:
        print("=== Tonikaku Kawaii Description ===")
        print(tonikawa.get('description'))
    else:
        print("Tonikawa not found in DB!")

if __name__ == "__main__":
    run()
