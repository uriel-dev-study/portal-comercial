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
        SELECT
            p.id_produto AS id,
            p.nome_produto AS produto,
            c.categoria,
            p.preco_unit AS preco
        FROM produtos AS p
        INNER JOIN categorias AS c
            ON c.id_categoria = p.id_categoria
        WHERE p.nome_produto LIKE %s
        ORDER BY p.nome_produto
    """

    dados = consultar(sql, (f"%{busca}%",))

    return render_template(
        "tabela.html",
        titulo="Produtos",
        dados=dados,
        busca=busca
    )


@app.errorhandler(404)
def pagina_nao_encontrada(error):
    return "Página não encontrada!", 404

@app.errorhandler(500)
def erro_interno(error):
    return "Erro interno do servidor!", 500

def erro_banco(erro):
    """Qualquer erro de banco fora de um formulário cai aqui."""
    app.logger.error("Falha MySQL %s", erro.errno)
    mensagem = "Falha ao acessar o banco. Confira o .env e se o MYSQL está ligado."
    return render_template("erro.html", mensagem=mensagem), 503


@app.route("/clientes")
def clientes():
    busca = request.args.get("busca", "").strip()

    sql = """
        SELECT
            id_cliente AS id,
            nome,
            sobrenome,
            email
        FROM clientes
        WHERE CONCAT(nome, ' ', sobrenome) LIKE %s
        ORDER BY nome, sobrenome
    """

    dados = consultar(sql, (f"%{busca}%",))

    return render_template(
        "tabela.html",
        titulo="Clientes",
        dados=dados,
        busca=busca,
        vazio="Nenhum cliente com esse nome"
    )


@app.route("/lojas")
def lojas():
    sql = """
        SELECT
            l.id_loja AS id,
            l.loja,
            loc.cidade,
            loc.estado
        FROM lojas AS l
        INNER JOIN locais AS loc
            ON loc.id_local = l.id_local
        ORDER BY l.loja
    """

    dados = consultar(sql)

    return render_template(
        "tabela.html",
        titulo="Lojas",
        dados=dados,
        vazio="Nenhuma loja cadastrada."
    )


@app.route("/relatorios")
def relatorios():
    sql = """
        SELECT
            'Total de produtos' AS indicador,
            COUNT(*) AS quantidade
        FROM produtos

        UNION ALL

        SELECT
            'Total de clientes',
            COUNT(*)
        FROM clientes

        UNION ALL

        SELECT
            'Total de lojas',
            COUNT(*)
        FROM lojas

        UNION ALL

        SELECT
            'Total de vendedores',
            COUNT(*)
        FROM vendedores

        UNION ALL

        SELECT
            'Total de pedidos',
            COUNT(*)
        FROM pedidos

        UNION ALL

        SELECT
            'Faturamento total (R$)',
            COALESCE(SUM(valor_total), 0)
        FROM pedidos
    """

    dados = consultar(sql)

    return render_template(
        "tabela.html",
        titulo="Relatórios",
        dados=dados,
        vazio="Não existem dados para os relatórios."
    )


@app.route("/pedidos")
def pedidos():
    sql = """
        SELECT
            p.id_pedido AS id,
            p.data_pedido AS data,
            CONCAT(c.nome, ' ', c.sobrenome) AS cliente,
            l.loja,
            v.nome AS vendedor,
            s.descricao AS status,
            p.valor_total AS total,
            p.origem_registro AS origem
        FROM pedidos AS p
        INNER JOIN clientes AS c
            ON c.id_cliente = p.id_cliente
        INNER JOIN lojas AS l
            ON l.id_loja = p.id_loja
        INNER JOIN status_pedido AS s
            ON s.id_status = p.id_status
        LEFT JOIN vendedores AS v
            ON v.id_vendedor = p.id_vendedor
        ORDER BY p.id_pedido DESC
        LIMIT 100
    """

    return render_template(
        "tabela.html",
        titulo="Pedidos (100 mais recentes)",
        dados=consultar(sql),
        detalhe="pedido_detalhe"
    )


@app.route("/categorias")
def categorias():
    sql = """
        SELECT
            id_categoria AS id,
            categoria
        FROM categorias
        ORDER BY categoria
    """

    dados = consultar(sql)

    return render_template(
        "tabela.html",
        titulo="Categorias",
        dados=dados,
        vazio="Nenhuma categoria cadastrada."
    )



@app.route("/vendedores")
def vendedores():
    sql = """
        SELECT
            v.id_vendedor AS id,
            v.nome,
            v.email,
            l.loja
        FROM vendedores AS v
        INNER JOIN lojas AS l
            ON l.id_loja = v.id_loja
        ORDER BY v.nome
    """

    dados = consultar(sql)

    return render_template(
        "tabela.html",
        titulo="Vendedores",
        dados=dados,
        vazio="Nenhum vendedor cadastrado."
    )

@app.route("/locais")
def locais():
    sql = """
        SELECT
            id_local AS id,
            cidade,
            estado
        FROM locais
        ORDER BY cidade
    """

    dados = consultar(sql)

    return render_template(
        "tabela.html",
        titulo="Locais",
        dados=dados,
        vazio="Nenhum local cadastrado."
    )


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

