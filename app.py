from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# Conexão com o MongoDB
try:
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client.get_database("clientesdb")
    clientes_collection = db.get_collection("clientes")
    produtos_collection = db.get_collection("produtos")
except Exception as e:
    print(f"Erro ao conectar ao MongoDB: {e}")
    clientes_collection = None
    produtos_collection = None

# --- Rotas para Clientes ---

@app.route('/')
def index():
    if clientes_collection is None:
        return "Erro de conexão com o banco de dados.", 500
    clientes = list(clientes_collection.find())
    return render_template('index.html', clientes=clientes)

@app.route('/add', methods=['GET', 'POST'])
def add_cliente():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        if nome and email:
            clientes_collection.insert_one({'nome': nome, 'email': email, 'telefone': telefone})
            return redirect(url_for('index'))
    return render_template('form.html', cliente=None)

@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit_cliente(id):
    cliente = clientes_collection.find_one({'_id': ObjectId(id)})
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        clientes_collection.update_one({'_id': ObjectId(id)}, {'$set': {'nome': nome, 'email': email, 'telefone': telefone}})
        return redirect(url_for('index'))
    return render_template('form.html', cliente=cliente)

@app.route('/delete/<id>')
def delete_cliente(id):
    clientes_collection.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('index'))

# --- Rotas para Produtos ---

@app.route('/produtos')
def listar_produtos():
    if produtos_collection is None:
        return "Erro de conexão com o banco de dados.", 500
    produtos = list(produtos_collection.find())
    return render_template('produtos.html', produtos=produtos)

@app.route('/produtos/add', methods=['GET', 'POST'])
def add_produto():
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        preco = request.form['preco']
        quantidade = request.form['quantidade']
        if nome and preco and quantidade is not None:
            produtos_collection.insert_one({'nome': nome, 'descricao': descricao, 'preco': preco, 'quantidade': int(quantidade)})
            return redirect(url_for('listar_produtos'))
    return render_template('form_produto.html', produto=None)

@app.route('/produtos/edit/<id>', methods=['GET', 'POST'])
def edit_produto(id):
    produto = produtos_collection.find_one({'_id': ObjectId(id)})
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        preco = request.form['preco']
        quantidade = request.form['quantidade']
        produtos_collection.update_one({'_id': ObjectId(id)}, {'$set': {'nome': nome, 'descricao': descricao, 'preco': preco, 'quantidade': int(quantidade)}})
        return redirect(url_for('listar_produtos'))
    return render_template('form_produto.html', produto=produto)

@app.route('/produtos/delete/<id>')
def delete_produto(id):
    produtos_collection.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('listar_produtos'))

if __name__ == '__main__':
    app.run(debug=True)