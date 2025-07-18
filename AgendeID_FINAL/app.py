from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta, date, datetime
import os
from dotenv import load_dotenv
import logging

from backend.chatbot import Chatbot
from backend.database import (
    criar_banco, autenticar_usuario, obter_usuario, executar_consulta, 
    obter_horarios_disponiveis, cadastrar_usuario
)

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Inicialização do app Flask
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'chave-secreta-local')

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app.logger.setLevel(logging.INFO)

# CORS e CSRF
CORS(app)
csrf = CSRFProtect(app)

# Limitação de requisições
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["500 per day", "100 per hour"])

# Configuração de sessão
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)
)

# Cabeçalhos de segurança
@app.after_request
def adicionar_cabecalhos_seguranca(resposta):
    resposta.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    resposta.headers['Access-Control-Allow-Credentials'] = 'true'
    resposta.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-CSRFToken'
    resposta.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    resposta.headers['X-Content-Type-Options'] = 'nosniff'
    resposta.headers['X-Frame-Options'] = 'DENY'
    resposta.headers['X-XSS-Protection'] = '1; mode=block'
    resposta.headers['Cache-Control'] = 'no-store, max-age=0'
    return resposta

# Inicialização do chatbot e banco de dados
chatbot = Chatbot()
app.config['chatbot'] = chatbot

with app.app_context():
    if criar_banco():
        app.logger.info("Banco de dados inicializado ou já existente.")
    else:
        app.logger.error("Falha ao inicializar o banco de dados.")

# Rotas
@app.route("/")
def rota_principal():
    # Obtém os dados da sessão atual
    usuario_sessao = session.get("usuario")
    tipo_usuario = session.get("tipo")

    # Verifica se o usuário está logado corretamente
    if isinstance(usuario_sessao, dict) and "email" in usuario_sessao and tipo_usuario:
        usuario_validado = obter_usuario(usuario_sessao["email"])
        if usuario_validado:
            # Redireciona com base no tipo de usuário
            if tipo_usuario == "cliente":
                return redirect("/painel_cliente")
            elif tipo_usuario == "funcionario":
                return redirect("/painel_funcionario")

    # Se a sessão estiver inválida, limpa e volta à tela inicial
    session.clear()
    return render_template("index.html")

@app.route("/painel_cliente")
def painel_cliente():
    # Verifica se o usuário está logado e é do tipo cliente
    if 'usuario' not in session or session.get('tipo') != 'cliente':
        return redirect("/")

    # Recupera o e-mail do usuário da sessão
    usuario_info = session.get('usuario')
    email_usuario = usuario_info.get('email') if isinstance(usuario_info, dict) else usuario_info

    # Busca os dados do usuário no banco
    usuario = obter_usuario(email_usuario)

    # Se o usuário não for encontrado, limpa a sessão e volta à tela inicial
    if not usuario:
        session.clear()
        return redirect("/")

    # Renderiza o painel do cliente com os dados do usuário
    return render_template("painel_cliente.html", usuario=usuario)

@app.route("/painel_funcionario")
def painel_funcionario():
    # Verifica se há sessão ativa e se o tipo de usuário é funcionário
    if 'usuario' not in session or session.get('tipo') != 'funcionario':
        app.logger.warning(f"Acesso negado ao painel do funcionário: {session.get('usuario')}")
        return redirect(url_for('index'))
    
    # Renderiza o painel do funcionário
    return render_template("painel_funcionario.html")

@app.route("/chat", methods=["POST"])
@limiter.limit("30 per minute")
@csrf.exempt
def processar_chat():
    try:
        # Verifica se a requisição é JSON
        if not request.is_json:
            return jsonify({"resposta": "Requisição deve ser JSON"}), 400

        dados = request.get_json()
        mensagem = dados.get("mensagem", "").strip()

        # Mensagem obrigatória
        if not mensagem:
            return jsonify({"resposta": "Campo 'mensagem' é obrigatório"}), 400

        # Inicializa o email do usuário (real ou temporário)
        email_usuario = None

        # Se já estiver logado, usa o e-mail da sessão
        if 'usuario' in session:
            email_usuario = session["usuario"]["email"]
        else:
            # Tenta identificar se há fluxo de login ou cadastro em andamento
            for email_temp, estado in chatbot.estados.items():
                if estado.get('etapa', '').startswith(('login', 'cadastro')):
                    email_usuario = email_temp
                    break

        # Permite saudações sem login
        if not email_usuario and mensagem.lower() in ['oi', 'olá', 'ola', 'bom dia', 'boa tarde', 'boa noite']:
            return jsonify({"resposta": "Olá! Para continuar, digite 'Login' ou 'Cadastro'."})

        # Inicia fluxo de login/cadastro gerando um email temporário
        if not email_usuario and mensagem.lower() in ['login', 'cadastro']:
            import uuid
            email_usuario = f"temp_{uuid.uuid4().hex[:8]}"

        # Se ainda não há email associado, bloqueia
        if not email_usuario:
            return jsonify({
                "resposta": "Você precisa estar logado para usar o chat. Digite 'Login' ou 'Cadastro'.",
                "redirect": "/"
            }), 403

        # Envia a mensagem para o chatbot
        resposta = chatbot.processar_mensagem(mensagem, email_usuario)

        # Se for uma resposta de login com sucesso
        if isinstance(resposta, dict) and resposta.get('login'):
            usuario = resposta.get('usuario')
            if usuario:
                session['usuario'] = {
                    "email": usuario['email'],
                    "nome": usuario['nome'],
                    "tipo": usuario['tipo']
                }
                session['tipo'] = usuario['tipo']
                session.permanent = True

                # Limpa estado de login temporário
                if email_usuario.startswith('temp_'):
                    chatbot.estados.pop(email_usuario, None)

        # Se for logout, limpa sessão e estado do chatbot
        if isinstance(resposta, dict) and resposta.get('logout'):
            chatbot.estados.pop(email_usuario, None)
            session.clear()

        return jsonify(resposta)

    except Exception as e:
        app.logger.error(f"Erro no /chat: {str(e)}", exc_info=True)
        return jsonify({"resposta": "Erro interno no processamento da mensagem"}), 500
    
@app.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    try:
        # Obtém os dados da requisição JSON
        dados = request.get_json()
        email = dados.get("email", "").strip()
        senha = dados.get("senha", "")

        # Verifica se os campos foram preenchidos
        if not email or not senha:
            return jsonify({"success": False, "mensagem": "Email e senha são obrigatórios."}), 400

        # Autentica no banco de dados
        usuario = autenticar_usuario(email, senha)
        if usuario:
            # Cria a sessão do usuário com estrutura consistente
            session['usuario'] = {
                "email": usuario['email'],
                "nome": usuario['nome'],
                "tipo": usuario['tipo']
            }
            session['tipo'] = usuario['tipo']
            session.permanent = True

            # Remove qualquer estado temporário se houver
            chatbot.estados.pop(email, None)

            app.logger.info(f"Usuário {email} logado com sucesso.")
            return jsonify({
                "success": True,
                "tipo": usuario['tipo'],
                "nome": usuario['nome']
            })
        else:
            # Falha de autenticação
            app.logger.warning(f"Tentativa de login falhou para: {email}")
            return jsonify({"success": False, "mensagem": "Email ou senha incorretos."}), 401

    except Exception as e:
        # Erro inesperado
        app.logger.error(f"Erro no login: {str(e)}", exc_info=True)
        return jsonify({"success": False, "mensagem": "Erro interno do servidor."}), 500


@app.route("/verificar-sessao")
def verificar_sessao():
    # Se usuário está logado, retorna os dados da sessão
    if 'usuario' in session:
        usuario_email = session['usuario']
        usuario_tipo = session['tipo']
        app.logger.info(f"Sessão ativa para: {usuario_email} ({usuario_tipo})")
        return jsonify({
            "logado": True,
            "usuario": usuario_email,
            "tipo": usuario_tipo
        })
    
    # Caso contrário, informa que não há sessão
    app.logger.info("Nenhuma sessão ativa.")
    return jsonify({"logado": False})


@app.route("/logout", methods=["POST"])
def logout():
    usuario_sessao = session.get('usuario')

    # Verifica se há um usuário válido na sessão
    if usuario_sessao and isinstance(usuario_sessao, dict):
        email_logout = usuario_sessao.get("email")

        if email_logout:
            # Remove o estado da conversa associado ao e-mail
            chatbot.estados.pop(email_logout, None)

            # Limpa completamente a sessão
            session.clear()

            app.logger.info(f"Usuário {email_logout} deslogado.")
            return jsonify({"success": True, "mensagem": "Você foi desconectado."})

    # Se não houver sessão ativa
    app.logger.info("Logout solicitado sem usuário logado.")
    return jsonify({"success": False, "mensagem": "Nenhum usuário logado."})

@app.route("/cadastro", methods=["POST"])
@limiter.limit("5 per minute")
def cadastro():
    try:
        dados = request.get_json()
        
        # Dados enviados pelo cliente
        nome = dados.get("nome")
        sexo = dados.get("sexo")
        nacionalidade = dados.get("nacionalidade")
        data_nascimento = dados.get("data_nascimento")
        nome_mae = dados.get("nome_mae")
        cpf = dados.get("cpf")
        email = dados.get("email")
        telefone = dados.get("telefone")
        senha = dados.get("senha")

        # Verifica se todos os campos obrigatórios foram preenchidos
        if not all([nome, sexo, nacionalidade, data_nascimento, nome_mae, cpf, email, senha]):
            return jsonify({"success": False, "mensagem": "Todos os campos obrigatórios devem ser preenchidos."}), 400

        # Valida cada campo
        if not chatbot.validarDado('cpf', cpf):
            return jsonify({"success": False, "mensagem": "CPF inválido."}), 400
        if not chatbot.validarDado('email', email):
            return jsonify({"success": False, "mensagem": "Email inválido."}), 400
        if not chatbot.validarDado('data', data_nascimento):
            return jsonify({"success": False, "mensagem": "Data de nascimento inválida."}), 400
        if not chatbot.validarDado('senha', senha):
            return jsonify({"success": False, "mensagem": "Senha muito curta."}), 400
        if telefone and not chatbot.validarDado('telefone', telefone):
            return jsonify({"success": False, "mensagem": "Telefone inválido."}), 400

        # Verifica se é maior de idade
        data_nasc = datetime.strptime(data_nascimento, '%d/%m/%Y').date()
        hoje = date.today()
        idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
        if idade < 18:
            return jsonify({"success": False, "mensagem": "Você precisa ter pelo menos 18 anos."}), 400

        # Registra no banco
        user_id = cadastrar_usuario(
            nome=nome, sexo=sexo, nacionalidade=nacionalidade, data_nascimento=data_nascimento,
            nome_mae=nome_mae, cpf=cpf, email=email, senha=senha, telefone=telefone
        )

        if user_id:
            usuario = obter_usuario(email)
            session['usuario'] = usuario['email']
            session['tipo'] = usuario['tipo']
            session.permanent = True
            return jsonify({
                "success": True,
                "mensagem": "Cadastro realizado com sucesso!",
                "tipo": usuario['tipo'],
                "nome": usuario['nome']
            }), 201

        return jsonify({"success": False, "mensagem": "Erro ao finalizar cadastro."}), 500

    except ValueError as e:
        return jsonify({"success": False, "mensagem": str(e)}), 409

    except Exception as e:
        app.logger.error(f"Erro no cadastro: {str(e)}", exc_info=True)
        return jsonify({"success": False, "mensagem": "Erro interno ao cadastrar."}), 500

@app.route("/agendamentos/disponiveis", methods=["GET"])
def get_horarios_disponiveis():
    data_str = request.args.get("data")

    if not data_str:
        return jsonify({"error": "Parâmetro 'data' é obrigatório."}), 400

    if not chatbot.validarDado('data', data_str):
        return jsonify({"error": "Formato de data inválido. Use DD/MM/AAAA."}), 400

    try:
        horarios = obter_horarios_disponiveis(data_str)
        return jsonify({"data": data_str, "horarios_disponiveis": horarios})
    except Exception as e:
        app.logger.error(f"Erro ao buscar horários: {str(e)}", exc_info=True)
        return jsonify({"error": "Erro interno ao buscar horários."}), 500

@app.route("/relatorios", methods=["GET"])
def gerar_relatorio():
    if 'usuario' not in session or session.get('tipo') != 'funcionario':
        return jsonify({"error": "Acesso negado. Apenas funcionários podem gerar relatórios."}), 403

    tipo_relatorio = request.args.get("tipo", "completo")
    data_inicio_str = request.args.get("data_inicio")
    data_fim_str = request.args.get("data_fim")

    if not data_inicio_str or not data_fim_str:
        return jsonify({"error": "Datas de início e fim são obrigatórias."}), 400

    if not chatbot.validarDado('data', data_inicio_str) or not chatbot.validarDado('data', data_fim_str):
        return jsonify({"error": "Formato de data inválido. Use DD/MM/AAAA."}), 400

    try:
        data_inicio = datetime.strptime(data_inicio_str, '%d/%m/%Y').strftime('%d/%m/%Y')
        data_fim = datetime.strptime(data_fim_str, '%d/%m/%Y').strftime('%d/%m/%Y')

        if tipo_relatorio == 'estatistico':
            stats = executar_consulta("""
                SELECT status, COUNT(*) as quantidade
                FROM agendamentos
                WHERE data BETWEEN ? AND ?
                GROUP BY status
            """, (data_inicio, data_fim), fetch_all=True)

            servicos = executar_consulta("""
                SELECT servico, COUNT(*) as quantidade
                FROM agendamentos
                WHERE data BETWEEN ? AND ?
                GROUP BY servico
                ORDER BY quantidade DESC
            """, (data_inicio, data_fim), fetch_all=True)

            return jsonify({
                "tipo": "estatistico",
                "periodo": {"inicio": data_inicio, "fim": data_fim},
                "stats_status": stats,
                "stats_servicos": servicos
            })

        else:
            campos = """a.id, a.protocolo, u.nome, u.email, u.cpf, u.telefone,
                        a.servico, a.data, a.horario, a.status, a.observacoes, a.created_at"""

            agendamentos = executar_consulta(f"""
                SELECT {campos}
                FROM agendamentos a
                JOIN usuarios u ON a.usuario_email = u.email
                WHERE a.data BETWEEN ? AND ?
                ORDER BY a.data, a.horario
            """, (data_inicio, data_fim), fetch_all=True)

            return jsonify({
                "tipo": "completo",
                "periodo": {"inicio": data_inicio, "fim": data_fim},
                "total": len(agendamentos),
                "agendamentos": agendamentos
            })

    except Exception as e:
        app.logger.error(f"Erro ao gerar relatório: {str(e)}", exc_info=True)
        return jsonify({"error": "Erro interno ao gerar relatório."}), 500
    
# Rota de status para verificar se o servidor está funcionando
@app.route("/status")
def status():
    return jsonify({"status": "ok"}), 200

# Inicia o servidor Flask
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
