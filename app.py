from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random, string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Substitua por sua chave secreta
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelo de usuário
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    role = db.Column(db.String(50))  # Papéis: Admin, Gerente, Vendedor, Usuário comum

# Modelo de token
class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100))
    token = db.Column(db.String(100), unique=True)
    expiration_date = db.Column(db.Date)
    used = db.Column(db.Boolean, default=False)  # Indica se o token foi usado

# Modelo de Key
class Key(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)  # Nome da Key
    key_value = db.Column(db.String(100))  # Valor da Key
    created_at = db.Column(db.DateTime, default=datetime.now)  # Data de criação da Key

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))  # Redireciona para a página de login

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login ou senha incorretos')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', role=current_user.role)

# Rota para criar tokens
@app.route('/create_token', methods=['GET', 'POST'])
@login_required
def create_token():
    if request.method == 'POST':
        action = request.form['action']
        validity_days = int(request.form['validity'])
        expiration_date = datetime.now() + timedelta(days=validity_days)
        token = generate_token(action)
        new_token = Token(action=action, token=token, expiration_date=expiration_date)
        db.session.add(new_token)
        db.session.commit()
        flash(f'Token {token} criado com sucesso! Expira em {expiration_date.strftime("%d/%m/%Y")}')
        return redirect(url_for('create_token'))

    # Obter todos os tokens já criados para exibição na página
    tokens = Token.query.all()
    return render_template('create_token.html', tokens=tokens)

# Rota para criar keys
@app.route('/create_key', methods=['GET', 'POST'])
@login_required
def create_key():
    if request.method == 'POST':
        name = request.form['name']
        key_value = generate_key_value()  # Gera o valor da key aleatoriamente
        new_key = Key(name=name, key_value=key_value)
        db.session.add(new_key)
        db.session.commit()
        flash(f'Key {name} criada com sucesso!')
        return redirect(url_for('create_key'))

    # Obter todas as keys já criadas para exibição na página
    keys = Key.query.all()
    return render_template('create_key.html', keys=keys)

def generate_key_value():
    # Gerar valor aleatório para a key
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=16))  # 16 caracteres aleatórios
    return random_string

@app.route('/validate_token', methods=['GET', 'POST'])
@login_required
def validate_token():
    if request.method == 'POST':
        token = request.form['token']
        valid_token = Token.query.filter_by(token=token).first()

        if valid_token:
            if valid_token.used:
                flash(f'Token {token} já foi usado!')
            else:
                valid_token.used = True
                db.session.commit()
                flash(f'Token {token} é válido! Expira em {valid_token.expiration_date.strftime("%d/%m/%Y")}')
        else:
            flash('Token inválido!')
        
        return redirect(url_for('validate_token'))

    # Obter todos os tokens já validados para exibição
    validated_tokens = Token.query.filter_by(used=True).all()
    return render_template('validate_token.html', validated_tokens=validated_tokens)

@app.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'Admin':  # Somente Admin pode gerenciar usuários
        flash('Acesso negado! Somente Admin pode gerenciar usuários.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe!')
            return redirect(url_for('manage_users'))
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Usuário {username} criado com sucesso!')
        return redirect(url_for('manage_users'))
    
    # Exibir lista de usuários
    users = User.query.all()
    return render_template('manage_users.html', users=users)

# Função para criar um super admin
def create_super_admin():
    if User.query.filter_by(username='superadmin').first() is None:
        hashed_password = generate_password_hash('superadmin123', method='pbkdf2:sha256')
        new_user = User(username='superadmin', email='superadmin@example.com', password=hashed_password, role='Admin')
        db.session.add(new_user)
        db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Cria as tabelas no banco de dados
        create_super_admin()  # Cria o superadmin se ele não existir
    app.run(debug=True)
