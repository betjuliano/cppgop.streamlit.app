import streamlit as st
import pandas as pd
import sqlite3
import os
import hashlib
import datetime
from enum import Enum
import random
import string
from PIL import Image

# Configuração da página
st.set_page_config(
    page_title="Sistema de Gestão de Alunos - PPGOP",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Definição de enums
class TipoAproveitamento(str, Enum):
    DISCIPLINA = 'disciplina'
    IDIOMA = 'idioma'

class StatusAproveitamento(str, Enum):
    SOLICITADO = 'solicitado'
    APROVADO_COORDENACAO = 'aprovado_coordenacao'
    APROVADO_COLEGIADO = 'aprovado_colegiado'
    DEFERIDO = 'deferido'
    INDEFERIDO = 'indeferido'

# Funções de banco de dados
def init_db():
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    # Tabela de usuários
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    ''')
    
    # Tabela de alunos
    c.execute('''
    CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY,
        matricula TEXT UNIQUE,
        nome TEXT NOT NULL,
        email TEXT NOT NULL,
        orientador TEXT,
        linha_pesquisa TEXT,
        data_ingresso DATE NOT NULL,
        prazo_defesa_projeto DATE,
        prazo_defesa_tese DATE,
        data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Tabela de aproveitamentos
    c.execute('''
    CREATE TABLE IF NOT EXISTS aproveitamentos (
        id INTEGER PRIMARY KEY,
        aluno_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        numero_processo TEXT UNIQUE,
        status TEXT DEFAULT 'solicitado',
        nome_disciplina TEXT,
        codigo_disciplina TEXT,
        creditos INTEGER,
        idioma TEXT,
        nota REAL,
        instituicao TEXT,
        observacoes TEXT,
        link_documentos TEXT,
        data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_aprovacao_coordenacao TIMESTAMP,
        data_aprovacao_colegiado TIMESTAMP,
        data_deferimento TIMESTAMP,
        FOREIGN KEY (aluno_id) REFERENCES alunos (id)
    )
    ''')
    
    # Inserir usuários padrão se não existirem
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'Breno'")
    if c.fetchone()[0] == 0:
        password_hash = hashlib.sha256('adm123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                 ('Breno', 'breno@ppgop.ufsm.br', password_hash))
    
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'PPGOP'")
    if c.fetchone()[0] == 0:
        password_hash = hashlib.sha256('123curso'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                 ('PPGOP', 'ppgop@ufsm.br', password_hash))
    
    conn.commit()
    conn.close()

# Função para gerar número de processo
def gerar_numero_processo():
    """Gera um número de processo no formato 23081.XXXXXX/ANO-XX"""
    ano_atual = datetime.datetime.now().year
    numero = ''.join(random.choices(string.digits, k=6))
    sequencial = ''.join(random.choices(string.digits, k=2))
    return f"23081.{numero}/{ano_atual}-{sequencial}"

# Funções de autenticação
def login(username, password):
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT id, username, email FROM users WHERE username = ? AND password_hash = ?",
             (username, password_hash))
    user = c.fetchone()
    
    conn.close()
    
    if user:
        return {'id': user[0], 'username': user[1], 'email': user[2]}
    return None

# Funções CRUD para alunos
def get_alunos():
    conn = sqlite3.connect('ppgop.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM alunos ORDER BY nome")
    alunos = [dict(row) for row in c.fetchall()]
    
    conn.close()
    return alunos

def get_aluno(aluno_id):
    conn = sqlite3.connect('ppgop.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM alunos WHERE id = ?", (aluno_id,))
    aluno = c.fetchone()
    
    conn.close()
    return dict(aluno) if aluno else None

def save_aluno(aluno_data, aluno_id=None):
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    if aluno_id:  # Atualizar
        c.execute("""
        UPDATE alunos SET 
            matricula = ?,
            nome = ?,
            email = ?,
            orientador = ?,
            linha_pesquisa = ?,
            data_ingresso = ?,
            prazo_defesa_projeto = ?,
            prazo_defesa_tese = ?,
            data_atualizacao = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (
            aluno_data['matricula'],
            aluno_data['nome'],
            aluno_data['email'],
            aluno_data['orientador'],
            aluno_data['linha_pesquisa'],
            aluno_data['data_ingresso'],
            aluno_data['prazo_defesa_projeto'],
            aluno_data['prazo_defesa_tese'],
            aluno_id
        ))
    else:  # Inserir
        c.execute("""
        INSERT INTO alunos (
            matricula, nome, email, orientador, linha_pesquisa, 
            data_ingresso, prazo_defesa_projeto, prazo_defesa_tese
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            aluno_data['matricula'],
            aluno_data['nome'],
            aluno_data['email'],
            aluno_data['orientador'],
            aluno_data['linha_pesquisa'],
            aluno_data['data_ingresso'],
            aluno_data['prazo_defesa_projeto'],
            aluno_data['prazo_defesa_tese']
        ))
    
    conn.commit()
    conn.close()

def delete_aluno(aluno_id):
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    # Verificar se existem aproveitamentos relacionados
    c.execute("SELECT COUNT(*) FROM aproveitamentos WHERE aluno_id = ?", (aluno_id,))
    if c.fetchone()[0] > 0:
        conn.close()
        return False
    
    c.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
    conn.commit()
    conn.close()
    return True

# Funções CRUD para aproveitamentos
def get_aproveitamentos():
    conn = sqlite3.connect('ppgop.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
    SELECT a.*, b.nome as aluno_nome 
    FROM aproveitamentos a
    JOIN alunos b ON a.aluno_id = b.id
    ORDER BY a.data_solicitacao DESC
    """)
    aproveitamentos = [dict(row) for row in c.fetchall()]
    
    conn.close()
    return aproveitamentos

def get_aproveitamento(aproveitamento_id):
    conn = sqlite3.connect('ppgop.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
    SELECT a.*, b.nome as aluno_nome 
    FROM aproveitamentos a
    JOIN alunos b ON a.aluno_id = b.id
    WHERE a.id = ?
    """, (aproveitamento_id,))
    aproveitamento = c.fetchone()
    
    conn.close()
    return dict(aproveitamento) if aproveitamento else None

def save_aproveitamento(aproveitamento_data, aproveitamento_id=None):
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    if aproveitamento_id:  # Atualizar
        # Verificar status anterior
        c.execute("SELECT status FROM aproveitamentos WHERE id = ?", (aproveitamento_id,))
        status_anterior = c.fetchone()[0]
        
        # Preparar campos para atualização
        fields = [
            "aluno_id = ?",
            "tipo = ?",
            "instituicao = ?",
            "observacoes = ?",
            "link_documentos = ?",
            "status = ?"
        ]
        params = [
            aproveitamento_data['aluno_id'],
            aproveitamento_data['tipo'],
            aproveitamento_data['instituicao'],
            aproveitamento_data['observacoes'],
            aproveitamento_data['link_documentos'],
            aproveitamento_data['status']
        ]
        
        # Adicionar campos específicos por tipo
        if aproveitamento_data['tipo'] == TipoAproveitamento.DISCIPLINA:
            fields.extend([
                "nome_disciplina = ?",
                "codigo_disciplina = ?",
                "creditos = ?"
            ])
            params.extend([
                aproveitamento_data['nome_disciplina'],
                aproveitamento_data['codigo_disciplina'],
                aproveitamento_data['creditos']
            ])
        elif aproveitamento_data['tipo'] == TipoAproveitamento.IDIOMA:
            fields.extend([
                "idioma = ?",
                "nota = ?"
            ])
            params.extend([
                aproveitamento_data['idioma'],
                aproveitamento_data['nota']
            ])
        
        # Atualizar datas com base no status
        if status_anterior != aproveitamento_data['status']:
            if aproveitamento_data['status'] == StatusAproveitamento.APROVADO_COORDENACAO:
                fields.append("data_aprovacao_coordenacao = CURRENT_TIMESTAMP")
            elif aproveitamento_data['status'] == StatusAproveitamento.APROVADO_COLEGIADO:
                fields.append("data_aprovacao_colegiado = CURRENT_TIMESTAMP")
            elif aproveitamento_data['status'] in [StatusAproveitamento.DEFERIDO, StatusAproveitamento.INDEFERIDO]:
                fields.append("data_deferimento = CURRENT_TIMESTAMP")
        
        # Executar atualização
        query = f"UPDATE aproveitamentos SET {', '.join(fields)} WHERE id = ?"
        params.append(aproveitamento_id)
        c.execute(query, params)
        
    else:  # Inserir
        # Gerar número de processo
        numero_processo = gerar_numero_processo()
        
        # Preparar campos comuns
        fields = [
            "aluno_id",
            "tipo",
            "numero_processo",
            "status",
            "instituicao",
            "observacoes",
            "link_documentos"
        ]
        params = [
            aproveitamento_data['aluno_id'],
            aproveitamento_data['tipo'],
            numero_processo,
            StatusAproveitamento.SOLICITADO,
            aproveitamento_data['instituicao'],
            aproveitamento_data['observacoes'],
            aproveitamento_data['link_documentos']
        ]
        
        # Adicionar campos específicos por tipo
        if aproveitamento_data['tipo'] == TipoAproveitamento.DISCIPLINA:
            fields.extend([
                "nome_disciplina",
                "codigo_disciplina",
                "creditos"
            ])
            params.extend([
                aproveitamento_data['nome_disciplina'],
                aproveitamento_data['codigo_disciplina'],
                aproveitamento_data['creditos']
            ])
        elif aproveitamento_data['tipo'] == TipoAproveitamento.IDIOMA:
            fields.extend([
                "idioma",
                "nota"
            ])
            params.extend([
                aproveitamento_data['idioma'],
                aproveitamento_data['nota']
            ])
        
        # Executar inserção
        query = f"INSERT INTO aproveitamentos ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})"
        c.execute(query, params)
    
    conn.commit()
    conn.close()

def delete_aproveitamento(aproveitamento_id):
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    c.execute("DELETE FROM aproveitamentos WHERE id = ?", (aproveitamento_id,))
    conn.commit()
    conn.close()
    return True

# Função para exibir o cabeçalho
def display_header():
    header_image = Image.open('assets/header.jpg')
    st.image(header_image, use_container_width=True)

# Inicializar banco de dados
init_db()

# Inicializar estado da sessão
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'alunos'

# Função para alternar páginas
def set_page(page):
    st.session_state.current_page = page

# Tela de login
if not st.session_state.authenticated:
    # Exibir cabeçalho
    display_header()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<h2 style="color: #0A4C92; text-align: center;">Login</h2>', unsafe_allow_html=True)
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        
        if st.button("Entrar"):
            user = login(username, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

# Interface principal após login
else:
    # Exibir cabeçalho
    display_header()
    
    # Barra superior
    st.markdown(f'<div style="position: absolute; top: 0.5rem; right: 6rem; font-size: 0.9rem; color: #0A4C92; font-weight: bold;">Usuário: {st.session_state.user["username"]}</div>', unsafe_allow_html=True)
    
    # Sidebar para navegação
    with st.sidebar:
        st.markdown('<div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 1rem; color: #0A4C92;">Menu</div>', unsafe_allow_html=True)
        
        if st.button("Alunos", key="nav_alunos"):
            set_page('alunos')
            st.rerun()
        
        if st.button("Aproveitamentos", key="nav_aproveitamentos"):
            set_page('aproveitamentos')
            st.rerun()
        
        st.markdown("---")
        if st.button("Sair"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
    
    # Página de Alunos
    if st.session_state.current_page == 'alunos':
        st.markdown('<div style="font-size: 2rem; font-weight: bold; margin-bottom: 1rem; color: #0A4C92;">Gestão de Alunos</div>', unsafe_allow_html=True)
        
        # Botão para adicionar novo aluno
        if st.button("➕ Novo Aluno"):
            st.session_state.editing_aluno = {}
            st.session_state.show_aluno_form = True
        
        # Formulário de aluno
        if st.session_state.get('show_aluno_form', False):
            st.markdown("### Cadastro de Aluno")
            
            with st.form("aluno_form"):
                aluno_id = st.session_state.editing_aluno.get('id', None)
                col1, col2 = st.columns(2)
                
                with col1:
                    matricula = st.text_input("Matrícula", value=st.session_state.editing_aluno.get('matricula', ''))
                    nome = st.text_input("Nome", value=st.session_state.editing_aluno.get('nome', ''))
                    email = st.text_input("Email", value=st.session_state.editing_aluno.get('email', ''))
                    orientador = st.text_input("Orientador(a)", value=st.session_state.editing_aluno.get('orientador', ''))
                
                with col2:
                    linha_pesquisa = st.text_input("Linha de Pesquisa", value=st.session_state.editing_aluno.get('linha_pesquisa', ''))
                    data_ingresso = st.date_input("Data de Ingresso", 
                                                value=datetime.datetime.strptime(st.session_state.editing_aluno.get('data_ingresso', datetime.datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date() if st.session_state.editing_aluno.get('data_ingresso') else datetime.datetime.now())
                    prazo_defesa_projeto = st.date_input("Prazo Defesa Projeto", 
                                                      value=datetime.datetime.strptime(st.session_state.editing_aluno.get('prazo_defesa_projeto', ''), '%Y-%m-%d').date() if st.session_state.editing_aluno.get('prazo_defesa_projeto') else None)
                    prazo_defesa_tese = st.date_input("Prazo Defesa Tese", 
                                                   value=datetime.datetime.strptime(st.session_state.editing_aluno.get('prazo_defesa_tese', ''), '%Y-%m-%d').date() if st.session_state.editing_aluno.get('prazo_defesa_tese') else None)
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    submitted = st.form_submit_button("Salvar")
                with col2:
                    if st.form_submit_button("Cancelar"):
                        st.session_state.show_aluno_form = False
                        st.rerun()
                
                if submitted:
                    if not nome or not email or not data_ingresso:
                        st.error("Nome, email e data de ingresso são obrigatórios")
                    else:
                        aluno_data = {
                            'matricula': matricula,
                            'nome': nome,
                            'email': email,
                            'orientador': orientador,
                            'linha_pesquisa': linha_pesquisa,
                            'data_ingresso': data_ingresso.strftime('%Y-%m-%d'),
                            'prazo_defesa_projeto': prazo_defesa_projeto.strftime('%Y-%m-%d') if prazo_defesa_projeto else None,
                            'prazo_defesa_tese': prazo_defesa_tese.strftime('%Y-%m-%d') if prazo_defesa_tese else None
                        }
                        
                        save_aluno(aluno_data, aluno_id)
                        st.session_state.show_aluno_form = False
                        st.success("Aluno salvo com sucesso!")
                        st.rerun()
        
        # Lista de alunos
        alunos = get_alunos()
        if alunos:
            # Converter para DataFrame para exibição
            df_alunos = pd.DataFrame(alunos)
            
            # Formatar datas
            for col in ['data_ingresso', 'prazo_defesa_projeto', 'prazo_defesa_tese']:
                if col in df_alunos.columns:
                    df_alunos[col] = pd.to_datetime(df_alunos[col]).dt.strftime('%d/%m/%Y')
            
            # Selecionar e renomear colunas para exibição
            cols_display = {
                'id': 'ID',
                'matricula': 'Matrícula',
                'nome': 'Nome',
                'email': 'Email',
                'orientador': 'Orientador(a)',
                'linha_pesquisa': 'Linha de Pesquisa',
                'data_ingresso': 'Ingresso'
            }
            
            df_display = df_alunos[list(cols_display.keys())].rename(columns=cols_display)
            
            # Exibir tabela
            st.dataframe(df_display, hide_index=True)
            
            # Ações para cada aluno
            col1, col2 = st.columns(2)
            
            with col1:
                aluno_id_edit = st.selectbox("Selecione um aluno para editar:", 
                                           options=[a['id'] for a in alunos],
                                           format_func=lambda x: next((a['nome'] for a in alunos if a['id'] == x), ''))
                if st.button("Editar Aluno"):
                    aluno = get_aluno(aluno_id_edit)
                    if aluno:
                        st.session_state.editing_aluno = aluno
                        st.session_state.show_aluno_form = True
                        st.rerun()
            
            with col2:
                aluno_id_delete = st.selectbox("Selecione um aluno para excluir:", 
                                             options=[a['id'] for a in alunos],
                                             format_func=lambda x: next((a['nome'] for a in alunos if a['id'] == x), ''))
                if st.button("Excluir Aluno"):
                    if st.session_state.get('confirm_delete', False):
                        success = delete_aluno(aluno_id_delete)
                        if success:
                            st.success("Aluno excluído com sucesso!")
                            st.session_state.confirm_delete = False
                            st.rerun()
                        else:
                            st.error("Não é possível excluir este aluno pois existem aproveitamentos relacionados.")
                    else:
                        st.session_state.confirm_delete = True
                        st.warning("Tem certeza que deseja excluir este aluno? Esta ação não pode ser desfeita.")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Sim, excluir"):
                                success = delete_aluno(aluno_id_delete)
                                if success:
                                    st.success("Aluno excluído com sucesso!")
                                    st.session_state.confirm_delete = False
                                    st.rerun()
                                else:
                                    st.error("Não é possível excluir este aluno pois existem aproveitamentos relacionados.")
                        with col2:
                            if st.button("Cancelar"):
                                st.session_state.confirm_delete = False
                                st.rerun()
        else:
            st.info("Nenhum aluno cadastrado.")
    
    # Página de Aproveitamentos
    elif st.session_state.current_page == 'aproveitamentos':
        st.markdown('<div style="font-size: 2rem; font-weight: bold; margin-bottom: 1rem; color: #0A4C92;">Aproveitamentos de Disciplinas</div>', unsafe_allow_html=True)
        
        # Botão para adicionar novo aproveitamento
        if st.button("➕ Novo Aproveitamento"):
            st.session_state.editing_aproveitamento = {}
            st.session_state.show_aproveitamento_form = True
        
        # Formulário de aproveitamento
        if st.session_state.get('show_aproveitamento_form', False):
            st.markdown("### Cadastro de Aproveitamento")
            
            with st.form("aproveitamento_form"):
                aproveitamento_id = st.session_state.editing_aproveitamento.get('id', None)
                
                # Campos comuns
                alunos = get_alunos()
                aluno_options = {a['id']: a['nome'] for a in alunos}
                
                aluno_id = st.selectbox("Aluno", 
                                      options=list(aluno_options.keys()),
                                      format_func=lambda x: aluno_options.get(x, ''),
                                      index=list(aluno_options.keys()).index(st.session_state.editing_aproveitamento.get('aluno_id')) if st.session_state.editing_aproveitamento.get('aluno_id') in aluno_options else 0)
                
                tipo = st.selectbox("Tipo de Aproveitamento",
                                  options=[t.value for t in TipoAproveitamento],
                                  format_func=lambda x: "Disciplina" if x == TipoAproveitamento.DISCIPLINA else "Idioma",
                                  index=[t.value for t in TipoAproveitamento].index(st.session_state.editing_aproveitamento.get('tipo')) if st.session_state.editing_aproveitamento.get('tipo') in [t.value for t in TipoAproveitamento] else 0)
                
                # Campos específicos por tipo
                if tipo == TipoAproveitamento.DISCIPLINA:
                    col1, col2 = st.columns(2)
                    with col1:
                        nome_disciplina = st.text_input("Nome da Disciplina", value=st.session_state.editing_aproveitamento.get('nome_disciplina', ''))
                    with col2:
                        codigo_disciplina = st.text_input("Código da Disciplina", value=st.session_state.editing_aproveitamento.get('codigo_disciplina', ''))
                    creditos = st.number_input("Créditos", min_value=1, value=int(st.session_state.editing_aproveitamento.get('creditos', 1)))
                elif tipo == TipoAproveitamento.IDIOMA:
                    col1, col2 = st.columns(2)
                    with col1:
                        idioma = st.selectbox("Idioma", 
                                            options=["Inglês", "Espanhol", "Francês", "Alemão", "Italiano"],
                                            index=["Inglês", "Espanhol", "Francês", "Alemão", "Italiano"].index(st.session_state.editing_aproveitamento.get('idioma')) if st.session_state.editing_aproveitamento.get('idioma') in ["Inglês", "Espanhol", "Francês", "Alemão", "Italiano"] else 0)
                    with col2:
                        nota = st.number_input("Nota", min_value=0.0, max_value=10.0, value=float(st.session_state.editing_aproveitamento.get('nota', 0.0)), step=0.1)
                
                # Campos comuns adicionais
                instituicao = st.text_input("Instituição", value=st.session_state.editing_aproveitamento.get('instituicao', ''))
                observacoes = st.text_area("Observações", value=st.session_state.editing_aproveitamento.get('observacoes', ''))
                link_documentos = st.text_input("Link para Documentos (Google Drive)", value=st.session_state.editing_aproveitamento.get('link_documentos', ''))
                
                # Campo de status (apenas para edição)
                if aproveitamento_id:
                    status = st.selectbox("Status",
                                        options=[s.value for s in StatusAproveitamento],
                                        format_func=lambda x: {
                                            'solicitado': 'Solicitado',
                                            'aprovado_coordenacao': 'Aprovado pela Coordenação',
                                            'aprovado_colegiado': 'Aprovado pelo Colegiado',
                                            'deferido': 'Deferido',
                                            'indeferido': 'Indeferido'
                                        }.get(x, x),
                                        index=[s.value for s in StatusAproveitamento].index(st.session_state.editing_aproveitamento.get('status')) if st.session_state.editing_aproveitamento.get('status') in [s.value for s in StatusAproveitamento] else 0)
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    submitted = st.form_submit_button("Salvar")
                with col2:
                    if st.form_submit_button("Cancelar"):
                        st.session_state.show_aproveitamento_form = False
                        st.rerun()
                
                if submitted:
                    # Validação básica
                    if not aluno_id:
                        st.error("Selecione um aluno")
                    elif tipo == TipoAproveitamento.DISCIPLINA and not nome_disciplina:
                        st.error("Nome da disciplina é obrigatório")
                    elif tipo == TipoAproveitamento.IDIOMA and not idioma:
                        st.error("Idioma é obrigatório")
                    else:
                        # Preparar dados
                        aproveitamento_data = {
                            'aluno_id': aluno_id,
                            'tipo': tipo,
                            'instituicao': instituicao,
                            'observacoes': observacoes,
                            'link_documentos': link_documentos
                        }
                        
                        # Adicionar campos específicos por tipo
                        if tipo == TipoAproveitamento.DISCIPLINA:
                            aproveitamento_data.update({
                                'nome_disciplina': nome_disciplina,
                                'codigo_disciplina': codigo_disciplina,
                                'creditos': creditos
                            })
                        elif tipo == TipoAproveitamento.IDIOMA:
                            aproveitamento_data.update({
                                'idioma': idioma,
                                'nota': nota
                            })
                        
                        # Adicionar status se estiver editando
                        if aproveitamento_id:
                            aproveitamento_data['status'] = status
                        
                        # Salvar
                        save_aproveitamento(aproveitamento_data, aproveitamento_id)
                        st.session_state.show_aproveitamento_form = False
                        st.success("Aproveitamento salvo com sucesso!")
                        st.rerun()
        
        # Lista de aproveitamentos
        aproveitamentos = get_aproveitamentos()
        if aproveitamentos:
            # Converter para DataFrame para exibição
            df_aproveitamentos = pd.DataFrame(aproveitamentos)
            
            # Formatar datas
            for col in ['data_solicitacao', 'data_aprovacao_coordenacao', 'data_aprovacao_colegiado', 'data_deferimento']:
                if col in df_aproveitamentos.columns:
                    df_aproveitamentos[col] = pd.to_datetime(df_aproveitamentos[col]).dt.strftime('%d/%m/%Y')
            
            # Adicionar colunas formatadas
            df_aproveitamentos['tipo_formatado'] = df_aproveitamentos['tipo'].apply(lambda x: "Disciplina" if x == TipoAproveitamento.DISCIPLINA else "Idioma")
            
            df_aproveitamentos['disciplina_idioma'] = df_aproveitamentos.apply(
                lambda row: row['nome_disciplina'] if row['tipo'] == TipoAproveitamento.DISCIPLINA 
                else f"{row['idioma']} (Nota: {row['nota']})", axis=1
            )
            
            df_aproveitamentos['status_formatado'] = df_aproveitamentos['status'].apply(
                lambda x: {
                    'solicitado': 'Solicitado',
                    'aprovado_coordenacao': 'Aprovado (Coord.)',
                    'aprovado_colegiado': 'Aprovado (Coleg.)',
                    'deferido': 'Deferido',
                    'indeferido': 'Indeferido'
                }.get(x, x)
            )
            
            # Selecionar e renomear colunas para exibição
            cols_display = {
                'id': 'ID',
                'aluno_nome': 'Aluno',
                'tipo_formatado': 'Tipo',
                'disciplina_idioma': 'Disciplina/Idioma',
                'numero_processo': 'Processo',
                'status_formatado': 'Status',
                'data_solicitacao': 'Data Solicitação'
            }
            
            df_display = df_aproveitamentos[list(cols_display.keys())].rename(columns=cols_display)
            
            # Exibir tabela
            st.dataframe(df_display, hide_index=True)
            
            # Ações para cada aproveitamento
            col1, col2 = st.columns(2)
            
            with col1:
                aproveitamento_id_edit = st.selectbox("Selecione um aproveitamento para editar:", 
                                                    options=[a['id'] for a in aproveitamentos],
                                                    format_func=lambda x: f"{next((a['aluno_nome'] for a in aproveitamentos if a['id'] == x), '')} - {next((a['disciplina_idioma'] for a in aproveitamentos if a['id'] == x), '')}")
                if st.button("Editar Aproveitamento"):
                    aproveitamento = get_aproveitamento(aproveitamento_id_edit)
                    if aproveitamento:
                        st.session_state.editing_aproveitamento = aproveitamento
                        st.session_state.show_aproveitamento_form = True
                        st.rerun()
            
            with col2:
                aproveitamento_id_delete = st.selectbox("Selecione um aproveitamento para excluir:", 
                                                      options=[a['id'] for a in aproveitamentos],
                                                      format_func=lambda x: f"{next((a['aluno_nome'] for a in aproveitamentos if a['id'] == x), '')} - {next((a['disciplina_idioma'] for a in aproveitamentos if a['id'] == x), '')}")
                if st.button("Excluir Aproveitamento"):
                    if st.session_state.get('confirm_delete_aproveitamento', False):
                        delete_aproveitamento(aproveitamento_id_delete)
                        st.success("Aproveitamento excluído com sucesso!")
                        st.session_state.confirm_delete_aproveitamento = False
                        st.rerun()
                    else:
                        st.session_state.confirm_delete_aproveitamento = True
                        st.warning("Tem certeza que deseja excluir este aproveitamento? Esta ação não pode ser desfeita.")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Sim, excluir"):
                                delete_aproveitamento(aproveitamento_id_delete)
                                st.success("Aproveitamento excluído com sucesso!")
                                st.session_state.confirm_delete_aproveitamento = False
                                st.rerun()
                        with col2:
                            if st.button("Cancelar"):
                                st.session_state.confirm_delete_aproveitamento = False
                                st.rerun()
        else:
            st.info("Nenhum aproveitamento cadastrado.")

# Adicionar rodapé com informações sobre o domínio personalizado
st.markdown("""
<div style="position: fixed; bottom: 0; left: 0; width: 100%; background-color: #0A4C92; color: white; text-align: center; padding: 10px; font-size: 0.8rem;">
    Sistema de Gestão de Alunos PPGOP - Disponível em: ppgop.streamlit.app
</div>
""", unsafe_allow_html=True)
