import random
import json
import os
import re
import numpy as np
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash
import tensorflow as tf
from tensorflow.keras.models import load_model
import nltk
from flask import session
from nltk.stem import PorterStemmer
import sqlite3
import pickle

from backend.database import (
    executar_consulta, validar_cpf, validar_data, validar_email, 
    obter_horarios_disponiveis, obter_usuario, obter_agendamentos_usuario, 
    autenticar_usuario, executar_consulta_retorna_id  
)

class Chatbot:
    def __init__(self):
        # Inicializa o chatbot carregando o modelo de IA e as intenções
        self.modelo = None
        self.palavras = []
        self.classes = []
        self.stemmer = PorterStemmer()  # Para reduzir palavras ao radical
        self.estados = {}  # Armazena o estado de cada conversa por usuário
        self.intencoes = {}  # Armazena as intenções carregadas do JSON

        self.carregarModelo()
        self.carregarIntencoes()

    def carregarModelo(self):
        # Carrega o modelo de IA treinado e os arquivos auxiliares
        try:
            modelo_path = 'backend/modelos_salvos/chatbot_model.h5'
            palavras_path = 'backend/modelos_salvos/words.pkl'
            classes_path = 'backend/modelos_salvos/classes.pkl'

            if os.path.exists(modelo_path):
                self.modelo = load_model(modelo_path)
                print("Modelo carregado")

            if os.path.exists(palavras_path):
                with open(palavras_path, 'rb') as f:
                    self.palavras = pickle.load(f)
                print("Lista de palavras carregada")

            if os.path.exists(classes_path):
                with open(classes_path, 'rb') as f:
                    self.classes = pickle.load(f)
                print("Lista de classes carregada")

        except Exception as e:
            print(f"Erro ao carregar modelo: {e}")
            self.modelo = None

    def carregarIntencoes(self):
        # Carrega as intenções do arquivo JSON
        try:
            with open('intents.json', encoding='utf-8') as arquivo:
                self.intencoes = json.load(arquivo)
            return True
        except Exception as e:
            print(f"Erro ao carregar intenções: {e}")
            return False

    def classificarMensagem(self, mensagem: str) -> Optional[str]:
        # Classifica a intenção da mensagem usando o modelo de IA
        if not self.modelo or not self.palavras or not self.classes:
            return None

        try:
            # Pré-processa a mensagem
            tokens = nltk.word_tokenize(mensagem.lower())
            tokens = [self.stemmer.stem(p) for p in tokens]

            # Cria vetor de características
            bag = [1 if palavra in tokens else 0 for palavra in self.palavras]
            entrada = np.array([bag])

            # Faz a predição
            resultado = self.modelo.predict(entrada, verbose=0)
            indice = np.argmax(resultado)
            confianca = resultado[0][indice]

            # Retorna a intenção se a confiança for alta
            if confianca > 0.7:
                intencao = self.classes[indice]
                print(f"Classificado: '{mensagem}' -> {intencao} (confiança: {confianca:.2f})")
                return intencao
                
        except Exception as e:
            print(f"Erro na classificação: {e}")

        return None

    def conversarLivre(self, mensagem: str, email: str) -> dict:
        # Modo de conversação livre com o chatbot
        try:
            print(f"Modo conversação livre ativado para: {email}")
            
            # Verifica se usuário está logado
            usuario = obter_usuario(email) if email else None
            if not usuario:
                return {
                    "resposta": "Para usar o chat, você precisa estar logado. Digite 'login' para entrar.",
                    "modo": "restrito"
                }
            
            mensagem = mensagem.lower().strip()
            
            # Comandos para sair do modo conversação
            if mensagem in ['sair chat', 'voltar menu', 'sair conversa', 'menu']:
                if email in self.estados:
                    if 'modo_conversa' in self.estados[email]:
                        del self.estados[email]['modo_conversa']
                return {
                    "resposta": f"Saindo do chat. Voltando ao menu principal, {usuario['nome'].split()[0]}!",
                    "modo": "sair_conversa"
                }
            
            # Marca que está em modo conversação
            if email not in self.estados:
                self.estados[email] = {}
            self.estados[email]['modo_conversa'] = True
            
            # Tenta classificar com IA primeiro
            intencao = self.classificarMensagem(mensagem)
            
            if intencao:
                resposta = self.obterResposta(intencao, mensagem)
                nome = usuario['nome'].split()[0]
                
                if intencao == 'saudacao':
                    resposta = f"Olá, {nome}! {resposta}"
                
                return {
                    "resposta": resposta,
                    "modo": "conversa_ia",
                    "intencao": intencao,
                    "usuario": nome
                }
            
            # Se IA não classificou, usa fallback
            else:
                resposta = self.respostaPadrao(mensagem, usuario)
                return {
                    "resposta": resposta,
                    "modo": "conversa_fallback",
                    "usuario": usuario['nome'].split()[0]
                }
                
        except Exception as e:
            print(f"Erro no modo conversação: {e}")
            return {
                "resposta": "Desculpe, ocorreu um erro no chat. Tente novamente.",
                "modo": "erro"
            }

    def respostaPadrao(self, mensagem: str, usuario: dict) -> str:
        # Resposta padrão quando a IA não reconhece a mensagem
        mensagem = mensagem.lower().strip()
        nome = usuario['nome'].split()[0]
        
        # Respostas contextuais baseadas em palavras-chave
        respostas = {
            'obrigado': f"Por nada, {nome}! Estou aqui para ajudar.",
            'tchau': f"Até logo, {nome}! Foi um prazer ajudar.",
            'como vai': f"Estou bem, obrigado por perguntar, {nome}!",
            'tudo bem': f"Tudo ótimo aqui, {nome}! E com você?",
            'bom dia': f"Bom dia, {nome}! Como posso ajudar?",
            'boa tarde': f"Boa tarde, {nome}! Em que posso ajudar?",
            'boa noite': f"Boa noite, {nome}! Precisa de algo?"
        }
        
        # Verifica palavras-chave na mensagem
        for palavra, resposta in respostas.items():
            if palavra in mensagem:
                return resposta
        
        # Resposta genérica
        return f"""Interessante pergunta, {nome}!

Posso ajudar com:
- Agendamentos
- Informações sobre documentos
- Horários de atendimento
- Localização
- Contato

Digite 'menu' para opções ou faça sua pergunta."""

    def classificarIntencao(self, mensagem: str) -> str:
        # Classifica a intenção por palavras-chave se a IA falhar
        mensagem = mensagem.lower().strip()
        
        # Tenta classificar com IA primeiro
        intencao = self.classificarMensagem(mensagem)
        if intencao:
            return intencao
        
        # Mapeamento de palavras-chave para intenções
        keywords = {
            'cadastro': ['cadastro', 'registrar', 'criar conta'],
            'login': ['login', 'entrar', 'acessar'],
            'agendar': ['agendar', 'marcar', 'horario', 'consulta'],
            'alterar': ['alterar', 'mudar', 'remarcar'],
            'cancelar': ['cancelar', 'desmarcar'],
            'consultar': ['meus agendamentos', 'ver agendamentos'],
            'documentos': ['documentos', 'papéis', 'necessário'],
            'atendente': ['atendente', 'falar com alguém'],
            'locais': ['local', 'onde', 'endereço'],
            'sair': ['sair', 'logout', 'deslogar']
        }

        # Procura por palavras-chave
        for intencao, palavras in keywords.items():
            if any(p in mensagem for p in palavras):
                return intencao

        return 'desconhecido'

    def obterResposta(self, tag: str) -> str:
        # Obtém uma resposta padrão para uma intenção específica
        if tag in self.intencoes:
            respostas = self.intencoes[tag].get('responses', [])
            if respostas:
                return random.choice(respostas)
        
        # Respostas padrão para cada tipo de intenção
        respostasPadrao = {
            'documentos': """Documentos necessários:
            - CPF original
            - Comprovante de residência
            - Foto 3x4""",
            
            'atendente': """Fale com nosso atendente:
            Telefone: (61) 1234-5678
            WhatsApp: (61) 98765-4321""",
            
            'locais': """Nossos postos:
            - Centro: Rua Principal, 123
            - Bairro: Av. Secundária, 456""",
            
            'desconhecido': """Não entendi. Você pode:
            - Agendar horário
            - Consultar documentos
            - Falar com atendente"""
        }
        
        return respostasPadrao.get(tag, "Como posso ajudar?")

    def validarDado(self, tipo: str, valor: str) -> bool:
        # Valida diferentes tipos de dados
        validadores = {
            'cpf': lambda x: validar_cpf(x),
            'data': lambda x: validar_data(x),
            'email': lambda x: validar_email(x),
            'senha': lambda x: len(x.strip()) >= 6
        }
        return validadores.get(tipo.lower(), lambda x: True)(valor)

    def iniciarEstadoUsuario(self, email: str) -> Dict[str, Any]:
        # Inicializa o estado de conversa para um usuário
        if email not in self.estados:
            self.estados[email] = {"etapa": "inicio", "dados": {}}
        return self.estados[email]

    def obterRespostaPorTag(self, tag: str) -> str:
        # Obtém uma resposta aleatória para uma tag específica das intenções
        try:
            for intent in self.intencoes['intents']:
                if intent['tag'] == tag:
                    respostas = intent.get('responses', [])
                    if respostas:
                        return random.choice(respostas)
            return "Desculpe, não encontrei uma resposta para isso."
        except Exception as e:
            print(f"Erro ao buscar resposta para tag '{tag}': {e}")
            return "Erro ao processar sua solicitação."

    def alterarAgendamento(self, mensagem: str, email: str) -> str:
        # Processa o fluxo de alteração de agendamento
        estado = self.iniciarEstadoUsuario(email)
        
        if estado["etapa"] == "inicial":
            # Lista agendamentos disponíveis para alteração
            agendamentos = executar_consulta(
                "SELECT id, servico, data, horario FROM agendamentos WHERE usuario_email = ? AND status = 'Agendado'",
                (email,), fetch_all=True
            )
            
            if not agendamentos:
                return "Você não possui agendamentos ativos para alterar."
            
            resposta = "Agendamentos disponíveis para alteração:\n\n"
            for ag in agendamentos:
                resposta += f"ID: {ag['id']} - {ag['servico']}\n"
                resposta += f"Data/Hora: {ag['data']} às {ag['horario']}\n\n"
            
            resposta += "Digite o ID do agendamento que deseja alterar:"
            estado["etapa"] = "selecionarAgendamento"
            return resposta
            
        elif estado["etapa"] == "selecionarAgendamento":
            try:
                # Valida o ID do agendamento
                agendamentoId = int(mensagem.strip())
                agendamento = executar_consulta(
                    "SELECT * FROM agendamentos WHERE id = ? AND usuario_email = ? AND status = 'Agendado'",
                    (agendamentoId, email), fetch_one=True
                )
                
                if not agendamento:
                    return "Agendamento não encontrado ou já alterado. Tente novamente:"
                
                # Armazena dados do agendamento
                estado["dados"]["agendamentoId"] = agendamentoId
                estado["dados"]["agendamentoOriginal"] = agendamento
                estado["etapa"] = "novaData"
                return f"Agendamento atual: {agendamento['data']} às {agendamento['horario']}\n\nDigite a nova data (DD/MM/AAAA):"
                
            except ValueError:
                return "ID inválido. Digite apenas números:"
                
        elif estado["etapa"] == "novaData":
            # Valida a nova data
            if not self.validarDado('data', mensagem.strip()):
                return "Data inválida. Use DD/MM/AAAA:"
            
            try:
                dataAgendamento = datetime.strptime(mensagem.strip(), '%d/%m/%Y').date()
                if dataAgendamento <= date.today():
                    return "Data deve ser futura. Digite uma nova data:"
                    
                estado["dados"]["novaData"] = mensagem.strip()
                estado["etapa"] = "novoHorario"
                horarios = obter_horarios_disponiveis(mensagem.strip())
                
                if not horarios:
                    return "Nenhum horário disponível nesta data. Escolha outra data:"
                    
                return f"Horários disponíveis para {mensagem.strip()}:\n{', '.join(horarios)}\n\nEscolha um horário:"
                
            except ValueError:
                return "Data inválida. Use o formato DD/MM/AAAA:"
                
        elif estado["etapa"] == "novoHorario":
            # Valida o novo horário
            if mensagem.strip() not in obter_horarios_disponiveis(estado["dados"]["novaData"]):
                return "Horário indisponível. Escolha outro horário:"
            
            estado["dados"]["novoHorario"] = mensagem.strip()
            estado["etapa"] = "confirmacaoAlteracao"
            
            agendamentoOriginal = estado["dados"]["agendamentoOriginal"]
            return f"""Confirmação de alteração:

Antes:
   Data: {agendamentoOriginal['data']}
   Horário: {agendamentoOriginal['horario']}

Depois:
   Data: {estado['dados']['novaData']}
   Horário: {estado['dados']['novoHorario']}

Digite SIM para confirmar ou NÃO para cancelar:"""
            
        elif estado["etapa"] == "confirmacaoAlteracao":
            # Confirma ou cancela a alteração
            if mensagem.strip().lower() == "sim":
                try:
                    # Atualiza o agendamento no banco

                    executar_consulta(
                        "UPDATE agendamentos SET data = ?, horario = ?, status = 'Agendado' WHERE id = ?",
                        (estado["dados"]["novaData"], estado["dados"]["novoHorario"], 
                         estado["dados"]["agendamentoId"])
                    )
                    del self.estados[email]
                    return f"Agendamento alterado com sucesso!\nNova data: {estado['dados']['novaData']} às {estado['dados']['novoHorario']}"
                except Exception as e:
                    return "Erro ao alterar agendamento. Tente novamente."
            else:
                del self.estados[email]
                return "Alteração cancelada."

    def verAgendaFuncionario(self, email: str) -> str:
        # Exibe a agenda do dia para funcionários
        usuario = obter_usuario(email)
        if not usuario or usuario['tipo'] != 'funcionario':
            return "Acesso negado. Apenas funcionários podem ver a agenda."
        
        hoje = date.today().strftime('%d/%m/%Y')
        agendamentos = executar_consulta(
            """SELECT a.id, u.nome, a.servico, a.horario, a.status, u.email, a.protocolo
               FROM agendamentos a 
               JOIN usuarios u ON a.usuario_email = u.email 
               WHERE a.data = ? 
               ORDER BY a.horario""",
            (hoje,), fetch_all=True
        )
        
        if not agendamentos:
            return f"Nenhum agendamento para hoje ({hoje})."
        
        resposta = f"AGENDA DO DIA - {hoje}\n\n"
        statusEmoji = {
            'Agendado': '⏰',
            'Presente': '✅',
            'Atendido': '☑️',
            'Cancelado': '❌',
            'Faltou': '❌'
        }
        
        for ag in agendamentos:
            emoji = statusEmoji.get(ag['status'], '⏰')
            resposta += (
                f"{emoji} {ag['horario']} - {ag['nome']}\n"
                f"   Serviço: {ag['servico']} | Status: {ag['status']}\n"
                f"   Email: {ag['email']}\n"
                f"   ID: {ag['id']} | Protocolo: {ag.get('protocolo', 'N/A')}\n\n"
            )
        
        return resposta

    def criarAgendamento(self, mensagem: str, email: str) -> str:
        # Processa o fluxo de criação de novo agendamento
        estado = self.estados[email]
        
        if estado["etapa"] == "servico":
            servicos = {
                "cin": "CIN", 
                "crnm": "CRNM", 
                "renovacao cin": "RENOVAÇÃO CIN", 
                "renovacao crnm": "RENOVAÇÃO CRNM"
            }
            
            servico = mensagem.lower().strip()
            if servico not in servicos:
                return "Serviços disponíveis: CIN, CRNM, Renovação CIN, Renovação CRNM"
            
            estado["dados"]["servico"] = servicos[servico]
            estado["etapa"] = "data"
            return "Digite a data desejada (DD/MM/AAAA):"
            
        elif estado["etapa"] == "data":
            if not self.validarDado('data', mensagem.strip()):
                return "Data inválida. Use DD/MM/AAAA:"
            
            try:
                dataAgendamento = datetime.strptime(mensagem.strip(), '%d/%m/%Y').date()
                if dataAgendamento <= date.today():
                    return "Data deve ser futura:"
                
                estado["dados"]["data"] = mensagem.strip()
                estado["etapa"] = "horario"
                horarios = obter_horarios_disponiveis(mensagem.strip())
                
                if not horarios:
                    return "Nenhum horário disponível. Escolha outra data:"
                
                return f"Horários disponíveis: {', '.join(horarios)}\nEscolha um:"
                
            except ValueError:
                return "Data inválida:"
                
        elif estado["etapa"] == "horario":
            if mensagem.strip() not in obter_horarios_disponiveis(estado["dados"]["data"]):
                return "Horário indisponível:"
            
            estado["dados"]["horario"] = mensagem.strip()
            estado["etapa"] = "confirmacao"
            
            return f"""Confirme seu agendamento:
Serviço: {estado['dados']['servico']}
Data: {estado['dados']['data']}
Horário: {estado['dados']['horario']}

Digite SIM para confirmar ou NÃO para cancelar:"""
            
        elif estado["etapa"] == "confirmacao":
            if mensagem.strip().lower() == "sim":
                try:
                    # Cria o agendamento no banco
                    agendamentoId = executar_consulta(
                        "INSERT INTO agendamentos (usuario_email, servico, data, horario) VALUES (?, ?, ?, ?)",
                        (email, estado["dados"]["servico"], estado["dados"]["data"], estado["dados"]["horario"]),
                        fetch_id=True
                    )
                    del self.estados[email]
                    return f"Agendamento realizado!\nProtocolo: CIN-{agendamentoId:06d}"
                    
                except Exception as e:
                    print(f"Erro no agendamento: {e}")
                    return "Erro ao realizar agendamento. Tente novamente."
            else:
                del self.estados[email]
                return "Agendamento cancelado."

    def processar_mensagem(self, mensagem: str, email_usuario: Optional[str] = None) -> dict:
        try:
            msg_limpa = mensagem.lower().strip()

            # Comandos iniciais especiais
            if msg_limpa == 'login':
                self.estados[email_usuario] = {'etapa': 'login_email'}
                return {"resposta": "Vamos iniciar seu login. Qual é o seu e-mail?"}

            elif msg_limpa == 'cadastro':
                self.estados[email_usuario] = {'etapa': 'cadastro_nome'}
                return {"resposta": "Vamos começar o seu cadastro. Qual é o seu nome completo?"}

            elif msg_limpa == 'agendar':
                if not email_usuario:
                    return {"resposta": "Você precisa estar logado para fazer agendamentos. Por favor, digite 'login' ou 'cadastro'."}
                self.estados[email_usuario] = {'etapa': 'agendamento_servico'}
                return {"resposta": "Certo, para agendar, qual serviço você precisa? (ex: 'RG', 'CNH', etc.)"}

            # Inicializa o estado do usuário se não existir
            if email_usuario not in self.estados:
                self.estados[email_usuario] = {'etapa': 'inicio'}

            estado_atual_usuario = self.estados[email_usuario]
            etapa_atual = estado_atual_usuario.get('etapa', 'inicio')

            # DEBUG
            print(f"DEBUG: Email: {email_usuario}, Etapa atual: {etapa_atual}, Mensagem: '{msg_limpa}'")

            # ESTADOS DE CADASTRO 
            if etapa_atual == 'cadastro_nome':
                estado_atual_usuario['nome'] = mensagem
                estado_atual_usuario['etapa'] = 'cadastro_tipo_usuario'
                return {
                    "resposta": "Você é um cliente ou funcionário? Digite 'cliente' ou 'funcionario':",
                    "parametros": {"nome": "preenchido"}
                }

            elif etapa_atual == 'cadastro_tipo_usuario':
                if msg_limpa in ['cliente', 'funcionario']:
                    estado_atual_usuario['tipo_usuario'] = msg_limpa
                    estado_atual_usuario['etapa'] = 'cadastro_sexo'
                    return {
                        "resposta": "Qual é o seu sexo? (masculino/feminino/outro)",
                        "parametros": {"tipo_usuario": "preenchido"}
                    }
                else:
                    return {"resposta": "Por favor, digite 'cliente' ou 'funcionario':"}

            elif etapa_atual == 'cadastro_sexo':
                if msg_limpa in ['masculino', 'feminino', 'outro']:
                    estado_atual_usuario['sexo'] = msg_limpa
                    estado_atual_usuario['etapa'] = 'cadastro_nacionalidade'
                    return {
                        "resposta": "Qual é a sua nacionalidade?",
                        "parametros": {"sexo": "preenchido"}
                    }
                else:
                    return {"resposta": "Por favor, digite 'masculino', 'feminino' ou 'outro':"}

            elif etapa_atual == 'cadastro_nacionalidade':
                estado_atual_usuario['nacionalidade'] = mensagem
                estado_atual_usuario['etapa'] = 'cadastro_data_nascimento'
                return {
                    "resposta": "Qual a sua data de nascimento? (DD/MM/AAAA)",
                    "parametros": {"nacionalidade": "preenchido"}
                }

            elif etapa_atual == 'cadastro_data_nascimento':
                if validar_data(msg_limpa):
                    estado_atual_usuario['data_nascimento'] = msg_limpa
                    estado_atual_usuario['etapa'] = 'cadastro_nome_mae'
                    return {
                        "resposta": "Qual o nome completo da sua mãe?",
                        "parametros": {"data_nascimento": "preenchido"}
                    }
                else:
                    return {"resposta": "Formato de data inválido. Por favor, use DD/MM/AAAA."}

            elif etapa_atual == 'cadastro_nome_mae':
                estado_atual_usuario['nome_mae'] = mensagem
                estado_atual_usuario['etapa'] = 'cadastro_cpf'
                return {
                    "resposta": "Agora, digite seu CPF (apenas números):",
                    "parametros": {"nome_mae": "preenchido"}
                }

            elif etapa_atual == 'cadastro_cpf':
                cpf_limpo = re.sub(r'\D', '', msg_limpa)
                if validar_cpf(cpf_limpo):
                    if executar_consulta("SELECT id FROM usuarios WHERE cpf = ?", (cpf_limpo,), fetch_one=True):
                        return {"resposta": "Este CPF já está cadastrado. Por favor, use outro."}
                    estado_atual_usuario['cpf'] = cpf_limpo
                    estado_atual_usuario['etapa'] = 'cadastro_email'
                    return {
                        "resposta": "Qual o seu melhor e-mail?",
                        "parametros": {"cpf": "preenchido"}
                    }
                else:
                    return {"resposta": "CPF inválido. Por favor, digite apenas os 11 números."}

            elif etapa_atual == 'cadastro_email':
                if validar_email(msg_limpa):
                    if obter_usuario(msg_limpa):
                        return {"resposta": "Este e-mail já está cadastrado. Por favor, use outro."}
                    estado_atual_usuario['email'] = msg_limpa
                    estado_atual_usuario['etapa'] = 'cadastro_senha'
                    return {
                        "resposta": "Crie uma senha para sua conta (mínimo 6 caracteres):",
                        "parametros": {"email": "preenchido"}
                    }
                else:
                    return {"resposta": "E-mail inválido. Por favor, digite um e-mail válido."}

            elif etapa_atual == 'cadastro_senha':
                if len(mensagem) >= 6:
                    estado_atual_usuario['senha'] = mensagem

                    campos_obrigatorios = ['nome', 'sexo', 'nacionalidade', 'data_nascimento', 
                                        'nome_mae', 'cpf', 'email', 'senha', 'tipo_usuario']
                    dados_completos = all(campo in estado_atual_usuario for campo in campos_obrigatorios)

                    if not dados_completos:
                        del self.estados[email_usuario]
                        return {"resposta": "Dados incompletos. Por favor, comece o cadastro novamente."}

                    try:
                        executar_consulta(
                            """INSERT INTO usuarios (nome, sexo, nacionalidade, data_nascimento, nome_mae, cpf, email, senha, tipo)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                estado_atual_usuario['nome'],
                                estado_atual_usuario['sexo'],
                                estado_atual_usuario['nacionalidade'],
                                estado_atual_usuario['data_nascimento'],
                                estado_atual_usuario['nome_mae'],
                                estado_atual_usuario['cpf'],
                                estado_atual_usuario['email'],
                                generate_password_hash(estado_atual_usuario['senha']),
                                estado_atual_usuario['tipo_usuario']
                            ),
                            commit=True
                        )

                        del self.estados[email_usuario]
                        return {
                            "resposta": "Cadastro concluído com sucesso! Faça login para continuar.",
                            "parametros": {"senha": "preenchido"},
                            "redirect": "/"
                        }

                    except sqlite3.IntegrityError as e:
                        if "UNIQUE constraint failed: usuarios.email" in str(e):
                            return {"resposta": "Este e-mail já está cadastrado. Por favor, use outro."}
                        elif "UNIQUE constraint failed: usuarios.cpf" in str(e):
                            return {"resposta": "Este CPF já está cadastrado. Por favor, verifique os dados."}
                        else:
                            print(f"Erro de integridade no cadastro: {e}")
                            return {"resposta": "Erro ao cadastrar. Verifique os dados e tente novamente."}

                    except Exception as e:
                        print(f"Erro ao cadastrar usuário: {e}")
                        del self.estados[email_usuario]
                        return {"resposta": "Ocorreu um erro no cadastro. Por favor, comece novamente."}
                else:
                    return {"resposta": "Senha muito curta. Digite pelo menos 6 caracteres:"}


 # ESTADOS DE LOGIN 
            elif etapa_atual == 'login_email':
                if validar_email(msg_limpa):
                    estado_atual_usuario['login_email'] = msg_limpa
                    estado_atual_usuario['etapa'] = 'login_senha'
                    return {
                        "resposta": "Qual a sua senha?",
                        "parametros": {"email": "preenchido"}
                    }
                else:
                    return {"resposta": "E-mail inválido. Por favor, digite um e-mail válido."}

            elif etapa_atual == 'login_senha':
                email_login = estado_atual_usuario['login_email']
                senha_login = mensagem

                usuario_autenticado = autenticar_usuario(email_login, senha_login)
                if usuario_autenticado:
                    session["usuario"] = {
                        "email": usuario_autenticado["email"],
                        "nome": usuario_autenticado["nome"],
                        "tipo": usuario_autenticado["tipo"]
                    }
                    session["tipo"] = usuario_autenticado["tipo"]

                    tipo_usuario_logado = usuario_autenticado["tipo"]
                    del self.estados[email_usuario]

                    if tipo_usuario_logado == 'cliente':
                        return {
                            "resposta": "Login realizado com sucesso! Bem-vindo(a) ao painel do cliente!",
                            "redirect": "/painel_cliente",
                            "login": True,
                            "usuario": usuario_autenticado,
                            "parametros": {"senha": "preenchido"}
                        }
                    elif tipo_usuario_logado == 'funcionario':
                        return {
                            "resposta": "Login realizado com sucesso! Bem-vindo(a) ao painel do funcionário!",
                            "redirect": "/painel_funcionario",
                            "login": True,
                            "usuario": usuario_autenticado,
                            "parametros": {"senha": "preenchido"}
                        }
                else:
                    self.estados[email_usuario] = {'etapa': 'inicio'}
                    return {"resposta": "E-mail ou senha incorretos. Digite 'login' para tentar novamente."}

            # ESTADOS DE AGENDAMENTO 
            elif etapa_atual == 'agendamento_servico':
                estado_atual_usuario['servico_agendamento'] = mensagem
                estado_atual_usuario['etapa'] = 'agendamento_data'
                return {"resposta": "Para qual data você gostaria de agendar? (DD/MM/AAAA)"}

            elif etapa_atual == 'agendamento_data':
                if validar_data(msg_limpa):
                    data_agendamento = msg_limpa
                    horarios_disponiveis = obter_horarios_disponiveis(data_agendamento)
                    if horarios_disponiveis:
                        estado_atual_usuario['data_agendamento'] = data_agendamento
                        estado_atual_usuario['horarios_disponiveis'] = horarios_disponiveis
                        estado_atual_usuario['etapa'] = 'agendamento_horario'
                        return {
                            "resposta": f"Horários disponíveis para {data_agendamento}: {', '.join(horarios_disponiveis)}. Qual horário você escolhe?"
                        }
                    else:
                        return {"resposta": f"Não há horários disponíveis para {data_agendamento}. Tente outra data."}
                else:
                    return {"resposta": "Formato de data inválido. Por favor, use DD/MM/AAAA."}

            elif etapa_atual == 'agendamento_horario':
                horario_escolhido = msg_limpa
                if horario_escolhido in estado_atual_usuario.get('horarios_disponiveis', []):
                    try:
                        servico = estado_atual_usuario['servico_agendamento']
                        data = estado_atual_usuario['data_agendamento']
                        usuario_email_agendamento = email_usuario

                        import uuid
                        protocolo = str(uuid.uuid4())[:8].upper()

                        novo_agendamento_id = executar_consulta_retorna_id(
                            """INSERT INTO agendamentos 
                            (usuario_email, servico, data, horario, status, protocolo, data_criacao)
                            VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))""",
                            (usuario_email_agendamento, servico, data, horario_escolhido, 'Agendado', protocolo)
                        )

                        if novo_agendamento_id:
                            del self.estados[email_usuario]
                            return {
                                "resposta": f"Agendamento de {servico} para {data} às {horario_escolhido} confirmado!\n🔒 Protocolo: {protocolo}\n🆔 ID: {novo_agendamento_id}"
                            }
                        else:
                            return {"resposta": "Erro ao finalizar agendamento. Por favor, tente novamente."}
                    except Exception as e:
                        print(f"Erro ao criar agendamento: {e}")
                        del self.estados[email_usuario]
                        return {"resposta": "Ocorreu um erro ao agendar. Por favor, tente novamente."}
                else:
                    return {"resposta": "Horário inválido ou não disponível. Por favor, escolha um dos horários listados."}

            elif etapa_atual == 'cancelar_agendamento_id':
                try:
                    agendamento_id = int(msg_limpa)
                    agendamento = executar_consulta(
                        "SELECT status FROM agendamentos WHERE id = ? AND usuario_email = ?",
                        (agendamento_id, email_usuario), fetch_one=True
                    )

                    if not agendamento:
                        return {"resposta": "Agendamento não encontrado ou você não tem permissão para cancelá-lo."}

                    if agendamento['status'] == 'Cancelado':
                        return {"resposta": "Esse agendamento já está cancelado."}
                    
                    executar_consulta(
                        "UPDATE agendamentos SET status = 'Cancelado' WHERE id = ? AND usuario_email = ?",
                        (agendamento_id, email_usuario), commit=True
                    )
                    del self.estados[email_usuario]
                    return {"resposta": "Agendamento cancelado com sucesso!"}

                except ValueError:
                    return {"resposta": "Por favor, digite um ID de agendamento válido (apenas números)."}
                except Exception as e:
                    print(f"Erro ao cancelar agendamento: {e}")
                    return {"resposta": "Ocorreu um erro ao cancelar. Tente novamente."}

            # ESTADOS DE ALTERAÇÃO DE AGENDAMENTO 
            elif etapa_atual == 'alterar_agendamento_id':
                try:
                    agendamento_id = int(msg_limpa)
                    agendamento = executar_consulta(
                        "SELECT * FROM agendamentos WHERE id = ? AND usuario_email = ?",
                        (agendamento_id, email_usuario), fetch_one=True
                    )
                    if agendamento:
                        estado_atual_usuario['agendamento_alterar'] = agendamento
                        estado_atual_usuario['etapa'] = 'alterar_agendamento_opcao'
                        return {"resposta": f"Agendamento encontrado: {agendamento['servico']} em {agendamento['data']} às {agendamento['horario']}\n\nO que deseja alterar?\n1 - Data\n2 - Horário\n3 - Cancelar alteração"}
                    else:
                        return {"resposta": "Agendamento não encontrado ou você não tem permissão para alterá-lo."}
                except ValueError:
                    return {"resposta": "Por favor, digite um ID de agendamento válido (apenas números)."}

            elif etapa_atual == 'alterar_agendamento_opcao':
                if msg_limpa == '1':
                    estado_atual_usuario['etapa'] = 'alterar_agendamento_nova_data'
                    return {"resposta": "Digite a nova data (DD/MM/AAAA):"}
                elif msg_limpa == '2':
                    estado_atual_usuario['etapa'] = 'alterar_agendamento_novo_horario'
                    agendamento = estado_atual_usuario['agendamento_alterar']
                    horarios = obter_horarios_disponiveis(agendamento['data'])
                    return {"resposta": f"Horários disponíveis para {agendamento['data']}: {', '.join(horarios)}. Escolha um:"}
                elif msg_limpa == '3':
                    del self.estados[email_usuario]
                    return {"resposta": "Alteração cancelada."}
                else:
                    return {"resposta": "Opção inválida. Digite 1, 2 ou 3."}

            elif etapa_atual == 'alterar_agendamento_nova_data':
                if validar_data(msg_limpa):
                    horarios = obter_horarios_disponiveis(msg_limpa)
                    if horarios:
                        estado_atual_usuario['nova_data'] = msg_limpa
                        estado_atual_usuario['horarios_nova_data'] = horarios
                        estado_atual_usuario['etapa'] = 'alterar_agendamento_novo_horario_nova_data'
                        return {"resposta": f"Horários disponíveis para {msg_limpa}: {', '.join(horarios)}. Escolha um:"}
                    else:
                        return {"resposta": f"Não há horários disponíveis para {msg_limpa}. Tente outra data."}
                else:
                    return {"resposta": "Formato de data inválido. Por favor, use DD/MM/AAAA."}

            elif etapa_atual == 'alterar_agendamento_novo_horario' or etapa_atual == 'alterar_agendamento_novo_horario_nova_data':
                agendamento = estado_atual_usuario['agendamento_alterar']
                
                if etapa_atual == 'alterar_agendamento_novo_horario_nova_data':
                    # Alterando data e horário
                    nova_data = estado_atual_usuario['nova_data']
                    horarios_disponiveis = estado_atual_usuario['horarios_nova_data']
                else:
                    # Alterando apenas horário
                    nova_data = agendamento['data']
                    horarios_disponiveis = obter_horarios_disponiveis(nova_data)

                if msg_limpa in horarios_disponiveis:
                    try:
                        executar_consulta(
                            "UPDATE agendamentos SET data = ?, horario = ? WHERE id = ?",
                            (nova_data, msg_limpa, agendamento['id']), commit=True
                        )
                        del self.estados[email_usuario]
                        return {"resposta": f"Agendamento alterado com sucesso!\nNova data: {nova_data}\nNovo horário: {msg_limpa}"}
                    except Exception as e:
                        print(f"Erro ao alterar agendamento: {e}")
                        del self.estados[email_usuario]
                        return {"resposta": "Erro ao alterar agendamento. Tente novamente."}
                else:
                    return {"resposta": "Horário inválido. Escolha um dos horários disponíveis."}

            # ESTADOS DE RELATÓRIOS PARA FUNCIONÁRIOS 
            elif etapa_atual == 'relatorio_menu':
                if msg_limpa == '1':
                    del self.estados[email_usuario]
                    return {"resposta": self.processarAgendaFuncionario(email_usuario)}
                elif msg_limpa == '2':
                    del self.estados[email_usuario]
                    return {"resposta": self.gerarRelatorioComparecimento()}
                elif msg_limpa == '3':
                    del self.estados[email_usuario]
                    return {"resposta": self.gerarRelatorioComparecimento()}
                elif msg_limpa == 'sair':
                    del self.estados[email_usuario]
                    return {"resposta": "Operação cancelada."}
                else:
                    tentativas = estado_atual_usuario.get('tentativas', 0) + 1
                    if tentativas > 2:
                        del self.estados[email_usuario]
                        return {"resposta": "Muitas tentativas inválidas. Operação cancelada."}
                    estado_atual_usuario['tentativas'] = tentativas
                    return {"resposta": "Opção inválida. Digite 1, 2, 3 ou 'sair'."}

            # ESTADOS FINAIS - CLASSIFICAÇÃO DE INTENÇÃO 
            # Se chegou até aqui, não está em nenhum estado específico, então classifica a intenção
            intencao = self.classificarIntencao(msg_limpa)

            # Verificar se é funcionário e processar comandos específicos
            usuario_logado = obter_usuario(email_usuario) if email_usuario else None
            if usuario_logado and usuario_logado['tipo'] == 'funcionario':
                if intencao == "agenda_funcionario" or msg_limpa in ['ver agenda', 'agenda']:
                    resposta = self.processarAgendaFuncionario(email_usuario)
                    return {"resposta": resposta}
                elif intencao == "confirmar_presenca" or msg_limpa.startswith('confirmar '):
                    partes = mensagem.split()
                    if len(partes) >= 2:
                        if 'presença' in partes and len(partes) >= 3:
                            identificador = partes[2]
                        else:
                            identificador = partes[1]

                        resposta = self.confirmarPresenca(identificador, email_usuario)
                        return {"resposta": resposta}
                    else:
                        return {"resposta": "Formato: 'confirmar [email_cliente]' ou 'confirmar [id_agendamento]'"}


                elif intencao == "gerar_relatorio" or msg_limpa in ['gerar relatório', 'gerar relatorio', 'relatório', 'relatorio']:
                    self.estados[email_usuario] = {'etapa': 'relatorio_menu', 'tentativas': 0}
                    return {"resposta": """RELATÓRIOS DISPONÍVEIS (digite o número):

    1. Agenda Diária - Lista completa de atendimentos do dia
    2. Confirmados x Faltas - Estatísticas de comparecimento
    3. Serviços Mais Demandados - Ranking dos últimos 30 dias

    Ou digite 'sair' para cancelar"""}
                elif intencao == "buscarCliente" or msg_limpa.startswith('buscar cliente '):
                    partes = mensagem.split()
                    if len(partes) >= 3:
                        identificador = partes[2]
                        cliente = self.buscarCliente(identificador)
                        if cliente:
                            return {"resposta": f"Cliente encontrado:\nNome: {cliente['nome']}\nEmail: {cliente['email']}\nCPF: {cliente['cpf']}"}
                        return {"resposta": "Cliente não encontrado."}
                    return {"resposta": "Formato: 'buscar cliente [CPF/email]'"}

            # Lógica para tratamento de intenções gerais
            if intencao == "saudacao":
                nome_usuario = ""
                if email_usuario and obter_usuario(email_usuario):
                    user_data = obter_usuario(email_usuario)
                    nome_usuario = user_data['nome'].split(' ')[0]
                return {"resposta": f"Olá{', ' + nome_usuario if nome_usuario else ''}! Como posso ajudar?\n\nOpções disponíveis:\n• Cadastro\n• Login\n• Agendamento\n• Meus agendamentos\n• Alterar agendamento\n• Documentos necessários"}

            elif intencao == "cadastro_inicio":
                self.estados[email_usuario] = {'etapa': 'cadastro_nome'}
                return {"resposta": "Vamos começar seu cadastro. Qual é o seu nome completo?"}

            elif intencao == "login_inicio":
                self.estados[email_usuario] = {'etapa': 'login_email'}
                return {"resposta": "Para fazer login, qual o seu e-mail?"}

            elif intencao == "iniciar_agendamento":
                if not email_usuario or not obter_usuario(email_usuario):
                    return {"resposta": "Você precisa estar logado para fazer agendamentos. Por favor, digite 'login' ou 'cadastro'."}
                
                self.estados[email_usuario] = {"etapa": "agendamento_servico"}
                return {"resposta": "Certo, para agendar, qual serviço você precisa? (ex: RG, CNH)"}

            
            elif intencao == "meus_agendamentos":
                if not email_usuario:
                    return {"resposta": "Você precisa estar logado para ver seus agendamentos."}

                agendamentos = obter_agendamentos_usuario(email_usuario)

                if agendamentos:
                    lista_agendamentos = " Seus agendamentos:\n\n"
                    for ag in agendamentos:
                        lista_agendamentos += (
                            f"ID: {ag['id']}\n"
                            f"Protocolo: {ag.get('protocolo', 'N/A')}\n"
                            f"Serviço: {ag['servico']}\n"
                            f"Data: {ag['data']}\n"
                            f"Hora: {ag['horario']}\n"
                            f"Status: {ag['status']}\n"
                            f"{'─' * 30}\n"
                        )
                    return {"resposta": lista_agendamentos}
                else:
                    return {"resposta": "Você não possui agendamentos. Deseja 'agendar' um serviço?"}

            elif intencao == "cancelar_agendamento":
                if not email_usuario or not obter_usuario(email_usuario):
                    return {"resposta": "Você precisa estar logado para cancelar agendamentos."}
                self.estados[email_usuario]['etapa'] = 'cancelar_agendamento_id'
                return {"resposta": "Para cancelar um agendamento, por favor, digite o ID do agendamento:"}

            elif intencao == "alterar_agendamento":
                if not email_usuario or not obter_usuario(email_usuario):
                    return {"resposta": "Você precisa estar logado para alterar agendamentos."}
                self.estados[email_usuario]['etapa'] = 'alterar_agendamento_id'
                return {"resposta": "Para alterar um agendamento, por favor, digite o ID do agendamento que deseja modificar:"}

            elif intencao == "documentos_necessarios":
                return {"resposta": self.obterRespostaPorTag("documentos_necessarios")}

            elif intencao == "falar_atendente":
                return {"resposta": self.obterRespostaPorTag("falar_atendente")}

            elif intencao == "locais_disponiveis":
                return {"resposta": self.obterRespostaPorTag("locais_disponiveis")}

            elif intencao == "logout":
                if email_usuario in self.estados:
                    del self.estados[email_usuario]
                return {
                    "resposta": "Você foi desconectado. Até mais!",
                    "logout": True,
                    "redirect": "/"  
                }

            # Intenção desconhecida
            for intent in self.intencoes.get("intents", []):
                            if intent["tag"] == intencao:
                                respostas = intent.get("responses", [])
                                if respostas:
                                    return {"resposta": random.choice(respostas)}

            # Intenção desconhecida
            return {"resposta": self.obterRespostaPorTag("desconhecido")}

        except Exception as e:
            print(f"ERRO no processar_mensagem: {str(e)}")
            return {"resposta": "Ocorreu um erro ao processar sua mensagem"}

    def processarAgendaFuncionario(self, emailFuncionario: str) -> str:
        try:
            hoje = date.today().strftime('%d/%m/%Y')
            agendamentos = executar_consulta(
                """SELECT a.id, u.nome, a.servico, a.horario, a.status, u.email, a.protocolo
                FROM agendamentos a 
                JOIN usuarios u ON a.usuario_email = u.email 
                WHERE a.data = ? 
                ORDER BY a.horario""",
                (hoje,), fetchAll=True
            )
            
            if not agendamentos:
                return f"Nenhum agendamento para hoje ({hoje})."
            
            resposta = f"AGENDA DO DIA - {hoje}\n\n"
            statusEmoji = {
                'Agendado': '🕐',
                'Presente': '✅',
                'Atendido': '👍',
                'Cancelado': '❌',
                'Faltou': '❗'
            }
            
            for ag in agendamentos:
                emoji = statusEmoji.get(ag['status'], '🕐')
                resposta += (
                    f"{ag['horario']} - {ag['nome']}\n"
                    f"   Serviço: {ag['servico']}\n"
                    f"   Email: {ag['email']}\n"
                    f"   Status: {emoji} {ag['status']}\n"
                    f"   ID: {ag['id']}\n"
                    f"   Protocolo: {ag['protocolo']}\n\n"
                )
            
            return resposta
        except Exception as e:
            print(f"Erro ao processar agenda: {e}")
            return "Erro ao carregar agenda. Tente novamente."

    def confirmarPresenca(self, identificador: str, emailFuncionario: str) -> str:
        try:
            hoje = date.today().strftime('%d/%m/%Y')

            if identificador.isdigit():
                agendamento = executar_consulta(
                    """SELECT a.id, u.nome, a.servico, a.horario, a.status 
                       FROM agendamentos a
                       JOIN usuarios u ON a.usuario_email = u.email
                       WHERE a.id = ? AND a.data = ? AND a.status != 'Presente'""",
                    (int(identificador), hoje), fetchOne=True
                )
            else:
                identificador = identificador.strip().lower()
                agendamento = executar_consulta(
                    """SELECT a.id, u.nome, a.servico, a.horario, a.status 
                       FROM agendamentos a
                       JOIN usuarios u ON a.usuario_email = u.email
                       WHERE u.email = ? AND a.data = ? AND a.status != 'Presente'""",
                    (identificador, hoje), fetchOne=True
                )

            if not agendamento:
                return f"Nenhum agendamento pendente de presença para '{identificador}' hoje ({hoje})."

            executar_consulta(
                "UPDATE agendamentos SET status = 'Presente' WHERE id = ?",
                (agendamento['id'],), commit=True
            )

            return (
                f"✅ Presença confirmada com sucesso!\n"
                f"Cliente: {agendamento['nome']}\n"
                f"Serviço: {agendamento['servico']}\n"
                f"Horário: {agendamento['horario']}\n"
                f"ID Agendamento: {agendamento['id']}"
            )

        except Exception as e:
            print(f"Erro ao confirmar presença: {e}")
            return "Erro ao confirmar presença. Tente novamente."

    def buscarCliente(self, identificador: str) -> dict:
        try:
            if '@' in identificador:
                return executar_consulta(
                    "SELECT nome, email, cpf FROM usuarios WHERE email = ?",
                    (identificador.lower(),), fetchOne=True
                )
            else:
                cpfLimpo = re.sub(r'\D', '', identificador)
                if len(cpfLimpo) == 11:
                    return executar_consulta(
                        "SELECT nome, email, cpf FROM usuarios WHERE cpf = ?",
                        (cpfLimpo,), fetchOne=True
                    )
                return None
        except Exception as e:
            print(f"Erro ao buscar cliente: {e}")
            return None

    def gerarRelatorioComparecimento(self) -> str:
        try:
            relatorio = executar_consulta(
                """SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'Presente' THEN 1 ELSE 0 END) as presentes,
                    SUM(CASE WHEN status = 'Faltou' OR status = 'Cancelado' THEN 1 ELSE 0 END) as ausencias
                FROM agendamentos 
                WHERE date(substr(data, 7, 4) || '-' || substr(data, 4, 2) || '-' || substr(data, 1, 2)) 
                    >= date('now', '-30 days')""",
                fetchOne=True
            )
            
            if relatorio and relatorio['total'] > 0:
                taxaComparecimento = (relatorio['presentes'] / relatorio['total']) * 100
                return (
                    f"RELATÓRIO DE COMPARECIMENTO (Últimos 30 dias)\n\n"
                    f"Total de agendamentos: {relatorio['total']}\n"
                    f"Presentes confirmados: {relatorio['presentes']}\n"
                    f"Ausências: {relatorio['ausencias']}\n"
                    f"Taxa de comparecimento: {taxaComparecimento:.1f}%\n"
                )
            return "Nenhum dado de comparecimento nos últimos 30 dias."
        except Exception as e:
            print(f"Erro ao gerar relatório: {e}")
            return "Erro ao gerar relatório. Tente novamente."

    def gerarRelatorioServicos(self) -> str:
        try:
            servicos = executar_consulta(
                """SELECT servico, COUNT(*) as quantidade
                FROM agendamentos 
                WHERE date(substr(data, 7, 4) || '-' || substr(data, 4, 2) || '-' || substr(data, 1, 2)) 
                    >= date('now', '-30 days')
                GROUP BY servico 
                ORDER BY quantidade DESC 
                LIMIT 10""",
                fetchAll=True
            )
            
            if servicos:
                relatorio = ["SERVIÇOS MAIS DEMANDADOS (Últimos 30 dias)\n"]
                for i, servico in enumerate(servicos, 1):
                    medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    relatorio.append(f"{medalha} {servico['servico']}: {servico['quantidade']}")
                return "\n".join(relatorio)
            return "Nenhum serviço agendado nos últimos 30 dias."
        except Exception as e:
            print(f"Erro ao gerar relatório: {e}")
            return "Erro ao gerar relatório. Tente novamente."