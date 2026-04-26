from flask import Flask, request, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
import cloudinary
import cloudinary.uploader
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'vetmed_secret_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///vetmed.db')

db = SQLAlchemy(app)

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

ADMIN_PASSWORD = "vetmed2024"

# ── MODÈLES
class Fichier(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    annee     = db.Column(db.String(10))
    semestre  = db.Column(db.String(5))
    ressource = db.Column(db.String(20))
    module    = db.Column(db.String(100))
    nom       = db.Column(db.String(200))
    url       = db.Column(db.String(500))

class Utilisateur(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    nom       = db.Column(db.String(100))
    prenom    = db.Column(db.String(100))
    email     = db.Column(db.String(200), unique=True)
    niveau    = db.Column(db.String(50))
    password  = db.Column(db.String(200))
    actif     = db.Column(db.Boolean, default=True)
    premium   = db.Column(db.Boolean, default=False)
    date_inscription = db.Column(db.String(50))

# ── ROUTES PRINCIPALES
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin.html')
def admin():
    return send_from_directory('.', 'admin.html')

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

# ── INSCRIPTION
@app.route('/api/inscription', methods=['POST'])
def inscription():
    data = request.json
    if Utilisateur.query.filter_by(email=data.get('email')).first():
        return jsonify({'success': False, 'error': 'Email déjà utilisé'}), 400
    
    from datetime import datetime
    u = Utilisateur(
        nom=data.get('nom'),
        prenom=data.get('prenom'),
        email=data.get('email'),
        niveau=data.get('niveau'),
        password=generate_password_hash(data.get('password')),
        date_inscription=datetime.now().strftime("%d/%m/%Y %H:%M")
    )
    db.session.add(u)
    db.session.commit()
    session['user_id'] = u.id
    session['user_nom'] = u.prenom
    return jsonify({'success': True, 'prenom': u.prenom})

# ── CONNEXION
@app.route('/api/connexion', methods=['POST'])
def connexion():
    data = request.json
    u = Utilisateur.query.filter_by(email=data.get('email')).first()
    if not u or not check_password_hash(u.password, data.get('password')):
        return jsonify({'success': False, 'error': 'Email ou mot de passe incorrect'}), 401
    if not u.actif:
        return jsonify({'success': False, 'error': 'Compte bloqué — contacte l\'administrateur'}), 403
    session['user_id'] = u.id
    session['user_nom'] = u.prenom
    session['user_premium'] = u.premium
    return jsonify({'success': True, 'prenom': u.prenom, 'premium': u.premium})

# ── DÉCONNEXION USER
@app.route('/api/deconnexion', methods=['POST'])
def deconnexion():
    session.pop('user_id', None)
    session.pop('user_nom', None)
    session.pop('user_premium', None)
    return jsonify({'success': True})

# ── CHECK SESSION USER
@app.route('/api/me', methods=['GET'])
def me():
    if session.get('user_id'):
        return jsonify({
            'connecte': True,
            'prenom': session.get('user_nom'),
            'premium': session.get('user_premium', False)
        })
    return jsonify({'connecte': False})

# ── UPLOAD FICHIER
@app.route('/api/admin/upload', methods=['POST'])
def upload_fichier():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    annee     = request.form.get('annee')
    semestre  = request.form.get('semestre')
    ressource = request.form.get('ressource')
    module    = request.form.get('module')
    nom       = request.form.get('nom')
    file      = request.files.get('fichier')
    if not file:
        return jsonify({'error': 'Aucun fichier'}), 400
    result = cloudinary.uploader.upload(
        file,
        resource_type   = "auto",
        folder          = f"vetmed/{annee}/{semestre}/{ressource}/{module}",
        use_filename    = True,
        unique_filename = True,
        access_mode     = "public"
    )
    f = Fichier(annee=annee, semestre=semestre, ressource=ressource, module=module, nom=nom, url=result['secure_url'])
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
        db.session.delete(f)
        db.session.commit()
    return jsonify({'success': True})

# ── RÉCUPÉRER FICHIERS
@app.route('/api/fichiers')
def get_fichiers():
    if not session.get('user_id'):
        return jsonify({'error': 'Non connecté'}), 401
    annee     = request.args.get('annee')
    semestre  = request.args.get('semestre')
    ressource = request.args.get('ressource')
    module    = request.args.get('module')
    fichiers  = Fichier.query.filter_by(annee=annee, semestre=semestre, ressource=ressource, module=module).all()
    return jsonify([{'id': f.id, 'nom': f.nom, 'url': f.url} for f in fichiers])

# ── TOUS LES FICHIERS (admin)
@app.route('/api/admin/fichiers')
def get_all_fichiers():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    annee     = request.args.get('annee', '')
    semestre  = request.args.get('semestre', '')
    ressource = request.args.get('ressource', '')
    query = Fichier.query
    if annee:     query = query.filter_by(annee=annee)
    if semestre:  query = query.filter_by(semestre=semestre)
    if ressource: query = query.filter_by(ressource=ressource)
    fichiers = query.all()
    return jsonify([{'id': f.id, 'annee': f.annee, 'semestre': f.semestre, 'ressource': f.ressource, 'module': f.module, 'nom': f.nom, 'url': f.url} for f in fichiers])

# ── GESTION UTILISATEURS (admin)
@app.route('/api/admin/utilisateurs')
def get_utilisateurs():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    users = Utilisateur.query.order_by(Utilisateur.id.desc()).all()
    return jsonify([{
        'id': u.id, 'nom': u.nom, 'prenom': u.prenom,
        'email': u.email, 'niveau': u.niveau,
        'actif': u.actif, 'premium': u.premium,
        'date_inscription': u.date_inscription
    } for u in users])

@app.route('/api/admin/utilisateur/<int:id>/toggle_actif', methods=['POST'])
def toggle_actif(id):
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    u = Utilisateur.query.get(id)
    if u:
        u.actif = not u.actif
        db.session.commit()
    return jsonify({'success': True, 'actif': u.actif})

@app.route('/api/admin/utilisateur/<int:id>/toggle_premium', methods=['POST'])
def toggle_premium(id):
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    u = Utilisateur.query.get(id)
    if u:
        u.premium = not u.premium
        db.session.commit()
    return jsonify({'success': True, 'premium': u.premium})

@app.route('/api/admin/utilisateur/<int:id>', methods=['DELETE'])
def delete_utilisateur(id):
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    u = Utilisateur.query.get(id)
    if u:
        db.session.delete(u)
        db.session.commit()
    return jsonify({'success': True})

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
