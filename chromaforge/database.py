"""MongoDB access; every user-owned query is scoped by user_id."""
from __future__ import annotations

from datetime import datetime, timezone
import re

import bcrypt
from bson import ObjectId
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError


def now():
    return datetime.now(timezone.utc)


class Store:
    COLLECTIONS = ("saved_colors", "palettes", "gradients", "color_history")

    def __init__(self, uri: str = "mongodb://localhost:27017/", database: str = "chromaforge_db"):
        self.client = MongoClient(uri, serverSelectionTimeoutMS=2500, connectTimeoutMS=2500)
        self.db = self.client[database]

    def connect(self):
        self.client.admin.command("ping")
        self.db.users.create_index("username_key", unique=True)
        self.db.users.create_index("email_key", unique=True)
        for name in self.COLLECTIONS:
            self.db[name].create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
        self.db.color_history.create_index([("user_id", ASCENDING), ("selected_at", ASCENDING)])

    def close(self):
        self.client.close()

    def register(self, full_name: str, username: str, email: str, password: str):
        full_name, username, email = full_name.strip(), username.strip(), email.strip().lower()
        if len(full_name) < 2 or not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", username):
            raise ValueError("Enter a name and a 3–30 character username using letters, numbers, ., _ or -.")
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Enter a valid email address.")
        if not 8 <= len(password.encode()) <= 72:
            raise ValueError("Use a password between 8 and 72 UTF-8 bytes.")
        doc = {"full_name": full_name, "username": username, "username_key": username.casefold(), "email": email,
               "email_key": email.casefold(), "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
               "preferences": {"theme": "dark"}, "created_at": now(), "updated_at": now()}
        try:
            doc["_id"] = self.db.users.insert_one(doc).inserted_id
        except DuplicateKeyError as exc:
            raise ValueError("That username or email is already registered.") from exc
        return doc

    def login(self, identity: str, password: str):
        key = identity.strip().casefold()
        user = self.db.users.find_one({"$or": [{"username_key": key}, {"email_key": key}]})
        if not user or not bcrypt.checkpw(password.encode(), user["password_hash"]):
            raise ValueError("Username/email or password is incorrect.")
        return user

    def update_profile(self, user_id: ObjectId, name: str):
        name = name.strip()
        if len(name) < 2:
            raise ValueError("Display name must have at least two characters.")
        self.db.users.update_one({"_id": user_id}, {"$set": {"full_name": name, "updated_at": now()}})

    def change_password(self, user_id: ObjectId, old: str, new: str):
        user = self.db.users.find_one({"_id": user_id})
        if not user or not bcrypt.checkpw(old.encode(), user["password_hash"]):
            raise ValueError("Current password is incorrect.")
        if not 8 <= len(new.encode()) <= 72:
            raise ValueError("New password must be between 8 and 72 UTF-8 bytes.")
        self.db.users.update_one({"_id": user_id}, {"$set": {"password_hash": bcrypt.hashpw(new.encode(), bcrypt.gensalt()), "updated_at": now()}})

    def set_theme(self, user_id: ObjectId, theme: str):
        self.db.users.update_one({"_id": user_id}, {"$set": {"preferences.theme": theme, "updated_at": now()}})

    def delete_account(self, user_id: ObjectId):
        for name in self.COLLECTIONS:
            self.db[name].delete_many({"user_id": user_id})
        self.db.users.delete_one({"_id": user_id})

    def add(self, collection: str, user_id: ObjectId, fields: dict):
        self._check(collection)
        doc = {**fields, "user_id": user_id, "created_at": now(), "updated_at": now()}
        return self.db[collection].insert_one(doc).inserted_id

    def list(self, collection: str, user_id: ObjectId, limit: int = 250):
        self._check(collection)
        key = "selected_at" if collection == "color_history" else "created_at"
        return list(self.db[collection].find({"user_id": user_id}).sort(key, -1).limit(limit))

    def update(self, collection: str, user_id: ObjectId, item_id: ObjectId, fields: dict):
        self._check(collection)
        safe = {k: v for k, v in fields.items() if k not in ("_id", "user_id", "created_at")}
        safe["updated_at"] = now()
        return self.db[collection].update_one({"_id": item_id, "user_id": user_id}, {"$set": safe}).matched_count

    def delete(self, collection: str, user_id: ObjectId, item_id: ObjectId):
        self._check(collection)
        return self.db[collection].delete_one({"_id": item_id, "user_id": user_id}).deleted_count

    def clear_history(self, user_id: ObjectId):
        return self.db.color_history.delete_many({"user_id": user_id}).deleted_count

    def history(self, user_id: ObjectId, color: str, source: str):
        self.db.color_history.insert_one({"user_id": user_id, "hex": color, "source": source, "selected_at": now()})

    def stats(self, user_id: ObjectId):
        since = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        return {
            "colors": self.db.saved_colors.count_documents({"user_id": user_id}),
            "palettes": self.db.palettes.count_documents({"user_id": user_id}),
            "favorites": self.db.saved_colors.count_documents({"user_id": user_id, "is_favorite": True}),
            "picked_today": self.db.color_history.count_documents({"user_id": user_id, "selected_at": {"$gte": since}}),
        }

    def _check(self, collection: str):
        if collection not in self.COLLECTIONS:
            raise ValueError("Unknown collection")
