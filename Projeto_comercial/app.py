from decimal import Decimal 

from flask import Flask, abort, render_template, request
from mysql.connector import Error

from conexao import consultar, consultar_um


app = Flask(__name__)

@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/produtos")
def produtos():
    busca = request.args.get("busca", "").strip()
    sql = """
        select 
            p.id_produto as id,
            p.nome_produto as produto,
            c.categoria,
            p.preco_unit as preco
from produtos as p
    inner join categorias as c on c.id_categoria = p.id_categoria
    where p.nome_produto
"""
    dados = consultar(sql, (f"%{busca}%"))
    return render_template("tabela.html", titulo="Produtos", dados=dados, busca=busca)

@app.errorhandler(error)
def erro_banco(erro):
    """Qualquer erro de banco fora de um formulário cai aqui."""
    app.logger.error("Falha MySQL %s", erro.errno)
    mensagem = "Falha ao acessar o banco. Confira o .env e se o MYSQL está ligado."
    return render_template("erro.html", mensagem=mensagem), 503


@app.route("/clientes")
def clientes():
    busca = request.args.get("busca", "").strip()
    sql = """
select id_cliente as id, nome, sobrenome, email
from clientes
where concat(Nome, '', Sobrenome) like %s
order by Nome, sobrenome
"""
    dados = consultar(sql, (f"%{busca}%"))
    return render_template("tabela.html", titulo="Clientes", dados=dados, busca=busca, vazio="Nenhum cliente com esse nome")

@app.route("/lojas")
def lojas():
    sql = """
        select 1.id_loja as id, l.loja, loc.cidade, loc.Estado
        from lojas as l
        inner join locais as loc on loc.id_local = l.id_local
        order by l.loja
    """
    return render_template("template.html", titulo="lojas", dados=consultar(sql))

@app.router("/vendedores")
def vendedores():
    sql = """
        select v.id_vendedor as id, v.nome, v.email, l.loja
        from vendedores as v
        inner join loja as l on l.id_loja = v.id_loja
        order by v.nome
    """
    return render_template("tabela.html", titulo="Vendedores", dados=consultar(sql),
    vazio="Nenhum vendedor cadastrado.")

@app.route("/pedidos")
def pedidos():
    sql = """
        select p.id_pedido as id, p.data_pedido as data,
                concat(c.nome, '', c.sobrenome) as cliente,
                l.loja, v.nome as vendedor, s.descricao as status,
                p.valor_total as total, p.Origem_Registro as Origem
            from pedidos as p
            inner join clients as c on c.id_cliente = p.id_cliente
            inner join lojas as l on l.id_loja = p.id_loja
            inner join status_pedido as s on s.id_status = p.id_status
            left join vendedores as v on v.id_vendedor = p.id_vendedor
            order by p.id_pedido desc
            limit 100
    """
    return render_template("tabela.html", titulo="Pedidos (100 mais recentes)",
                           dados=consultar(sql), detalhe="pedido_detalhe")

@app.route('/pedidos/<int:ident>')
def pedido_detalhe(ident):
    pedido = consultar_um("""
        SELECT P.ID_Pedido, P.Data_Pedido, P.Valor_Total, P.Origem_Registro,
               CONCAT(C.Nome, ' ', C.Sobrenome) AS Cliente, L.Loja,
               V.Nome AS Vendedor, S.Descricao AS Status
        FROM pedidos AS P
        INNER JOIN clientes AS C ON C.ID_Cliente = P.ID_Cliente
        INNER JOIN lojas AS L ON L.ID_Loja = P.ID_Loja
        INNER JOIN status_pedido AS S ON S.ID_Status = P.ID_Status
        LEFT JOIN vendedores AS V ON V.ID_Vendedor = P.ID_Vendedor
        WHERE P.ID_Pedido = %s
    """, (ident,))

    if pedido is None:
        abort(404)

    itens = consultar("""
        SELECT pr.Nome_Produto AS Produto, i.Quantidade, i.Preco_Unit AS Preco,
               i.Desconto_Valor AS Desconto,
               i.Quantidade * i.Preco_Unit - i.Desconto_Valor + i.Ajuste_Valor AS Subtotal
        FROM itens_pedido AS i
        INNER JOIN produtos AS pr ON pr.ID_Produto = i.ID_Produto
        WHERE i.ID_Pedido = %s
        ORDER BY i.ID_Item
    """, (ident,))

    pagamentos = consultar("""
        SELECT pg.ID_Pagamento AS ID, f.Descricao AS Forma, s.Descricao AS Status,
               pg.Valor_Pagamento AS Valor, pg.Data_Pagamento AS Data
        FROM pagamentos AS pg
        INNER JOIN formas_pagamento AS f ON f.ID_Forma = pg.ID_Forma
        INNER JOIN status_pagamento AS s ON s.ID_Status = pg.ID_Status
        WHERE pg.ID_Pedido = %s
        ORDER BY pg.ID_Pagamento
    """, (ident,))

    soma_itens = sum((i['Subtotal'] for i in itens), Decimal("0.00"))

    return render_template("pedido_detalhe.html", pedido=pedido, itens=itens,
                           pagamentos=pagamentos, soma_itens=soma_itens)

