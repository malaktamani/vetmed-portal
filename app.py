from flask import Flask, request, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
import cloudinary
import cloudinary.uploader
import os
import requests
import pdfplumber
import pytesseract
from PIL import Image
import io
from werkzeug.security import generate_password_hash, check_password_hash

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'vetmed_secret_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///vetmed.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

ADMIN_PASSWORD = "vetmed2024"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

class Fichier(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    annee     = db.Column(db.String(10))
    semestre  = db.Column(db.String(5))
    ressource = db.Column(db.String(20))
    module    = db.Column(db.String(100))
    nom       = db.Column(db.String(200))
    url       = db.Column(db.String(500))
    texte     = db.Column(db.Text, default='')

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

def extraire_texte(file_bytes):
    texte = ''
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t and len(t.strip()) > 20:
                    texte += t + '\n'
                else:
                    img = page.to_image(resolution=200).original
                    t_ocr = pytesseract.image_to_string(img, lang='fra+eng')
                    texte += t_ocr + '\n'
    except Exception as e:
        print(f"Erreur extraction: {e}")
    return texte.strip()

def extraire_texte_depuis_url(url):
    try:
        r = requests.get(url, timeout=30)
        return extraire_texte(r.content)
    except Exception as e:
        print(f"Erreur téléchargement: {e}")
        return ''

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin.html')
def admin():
    return send_from_directory('.', 'admin.html')

@app.route('/chat.html')
def chat_page():
    return send_from_directory('.', 'chat.html')

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
    session['user_premium'] = u.premium
    return jsonify({'success': True, 'prenom': u.prenom})

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

@app.route('/api/deconnexion', methods=['POST'])
def deconnexion():
    session.pop('user_id', None)
    session.pop('user_nom', None)
    session.pop('user_premium', None)
    return jsonify({'success': True})

@app.route('/api/me', methods=['GET'])
def me():
    if session.get('user_id'):
        return jsonify({'connecte': True, 'prenom': session.get('user_nom'), 'premium': session.get('user_premium', False)})
    return jsonify({'connecte': False})

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
    file_bytes = file.read()
    texte = extraire_texte(file_bytes)
    file.seek(0)
    result = cloudinary.uploader.upload(
        file,
        resource_type   = "auto",
        folder          = f"vetmed/{annee}/{semestre}/{ressource}/{module}",
        use_filename    = True,
        unique_filename = True,
        access_mode     = "public"
    )
    f = Fichier(annee=annee, semestre=semestre, ressource=ressource, module=module, nom=nom, url=result['secure_url'], texte=texte)
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
    if not session.get('user_id') and not session.get('admin'):
        return jsonify({'error': 'Non connecté'}), 401
    annee     = request.args.get('annee')
    semestre  = request.args.get('semestre')
    ressource = request.args.get('ressource')
    module    = request.args.get('module')
    fichiers  = Fichier.query.filter_by(annee=annee, semestre=semestre, ressource=ressource, module=module).all()
    return jsonify([{'id': f.id, 'nom': f.nom, 'url': f.url} for f in fichiers])

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

@app.route('/api/admin/extraire_textes', methods=['POST'])
def extraire_textes_anciens():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    
    fichiers = Fichier.query.filter(
        (Fichier.texte == None) | (Fichier.texte == '')
    ).limit(3).all()
    
    if not fichiers:
        return jsonify({'success': True, 'traites': 0, 'total': 0, 'termine': True})
    
    traites = 0
    for f in fichiers:
        try:
            texte = extraire_texte_depuis_url(f.url)
            if texte:
                f.texte = texte
                db.session.commit()
                traites += 1
        except Exception as e:
            print(f"Erreur fichier {f.id}: {e}")
    
    restants = Fichier.query.filter(
        (Fichier.texte == None) | (Fichier.texte == '')
    ).count()
    
    return jsonify({
        'success': True,
        'traites': traites,
        'total': restants,
        'termine': restants == 0
    })

@app.route('/api/admin/fichiers_sans_texte')
def fichiers_sans_texte():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    fichiers = Fichier.query.filter(
        (Fichier.texte == None) | (Fichier.texte == '')
    ).all()
    return jsonify({'ids': [f.id for f in fichiers]})

@app.route('/api/admin/fichier/<int:id>')
def get_fichier(id):
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    f = Fichier.query.get(id)
    if not f:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': f.id,
        'nom': f.nom,
        'url': f.url,
        'annee': f.annee,
        'semestre': f.semestre,
        'ressource': f.ressource,
        'module': f.module
    })

@app.route('/api/admin/maj_texte/<int:id>', methods=['POST'])
def maj_texte(id):
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    f = Fichier.query.get(id)
    if not f:
        return jsonify({'error': 'Fichier introuvable'}), 404
    data = request.json
    f.texte = data.get('texte', '').replace('\x00', '')
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/chat', methods=['POST'])
def chat():
    if not session.get('user_id') and not session.get('admin'):
        return jsonify({'error': 'Non connecté'}), 401
    data     = request.json
    question = data.get('message', '')
    if not question:
        return jsonify({'error': 'Message vide'}), 400

    fichiers = Fichier.query.all()

    contexte_fichiers = []
    for f in fichiers:
        info = f"[{f.annee} | {f.semestre} | {f.ressource} | {f.module}] — {f.nom}"
        contexte_fichiers.append(info)

    question_lower = question.lower()
    textes_pertinents = []
    for f in fichiers:
        if f.texte and any(mot in question_lower for mot in [f.module.lower(), f.nom.lower()]):
            textes_pertinents.append(f"=== {f.nom} ({f.module} - {f.annee} {f.semestre}) ===\n{f.texte[:3000]}")

    system_prompt = f"""Tu es VetBot, l'assistant IA du portail VetStudy — une plateforme de ressources pour les étudiants en médecine vétérinaire.

Tu as accès à la liste complète des fichiers disponibles sur le site :
{chr(10).join(contexte_fichiers[:100])}

{"Tu as aussi accès au contenu de certains cours pertinents :" + chr(10) + chr(10).join(textes_pertinents[:5]) if textes_pertinents else ""}

Tes capacités :
- Dire quels fichiers sont disponibles et où les trouver (année, semestre, type, module)
- Répondre aux questions sur le contenu des cours
- Expliquer des concepts vétérinaires
- Traduire du contenu français ↔ anglais
- Résumer des cours

Réponds toujours en français sauf si on te demande autre chose.
Sois précis, pédagogique et utile pour les étudiants vétérinaires."""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 1500,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ]
            },
            timeout=30
        )
        result = response.json()
        if 'choices' in result:
            answer = result['choices'][0]['message']['content']
        elif 'error' in result:
            answer = "Erreur API : " + str(result['error'])
        else:
            answer = "Réponse inattendue : " + str(result)
        return jsonify({'success': True, 'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text('ALTER TABLE fichier ADD COLUMN texte TEXT DEFAULT \'\''))
            conn.commit()
    except:
        pass

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
