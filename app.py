from flask import Flask, request, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'vetmed_secret_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vetmed.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

db = SQLAlchemy(app)

# ── MODÈLES
class Fichier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    annee = db.Column(db.String(10))
    semestre = db.Column(db.String(5))
    ressource = db.Column(db.String(20))
    module = db.Column(db.String(100))
    nom = db.Column(db.String(200))
    filename = db.Column(db.String(200))

ADMIN_PASSWORD = "vetmed2024"

# ── ROUTES PRINCIPALES
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

# ── ADMIN LOGIN
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

# ── UPLOAD FICHIER
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

    filename = f"{annee}_{semestre}_{ressource}_{module}_{file.filename}".replace(' ', '_')
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    f = Fichier(annee=annee, semestre=semestre, ressource=ressource, module=module, nom=nom, filename=filename)
    db.session.add(f)
    db.session.commit()

    return jsonify({'success': True})

# ── SUPPRIMER FICHIER
@app.route('/api/admin/delete/<int:id>', methods=['DELETE'])
def delete_fichier(id):
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401

    f = Fichier.query.get(id)
    if f:
        path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
        if os.path.exists(path):
            os.remove(path)
        db.session.delete(f)
        db.session.commit()
    return jsonify({'success': True})

# ── RÉCUPÉRER FICHIERS D'UN MODULE
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
        'id': f.id,
        'nom': f.nom,
        'url': f'/uploads/{f.filename}'
    } for f in fichiers])

# ── TOUS LES FICHIERS (admin)
@app.route('/api/admin/fichiers')
def get_all_fichiers():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    fichiers = Fichier.query.all()
    return jsonify([{
        'id': f.id, 'annee': f.annee, 'semestre': f.semestre,
        'ressource': f.ressource, 'module': f.module,
        'nom': f.nom, 'filename': f.filename
    } for f in fichiers])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)