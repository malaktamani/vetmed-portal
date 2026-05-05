from flask import Flask, request, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
import os
import requests
import pdfplumber
import pytesseract
from PIL import Image
import io
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import google.generativeai as genai
import uuid

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'vetmed_secret_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///vetmed.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configuration Tebi.io
TEBI_ACCESS_KEY = os.environ.get("TEBI_ACCESS_KEY")
TEBI_SECRET_KEY = os.environ.get("TEBI_SECRET_KEY")
TEBI_BUCKET     = os.environ.get("TEBI_BUCKET", "vetmed-files")
TEBI_ENDPOINT   = os.environ.get("TEBI_ENDPOINT", "https://s3.tebi.io")

ADMIN_PASSWORD     = "vetmed2024"
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY")
GOOGLE_API_KEY     = os.environ.get("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ── MODELS ─────────────────
class Fichier(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    annee         = db.Column(db.String(10))
    semestre      = db.Column(db.String(5))
    ressource     = db.Column(db.String(20))
    module        = db.Column(db.String(100))
    nom           = db.Column(db.String(200))
    url           = db.Column(db.String(500))
    texte         = db.Column(db.Text, default='')
    date_creation = db.Column(db.String(50), default='')

class Utilisateur(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    nom              = db.Column(db.String(100))
    prenom           = db.Column(db.String(100))
    email            = db.Column(db.String(200), unique=True)
    niveau           = db.Column(db.String(50))
    password         = db.Column(db.String(200))
    actif            = db.Column(db.Boolean, default=True)
    premium          = db.Column(db.Boolean, default=False)
    date_inscription = db.Column(db.String(50))

class Favori(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    fichier_id     = db.Column(db.Integer, db.ForeignKey('fichier.id'), nullable=False)
    date_creation  = db.Column(db.String(50))

class Consultation(db.Model):
    id                = db.Column(db.Integer, primary_key=True)
    utilisateur_id    = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    fichier_id        = db.Column(db.Integer, db.ForeignKey('fichier.id'), nullable=False)
    date_consultation = db.Column(db.String(50))

# ── HELPERS ─────────────────
def extraire_texte(file_bytes):
    texte = ''
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t and len(t.strip()) > 20:
                    texte += t + '\n'
                else:
                    try:
                        img = page.to_image(resolution=200).original
                        t_ocr = pytesseract.image_to_string(img, lang='fra+eng')
                        texte += t_ocr + '\n'
                    except:
                        pass
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

# ⚠️ NOUVELLE FONCTION UPLOAD (sans boto3, avec requests)
def upload_to_tebi(file_bytes, object_path):
    try:
        url = f"{TEBI_ENDPOINT}/{TEBI_BUCKET}/{object_path}"
        response = requests.put(
            url,
            data=file_bytes,
            headers={
                'Content-Type': 'application/pdf',
                'Content-Length': str(len(file_bytes))
            },
            timeout=60
        )
        print(f"Upload Tebi response: {response.status_code}")
        if response.status_code == 200:
            return url
        else:
            print(f"Erreur HTTP {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"Erreur upload Tebi: {e}")
        return None

# ── SERVE HTML ─────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin.html')
def admin():
    return send_from_directory('.', 'admin.html')

@app.route('/chat.html')
def chat_page():
    return send_from_directory('.', 'chat.html')

# ── AUTH ─────────────────
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
    u = Utilisateur(
        nom=data.get('nom'), prenom=data.get('prenom'),
        email=data.get('email'), niveau=data.get('niveau'),
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
        return jsonify({'success': False, 'error': "Compte bloqué — contacte l'administrateur"}), 403
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

# ── UPLOAD / DELETE ─────────────────
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
    
    file_bytes  = file.read()
    texte       = extraire_texte(file_bytes)
    object_path = f"{annee}/{semestre}/{ressource}/{module}/{uuid.uuid4()}.pdf"
    public_url  = upload_to_tebi(file_bytes, object_path)
    
    if not public_url:
        return jsonify({'error': "Échec de l'upload vers Tebi"}), 500
    
    f = Fichier(
        annee=annee, semestre=semestre, ressource=ressource, module=module,
        nom=nom, url=public_url, texte=texte,
        date_creation=datetime.now().strftime("%d/%m/%Y %H:%M")
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

# ── GET FICHIERS ─────────────────
@app.route('/api/fichiers')
def get_fichiers():
    if not session.get('user_id') and not session.get('admin'):
        return jsonify({'error': 'Non connecté'}), 401
    annee     = request.args.get('annee')
    semestre  = request.args.get('semestre')
    ressource = request.args.get('ressource')
    module    = request.args.get('module')
    fichiers  = Fichier.query.filter_by(annee=annee, semestre=semestre, ressource=ressource, module=module).all()
    return jsonify([{'id': f.id, 'nom': f.nom, 'url': f.url, 'date_creation': f.date_creation or ''} for f in fichiers])

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
    return jsonify([{
        'id': f.id, 'annee': f.annee, 'semestre': f.semestre,
        'ressource': f.ressource, 'module': f.module,
        'nom': f.nom, 'url': f.url, 'date_creation': f.date_creation or ''
    } for f in fichiers])

# ── RECHERCHE ─────────────────
@app.route('/api/recherche')
def recherche():
    q = request.args.get('q', '').lower()
    if not q:
        return jsonify([])
    fichiers  = Fichier.query.all()
    resultats = []
    for f in fichiers:
        if q in f.nom.lower() or q in f.module.lower() or (f.texte and q in f.texte.lower()):
            resultats.append({
                'id': f.id, 'nom': f.nom, 'annee': f.annee,
                'semestre': f.semestre, 'ressource': f.ressource,
                'module': f.module, 'url': f.url
            })
    return jsonify(resultats[:20])

# ── EXTRACTION (admin) ─────────────────
@app.route('/api/admin/extraire_textes', methods=['POST'])
def extraire_textes_anciens():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    fichiers = Fichier.query.filter((Fichier.texte == None) | (Fichier.texte == '')).limit(3).all()
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
    restants = Fichier.query.filter((Fichier.texte == None) | (Fichier.texte == '')).count()
    return jsonify({'success': True, 'traites': traites, 'total': restants, 'termine': restants == 0})

@app.route('/api/admin/fichiers_sans_texte')
def fichiers_sans_texte():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    fichiers = Fichier.query.filter((Fichier.texte == None) | (Fichier.texte == '')).all()
    return jsonify({'ids': [f.id for f in fichiers]})

@app.route('/api/admin/fichier/<int:id>')
def get_fichier(id):
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    f = Fichier.query.get(id)
    if not f:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': f.id, 'nom': f.nom, 'url': f.url, 'annee': f.annee, 'semestre': f.semestre, 'ressource': f.ressource, 'module': f.module})

@app.route('/api/admin/maj_texte/<int:id>', methods=['POST'])
def maj_texte(id):
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    f = Fichier.query.get(id)
    if not f:
        return jsonify({'error': 'Fichier introuvable'}), 404
    data    = request.json
    f.texte = data.get('texte', '').replace('\x00', '')
    db.session.commit()
    return jsonify({'success': True})

# ── MIGRATION SUPABASE → TEBI ─────────────────
@app.route('/api/admin/migrer_tebi', methods=['POST'])
def migrer_tebi():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    try:
        fichiers = Fichier.query.filter(Fichier.url.like('%supabase%')).limit(10).all()
        if not fichiers:
            return jsonify({'success': True, 'traites': 0, 'restants': 0, 'termine': True})
        traites = 0
        echecs  = 0
        for f in fichiers:
            try:
                r = requests.get(f.url, timeout=30)
                if r.status_code != 200:
                    echecs += 1
                    continue
                object_path = f"{f.annee}/{f.semestre}/{f.ressource}/{f.module}/{f.id}_{uuid.uuid4()}.pdf"
                url = f"{TEBI_ENDPOINT}/{TEBI_BUCKET}/{object_path}"
                response = requests.put(
                    url,
                    data=r.content,
                    headers={
                        'Content-Type': 'application/pdf',
                        'Content-Length': str(len(r.content))
                    },
                    timeout=60
                )
                if response.status_code == 200:
                    f.url = url
                    db.session.commit()
                    traites += 1
                else:
                    echecs += 1
            except Exception as e:
                print(f"Erreur migration fichier {f.id}: {e}")
                echecs += 1
        restants = Fichier.query.filter(Fichier.url.like('%supabase%')).count()
        return jsonify({'success': True, 'traites': traites, 'echecs': echecs, 'restants': restants, 'termine': restants == 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/migration_status')
def migration_status():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    restants = Fichier.query.filter(Fichier.url.like('%supabase%')).count()
    total    = Fichier.query.count()
    return jsonify({'restants': restants, 'total': total, 'termine': restants == 0})

# ── FAVORIS ─────────────────
@app.route('/api/favoris', methods=['GET'])
def get_favoris():
    if not session.get('user_id'):
        return jsonify([])
    favs     = Favori.query.filter_by(utilisateur_id=session['user_id']).all()
    ids      = [f.fichier_id for f in favs]
    fichiers = Fichier.query.filter(Fichier.id.in_(ids)).all() if ids else []
    return jsonify([{'id': f.id, 'nom': f.nom, 'url': f.url, 'date_creation': f.date_creation} for f in fichiers])

@app.route('/api/favoris/<int:fichier_id>', methods=['POST'])
def ajouter_favori(fichier_id):
    if not session.get('user_id'):
        return jsonify({'error': 'Non connecté'}), 401
    if Favori.query.filter_by(utilisateur_id=session['user_id'], fichier_id=fichier_id).first():
        return jsonify({'success': True})
    fav = Favori(utilisateur_id=session['user_id'], fichier_id=fichier_id, date_creation=datetime.now().strftime("%d/%m/%Y %H:%M"))
    db.session.add(fav)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/favoris/<int:fichier_id>', methods=['DELETE'])
def supprimer_favori(fichier_id):
    if not session.get('user_id'):
        return jsonify({'error': 'Non connecté'}), 401
    Favori.query.filter_by(utilisateur_id=session['user_id'], fichier_id=fichier_id).delete()
    db.session.commit()
    return jsonify({'success': True})

# ── CONSULTATIONS ─────────────────
@app.route('/api/consultations', methods=['POST'])
def enregistrer_consultation():
    if not session.get('user_id'):
        return jsonify({'error': 'Non connecté'}), 401
    data       = request.json
    fichier_id = data.get('fichier_id')
    if not fichier_id:
        return jsonify({'error': 'fichier_id manquant'}), 400
    c = Consultation(utilisateur_id=session['user_id'], fichier_id=fichier_id, date_consultation=datetime.now().strftime("%d/%m/%Y %H:%M"))
    db.session.add(c)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/consultations', methods=['GET'])
def get_consultations():
    if not session.get('user_id'):
        return jsonify([])
    cons     = Consultation.query.filter_by(utilisateur_id=session['user_id']).order_by(Consultation.id.desc()).limit(10).all()
    ids      = [c.fichier_id for c in cons]
    fichiers = Fichier.query.filter(Fichier.id.in_(ids)).all() if ids else []
    return jsonify([{'id': f.id, 'nom': f.nom, 'url': f.url} for f in fichiers])

# ── CHAT ─────────────────
def chat_with_groq(question, system_prompt):
    if not GROQ_API_KEY:
        return None
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "max_tokens": 2000, "temperature": 0.3,
                  "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]},
            timeout=30
        )
        result = response.json()
        return result['choices'][0]['message']['content'] if 'choices' in result else None
    except Exception as e:
        print(f"Erreur Groq: {e}")
        return None

def chat_with_openrouter(question, system_prompt, model="meta-llama/llama-3.1-8b-instruct:free"):
    if not OPENROUTER_API_KEY:
        return None
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://vetmed-portal.onrender.com", "X-Title": "VetStudy"},
            json={"model": model, "max_tokens": 2000, "temperature": 0.3,
                  "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]},
            timeout=30
        )
        result = response.json()
        return result['choices'][0]['message']['content'] if 'choices' in result else None
    except Exception as e:
        print(f"Erreur OpenRouter: {e}")
        return None

@app.route('/api/chat', methods=['POST'])
def chat():
    if not session.get('user_id') and not session.get('admin'):
        return jsonify({'error': 'Non connecté'}), 401
    data     = request.json
    question = data.get('message', '')
    if not question:
        return jsonify({'error': 'Message vide'}), 400

    annee_specifique = None
    for annee_id, mots_annee in [
        ('1a', ['1ère','1ere','première','premiere','1er']),
        ('2a', ['2ème','2eme','deuxième','deuxieme','2nd']),
        ('3a', ['3ème','3eme','troisième','troisieme']),
        ('4a', ['4ème','4eme','quatrième','quatrieme']),
        ('5a', ['5ème','5eme','cinquième','cinquieme']),
        ('6a', ['6ème','6eme','sixième','sixieme'])
    ]:
        if any(mot in question.lower() for mot in mots_annee):
            annee_specifique = annee_id
            break

    fichiers = Fichier.query.filter_by(annee=annee_specifique).all() if annee_specifique else Fichier.query.all()

    if question.startswith('/'):
        if question == '/help':
            return jsonify({'success': True, 'answer': "Commandes :\n/liste <annee> : modules d'une année\n/modules <annee> <semestre> : modules d'un semestre\n/recent : derniers fichiers\n/help : cette aide."})
        elif question.startswith('/liste'):
            annee = question[7:].strip()
            mods  = sorted(set(f.module for f in Fichier.query.filter_by(annee=annee).all()))
            return jsonify({'success': True, 'answer': ("Modules de " + annee + " :\n" + "\n".join(mods)) if mods else "Aucun fichier trouvé."})
        elif question.startswith('/modules'):
            parts = question[9:].strip().split()
            if len(parts) >= 2:
                mods = sorted(set(f.module for f in Fichier.query.filter_by(annee=parts[0], semestre=parts[1]).all()))
                return jsonify({'success': True, 'answer': (f"Modules {parts[0]} {parts[1]} :\n" + "\n".join(mods)) if mods else "Aucun fichier trouvé."})
        elif question == '/recent':
            recent = Fichier.query.order_by(Fichier.date_creation.desc()).limit(5).all()
            msg    = "Derniers fichiers :\n" + "\n".join(f"• {f.nom} ({f.date_creation})" for f in recent) if recent else "Aucun fichier."
            return jsonify({'success': True, 'answer': msg})

    tous_fichiers = [{'info': f"[{f.annee}|{f.semestre}|{f.ressource}|{f.module}] — {f.nom}", 'module': f.module or '', 'nom': f.nom or '', 'texte': f.texte or '', 'annee': f.annee or '', 'semestre': f.semestre or ''} for f in fichiers]
    mots_question = question.lower().split()
    pertinents, autres = [], []
    for f in tous_fichiers:
        score = sum(1 for mot in mots_question if mot in f['module'].lower() or mot in f['nom'].lower() or (f['texte'] and mot in f['texte'].lower()))
        (pertinents if score > 0 else autres).append(f)

    ordonnes     = pertinents + autres
    selectionnes = list(ordonnes[:40])
    for annee_id in sorted(set(f['annee'] for f in ordonnes if f['annee'])):
        fichiers_annee = [f for f in ordonnes if f['annee'] == annee_id]
        deja_pris      = len([f for f in selectionnes if f['annee'] == annee_id])
        selectionnes  += [f for f in fichiers_annee if f not in selectionnes][:max(0, 12 - deja_pris)]
    for f in ordonnes:
        if len(selectionnes) >= 100: break
        if f not in selectionnes: selectionnes.append(f)

    textes_pertinents = [f"=== {f['nom']} ({f['module']} - {f['annee']} {f['semestre']}) ===\n{f['texte'][:3000]}" for f in pertinents[:5] if f['texte']]
    extraits_texte    = ("**Contenu des cours pertinents :**\n" + "\n\n".join(textes_pertinents)) if textes_pertinents else "Aucun extrait spécifique trouvé."

    system_prompt = f"""Tu es VetBot, assistant IA spécialisé en médecine vétérinaire pour le portail VetStudy.
Ta mission est de répondre aux étudiants en te basant sur le contenu des cours listés ici.
Si la réponse se trouve dans les extraits, cite le fichier source.
Si non, indique les fichiers qui pourraient contenir l'info.

Règles IMPORTANTES :
- Pas de markdown (#, *, etc.)
- Titres EN MAJUSCULES
- Listes avec tirets (-)
- Concis et pédagogique
- Uniquement médecine vétérinaire

{extraits_texte}

Fichiers disponibles :
{chr(10).join(f['info'] for f in selectionnes[:100])}
"""
    answer = chat_with_groq(question, system_prompt)
    if answer is None:
        answer = chat_with_openrouter(question, system_prompt)
    if answer is None:
        answer = chat_with_openrouter(question, system_prompt, model="google/gemma-7b-it:free")
    if answer is None:
        answer = "Désolé, le chatbot est temporairement indisponible. Réessaie plus tard."

    return jsonify({'success': True, 'answer': answer})

# ── UTILISATEURS ─────────────────
@app.route('/api/admin/utilisateurs')
def get_utilisateurs():
    if not session.get('admin'):
        return jsonify({'error': 'Non autorisé'}), 401
    users = Utilisateur.query.order_by(Utilisateur.id.desc()).all()
    return jsonify([{'id': u.id, 'nom': u.nom, 'prenom': u.prenom, 'email': u.email, 'niveau': u.niveau, 'actif': u.actif, 'premium': u.premium, 'date_inscription': u.date_inscription} for u in users])

@app.route('/api/admin/utilisateur/<int:id>/toggle_actif', methods=['POST'])
def toggle_actif(id):
    if not session.get('admin'): return jsonify({'error': 'Non autorisé'}), 401
    u = Utilisateur.query.get(id)
    if u:
        u.actif = not u.actif
        db.session.commit()
    return jsonify({'success': True, 'actif': u.actif})

@app.route('/api/admin/utilisateur/<int:id>/toggle_premium', methods=['POST'])
def toggle_premium(id):
    if not session.get('admin'): return jsonify({'error': 'Non autorisé'}), 401
    u = Utilisateur.query.get(id)
    if u:
        u.premium = not u.premium
        db.session.commit()
    return jsonify({'success': True, 'premium': u.premium})

@app.route('/api/admin/utilisateur/<int:id>', methods=['DELETE'])
def delete_utilisateur(id):
    if not session.get('admin'): return jsonify({'error': 'Non autorisé'}), 401
    u = Utilisateur.query.get(id)
    if u:
        db.session.delete(u)
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/utilisateur/<int:id>/activite')
def get_activite_utilisateur(id):
    if not session.get('admin'): return jsonify({'error': 'Non autorisé'}), 401
    u = Utilisateur.query.get(id)
    if not u: return jsonify({'error': 'Introuvable'}), 404
    favs         = Favori.query.filter_by(utilisateur_id=id).all()
    fichiers_fav = Fichier.query.filter(Fichier.id.in_([f.fichier_id for f in favs])).all() if favs else []
    cons         = Consultation.query.filter_by(utilisateur_id=id).order_by(Consultation.id.desc()).limit(20).all()
    fichiers_con = Fichier.query.filter(Fichier.id.in_([c.fichier_id for c in cons])).all() if cons else []
    return jsonify({
        'favoris':       [{'id': f.id, 'nom': f.nom} for f in fichiers_fav],
        'consultations': [{'id': f.id, 'nom': f.nom, 'date': c.date_consultation} for c, f in zip(cons, fichiers_con)]
    })

# ── INIT DB ─────────────────
with app.app_context():
    db.create_all()
    for col_sql in [
        "ALTER TABLE fichier ADD COLUMN date_creation TEXT DEFAULT ''",
        "ALTER TABLE fichier ADD COLUMN texte TEXT DEFAULT ''"
    ]:
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text(col_sql))
                conn.commit()
        except:
            pass

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
