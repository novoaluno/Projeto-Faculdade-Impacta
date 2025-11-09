# Imports existentes
from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime

# Carrega as variáveis de ambiente
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Conexão com o MongoDB
try:
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client.get_database("clientesdb")
    clientes_collection = db.get_collection("clientes")
    produtos_collection = db.get_collection("produtos")
    pedidos_collection = db.get_collection("pedidos")
except Exception as e:
    print(f"Erro ao conectar ao MongoDB: {e}")
    clientes_collection = None
    produtos_collection = None
    pedidos_collection = None

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

# --- Rotas para Pedidos ---
@app.route('/pedidos')
def listar_pedidos():
    if pedidos_collection is None:
        return "Erro de conexão com o banco de dados.", 500
    
    # Busca pedidos e faz o "join" manual com o nome do cliente
    pedidos_lista = []
    for pedido in pedidos_collection.find().sort("data_criacao", -1):
        cliente = clientes_collection.find_one({'_id': pedido['cliente_id']})
        pedido['cliente_nome'] = cliente['nome'] if cliente else "Cliente Deletado"
        pedidos_lista.append(pedido)
        
    return render_template('pedidos.html', pedidos=pedidos_lista)

@app.route('/pedidos/add', methods=['GET', 'POST'])
def add_pedido():
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        # Pega todos os IDs de produtos que foram enviados pelo formulário
        produto_ids = request.form.getlist('produto_id') 

        produtos_pedidos = []
        total_pedido = 0.0
        erros_estoque = False

        for pid in produto_ids:
            # Pega a quantidade para este produto específico
            quantidade_str = request.form.get(f'quantidade_{pid}')
            quantidade = int(quantidade_str) if quantidade_str else 0

            if quantidade > 0:
                produto_db = produtos_collection.find_one({'_id': ObjectId(pid)})
                
                if not produto_db:
                    flash(f"Produto com ID {pid} não encontrado.", "error")
                    erros_estoque = True
                    continue

                estoque_atual = int(produto_db['quantidade'])
                
                # 1. Validação de Estoque
                if estoque_atual < quantidade:
                    flash(f"Estoque insuficiente para {produto_db['nome']}. Disponível: {estoque_atual}", "error")
                    erros_estoque = True
                else:
                    # Se tiver estoque, adiciona ao pedido
                    preco_unit = float(produto_db['preco'])
                    subtotal = preco_unit * quantidade
                    total_pedido += subtotal
                    
                    produtos_pedidos.append({
                        'produto_id': ObjectId(pid),
                        'nome': produto_db['nome'],
                        'quantidade': quantidade,
                        'preco_unitario': preco_unit,
                        'subtotal': subtotal
                    })

        # 2. Se houver qualquer erro de estoque, para e volta ao formulário
        if erros_estoque:
            return redirect(url_for('add_pedido'))
        
        # 3. Se não houver produtos, avisa
        if not produtos_pedidos:
            flash("Nenhum produto selecionado para o pedido.", "error")
            return redirect(url_for('add_pedido'))

        # 4. Se tudo estiver OK, atualiza o estoque no banco
        for item in produtos_pedidos:
            produtos_collection.update_one(
                {'_id': item['produto_id']},
                {'$inc': {'quantidade': -item['quantidade']}}
            )

        # 5. Cria o documento do pedido
        novo_pedido = {
            'cliente_id': ObjectId(cliente_id),
            'data_criacao': datetime.utcnow(),
            'produtos': produtos_pedidos,
            'total_pedido': total_pedido,
            'status': 'Pendente'
        }
        pedidos_collection.insert_one(novo_pedido)

        flash("Pedido criado com sucesso!", "success")
        return redirect(url_for('listar_pedidos'))

    # Método GET: Carrega o formulário
    clientes = list(clientes_collection.find())
    # Apenas produtos com estoque > 0
    produtos_disponiveis = list(produtos_collection.find({'quantidade': {'$gt': 0}}))
    
    return render_template('form_pedido.html', clientes=clientes, produtos=produtos_disponiveis)


@app.route('/pedidos/delete/<id>')
def delete_pedido(id):
    pedido = pedidos_collection.find_one({'_id': ObjectId(id)})
    
    if pedido:
        # Devolver o estoque ao deletar um pedido
        for item in pedido['produtos']:
            produtos_collection.update_one(
                {'_id': item['produto_id']},
                {'$inc': {'quantidade': item['quantidade']}}
            )
        
        pedidos_collection.delete_one({'_id': ObjectId(id)})
        flash("Pedido deletado e estoque restaurado.", "success")
    else:
        flash("Pedido não encontrado.", "error")
        
    return redirect(url_for('listar_pedidos'))


if __name__ == '__main__':
    app.run(debug=True)

    