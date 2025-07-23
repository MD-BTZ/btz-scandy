from datetime import datetime
from app.models.mongodb_database import db
from app.models.user import User
from app.models.job import Job

class Experience(db.Document):
    """Erfahrungsbericht-Modell für Jobs"""
    
    # Referenzen
    job = db.ReferenceField(Job, required=True)
    author = db.ReferenceField(User, required=True)
    
    # Bewertung
    rating = db.IntField(required=True, min_value=1, max_value=5)
    overall_experience = db.StringField(choices=['Sehr positiv', 'Positiv', 'Neutral', 'Negativ', 'Sehr negativ'])
    
    # Bewertungsdetails
    work_environment = db.IntField(min_value=1, max_value=5)
    salary_benefits = db.IntField(min_value=1, max_value=5)
    career_growth = db.IntField(min_value=1, max_value=5)
    work_life_balance = db.IntField(min_value=1, max_value=5)
    
    # Text-Bewertung
    review_title = db.StringField(max_length=200)
    review_text = db.StringField(required=True, max_length=2000)
    pros = db.StringField(max_length=1000)
    cons = db.StringField(max_length=1000)
    recommendations = db.StringField(max_length=1000)
    
    # Metadaten
    created_at = db.DateTimeField(default=datetime.utcnow)
    updated_at = db.DateTimeField(default=datetime.utcnow)
    is_verified = db.BooleanField(default=False)
    is_anonymous = db.BooleanField(default=False)
    
    # Statistiken
    helpful_votes = db.IntField(default=0)
    not_helpful_votes = db.IntField(default=0)
    
    meta = {
        'collection': 'experiences',
        'indexes': [
            'job',
            'author',
            'rating',
            'overall_experience',
            'created_at'
        ]
    }
    
    def __str__(self):
        return f"Erfahrungsbericht für {self.job.title} von {self.author.username}"
    
    def to_dict(self):
        """Konvertiert Experience zu Dictionary"""
        return {
            'id': str(self.id),
            'job_id': str(self.job.id),
            'job_title': self.job.title,
            'author_id': str(self.author.id),
            'author_name': self.author.username if not self.is_anonymous else 'Anonym',
            'rating': self.rating,
            'overall_experience': self.overall_experience,
            'work_environment': self.work_environment,
            'salary_benefits': self.salary_benefits,
            'career_growth': self.career_growth,
            'work_life_balance': self.work_life_balance,
            'review_title': self.review_title,
            'review_text': self.review_text,
            'pros': self.pros,
            'cons': self.cons,
            'recommendations': self.recommendations,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'helpful_votes': self.helpful_votes,
            'not_helpful_votes': self.not_helpful_votes,
            'is_verified': self.is_verified,
            'is_anonymous': self.is_anonymous
        }
    
    def get_average_rating(self):
        """Berechnet die durchschnittliche Bewertung"""
        ratings = [
            self.work_environment,
            self.salary_benefits,
            self.career_growth,
            self.work_life_balance
        ]
        return sum(ratings) / len(ratings) if ratings else 0 