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
except Exception as e:
    print(f"Erro ao conectar ao MongoDB: {e}")
    clientes_collection = None # Garante que a aplicação não trave

# Rota principal - READ (Listar clientes)
@app.route('/')
def index():
    if clientes_collection is None:
        return "Erro de conexão com o banco de dados.", 500

    clientes = list(clientes_collection.find())
    return render_template('index.html', clientes=clientes)

# Rota para adicionar um novo cliente - CREATE
@app.route('/add', methods=['GET', 'POST'])
def add_cliente():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']

        if nome and email:
            clientes_collection.insert_one({
                'nome': nome,
                'email': email,
                'telefone': telefone
            })
            return redirect(url_for('index'))
    return render_template('form.html', cliente=None)

# Rota para editar um cliente - UPDATE
@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit_cliente(id):
    cliente = clientes_collection.find_one({'_id': ObjectId(id)})

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']

        clientes_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': {'nome': nome, 'email': email, 'telefone': telefone}}
        )
        return redirect(url_for('index'))

    return render_template('form.html', cliente=cliente)

# Rota para deletar um cliente - DELETE
@app.route('/delete/<id>')
def delete_cliente(id):
    clientes_collection.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)