from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

def init_app(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()

    #db.session.add(User(username="example"))
    #db.session.commit()

    #users = db.session.execute(db.select(User)).scalars()