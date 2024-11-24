# -*- coding: utf8 -*-
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(50))
    qq = db.Column(db.String(50))
    wechat = db.Column(db.String(50))
    stock = db.Column(db.Integer, default=0)
    address = db.Column(db.String(100))
