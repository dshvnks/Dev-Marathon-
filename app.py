from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
import subprocess

# Configuration de l'application
app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/avatars'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # Limite à 2 Mo pour les avatars

# Initialisation de la base de données et du gestionnaire de sessions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modèle de base de données pour les utilisateurs
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    avatar = db.Column(db.String(255), default='defaut.png')

# Modèle de base de données pour les scores
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_name = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Route d'accueil - affiche la page de bienvenue
@app.route('/')
def home():
    return render_template('bienvenue.html')  # Page de bienvenue

# Route pour la page d'inscription
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Vérification si le nom d'utilisateur existe déjà
        if User.query.filter_by(username=username).first():
            flash('Nom d\'utilisateur déjà utilisé.', 'error')
        else:
            user = User(username=username, password=password)
            db.session.add(user)
            db.session.commit()
            flash('Inscription réussie ! Connectez-vous.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')

# Route pour la page de connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        # Vérification des informations de connexion
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'error')

    return render_template('login.html')



 # Route pour le mode invité
@app.route('/guest')
def guest():
    if current_user.is_authenticated:
        # Si l'utilisateur est connecté, le rediriger vers son tableau de bord
        return redirect(url_for('dashboard'))
    else:
        # Si l'utilisateur n'est pas connecté, afficher le tableau de bord sans authentification
        games = os.listdir('games')
        scores = Score.query.filter_by(user_id=None).all()  # Pas de scores pour l'invité pour l'instant
        return render_template('dashboard.html', games=games, scores=scores)


# Route pour le tableau de bord de l'utilisateur
@app.route('/dashboard')
@login_required
def dashboard():
    # Récupérer la liste des jeux à partir du répertoire 'games'
    games = os.listdir('games')
    
    # Récupérer les scores de l'utilisateur actuel depuis la base de données
    scores = Score.query.filter_by(user_id=current_user.id).all()
    
    # Rendre le template avec les variables 'games' et 'scores'
    return render_template('dashboard.html', games=games, scores=scores)
    

# Route pour changer l'avatar
@app.route('/update_avatar', methods=['GET', 'POST'])
@login_required
def update_avatar():
    if request.method == 'POST':
        if 'avatar' in request.files:
            avatar_file = request.files['avatar']
            if avatar_file.filename != '':
                # Générer un nom de fichier unique pour éviter les conflits
                avatar_filename = os.path.join(app.config['UPLOAD_FOLDER'], avatar_file.filename)
                avatar_file.save(avatar_filename)
                
                # Mettre à jour le champ avatar de l'utilisateur dans la base de données
                current_user.avatar = avatar_file.filename
                db.session.commit()
               
        return redirect(url_for('dashboard'))
    
    return render_template('update_avatar.html')

# Route pour jouer à un jeu
@app.route('/play/<game_name>')
@login_required
def play_game(game_name):
    # Chemin vers le dossier des jeux
    game_folder = os.path.join('games', game_name)
    # Chemin complet vers le script du jeu
    game_script = os.path.abspath(os.path.join(game_folder, f"{game_name}.py"))

    # Vérification de l'existence du dossier et du script
    if not os.path.exists(game_folder) or not os.path.isfile(game_script):
        return abort(404, description="Jeu introuvable")

    try:
        # Lancer le script Python du jeu
        process = subprocess.Popen(['python', game_script], start_new_session=True)
        print(f"Le jeu {game_name} a été lancé avec le PID {process.pid}.")
        return render_template('game_running.html', game_name=game_name)
    except Exception as e:
        print(f"Erreur lors du lancement du jeu : {str(e)}")
        return f"Erreur lors du lancement du jeu : {str(e)}", 500
    


# Déconnexion de l'utilisateur
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Efface toutes les données de session (cela déconnecte l'utilisateur)
    return redirect(url_for('login'))  # Redirige vers la page de connexion


if __name__ == '__main__':
    # Création de la base de données si elle n'existe pas
    with app.app_context():
        if not os.path.exists('database.db'):
            db.create_all()
    
    # Lancer l'application Flask
    app.run(debug=True)
