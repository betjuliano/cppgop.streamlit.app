import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import fpdf
import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
from enum import Enum
from PIL import Image

# Configuração da página
st.set_page_config(
    page_title="PPGOP - Sistema de Gestão",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enums para tipos e status
class TipoAproveitamento(str, Enum):
    DISCIPLINA = "disciplina"
    IDIOMA = "idioma"

class StatusAproveitamento(str, Enum):
    SOLICITADO = "solicitado"
    APROVADO_COORDENACAO = "aprovado_coordenacao"
    APROVADO_COLEGIADO = "aprovado_colegiado"
    DEFERIDO = "deferido"
    INDEFERIDO = "indeferido"

# Inicializar banco de dados
def init_db():
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    # Tabela de usuários
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
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
        turma TEXT,
        nivel TEXT,
        prazo_defesa_projeto DATE,
        prazo_defesa_tese DATE,
        data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Verificar se a coluna nivel já existe
    c.execute("PRAGMA table_info(alunos)")
    colunas = [info[1] for info in c.fetchall()]
    if 'nivel' not in colunas:
        try:
            c.execute("ALTER TABLE alunos ADD COLUMN nivel TEXT")
        except:
            pass  # Coluna já existe ou erro ao adicionar
    
    # Tabela de aproveitamentos
    c.execute('''
    CREATE TABLE IF NOT EXISTS aproveitamentos (
        id INTEGER PRIMARY KEY,
        aluno_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        nome_disciplina TEXT,
        codigo_disciplina TEXT,
        creditos INTEGER,
        idioma TEXT,
        nota REAL,
        instituicao TEXT,
        observacoes TEXT,
        link_documentos TEXT,
        numero_processo TEXT,
        status TEXT DEFAULT 'solicitado',
        data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_aprovacao_coordenacao TIMESTAMP,
        data_aprovacao_colegiado TIMESTAMP,
        data_deferimento TIMESTAMP,
        FOREIGN KEY (aluno_id) REFERENCES alunos (id) ON DELETE CASCADE
    )
    ''')
    
    # Inserir usuários padrão se não existirem
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'Breno'")
    if c.fetchone()[0] == 0:
        password_hash = hashlib.sha256("adm123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("Breno", password_hash))
    
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'PPGOP'")
    if c.fetchone()[0] == 0:
        password_hash = hashlib.sha256("123curso".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("PPGOP", password_hash))
    
    conn.commit()
    conn.close()

# Funções de acesso ao banco de dados
def get_user(username, password):
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT id, username FROM users WHERE username = ? AND password_hash = ?", (username, password_hash))
    user = c.fetchone()
    
    conn.close()
    return {"id": user[0], "username": user[1]} if user else None

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
            turma = ?,
            nivel = ?,
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
            aluno_data['turma'],
            aluno_data['nivel'],
            aluno_data['prazo_defesa_projeto'],
            aluno_data['prazo_defesa_tese'],
            aluno_id
        ))
    else:  # Inserir
        c.execute("""
        INSERT INTO alunos (
            matricula, nome, email, orientador, linha_pesquisa, 
            data_ingresso, turma, nivel, prazo_defesa_projeto, prazo_defesa_tese
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            aluno_data['matricula'],
            aluno_data['nome'],
            aluno_data['email'],
            aluno_data['orientador'],
            aluno_data['linha_pesquisa'],
            aluno_data['data_ingresso'],
            aluno_data['turma'],
            aluno_data['nivel'],
            aluno_data['prazo_defesa_projeto'],
            aluno_data['prazo_defesa_tese']
        ))
    
    conn.commit()
    conn.close()

def delete_aluno(aluno_id):
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    # Excluir o aluno
    c.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
    
    # Commit e fechar conexão
    conn.commit()
    conn.close()
    
    return True
    
    c.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
    
    conn.commit()
    conn.close()

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
    
    c.execute("SELECT * FROM aproveitamentos WHERE id = ?", (aproveitamento_id,))
    aproveitamento = c.fetchone()
    
    conn.close()
    return dict(aproveitamento) if aproveitamento else None

def get_aproveitamentos_aluno(aluno_id):
    conn = sqlite3.connect('ppgop.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
    SELECT * FROM aproveitamentos 
    WHERE aluno_id = ? 
    ORDER BY data_solicitacao DESC
    """, (aluno_id,))
    aproveitamentos = [dict(row) for row in c.fetchall()]
    
    conn.close()
    return aproveitamentos

def save_aproveitamento(aproveitamento_data, aproveitamento_id=None):
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    # Campos comuns
    fields = [
        'aluno_id', 'tipo', 'instituicao', 'observacoes', 'link_documentos'
    ]
    
    # Adicionar campos específicos por tipo
    if aproveitamento_data['tipo'] == TipoAproveitamento.DISCIPLINA:
        fields.extend(['nome_disciplina', 'codigo_disciplina', 'creditos'])
    elif aproveitamento_data['tipo'] == TipoAproveitamento.IDIOMA:
        fields.extend(['idioma', 'nota'])
    
    # Adicionar status se estiver editando
    if aproveitamento_id and 'status' in aproveitamento_data:
        fields.append('status')
        
        # Atualizar campos de data com base no status
        if aproveitamento_data['status'] == StatusAproveitamento.APROVADO_COORDENACAO:
            aproveitamento_data['data_aprovacao_coordenacao'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            fields.append('data_aprovacao_coordenacao')
        elif aproveitamento_data['status'] == StatusAproveitamento.APROVADO_COLEGIADO:
            aproveitamento_data['data_aprovacao_colegiado'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            fields.append('data_aprovacao_colegiado')
        elif aproveitamento_data['status'] in [StatusAproveitamento.DEFERIDO, StatusAproveitamento.INDEFERIDO]:
            aproveitamento_data['data_deferimento'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            fields.append('data_deferimento')
    
    # Gerar número de processo se for novo aproveitamento
    if not aproveitamento_id:
        # Formato: ANO/SEQUENCIAL-TIPO
        ano_atual = datetime.datetime.now().year
        
        # Obter último número de processo do ano
        c.execute("""
        SELECT numero_processo FROM aproveitamentos 
        WHERE numero_processo LIKE ? 
        ORDER BY id DESC LIMIT 1
        """, (f"{ano_atual}/%",))
        
        ultimo_processo = c.fetchone()
        
        if ultimo_processo and ultimo_processo[0]:
            # Extrair sequencial
            try:
                sequencial = int(ultimo_processo[0].split('/')[1].split('-')[0]) + 1
            except:
                sequencial = 1
        else:
            sequencial = 1
        
        # Tipo abreviado
        tipo_abrev = "D" if aproveitamento_data['tipo'] == TipoAproveitamento.DISCIPLINA else "I"
        
        # Gerar número de processo
        aproveitamento_data['numero_processo'] = f"{ano_atual}/{sequencial:03d}-{tipo_abrev}"
        fields.append('numero_processo')
    
    # Construir query
    if aproveitamento_id:  # Atualizar
        set_clause = ", ".join([f"{field} = ?" for field in fields])
        query = f"UPDATE aproveitamentos SET {set_clause} WHERE id = ?"
        values = [aproveitamento_data[field] for field in fields] + [aproveitamento_id]
    else:  # Inserir
        placeholders = ", ".join(["?" for _ in fields])
        query = f"INSERT INTO aproveitamentos ({', '.join(fields)}) VALUES ({placeholders})"
        values = [aproveitamento_data[field] for field in fields]
    
    c.execute(query, values)
    conn.commit()
    conn.close()

def delete_aproveitamento(aproveitamento_id):
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    c.execute("DELETE FROM aproveitamentos WHERE id = ?", (aproveitamento_id,))
    
    conn.commit()
    conn.close()

def calcular_resumo_aproveitamentos(aluno_id):
    aproveitamentos = get_aproveitamentos_aluno(aluno_id)
    
    # Inicializar resumo
    resumo = {
        'disciplinas': {
            'total': 0,
            'creditos': 0,
            'horas': 0,
            'deferidos': 0,
            'pendentes': 0
        },
        'idiomas': {
            'total': 0,
            'aprovados': 0,
            'pendentes': 0
        },
        'detalhes': {
            'disciplinas': [],
            'idiomas': []
        }
    }
    
    # Processar cada aproveitamento
    for aprov in aproveitamentos:
        if aprov['tipo'] == TipoAproveitamento.DISCIPLINA:
            # Adicionar ao resumo de disciplinas
            resumo['disciplinas']['total'] += 1
            
            # Adicionar detalhes
            resumo['detalhes']['disciplinas'].append({
                'nome': aprov['nome_disciplina'],
                'codigo': aprov['codigo_disciplina'],
                'creditos': aprov['creditos'],
                'horas': aprov['creditos'] * 15,  # 1 crédito = 15 horas
                'instituicao': aprov['instituicao'],
                'status': aprov['status'],
                'processo': aprov['numero_processo']
            })
            
            # Contabilizar se deferido
            if aprov['status'] == StatusAproveitamento.DEFERIDO:
                resumo['disciplinas']['deferidos'] += 1
                resumo['disciplinas']['creditos'] += aprov['creditos']
                resumo['disciplinas']['horas'] += aprov['creditos'] * 15
            else:
                resumo['disciplinas']['pendentes'] += 1
                
        elif aprov['tipo'] == TipoAproveitamento.IDIOMA:
            # Adicionar ao resumo de idiomas
            resumo['idiomas']['total'] += 1
            
            # Adicionar detalhes
            resumo['detalhes']['idiomas'].append({
                'idioma': aprov['idioma'],
                'nota': aprov['nota'],
                'instituicao': aprov['instituicao'],
                'status': aprov['status'],
                'processo': aprov['numero_processo']
            })
            
            # Contabilizar se deferido
            if aprov['status'] == StatusAproveitamento.DEFERIDO:
                resumo['idiomas']['aprovados'] += 1
            else:
                resumo['idiomas']['pendentes'] += 1
    
    return resumo

# Função para importar alunos do Excel
def import_alunos_from_excel(uploaded_file):
    """
    Importa alunos do arquivo Excel para o banco de dados.
    
    Args:
        uploaded_file: Arquivo Excel carregado via Streamlit
        
    Returns:
        dict: Estatísticas da importação (total, importados, ignorados)
    """
    # Ler o arquivo Excel
    df = pd.read_excel(uploaded_file, header=None)
    
    # Encontrar a linha do cabeçalho (que contém "Matrícula", "Nome", etc.)
    header_row = None
    for i, row in df.iterrows():
        if isinstance(row[0], str) and row[0].strip() == "Matrícula":
            header_row = i
            break
    
    if header_row is None:
        return {"error": "Formato de arquivo inválido. Cabeçalho não encontrado."}
    
    # Extrair os dados a partir da linha após o cabeçalho
    data_df = df.iloc[header_row+1:].copy()
    data_df.columns = df.iloc[header_row]
    
    # Remover linhas sem nome (provavelmente vazias)
    data_df = data_df[data_df["Nome"].notna()]
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('ppgop.db')
    cursor = conn.cursor()
    
    # Estatísticas
    stats = {
        "total": len(data_df),
        "importados": 0,
        "ignorados": 0,
        "erros": []
    }
    
    # Inserir cada aluno no banco de dados
    for _, row in data_df.iterrows():
        try:
            # Verificar se o aluno já existe (pelo email)
            cursor.execute("SELECT id FROM alunos WHERE email = ?", (row["E-mail"],))
            existing = cursor.fetchone()
            
            if existing:
                stats["ignorados"] += 1
                stats["erros"].append(f"Aluno já existe: {row['Nome']} ({row['E-mail']})")
                continue
            
            # Formatar datas
            try:
                data_ingresso = pd.to_datetime(row["Ingresso"]).strftime('%Y-%m-%d') if pd.notna(row["Ingresso"]) else datetime.datetime.now().strftime('%Y-%m-%d')
            except:
                data_ingresso = datetime.datetime.now().strftime('%Y-%m-%d')
                stats["erros"].append(f"Data de ingresso inválida para {row['Nome']}, usando data atual")
            
            # Extrair turma
            try:
                turma = str(row["Turma"]) if pd.notna(row["Turma"]) else ""
            except:
                turma = ""
                stats["erros"].append(f"Turma inválida para {row['Nome']}")
            
            # Extrair nível
            try:
                nivel = str(row["Nível"]) if pd.notna(row["Nível"]) else ""
            except:
                nivel = ""
                stats["erros"].append(f"Nível inválido para {row['Nome']}")
                
            try:
                prazo_defesa_projeto = pd.to_datetime(row["Prazo defesa do Projeto"]).strftime('%Y-%m-%d') if pd.notna(row["Prazo defesa do Projeto"]) else None
            except:
                prazo_defesa_projeto = None
                stats["erros"].append(f"Prazo de defesa de projeto inválido para {row['Nome']}")
                
            try:
                prazo_defesa_tese = pd.to_datetime(row["Prazo para Defesa da Tese"]).strftime('%Y-%m-%d') if pd.notna(row["Prazo para Defesa da Tese"]) else None
            except:
                prazo_defesa_tese = None
                stats["erros"].append(f"Prazo de defesa de tese inválido para {row['Nome']}")
            
            # Inserir aluno
            cursor.execute("""
            INSERT INTO alunos (
                matricula, nome, email, orientador, linha_pesquisa, 
                data_ingresso, turma, nivel, prazo_defesa_projeto, prazo_defesa_tese
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["Matrícula"] if pd.notna(row["Matrícula"]) else None,
                row["Nome"],
                row["E-mail"],
                row["Orientador(a)"] if pd.notna(row["Orientador(a)"]) else None,
                row["Linha de Pesquisa"] if pd.notna(row["Linha de Pesquisa"]) else None,
                data_ingresso,
                turma,
                nivel,
                prazo_defesa_projeto,
                prazo_defesa_tese
            ))
            
            stats["importados"] += 1
            
        except Exception as e:
            stats["ignorados"] += 1
            stats["erros"].append(f"Erro ao importar {row['Nome']}: {str(e)}")
    
    # Commit e fechar conexão
    conn.commit()
    conn.close()
    
    return stats

# Função para exibir o cabeçalho
def display_header():
    header_image = Image.open('assets/header.jpg')
    st.image(header_image, use_container_width=True)

# Função para gerar PDF do dashboard do aluno
def gerar_pdf_dashboard(aluno, resumo):
    # Criar PDF usando FPDF2
    pdf = fpdf.FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # Configurar fontes
    pdf.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', uni=True)
    pdf.set_font('DejaVu', '', 12)
    
    # Cabeçalho
    pdf.set_font('DejaVu', '', 16)
    pdf.cell(0, 10, 'Dashboard do Aluno', 0, 1, 'C')
    pdf.set_font('DejaVu', '', 12)
    pdf.cell(0, 6, 'Programa de Pós-Graduação em Gestão de Organizações Públicas', 0, 1, 'C')
    pdf.cell(0, 6, f'Relatório gerado em {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
    pdf.ln(5)
    
    # Dados do aluno
    pdf.set_font('DejaVu', '', 14)
    pdf.set_fill_color(10, 76, 146)  # Azul PPGOP
    pdf.set_text_color(255, 255, 255)  # Branco
    pdf.cell(0, 8, 'Dados do Aluno', 0, 1, 'L', True)
    pdf.set_text_color(0, 0, 0)  # Preto
    pdf.ln(2)
    
    # Formatar datas
    data_ingresso = datetime.datetime.strptime(aluno['data_ingresso'], '%Y-%m-%d').strftime('%d/%m/%Y') if aluno['data_ingresso'] else 'Não informada'
    prazo_projeto = datetime.datetime.strptime(aluno['prazo_defesa_projeto'], '%Y-%m-%d').strftime('%d/%m/%Y') if aluno['prazo_defesa_projeto'] else 'Não informado'
    prazo_tese = datetime.datetime.strptime(aluno['prazo_defesa_tese'], '%Y-%m-%d').strftime('%d/%m/%Y') if aluno['prazo_defesa_tese'] else 'Não informado'
    
    # Informações do aluno
    pdf.set_font('DejaVu', '', 12)
    pdf.cell(0, 6, f'Nome: {aluno["nome"]}', 0, 1)
    pdf.cell(0, 6, f'Matrícula: {aluno["matricula"] or "Não informada"}', 0, 1)
    pdf.cell(0, 6, f'Email: {aluno["email"]}', 0, 1)
    pdf.cell(0, 6, f'Orientador: {aluno["orientador"] or "Não informado"}', 0, 1)
    pdf.cell(0, 6, f'Linha de Pesquisa: {aluno["linha_pesquisa"] or "Não informada"}', 0, 1)
    pdf.cell(0, 6, f'Data de Ingresso: {data_ingresso}', 0, 1)
    pdf.cell(0, 6, f'Turma: {aluno["turma"] or "Não informada"}', 0, 1)
    pdf.cell(0, 6, f'Nível: {aluno["nivel"] or "Não informado"}', 0, 1)
    pdf.cell(0, 6, f'Prazo Defesa Projeto: {prazo_projeto}', 0, 1)
    pdf.cell(0, 6, f'Prazo Defesa Tese: {prazo_tese}', 0, 1)
    pdf.ln(5)
    
    # Resumo de aproveitamentos
    pdf.set_font('DejaVu', '', 14)
    pdf.set_fill_color(10, 76, 146)  # Azul PPGOP
    pdf.set_text_color(255, 255, 255)  # Branco
    pdf.cell(0, 8, 'Resumo de Aproveitamentos', 0, 1, 'L', True)
    pdf.set_text_color(0, 0, 0)  # Preto
    pdf.ln(2)
    
    # Disciplinas
    pdf.set_font('DejaVu', '', 12)
    pdf.set_fill_color(235, 245, 255)  # Azul claro
    pdf.cell(0, 8, 'Disciplinas', 0, 1, 'L', True)
    pdf.cell(0, 6, f'Total de disciplinas: {resumo["disciplinas"]["total"]}', 0, 1)
    pdf.cell(0, 6, f'Créditos aproveitados: {resumo["disciplinas"]["creditos"]}', 0, 1)
    pdf.cell(0, 6, f'Horas aproveitadas: {resumo["disciplinas"]["horas"]}', 0, 1)
    pdf.cell(0, 6, f'Disciplinas deferidas: {resumo["disciplinas"]["deferidos"]}', 0, 1)
    pdf.cell(0, 6, f'Disciplinas pendentes: {resumo["disciplinas"]["pendentes"]}', 0, 1)
    pdf.ln(2)
    
    # Idiomas
    pdf.set_fill_color(235, 245, 255)  # Azul claro
    pdf.cell(0, 8, 'Idiomas', 0, 1, 'L', True)
    pdf.cell(0, 6, f'Total de idiomas: {resumo["idiomas"]["total"]}', 0, 1)
    pdf.cell(0, 6, f'Idiomas aprovados: {resumo["idiomas"]["aprovados"]}', 0, 1)
    pdf.cell(0, 6, f'Idiomas pendentes: {resumo["idiomas"]["pendentes"]}', 0, 1)
    pdf.ln(5)
    
    # Detalhes dos aproveitamentos
    pdf.set_font('DejaVu', '', 14)
    pdf.set_fill_color(10, 76, 146)  # Azul PPGOP
    pdf.set_text_color(255, 255, 255)  # Branco
    pdf.cell(0, 8, 'Detalhes dos Aproveitamentos', 0, 1, 'L', True)
    pdf.set_text_color(0, 0, 0)  # Preto
    pdf.ln(2)
    
    # Mapeamento de status
    status_map = {
        'solicitado': 'Solicitado',
        'aprovado_coordenacao': 'Aprovado (Coord.)',
        'aprovado_colegiado': 'Aprovado (Coleg.)',
        'deferido': 'Deferido',
        'indeferido': 'Indeferido'
    }
    
    # Disciplinas
    if resumo['detalhes']['disciplinas']:
        pdf.set_font('DejaVu', '', 12)
        pdf.set_fill_color(235, 245, 255)  # Azul claro
        pdf.cell(0, 8, 'Disciplinas', 0, 1, 'L', True)
        
        # Cabeçalho da tabela
        pdf.set_font('DejaVu', '', 10)
        pdf.set_fill_color(10, 76, 146)  # Azul PPGOP
        pdf.set_text_color(255, 255, 255)  # Branco
        
        # Definir larguras das colunas
        col_widths = [60, 20, 15, 15, 40, 25, 25]
        
        # Cabeçalho
        pdf.cell(col_widths[0], 8, 'Disciplina', 1, 0, 'C', True)
        pdf.cell(col_widths[1], 8, 'Código', 1, 0, 'C', True)
        pdf.cell(col_widths[2], 8, 'Créditos', 1, 0, 'C', True)
        pdf.cell(col_widths[3], 8, 'Horas', 1, 0, 'C', True)
        pdf.cell(col_widths[4], 8, 'Instituição', 1, 0, 'C', True)
        pdf.cell(col_widths[5], 8, 'Status', 1, 0, 'C', True)
        pdf.cell(col_widths[6], 8, 'Processo', 1, 1, 'C', True)
        
        # Dados
        pdf.set_text_color(0, 0, 0)  # Preto
        for i, disc in enumerate(resumo['detalhes']['disciplinas']):
            # Alternar cores das linhas
            if i % 2 == 0:
                pdf.set_fill_color(245, 245, 245)  # Cinza claro
                fill = True
            else:
                pdf.set_fill_color(255, 255, 255)  # Branco
                fill = True
            
            # Verificar se precisa quebrar texto
            nome = disc['nome'] or '-'
            if pdf.get_string_width(nome) > col_widths[0] - 4:
                nome = nome[:30] + '...'
            
            codigo = disc['codigo'] or '-'
            if pdf.get_string_width(codigo) > col_widths[1] - 4:
                codigo = codigo[:10] + '...'
            
            instituicao = disc['instituicao'] or '-'
            if pdf.get_string_width(instituicao) > col_widths[4] - 4:
                instituicao = instituicao[:20] + '...'
            
            # Linha da tabela
            pdf.cell(col_widths[0], 8, nome, 1, 0, 'L', fill)
            pdf.cell(col_widths[1], 8, codigo, 1, 0, 'L', fill)
            pdf.cell(col_widths[2], 8, str(disc['creditos'] or 0), 1, 0, 'C', fill)
            pdf.cell(col_widths[3], 8, str(disc['horas'] or 0), 1, 0, 'C', fill)
            pdf.cell(col_widths[4], 8, instituicao, 1, 0, 'L', fill)
            pdf.cell(col_widths[5], 8, status_map.get(disc['status'], disc['status']), 1, 0, 'L', fill)
            pdf.cell(col_widths[6], 8, disc['processo'] or '-', 1, 1, 'L', fill)
        
        pdf.ln(2)
    else:
        pdf.set_font('DejaVu', '', 12)
        pdf.cell(0, 8, 'Nenhuma disciplina cadastrada para este aluno.', 0, 1)
        pdf.ln(2)
    
    # Idiomas
    if resumo['detalhes']['idiomas']:
        pdf.set_font('DejaVu', '', 12)
        pdf.set_fill_color(235, 245, 255)  # Azul claro
        pdf.cell(0, 8, 'Idiomas', 0, 1, 'L', True)
        
        # Cabeçalho da tabela
        pdf.set_font('DejaVu', '', 10)
        pdf.set_fill_color(10, 76, 146)  # Azul PPGOP
        pdf.set_text_color(255, 255, 255)  # Branco
        
        # Definir larguras das colunas
        col_widths = [40, 20, 60, 40, 40]
        
        # Cabeçalho
        pdf.cell(col_widths[0], 8, 'Idioma', 1, 0, 'C', True)
        pdf.cell(col_widths[1], 8, 'Nota', 1, 0, 'C', True)
        pdf.cell(col_widths[2], 8, 'Instituição', 1, 0, 'C', True)
        pdf.cell(col_widths[3], 8, 'Status', 1, 0, 'C', True)
        pdf.cell(col_widths[4], 8, 'Processo', 1, 1, 'C', True)
        
        # Dados
        pdf.set_text_color(0, 0, 0)  # Preto
        for i, idioma in enumerate(resumo['detalhes']['idiomas']):
            # Alternar cores das linhas
            if i % 2 == 0:
                pdf.set_fill_color(245, 245, 245)  # Cinza claro
                fill = True
            else:
                pdf.set_fill_color(255, 255, 255)  # Branco
                fill = True
            
            # Verificar se precisa quebrar texto
            nome_idioma = idioma['idioma'] or '-'
            if pdf.get_string_width(nome_idioma) > col_widths[0] - 4:
                nome_idioma = nome_idioma[:20] + '...'
            
            instituicao = idioma['instituicao'] or '-'
            if pdf.get_string_width(instituicao) > col_widths[2] - 4:
                instituicao = instituicao[:30] + '...'
            
            # Linha da tabela
            pdf.cell(col_widths[0], 8, nome_idioma, 1, 0, 'L', fill)
            pdf.cell(col_widths[1], 8, str(idioma['nota'] or '-'), 1, 0, 'C', fill)
            pdf.cell(col_widths[2], 8, instituicao, 1, 0, 'L', fill)
            pdf.cell(col_widths[3], 8, status_map.get(idioma['status'], idioma['status']), 1, 0, 'L', fill)
            pdf.cell(col_widths[4], 8, idioma['processo'] or '-', 1, 1, 'L', fill)
        
        pdf.ln(2)
    else:
        pdf.set_font('DejaVu', '', 12)
        pdf.cell(0, 8, 'Nenhum idioma cadastrado para este aluno.', 0, 1)
        pdf.ln(2)
    
    # Rodapé
    pdf.set_y(-20)
    pdf.set_font('DejaVu', '', 8)
    pdf.cell(0, 5, 'PPGOP - Sistema de Gestão de Alunos e Aproveitamento de Disciplinas', 0, 1, 'C')
    pdf.cell(0, 5, f'Gerado em {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
    
    return pdf.output(dest='S').encode('latin1')

# Função para criar link de download
def get_download_link(pdf_bytes, filename):
    b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}" class="download-button">Baixar PDF</a>'
    return href

# Função para definir a página atual
def set_page(page):
    st.session_state.current_page = page

# Inicializar banco de dados
init_db()

# Inicializar estado da sessão
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.current_page = 'alunos'
    st.session_state.show_aluno_form = False
    st.session_state.editing_aluno = {}
    st.session_state.show_aproveitamento_form = False
    st.session_state.editing_aproveitamento = {}

# Tela de login
if not st.session_state.authenticated:
    # Exibir cabeçalho
    display_header()
    
    st.markdown('<div style="font-size: 2rem; font-weight: bold; margin-bottom: 1rem; color: #0A4C92;">Login</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
            
            if submitted:
                user = get_user(username, password)
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
        
        if st.button("Dashboard", key="nav_dashboard"):
            set_page('dashboard')
            st.rerun()
        
        if st.button("Importar Alunos", key="nav_importar"):
            set_page('importar')
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
                    linha_pesquisa = st.text_input("Linha de Pesquisa", value=st.session_state.editing_aluno.get('linha_pesquisa', ''))
                
                with col2:
                    data_ingresso = st.date_input("Data de Ingresso", 
                                                value=datetime.datetime.strptime(st.session_state.editing_aluno.get('data_ingresso', datetime.datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date() if st.session_state.editing_aluno.get('data_ingresso') else datetime.datetime.now())
                    turma = st.text_input("Turma", value=st.session_state.editing_aluno.get('turma', ''))
                    nivel = st.selectbox("Nível", 
                                       options=["Mestrado", "Doutorado"],
                                       index=0 if st.session_state.editing_aluno.get('nivel') != "Doutorado" else 1)
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
                            'turma': turma,
                            'nivel': nivel,
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
                'data_ingresso': 'Ingresso',
                'turma': 'Turma',
                'prazo_defesa_projeto': 'Prazo Projeto',
                'prazo_defesa_tese': 'Prazo Defesa'
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
                        delete_aluno(aluno_id_delete)
                        st.success("Aluno excluído com sucesso!")
                        st.session_state.confirm_delete = False
                        st.rerun()
                    else:
                        st.session_state.confirm_delete = True
                        st.warning("Tem certeza que deseja excluir este aluno? Esta ação não pode ser desfeita.")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Sim, excluir"):
                                delete_aluno(aluno_id_delete)
                                st.success("Aluno excluído com sucesso!")
                                st.session_state.confirm_delete = False
                                st.rerun()
                        with col2:
                            if st.button("Cancelar"):
                                st.session_state.confirm_delete = False
                                st.rerun()
        else:
            st.info("Nenhum aluno cadastrado.")
    
    # Página de Aproveitamentos
    elif st.session_state.current_page == 'aproveitamentos':
        st.markdown('<div style="font-size: 2rem; font-weight: bold; margin-bottom: 1rem; color: #0A4C92;">Gestão de Aproveitamentos</div>', unsafe_allow_html=True)
        
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
    
    # Página de Dashboard
    elif st.session_state.current_page == 'dashboard':
        st.markdown('<div style="font-size: 2rem; font-weight: bold; margin-bottom: 1rem; color: #0A4C92;">Dashboard de Alunos</div>', unsafe_allow_html=True)
        
        # Selecionar aluno
        alunos = get_alunos()
        if not alunos:
            st.info("Nenhum aluno cadastrado para exibir no dashboard.")
        else:
            aluno_options = {a['id']: a['nome'] for a in alunos}
            
            aluno_id = st.selectbox("Selecione um aluno:", 
                                  options=list(aluno_options.keys()),
                                  format_func=lambda x: aluno_options.get(x, ''))
            
            if aluno_id:
                # Obter dados do aluno
                aluno = get_aluno(aluno_id)
                
                # Obter resumo de aproveitamentos
                resumo = calcular_resumo_aproveitamentos(aluno_id)
                
                # Botão para exportar PDF
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button("📄 Exportar PDF"):
                        with st.spinner("Gerando PDF..."):
                            # Gerar PDF
                            pdf_bytes = gerar_pdf_dashboard(aluno, resumo)
                            
                            # Criar link de download
                            filename = f"dashboard_{aluno['nome'].replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
                            st.markdown(get_download_link(pdf_bytes, filename), unsafe_allow_html=True)
                            
                            # Estilizar botão de download
                            st.markdown("""
                            <style>
                            .download-button {
                                display: inline-block;
                                padding: 0.5em 1em;
                                background-color: #0A4C92;
                                color: white;
                                text-decoration: none;
                                border-radius: 4px;
                                font-weight: bold;
                                margin-top: 10px;
                            }
                            .download-button:hover {
                                background-color: #083b73;
                            }
                            </style>
                            """, unsafe_allow_html=True)
                
                # Exibir dados do aluno
                st.markdown(f"### Dados do Aluno: {aluno['nome']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Matrícula:** {aluno['matricula'] or 'Não informada'}")
                    st.markdown(f"**Email:** {aluno['email']}")
                    st.markdown(f"**Orientador:** {aluno['orientador'] or 'Não informado'}")
                
                with col2:
                    st.markdown(f"**Linha de Pesquisa:** {aluno['linha_pesquisa'] or 'Não informada'}")
                    st.markdown(f"**Data de Ingresso:** {datetime.datetime.strptime(aluno['data_ingresso'], '%Y-%m-%d').strftime('%d/%m/%Y')}")
                    st.markdown(f"**Turma:** {aluno['turma'] or 'Não informada'}")
                    st.markdown(f"**Prazo Defesa Projeto:** {datetime.datetime.strptime(aluno['prazo_defesa_projeto'], '%Y-%m-%d').strftime('%d/%m/%Y') if aluno['prazo_defesa_projeto'] else 'Não informado'}")
                    st.markdown(f"**Prazo Defesa Tese:** {datetime.datetime.strptime(aluno['prazo_defesa_tese'], '%Y-%m-%d').strftime('%d/%m/%Y') if aluno['prazo_defesa_tese'] else 'Não informado'}")
                
                # Exibir resumo de aproveitamentos
                st.markdown("### Resumo de Aproveitamentos")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Card para disciplinas
                    st.markdown("""
                    <div style="background-color: #EBF5FF; padding: 15px; border-radius: 5px; border-left: 5px solid #0A4C92;">
                        <h4 style="color: #0A4C92; margin-top: 0;">Disciplinas</h4>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"**Total de disciplinas:** {resumo['disciplinas']['total']}")
                    st.markdown(f"**Créditos aproveitados:** {resumo['disciplinas']['creditos']}")
                    st.markdown(f"**Horas aproveitadas:** {resumo['disciplinas']['horas']}")
                    st.markdown(f"**Disciplinas deferidas:** {resumo['disciplinas']['deferidos']}")
                    st.markdown(f"**Disciplinas pendentes:** {resumo['disciplinas']['pendentes']}")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with col2:
                    # Card para idiomas
                    st.markdown("""
                    <div style="background-color: #EBF5FF; padding: 15px; border-radius: 5px; border-left: 5px solid #0A4C92;">
                        <h4 style="color: #0A4C92; margin-top: 0;">Idiomas</h4>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"**Total de idiomas:** {resumo['idiomas']['total']}")
                    st.markdown(f"**Idiomas aprovados:** {resumo['idiomas']['aprovados']}")
                    st.markdown(f"**Idiomas pendentes:** {resumo['idiomas']['pendentes']}")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # Gráfico de aproveitamentos
                if resumo['disciplinas']['total'] > 0 or resumo['idiomas']['total'] > 0:
                    st.markdown("### Gráficos de Aproveitamentos")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Gráfico de disciplinas
                        if resumo['disciplinas']['total'] > 0:
                            fig, ax = plt.subplots(figsize=(8, 5))
                            
                            labels = ['Deferidas', 'Pendentes']
                            sizes = [resumo['disciplinas']['deferidos'], resumo['disciplinas']['pendentes']]
                            colors = ['#0A4C92', '#EBF5FF']
                            
                            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                            ax.axis('equal')
                            plt.title('Status das Disciplinas')
                            
                            st.pyplot(fig)
                    
                    with col2:
                        # Gráfico de idiomas
                        if resumo['idiomas']['total'] > 0:
                            fig, ax = plt.subplots(figsize=(8, 5))
                            
                            labels = ['Aprovados', 'Pendentes']
                            sizes = [resumo['idiomas']['aprovados'], resumo['idiomas']['pendentes']]
                            colors = ['#0A4C92', '#EBF5FF']
                            
                            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                            ax.axis('equal')
                            plt.title('Status dos Idiomas')
                            
                            st.pyplot(fig)
                
                # Detalhes dos aproveitamentos
                st.markdown("### Detalhes dos Aproveitamentos")
                
                # Disciplinas
                if resumo['detalhes']['disciplinas']:
                    st.markdown("#### Disciplinas")
                    
                    # Converter para DataFrame
                    df_disciplinas = pd.DataFrame(resumo['detalhes']['disciplinas'])
                    
                    # Formatar status
                    status_map = {
                        'solicitado': 'Solicitado',
                        'aprovado_coordenacao': 'Aprovado (Coord.)',
                        'aprovado_colegiado': 'Aprovado (Coleg.)',
                        'deferido': 'Deferido',
                        'indeferido': 'Indeferido'
                    }
                    df_disciplinas['status'] = df_disciplinas['status'].map(status_map)
                    
                    # Renomear colunas
                    cols_display = {
                        'nome': 'Disciplina',
                        'codigo': 'Código',
                        'creditos': 'Créditos',
                        'horas': 'Horas',
                        'instituicao': 'Instituição',
                        'status': 'Status',
                        'processo': 'Processo'
                    }
                    
                    df_display = df_disciplinas.rename(columns=cols_display)
                    
                    # Exibir tabela
                    st.dataframe(df_display, hide_index=True)
                else:
                    st.info("Nenhuma disciplina cadastrada para este aluno.")
                
                # Idiomas
                if resumo['detalhes']['idiomas']:
                    st.markdown("#### Idiomas")
                    
                    # Converter para DataFrame
                    df_idiomas = pd.DataFrame(resumo['detalhes']['idiomas'])
                    
                    # Formatar status
                    df_idiomas['status'] = df_idiomas['status'].map(status_map)
                    
                    # Renomear colunas
                    cols_display = {
                        'idioma': 'Idioma',
                        'nota': 'Nota',
                        'instituicao': 'Instituição',
                        'status': 'Status',
                        'processo': 'Processo'
                    }
                    
                    df_display = df_idiomas.rename(columns=cols_display)
                    
                    # Exibir tabela
                    st.dataframe(df_display, hide_index=True)
                else:
                    st.info("Nenhum idioma cadastrado para este aluno.")
    
    # Página de Importação de Alunos
    elif st.session_state.current_page == 'importar':
        st.markdown('<div style="font-size: 2rem; font-weight: bold; margin-bottom: 1rem; color: #0A4C92;">Importação de Alunos</div>', unsafe_allow_html=True)
        
        st.markdown("""
        Esta funcionalidade permite importar alunos a partir de um arquivo Excel.
        
        **Instruções:**
        1. O arquivo Excel deve conter uma linha de cabeçalho com os campos: Matrícula, Nome, E-mail, Orientador(a), Linha de Pesquisa, Ingresso, Turma, Prazo defesa do Projeto, Prazo para Defesa da Tese
        2. Os alunos com e-mails já cadastrados serão ignorados para evitar duplicações
        3. Após o upload, será exibido um relatório com o resultado da importação
        """)
        
        uploaded_file = st.file_uploader("Selecione o arquivo Excel", type=["xlsx", "xls"])
        
        if uploaded_file is not None:
            if st.button("Importar Alunos"):
                with st.spinner("Importando alunos..."):
                    # Salvar o arquivo temporariamente
                    stats = import_alunos_from_excel(uploaded_file)
                    
                    if "error" in stats:
                        st.error(stats["error"])
                    else:
                        st.success(f"Importação concluída! {stats['importados']} alunos importados, {stats['ignorados']} ignorados.")
                        
                        if stats["erros"]:
                            with st.expander("Detalhes dos erros"):
                                for erro in stats["erros"]:
                                    st.warning(erro)
                        
                        # Exibir botão para voltar à lista de alunos
                        if st.button("Ver Lista de Alunos"):
                            set_page('alunos')
                            st.rerun()
