from flask import Flask, render_template, request, redirect, send_file, session, url_for, flash
import os
import sqlite3
from fpdf import FPDF
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'troque_para_uma_chave_secreta_complexa')  # Defina SECRET_KEY em variável de ambiente em produção

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def conectar():
    conexao = sqlite3.connect("estoque_ovos.db")
    cursor = conexao.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_ovo TEXT,
    tipo_caixa INTEGER,
    data_lote TEXT,
    quantidade_caixas INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente TEXT,
    tipo_ovo TEXT,
    tipo_caixa INTEGER,
    quantidade INTEGER,
    data TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password_hash TEXT
    )
    """)

    conexao.commit()
    return conexao


def get_user_by_username(username):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conexao.close()
    return user


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Preencha usuário e senha.', 'danger')
            return redirect(url_for('register'))

        if get_user_by_username(username):
            flash('Usuário já existe.', 'danger')
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
        conexao.commit()
        conexao.close()
        flash('Cadastro realizado com sucesso. Faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = get_user_by_username(username)
        if not user or not check_password_hash(user[2], password):
            flash('Usuário ou senha inválidos.', 'danger')
            return redirect(url_for('login'))

        session['user_id'] = user[0]
        session['username'] = user[1]
        flash('Login realizado com sucesso.', 'success')
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Desconectado com sucesso.', 'success')
    return redirect(url_for('login'))


@app.route("/")
@login_required
def index():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT * FROM estoque")
    dados = cursor.fetchall()

    # lote mais antigo
    cursor.execute("""
    SELECT * FROM estoque
    ORDER BY data_lote ASC
    LIMIT 1
    """)

    lote_antigo = cursor.fetchone()

    # totais por tipo
    cursor.execute("""
    SELECT tipo_ovo, SUM(quantidade_caixas)
    FROM estoque
    GROUP BY tipo_ovo
    """)

    totais_por_tipo = cursor.fetchall()

    # total de caixas
    cursor.execute("SELECT SUM(quantidade_caixas) FROM estoque")
    total_caixas = cursor.fetchone()[0] or 0

    # paletes (30 caixas por palete)
    paletes = total_caixas // 30

    conexao.close()

    return render_template("index.html", dados=dados, lote=lote_antigo, totais_por_tipo=totais_por_tipo, total_caixas=total_caixas, paletes=paletes)


@app.route("/entrada", methods=["POST"])
@login_required
def entrada():

    tipo = request.form["tipo"]
    caixa = request.form["caixa"]
    data = request.form["data"]
    quantidade = request.form["quantidade"]

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
    INSERT INTO estoque (tipo_ovo, tipo_caixa, data_lote, quantidade_caixas)
    VALUES (?, ?, ?, ?)
    """, (tipo, caixa, data, quantidade))

    conexao.commit()
    conexao.close()

    return redirect("/")


@app.route("/saida/<int:id>", methods=["POST"])
@login_required
def saida(id):

    quantidade = int(request.form["quantidade"])
    cliente = request.form["cliente"]

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT quantidade_caixas, tipo_ovo, tipo_caixa FROM estoque WHERE id = ?", (id,))
    atual = cursor.fetchone()

    if atual:
        nova = atual[0] - quantidade

        cursor.execute("""
        UPDATE estoque
        SET quantidade_caixas = ?
        WHERE id = ?
        """, (nova, id))

        # registrar saida
        from datetime import datetime
        data_saida = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO saidas (cliente, tipo_ovo, tipo_caixa, quantidade, data)
        VALUES (?, ?, ?, ?, ?)
        """, (cliente, atual[1], atual[2], quantidade, data_saida))

        conexao.commit()

    conexao.close()

    return redirect("/")


@app.route("/excluir/<int:id>")
@login_required
def excluir(id):

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("DELETE FROM estoque WHERE id = ?", (id,))
    conexao.commit()
    conexao.close()

    return redirect("/")


@app.route("/relatorio")
@login_required
def relatorio():
    data_inicio = request.args.get('data_inicio', datetime.now().replace(day=1).strftime('%Y-%m-%d'))
    data_fim = request.args.get('data_fim', datetime.now().strftime('%Y-%m-%d'))
    cliente = request.args.get('cliente', '')

    conexao = conectar()
    cursor = conexao.cursor()

    query = "SELECT * FROM saidas WHERE data >= ? AND data <= ?"
    params = [data_inicio, data_fim]

    if cliente:
        query += " AND cliente = ?"
        params.append(cliente)

    query += " ORDER BY data DESC"

    cursor.execute(query, params)
    saidas = cursor.fetchall()

    # Lista de clientes únicos para o select
    cursor.execute("SELECT DISTINCT cliente FROM saidas ORDER BY cliente")
    clientes = [row[0] for row in cursor.fetchall()]

    conexao.close()

    return render_template("relatorio.html", saidas=saidas, data_inicio=data_inicio, data_fim=data_fim, cliente=cliente, clientes=clientes)


@app.route("/relatorio/pdf")
@login_required
def relatorio_pdf():
    data_inicio = request.args.get('data_inicio', datetime.now().replace(day=1).strftime('%Y-%m-%d'))
    data_fim = request.args.get('data_fim', datetime.now().strftime('%Y-%m-%d'))
    cliente = request.args.get('cliente', '')

    conexao = conectar()
    cursor = conexao.cursor()

    query = "SELECT * FROM saidas WHERE data >= ? AND data <= ?"
    params = [data_inicio, data_fim]

    if cliente:
        query += " AND cliente = ?"
        params.append(cliente)

    query += " ORDER BY data DESC"

    cursor.execute(query, params)
    saidas = cursor.fetchall()

    conexao.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    titulo = f"Relatório de Saídas - {data_inicio} a {data_fim}"
    if cliente:
        titulo += f" - Cliente: {cliente}"
    pdf.cell(200, 10, txt=titulo, ln=True, align='C')
    pdf.ln(10)

    for saida in saidas:
        pdf.cell(200, 10, txt=f"ID: {saida[0]} | Cliente: {saida[1]} | Tipo: {saida[2]} | Caixa: {saida[3]} | Qtd: {saida[4]} | Data: {saida[5]}", ln=True)

    pdf_output = pdf.output(dest='S').encode('latin1')

    from io import BytesIO
    pdf_buffer = BytesIO(pdf_output)

    nome_arquivo = f"relatorio_saidas_{data_inicio}_a_{data_fim}"
    if cliente:
        nome_arquivo += f"_{cliente.replace(' ', '_')}"
    nome_arquivo += ".pdf"

    return send_file(pdf_buffer, as_attachment=True, download_name=nome_arquivo, mimetype='application/pdf')


if __name__ == "__main__":
    # Em produção, use um servidor WSGI e HTTPS com certificado válido
    app.run(debug=True, host='0.0.0.0')