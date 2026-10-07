import os
import json
import logging
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from bson import ObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db")

_db_instance = None
_is_mock = False

def get_db(config=None):
    global _db_instance, _is_mock
    if _db_instance is not None:
        return _db_instance

    from backend.config import Config
    mongo_uri = config.MONGO_URI if config else Config.MONGO_URI
    db_name = config.DB_NAME if config else Config.DB_NAME

    try:
        # Try real MongoDB with a 2-second timeout
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        _db_instance = client[db_name]
        logger.info(f"Connected successfully to real MongoDB: {db_name}")
    except (ServerSelectionTimeoutError, ConnectionFailure, Exception) as e:
        logger.warning(f"Could not connect to MongoDB ({e}). Initializing robust MongoMock fallback engine.")
        import mongomock
        mock_client = mongomock.MongoClient()
        _db_instance = mock_client[db_name]
        _is_mock = True
        _seed_mock_data(_db_instance)

    _init_indexes(_db_instance)
    _seed_default_tariffs(_db_instance)
    return _db_instance

def _init_indexes(db):
    try:
        db.users.create_index("email", unique=True)
        db.bills.create_index([("user_id", 1), ("month", -1)], unique=True)
        db.appliances.create_index([("user_id", 1)])
        db.alerts.create_index([("user_id", 1), ("created_at", -1)])
        db.tariffs.create_index([("user_id", 1)])
    except Exception as e:
        logger.warning(f"Index creation note: {e}")

def _seed_default_tariffs(db):
    try:
        count = db.tariffs.count_documents({"user_id": None})
        if count == 0:
            default_tariff = {
                "user_id": None,
                "name": "MSEDCL Residential (Default)",
                "distributor": "MSEDCL",
                "category": "LT-I Residential",
                "slabs": [
                    {"from": 0, "to": 100, "rate": 5.0},
                    {"from": 101, "to": 300, "rate": 10.0},
                    {"from": 301, "to": None, "rate": 14.0}
                ],
                "fixed_charge": 120.0,
                "duty_percent": 16.0,
                "other_charges": 0.0,
                "is_default": True
            }
            db.tariffs.insert_one(default_tariff)
            logger.info("Default MSEDCL tariff profile seeded successfully.")
    except Exception as e:
        logger.error(f"Error seeding default tariff: {e}")

def _seed_mock_data(db):
    try:
        from backend.seed import seed_demo_data
        seed_demo_data()
    except Exception as e:
        logger.info(f"Auto-seed demo data note: {e}")
