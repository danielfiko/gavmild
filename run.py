from app import app, db
if __name__ == "__main__":
    db.create_all()
    app.run(debug=True, ssl_context=("/etc/letsencrypt/live/gavmild.sekta.no/fullchain.pem",
                                     "/etc/letsencrypt/live/gavmild.sekta.no/privkey.pem"))