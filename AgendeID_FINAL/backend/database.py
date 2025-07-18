import sqlite3
import re
from datetime import datetime
from contextlib import contextmanager
from typing import Any, Optional, Union, List, Dict
from werkzeug.security import check_password_hash, generate_password_hash

# Caminho do banco de dados
BANCO_DADOS = 'banco.db'

# Gerenciador de conexão com o banco de dados
@contextmanager
def obter_conexao():
    conexao = None
    try:
        conexao = sqlite3.connect(BANCO_DADOS)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        yield conexao
    except sqlite3.Error as erro:
        print(f"Erro no banco: {erro}")
        if conexao:
            conexao.rollback()
        raise
    finally:
        if conexao:
            conexao.close()

# Criação das tabelas do banco de dados

def criar_banco() -> bool:
    try:
        with obter_conexao() as conexao:
            cursor = conexao.cursor()

            # Tabela de usuários
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    sexo TEXT NOT NULL,
                    nacionalidade TEXT NOT NULL,
                    data_nascimento TEXT NOT NULL,
                    nome_mae TEXT NOT NULL,
                    cpf TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    senha TEXT NOT NULL,
                    telefone TEXT,
                    tipo TEXT DEFAULT 'cliente',
                    ativo BOOLEAN DEFAULT 1,
                    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Tabela de agendamentos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agendamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_email TEXT NOT NULL,
                    servico TEXT NOT NULL,
                    data TEXT NOT NULL,
                    horario TEXT NOT NULL,
                    status TEXT DEFAULT 'Agendado',
                    protocolo TEXT UNIQUE,
                    observacoes TEXT,
                    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_email) REFERENCES usuarios(email) ON DELETE CASCADE
                );
            """)

            conexao.commit()
            return True
    except sqlite3.Error as erro:
        print(f"Erro ao criar banco: {erro}")
        return False

def autenticar_usuario(email: str, senha: str) -> Optional[Dict[str, Any]]:
    with obter_conexao() as conexao:
        usuario = conexao.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        if usuario and check_password_hash(usuario['senha'], senha):
            return dict(usuario)
    return None

# Obter dados do usuário

def obter_usuario(email: str) -> Optional[Dict[str, Any]]:
    with obter_conexao() as conexao:
        usuario = conexao.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        return dict(usuario) if usuario else None

# Executar consulta genérica

def executar_consulta(query, params=None, fetch_one=False, fetch_all=False, fetchAll=False, fetchOne=False, commit=True):
    fetch_one = fetch_one or fetchOne
    fetch_all = fetch_all or fetchAll

    conn = sqlite3.connect("banco.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if commit:
            conn.commit()

        if query.strip().lower().startswith("select"):
            if fetch_one:
                resultado = cursor.fetchone()
                return dict(resultado) if resultado else None
            elif fetch_all:
                return [dict(linha) for linha in cursor.fetchall()]
        return True
    except Exception as e:
        print(f"Erro ao executar consulta: {e}")
        return None
    finally:
        conn.close()

# Executar consulta e retornar ID inserido

def executar_consulta_retorna_id(query: str, parametros: tuple = ()) -> Optional[int]:
    with obter_conexao() as conexao:
        try:
            cursor = conexao.cursor()
            cursor.execute(query, parametros)
            conexao.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Erro ao executar consulta com retorno de ID: {e}")
            return None

# Obter horários disponíveis para agendamento

def obter_horarios_disponiveis(data_str: str) -> List[str]:
    data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
    horarios_totais = [f"{h:02d}:00" for h in range(8, 17)]

    with obter_conexao() as conexao:
        resultados = conexao.execute(
            """
            SELECT horario FROM agendamentos
            WHERE data = ? AND status IN ('Agendado', 'Presente', 'Atendido')
            """,
            (data_obj.strftime('%d/%m/%Y'),)
        ).fetchall()

        horarios_ocupados = [linha['horario'] for linha in resultados]
        return [hora for hora in horarios_totais if hora not in horarios_ocupados]

# Obter agendamentos do usuário

def obter_agendamentos_usuario(email: str) -> List[Dict[str, Any]]:
    with obter_conexao() as conexao:
        resultados = conexao.execute(
            """
            SELECT id, servico, data, horario, status, protocolo
            FROM agendamentos WHERE usuario_email = ?
            ORDER BY data, horario
            """,
            (email,)
        ).fetchall()
        return [dict(linha) for linha in resultados]

# Cadastro de novo usuário

def cadastrar_usuario(nome: str, sexo: str, nacionalidade: str, data_nascimento: str, nome_mae: str, cpf: str, email: str, senha: str, telefone: Optional[str] = None, tipo: str = 'cliente') -> Optional[int]:
    senha_criptografada = generate_password_hash(senha)
    try:
        return executar_consulta_retorna_id(
            """
            INSERT INTO usuarios (nome, sexo, nacionalidade, data_nascimento, nome_mae, cpf, email, senha, telefone, tipo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (nome, sexo, nacionalidade, data_nascimento, nome_mae, cpf, email, senha_criptografada, telefone, tipo)
        )
    except sqlite3.IntegrityError as e:
        if "cpf" in str(e):
            raise ValueError("CPF já cadastrado.")
        elif "email" in str(e):
            raise ValueError("Email já cadastrado.")
        else:
            raise

# Agendar serviço para o usuário

def agendar_servico(email_usuario: str, servico: str, data: str, horario: str, protocolo: str, observacoes: Optional[str] = None) -> Optional[int]:
    try:
        return executar_consulta_retorna_id(
            """
            INSERT INTO agendamentos (usuario_email, servico, data, horario, protocolo, observacoes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (email_usuario, servico, data, horario, protocolo, observacoes)
        )
    except sqlite3.IntegrityError as e:
        if "protocolo" in str(e):
            raise ValueError("Protocolo de agendamento já existe.")
        else:
            raise

# Atualizar status de um agendamento

def atualizar_status_agendamento(agendamento_id: int, status: str, email_usuario: str = None) -> bool:
    with obter_conexao() as conexao:
        sql = "UPDATE agendamentos SET status = ? WHERE id = ?"
        parametros = [status, agendamento_id]
        if email_usuario:
            sql += " AND usuario_email = ?"
            parametros.append(email_usuario)

        cursor = conexao.execute(sql, tuple(parametros))
        conexao.commit()
        return cursor.rowcount > 0

# Alterar data e horário de um agendamento

def alterar_agendamento(agendamento_id: int, nova_data: str, novo_horario: str, email_usuario: str = None) -> bool:
    with obter_conexao() as conexao:
        sql = "UPDATE agendamentos SET data = ?, horario = ?, status = 'Agendado' WHERE id = ?"
        parametros = [nova_data, novo_horario, agendamento_id]
        if email_usuario:
            sql += " AND usuario_email = ?"
            parametros.append(email_usuario)

        cursor = conexao.execute(sql, tuple(parametros))
        conexao.commit()
        return cursor.rowcount > 0

# Validar CPF

def validar_cpf(cpf: str) -> bool:
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    def calcular_digito(cpf_parcial, peso):
        soma = sum(int(digito) * (peso - i) for i, digito in enumerate(cpf_parcial))
        resto = 11 - (soma % 11)
        return 0 if resto > 9 else resto

    digito1 = calcular_digito(cpf[:9], 10)
    digito2 = calcular_digito(cpf[:10], 11)

    return cpf[-2:] == f"{digito1}{digito2}"

# Validar data

def validar_data(data_str: str) -> bool:
    try:
        datetime.strptime(data_str, '%d/%m/%Y')
        return True
    except ValueError:
        return False

# Validar e-mail

def validar_email(email: str) -> bool:
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None
