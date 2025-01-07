from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["asistente"]

# Inserta un documento de prueba
db["job_offers"].insert_one({"title": "Test Job", "company": "Test Company"})

# Recupera los datos
data = list(db["job_offers"].find())
print(data)
