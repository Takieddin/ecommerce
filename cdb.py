from app import db, app  # Import db and Flask app

# Use the application context to create the database
with app.app_context():
    db.create_all()
    print("Database created successfully!")

print("Database created successfully!")
