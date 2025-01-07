from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

class DBManager:
    def __init__(self):
        """Inicializa la conexión con la base de datos MongoDB usando variables de entorno."""
        uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DB_NAME")
        if not uri or not db_name:
            raise ValueError("MONGODB_URI o MONGODB_DB_NAME no están configurados en el archivo .env.")
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    def save_data(self, collection_name, data):
        """Guarda un documento en una colección específica."""
        collection = self.db[collection_name]
        collection.insert_one(data)

    def fetch_data(self, collection_name, query=None):
        """Obtiene documentos de una colección específica."""
        collection = self.db[collection_name]
        if query is None:
            query = {}
        return list(collection.find(query))

    def delete_data(self, collection_name, query):
        """Elimina documentos de una colección específica."""
        collection = self.db[collection_name]
        collection.delete_many(query)
