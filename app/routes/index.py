from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models.mongodb_models import MongoDBTool, MongoDBWorker, MongoDBConsumable
from app.models.mongodb_database import MongoDB

bp = Blueprint("index", __name__)
mongodb = MongoDB()

notices = list(mongodb.find('homepage_notices', {'is_active': True}).sort([('priority', -1), ('created_at', -1)]))

