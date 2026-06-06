from app import create_app, db

app = create_app()

# Create all tables if they don't exist yet (fallback for dev without migrations)
with app.app_context():
    db.create_all()
