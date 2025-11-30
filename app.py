from flask import Flask, render_template, request, redirect, url_for, flash
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
        
        clientes_collection.insert_one({'nome': nome, 'email': email, 'telefone': telefone})
        flash("Cliente adicionado com sucesso!", "success")
        return redirect(url_for('index'))
    
    return render_template('form.html', cliente=None)

@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit_cliente(id):
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        
        clientes_collection.update_one({'_id': ObjectId(id)}, {'$set': {'nome': nome, 'email': email, 'telefone': telefone}})
        flash("Cliente atualizado com sucesso!", "success")
        return redirect(url_for('index'))
        
    cliente = clientes_collection.find_one({'_id': ObjectId(id)})
    return render_template('form.html', cliente=cliente)

@app.route('/delete/<id>')
def delete_cliente(id):
    clientes_collection.delete_one({'_id': ObjectId(id)})
    flash("Cliente deletado com sucesso!", "success")
    return redirect(url_for('index'))

# --- Rotas para Produtos ---

@app.route('/produtos')
def listar_produtos():
    produtos = list(produtos_collection.find())
    return render_template('produtos.html', produtos=produtos)

@app.route('/produtos/add', methods=['GET', 'POST'])
def add_produto():
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        preco = float(request.form['preco'])
        quantidade = int(request.form['quantidade'])
        
        produtos_collection.insert_one({
            'nome': nome, 
            'descricao': descricao, 
            'preco': preco, 
            'quantidade': quantidade
        })
        flash("Produto adicionado com sucesso!", "success")
        return redirect(url_for('listar_produtos'))
    
    return render_template('form_produto.html', produto=None)

@app.route('/produtos/edit/<id>', methods=['GET', 'POST'])
def edit_produto(id):
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        preco = float(request.form['preco'])
        quantidade = int(request.form['quantidade'])
        
        produtos_collection.update_one(
            {'_id': ObjectId(id)}, 
            {'$set': {
                'nome': nome, 
                'descricao': descricao, 
                'preco': preco, 
                'quantidade': quantidade
            }}
        )
        flash("Produto atualizado com sucesso!", "success")
        return redirect(url_for('listar_produtos'))
        
    produto = produtos_collection.find_one({'_id': ObjectId(id)})
    return render_template('form_produto.html', produto=produto)

@app.route('/produtos/delete/<id>')
def delete_produto(id):
    produtos_collection.delete_one({'_id': ObjectId(id)})
    flash("Produto deletado com sucesso!", "success")
    return redirect(url_for('listar_produtos'))

# --- Rotas para Pedidos ---

@app.route('/pedidos')
def listar_pedidos():
    # 1. Captura o filtro da URL
    filtro_status = request.args.get('status')
    
    # 2. Monta a query
    query = {}
    if filtro_status and filtro_status != 'Todos':
        query['status_entrega'] = filtro_status

    # 3. Busca aplicando filtro e ordenação
    pedidos = list(pedidos_collection.find(query).sort("data_criacao", -1))
    
    # 4. Busca nome do cliente manualmente (Join simples)
    for pedido in pedidos:
        cliente = clientes_collection.find_one({'_id': pedido['cliente_id']})
        pedido['cliente_nome'] = cliente['nome'] if cliente else "Cliente Removido"

    return render_template('pedidos.html', pedidos=pedidos, filtro_atual=filtro_status)

@app.route('/pedidos/add', methods=['GET', 'POST'])
def add_pedido():
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        
        # 1. Captura dados do endereço
        endereco_entrega = {
            'logradouro': request.form['logradouro'],
            'numero': request.form['numero'],
            'bairro': request.form['bairro'],
            'cidade': request.form['cidade']
        }

        # 2. Processamento dos produtos
        produto_ids = request.form.getlist('produto_id') 
        produtos_pedidos = []
        total_pedido = 0.0
        erros_estoque = False

        for pid in produto_ids:
            quantidade_str = request.form.get(f'quantidade_{pid}')
            quantidade = int(quantidade_str) if quantidade_str else 0

            if quantidade > 0:
                produto_db = produtos_collection.find_one({'_id': ObjectId(pid)})
                
                if not produto_db:
                    flash(f"Produto ID {pid} não encontrado.", "error")
                    erros_estoque = True
                    continue

                estoque_atual = int(produto_db['quantidade'])
                
                if estoque_atual < quantidade:
                    flash(f"Estoque insuficiente para {produto_db['nome']}.", "error")
                    erros_estoque = True
                else:
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

        if erros_estoque:
            return redirect(url_for('add_pedido'))
        
        if not produtos_pedidos:
            flash("Selecione pelo menos um produto.", "error")
            return redirect(url_for('add_pedido'))

        # 3. Baixa no estoque
        for item in produtos_pedidos:
            produtos_collection.update_one(
                {'_id': item['produto_id']},
                {'$inc': {'quantidade': -item['quantidade']}}
            )

        # 4. Criação do Pedido
        novo_pedido = {
            'cliente_id': ObjectId(cliente_id),
            'data_criacao': datetime.utcnow(),
            'produtos': produtos_pedidos,
            'total_pedido': total_pedido,
            'status': 'Confirmado',
            'status_entrega': 'Pendente',   # Novo campo
            'endereco_entrega': endereco_entrega # Novo campo
        }
        pedidos_collection.insert_one(novo_pedido)

        flash("Pedido criado com sucesso!", "success")
        return redirect(url_for('listar_pedidos'))

    # Método GET
    clientes = list(clientes_collection.find())
    produtos_disponiveis = list(produtos_collection.find({'quantidade': {'$gt': 0}}))
    return render_template('form_pedido.html', clientes=clientes, produtos=produtos_disponiveis)

@app.route('/pedidos/status/<id>/<novo_status>')
def update_status_pedido(id, novo_status):
    status_permitidos = ['Pendente', 'Em Trânsito', 'Entregue', 'Cancelado']
    
    if novo_status in status_permitidos:
        pedidos_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': {'status_entrega': novo_status}}
        )
        flash(f"Status atualizado para: {novo_status}", "success")
    else:
        flash("Status inválido.", "error")
        
    return redirect(url_for('listar_pedidos'))

@app.route('/pedidos/delete/<id>')
def delete_pedido(id):
    pedido = pedidos_collection.find_one({'_id': ObjectId(id)})
    
    if pedido:
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