from flask import Flask, request, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
import cloudinary
import cloudinary.uploader
import os

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'vetmed_secret_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vetmed.db'

db = SQLAlchemy(app)

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

ADMIN_PASSWORD = "vetmed2024"

class Fichier(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    annee    = db.Column(db.String(10))
    semestre = db.Column(db.String(5))
    ressource= db.Column(db.String(20))
    module   = db.Column(db.String(100))
    nom      = db.Column(db.String(200))
    url      = db.Column(db.String(500))

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin.html')
def admin():
    return send_from_directory('.', 'admin.html')

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if data.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Mot de passe incorrect'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin', None)
    return jsonify({'success': True})

@app.route('/api/admin/check', methods=['GET'])
def admin_check():
    return jsonify({'admin': session.get('admin', False)})

@app.route('/api/admin/upload', methods=['POST'])
def upload_fichier():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401

    annee    = request.form.get('annee')
    semestre = request.form.get('semestre')
    ressource= request.form.get('ressource')
    module   = request.form.get('module')
    nom      = request.form.get('nom')
    file     = request.files.get('fichier')

    if not file:
        return jsonify({'error': 'Aucun fichier'}), 400

    result = cloudinary.uploader.upload(
        file,
        resource_type = "auto",
        folder        = f"vetmed/{annee}/{semestre}/{ressource}/{module}",
        use_filename  = True,
        unique_filename = True,
        access_mode   = "public"
    )

    f = Fichier(
        annee=annee, semestre=semestre,
        ressource=ressource, module=module,
        nom=nom, url=result['secure_url']
    )
    db.session.add(f)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/api/admin/delete/<int:id>', methods=['DELETE'])
def delete_fichier(id):
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401

    f = Fichier.query.get(id)
    if f:
        db.session.delete(f)
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/fichiers')
def get_fichiers():
    annee    = request.args.get('annee')
    semestre = request.args.get('semestre')
    ressource= request.args.get('ressource')
    module   = request.args.get('module')

    fichiers = Fichier.query.filter_by(
        annee=annee, semestre=semestre,
        ressource=ressource, module=module
    ).all()

    return jsonify([{
        'id' : f.id,
        'nom': f.nom,
        'url': f.url
    } for f in fichiers])

@app.route('/api/admin/fichiers')
def get_all_fichiers():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    fichiers = Fichier.query.all()
    return jsonify([{
        'id': f.id, 'annee': f.annee, 'semestre': f.semestre,
        'ressource': f.ressource, 'module': f.module,
        'nom': f.nom, 'url': f.url
    } for f in fichiers])

with app.app_context():
    db.create_all()
    
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
