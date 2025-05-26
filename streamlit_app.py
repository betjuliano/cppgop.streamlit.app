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
import os
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
    # Remover banco de dados existente para garantir estrutura limpa
    if os.path.exists('ppgop.db'):
        os.remove('ppgop.db')
        print("Banco de dados antigo removido.")
    
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
    
    # Tabela de alunos com estrutura exata do Excel
    c.execute('''
    CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY,
        matricula TEXT UNIQUE,
        nivel TEXT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL,
        orientador TEXT,
        linha_pesquisa TEXT,
        data_ingresso DATE NOT NULL,
        turma TEXT,
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
    
    print("Banco de dados inicializado com sucesso.")

# Função para obter aluno por ID
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
            nivel = ?,
            nome = ?,
            email = ?,
            orientador = ?,
            linha_pesquisa = ?,
            data_ingresso = ?,
            turma = ?,
            prazo_defesa_projeto = ?,
            prazo_defesa_tese = ?,
            data_atualizacao = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (
            aluno_data['matricula'],
            aluno_data['nivel'],
            aluno_data['nome'],
            aluno_data['email'],
            aluno_data['orientador'],
            aluno_data['linha_pesquisa'],
            aluno_data['data_ingresso'],
            aluno_data['turma'],
            aluno_data['prazo_defesa_projeto'],
            aluno_data['prazo_defesa_tese'],
            aluno_id
        ))
    else:  # Inserir
        c.execute("""
        INSERT INTO alunos (
            matricula, nivel, nome, email, orientador, linha_pesquisa, 
            data_ingresso, turma, prazo_defesa_projeto, prazo_defesa_tese
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            aluno_data['matricula'],
            aluno_data['nivel'],
            aluno_data['nome'],
            aluno_data['email'],
            aluno_data['orientador'],
            aluno_data['linha_pesquisa'],
            aluno_data['data_ingresso'],
            aluno_data['turma'],
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

# Função para salvar aproveitamento
def save_aproveitamento(aproveitamento_data, aproveitamento_id=None):
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    if aproveitamento_id:  # Atualizar
        c.execute("""
        UPDATE aproveitamentos SET 
            aluno_id = ?,
            tipo = ?,
            nome_disciplina = ?,
            codigo_disciplina = ?,
            creditos = ?,
            idioma = ?,
            nota = ?,
            instituicao = ?,
            observacoes = ?,
            link_documentos = ?,
            numero_processo = ?,
            status = ?
        WHERE id = ?
        """, (
            aproveitamento_data['aluno_id'],
            aproveitamento_data['tipo'],
            aproveitamento_data.get('nome_disciplina'),
            aproveitamento_data.get('codigo_disciplina'),
            aproveitamento_data.get('creditos'),
            aproveitamento_data.get('idioma'),
            aproveitamento_data.get('nota'),
            aproveitamento_data.get('instituicao'),
            aproveitamento_data.get('observacoes'),
            aproveitamento_data.get('link_documentos'),
            aproveitamento_data.get('numero_processo'),
            aproveitamento_data.get('status', 'solicitado'),
            aproveitamento_id
        ))
    else:  # Inserir
        c.execute("""
        INSERT INTO aproveitamentos (
            aluno_id, tipo, nome_disciplina, codigo_disciplina, creditos,
            idioma, nota, instituicao, observacoes, link_documentos, numero_processo, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            aproveitamento_data['aluno_id'],
            aproveitamento_data['tipo'],
            aproveitamento_data.get('nome_disciplina'),
            aproveitamento_data.get('codigo_disciplina'),
            aproveitamento_data.get('creditos'),
            aproveitamento_data.get('idioma'),
            aproveitamento_data.get('nota'),
            aproveitamento_data.get('instituicao'),
            aproveitamento_data.get('observacoes'),
            aproveitamento_data.get('link_documentos'),
            aproveitamento_data.get('numero_processo'),
            aproveitamento_data.get('status', 'solicitado')
        ))
    
    conn.commit()
    conn.close()

# Função para obter aproveitamentos de um aluno
def get_aproveitamentos(aluno_id):
    conn = sqlite3.connect('ppgop.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM aproveitamentos WHERE aluno_id = ? ORDER BY data_solicitacao DESC", (aluno_id,))
    aproveitamentos = [dict(row) for row in c.fetchall()]
    
    conn.close()
    return aproveitamentos

# Função para obter resumo de aproveitamentos de um aluno
def get_resumo_aproveitamentos(aluno_id):
    aproveitamentos = get_aproveitamentos(aluno_id)
    
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
            resumo['detalhes']['disciplinas'].append({
                'id': aprov['id'],
                'nome': aprov['nome_disciplina'],
                'codigo': aprov['codigo_disciplina'],
                'creditos': aprov['creditos'],
                'horas': aprov['creditos'] * 15 if aprov['creditos'] else 0,  # 1 crédito = 15 horas
                'instituicao': aprov['instituicao'],
                'status': aprov['status'],
                'processo': aprov['numero_processo']
            })
            
            resumo['disciplinas']['total'] += 1
            
            if aprov['status'] == StatusAproveitamento.DEFERIDO:
                resumo['disciplinas']['deferidos'] += 1
                resumo['disciplinas']['creditos'] += aprov['creditos'] or 0
                resumo['disciplinas']['horas'] += (aprov['creditos'] or 0) * 15
            else:
                resumo['disciplinas']['pendentes'] += 1
                
        elif aprov['tipo'] == TipoAproveitamento.IDIOMA:
            resumo['detalhes']['idiomas'].append({
                'id': aprov['id'],
                'idioma': aprov['idioma'],
                'nota': aprov['nota'],
                'instituicao': aprov['instituicao'],
                'status': aprov['status'],
                'processo': aprov['numero_processo']
            })
            
            resumo['idiomas']['total'] += 1
            
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
    df = pd.read_excel(uploaded_file)
    
    # Remover linhas sem nome (provavelmente vazias)
    df = df[df["Nome"].notna()]
    
    # Conectar ao banco de dados
    conn = sqlite3.connect('ppgop.db')
    cursor = conn.cursor()
    
    # Estatísticas
    stats = {
        "total": len(df),
        "importados": 0,
        "ignorados": 0,
        "erros": []
    }
    
    # Inserir cada aluno no banco de dados
    for _, row in df.iterrows():
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
                prazo_defesa_tese = pd.to_datetime(row["Prazo para Defesa da tese"]).strftime('%Y-%m-%d') if pd.notna(row["Prazo para Defesa da tese"]) else None
            except:
                prazo_defesa_tese = None
                stats["erros"].append(f"Prazo de defesa de tese inválido para {row['Nome']}")
            
            # Inserir aluno
            cursor.execute("""
            INSERT INTO alunos (
                matricula, nivel, nome, email, orientador, linha_pesquisa, 
                data_ingresso, turma, prazo_defesa_projeto, prazo_defesa_tese
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["Matrícula"] if pd.notna(row["Matrícula"]) else None,
                nivel,
                row["Nome"],
                row["E-mail"],
                row["Orientador(a)"] if pd.notna(row["Orientador(a)"]) else None,
                row["Linha de Pesquisa"] if pd.notna(row["Linha de Pesquisa"]) else None,
                data_ingresso,
                turma,
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

# Função para verificar login
def check_login(username, password):
    conn = sqlite3.connect('ppgop.db')
    c = conn.cursor()
    
    # Hash da senha
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Verificar usuário e senha
    c.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", (username, password_hash))
    user = c.fetchone()
    
    conn.close()
    
    return user is not None

# Inicializar sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'current_page' not in st.session_state:
    st.session_state.current_page = 'login'

if 'show_aluno_form' not in st.session_state:
    st.session_state.show_aluno_form = False

if 'editing_aluno' not in st.session_state:
    st.session_state.editing_aluno = {}

if 'show_aproveitamento_form' not in st.session_state:
    st.session_state.show_aproveitamento_form = False

if 'editing_aproveitamento' not in st.session_state:
    st.session_state.editing_aproveitamento = {}

if 'selected_aluno_id' not in st.session_state:
    st.session_state.selected_aluno_id = None

if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = None

if 'confirm_delete_name' not in st.session_state:
    st.session_state.confirm_delete_name = None

# Inicializar banco de dados
init_db()

# Aplicação principal
if not st.session_state.logged_in:
    # Página de login
    st.title("PPGOP - Sistema de Gestão")
    
    # Formulário de login
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        
        if submitted:
            if check_login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")
else:
    # Cabeçalho
    display_header()
    
    # Sidebar
    with st.sidebar:
        st.write(f"Usuário: {st.session_state.username}")
        
        # Menu
        st.subheader("Menu")
        if st.button("Alunos"):
            set_page('alunos')
            st.session_state.show_aluno_form = False
            st.session_state.show_aproveitamento_form = False
            st.rerun()
            
        if st.button("Aproveitamentos"):
            set_page('aproveitamentos')
            st.session_state.show_aluno_form = False
            st.session_state.show_aproveitamento_form = False
            st.rerun()
            
        if st.button("Dashboard"):
            set_page('dashboard')
            st.session_state.show_aluno_form = False
            st.session_state.show_aproveitamento_form = False
            st.rerun()
            
        if st.button("Importar Alunos"):
            set_page('importar')
            st.session_state.show_aluno_form = False
            st.session_state.show_aproveitamento_form = False
            st.rerun()
            
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()
    
    # Conteúdo principal
    if st.session_state.current_page == 'alunos':
        st.title("Gestão de Alunos")
        
        if st.session_state.show_aluno_form:
            # Formulário de cadastro/edição de aluno
            st.subheader("Cadastro de Aluno")
            
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
                                       index=1 if st.session_state.editing_aluno.get('nivel', '').lower() == "doutorado" else 0)
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
                            'nivel': nivel,
                            'nome': nome,
                            'email': email,
                            'orientador': orientador,
                            'linha_pesquisa': linha_pesquisa,
                            'data_ingresso': data_ingresso.strftime('%Y-%m-%d'),
                            'turma': turma,
                            'prazo_defesa_projeto': prazo_defesa_projeto.strftime('%Y-%m-%d') if prazo_defesa_projeto else None,
                            'prazo_defesa_tese': prazo_defesa_tese.strftime('%Y-%m-%d') if prazo_defesa_tese else None
                        }
                        
                        save_aluno(aluno_data, aluno_id)
                        st.session_state.show_aluno_form = False
                        st.success("Aluno salvo com sucesso!")
                        st.rerun()
        else:
            # Tabela de alunos
            st.subheader("Alunos Cadastrados")
            
            # Botões de ação
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("➕ Novo Aluno"):
                    st.session_state.show_aluno_form = True
                    st.session_state.editing_aluno = {}
                    st.rerun()
            
            # Tabela de alunos
            conn = sqlite3.connect('ppgop.db')
            alunos_df = pd.read_sql_query("SELECT * FROM alunos ORDER BY nome", conn)
            conn.close()
            
            if not alunos_df.empty:
                # Formatar datas para exibição
                for col in ['data_ingresso', 'prazo_defesa_projeto', 'prazo_defesa_tese']:
                    alunos_df[col] = pd.to_datetime(alunos_df[col], errors='coerce').dt.strftime('%d/%m/%Y')
                
                # Renomear colunas para exibição
                alunos_df = alunos_df.rename(columns={
                    'matricula': 'Matrícula',
                    'nivel': 'Nível',
                    'nome': 'Nome',
                    'email': 'Email',
                    'orientador': 'Orientador',
                    'linha_pesquisa': 'Linha de Pesquisa',
                    'data_ingresso': 'Data de Ingresso',
                    'turma': 'Turma',
                    'prazo_defesa_projeto': 'Prazo Projeto',
                    'prazo_defesa_tese': 'Prazo Tese'
                })
                
                # Selecionar colunas para exibição
                display_cols = ['Matrícula', 'Nível', 'Nome', 'Email', 'Orientador', 'Linha de Pesquisa', 'Data de Ingresso', 'Turma', 'Prazo Projeto', 'Prazo Tese']
                
                # Adicionar coluna de ações
                alunos_df['Ações'] = None
                
                # Exibir tabela com formatação
                for i, row in alunos_df.iterrows():
                    cols = st.columns([1.5, 1.5, 3, 3, 3, 3, 2, 1.5, 2, 2, 2.5])
                    
                    for j, col in enumerate(display_cols):
                        with cols[j]:
                            st.write(row[col] if pd.notna(row[col]) else "-")
                    
                    with cols[-1]:
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✏️", key=f"edit_{row['id']}"):
                                # Converter para formato Python
                                aluno = {
                                    'id': row['id'],
                                    'matricula': row['Matrícula'] if pd.notna(row['Matrícula']) else '',
                                    'nivel': row['Nível'] if pd.notna(row['Nível']) else '',
                                    'nome': row['Nome'],
                                    'email': row['Email'],
                                    'orientador': row['Orientador'] if pd.notna(row['Orientador']) else '',
                                    'linha_pesquisa': row['Linha de Pesquisa'] if pd.notna(row['Linha de Pesquisa']) else '',
                                    'data_ingresso': datetime.datetime.strptime(row['Data de Ingresso'], '%d/%m/%Y').strftime('%Y-%m-%d') if pd.notna(row['Data de Ingresso']) else None,
                                    'turma': row['Turma'] if pd.notna(row['Turma']) else '',
                                    'prazo_defesa_projeto': datetime.datetime.strptime(row['Prazo Projeto'], '%d/%m/%Y').strftime('%Y-%m-%d') if pd.notna(row['Prazo Projeto']) else None,
                                    'prazo_defesa_tese': datetime.datetime.strptime(row['Prazo Tese'], '%d/%m/%Y').strftime('%Y-%m-%d') if pd.notna(row['Prazo Tese']) else None
                                }
                                st.session_state.editing_aluno = aluno
                                st.session_state.show_aluno_form = True
                                st.rerun()
                        with col2:
                            if st.button("🗑️", key=f"delete_{row['id']}"):
                                st.session_state.confirm_delete = row['id']
                                st.session_state.confirm_delete_name = row['Nome']
                                st.rerun()
                
                # Confirmação de exclusão
                if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
                    st.warning(f"Tem certeza que deseja excluir o aluno {st.session_state.confirm_delete_name}? Esta ação não pode ser desfeita.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Sim, excluir"):
                            delete_aluno(st.session_state.confirm_delete)
                            st.session_state.confirm_delete = None
                            st.session_state.confirm_delete_name = None
                            st.success("Aluno excluído com sucesso!")
                            st.rerun()
                    with col2:
                        if st.button("Cancelar"):
                            st.session_state.confirm_delete = None
                            st.session_state.confirm_delete_name = None
                            st.rerun()
            else:
                st.info("Nenhum aluno cadastrado. Clique em 'Novo Aluno' para adicionar.")
    
    elif st.session_state.current_page == 'aproveitamentos':
        st.title("Aproveitamentos de Disciplinas e Idiomas")
        
        # Selecionar aluno
        conn = sqlite3.connect('ppgop.db')
        alunos_df = pd.read_sql_query("SELECT id, nome FROM alunos ORDER BY nome", conn)
        conn.close()
        
        if alunos_df.empty:
            st.warning("Nenhum aluno cadastrado. Cadastre um aluno primeiro.")
        else:
            aluno_options = alunos_df['nome'].tolist()
            aluno_ids = alunos_df['id'].tolist()
            
            selected_aluno_name = st.selectbox("Selecione um aluno", aluno_options)
            selected_aluno_index = aluno_options.index(selected_aluno_name)
            selected_aluno_id = aluno_ids[selected_aluno_index]
            
            st.session_state.selected_aluno_id = selected_aluno_id
            
            # Exibir aproveitamentos do aluno
            aproveitamentos = get_aproveitamentos(selected_aluno_id)
            
            # Botões de ação
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button("➕ Nova Disciplina"):
                    st.session_state.show_aproveitamento_form = True
                    st.session_state.editing_aproveitamento = {
                        'aluno_id': selected_aluno_id,
                        'tipo': TipoAproveitamento.DISCIPLINA
                    }
                    st.rerun()
            with col2:
                if st.button("➕ Novo Idioma"):
                    st.session_state.show_aproveitamento_form = True
                    st.session_state.editing_aproveitamento = {
                        'aluno_id': selected_aluno_id,
                        'tipo': TipoAproveitamento.IDIOMA
                    }
                    st.rerun()
            
            if st.session_state.show_aproveitamento_form:
                # Formulário de cadastro/edição de aproveitamento
                tipo = st.session_state.editing_aproveitamento.get('tipo', TipoAproveitamento.DISCIPLINA)
                aproveitamento_id = st.session_state.editing_aproveitamento.get('id', None)
                
                if tipo == TipoAproveitamento.DISCIPLINA:
                    st.subheader("Cadastro de Aproveitamento de Disciplina")
                else:
                    st.subheader("Cadastro de Aproveitamento de Idioma")
                
                with st.form("aproveitamento_form"):
                    col1, col2 = st.columns(2)
                    
                    if tipo == TipoAproveitamento.DISCIPLINA:
                        with col1:
                            nome_disciplina = st.text_input("Nome da Disciplina", value=st.session_state.editing_aproveitamento.get('nome_disciplina', ''))
                            codigo_disciplina = st.text_input("Código da Disciplina", value=st.session_state.editing_aproveitamento.get('codigo_disciplina', ''))
                            creditos = st.number_input("Créditos", min_value=0, value=st.session_state.editing_aproveitamento.get('creditos', 0))
                            instituicao = st.text_input("Instituição", value=st.session_state.editing_aproveitamento.get('instituicao', ''))
                        
                        with col2:
                            observacoes = st.text_area("Observações", value=st.session_state.editing_aproveitamento.get('observacoes', ''))
                            link_documentos = st.text_input("Link para Documentos", value=st.session_state.editing_aproveitamento.get('link_documentos', ''))
                            numero_processo = st.text_input("Número do Processo", value=st.session_state.editing_aproveitamento.get('numero_processo', ''))
                            status = st.selectbox("Status", 
                                               options=[s.value for s in StatusAproveitamento],
                                               index=[s.value for s in StatusAproveitamento].index(st.session_state.editing_aproveitamento.get('status', 'solicitado')) if st.session_state.editing_aproveitamento.get('status') in [s.value for s in StatusAproveitamento] else 0)
                    else:  # Idioma
                        with col1:
                            idioma = st.text_input("Idioma", value=st.session_state.editing_aproveitamento.get('idioma', ''))
                            nota = st.number_input("Nota", min_value=0.0, max_value=10.0, value=float(st.session_state.editing_aproveitamento.get('nota', 0.0)))
                            instituicao = st.text_input("Instituição", value=st.session_state.editing_aproveitamento.get('instituicao', ''))
                        
                        with col2:
                            observacoes = st.text_area("Observações", value=st.session_state.editing_aproveitamento.get('observacoes', ''))
                            link_documentos = st.text_input("Link para Documentos", value=st.session_state.editing_aproveitamento.get('link_documentos', ''))
                            numero_processo = st.text_input("Número do Processo", value=st.session_state.editing_aproveitamento.get('numero_processo', ''))
                            status = st.selectbox("Status", 
                                               options=[s.value for s in StatusAproveitamento],
                                               index=[s.value for s in StatusAproveitamento].index(st.session_state.editing_aproveitamento.get('status', 'solicitado')) if st.session_state.editing_aproveitamento.get('status') in [s.value for s in StatusAproveitamento] else 0)
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        submitted = st.form_submit_button("Salvar")
                    with col2:
                        if st.form_submit_button("Cancelar"):
                            st.session_state.show_aproveitamento_form = False
                            st.rerun()
                    
                    if submitted:
                        if tipo == TipoAproveitamento.DISCIPLINA and not nome_disciplina:
                            st.error("Nome da disciplina é obrigatório")
                        elif tipo == TipoAproveitamento.IDIOMA and not idioma:
                            st.error("Idioma é obrigatório")
                        else:
                            aproveitamento_data = {
                                'aluno_id': selected_aluno_id,
                                'tipo': tipo,
                                'status': status
                            }
                            
                            if tipo == TipoAproveitamento.DISCIPLINA:
                                aproveitamento_data.update({
                                    'nome_disciplina': nome_disciplina,
                                    'codigo_disciplina': codigo_disciplina,
                                    'creditos': creditos,
                                    'instituicao': instituicao,
                                    'observacoes': observacoes,
                                    'link_documentos': link_documentos,
                                    'numero_processo': numero_processo
                                })
                            else:  # Idioma
                                aproveitamento_data.update({
                                    'idioma': idioma,
                                    'nota': nota,
                                    'instituicao': instituicao,
                                    'observacoes': observacoes,
                                    'link_documentos': link_documentos,
                                    'numero_processo': numero_processo
                                })
                            
                            save_aproveitamento(aproveitamento_data, aproveitamento_id)
                            st.session_state.show_aproveitamento_form = False
                            st.success("Aproveitamento salvo com sucesso!")
                            st.rerun()
            else:
                # Exibir aproveitamentos
                if not aproveitamentos:
                    st.info("Nenhum aproveitamento cadastrado para este aluno.")
                else:
                    # Separar por tipo
                    disciplinas = [a for a in aproveitamentos if a['tipo'] == TipoAproveitamento.DISCIPLINA]
                    idiomas = [a for a in aproveitamentos if a['tipo'] == TipoAproveitamento.IDIOMA]
                    
                    # Mapeamento de status
                    status_map = {
                        'solicitado': 'Solicitado',
                        'aprovado_coordenacao': 'Aprovado (Coord.)',
                        'aprovado_colegiado': 'Aprovado (Coleg.)',
                        'deferido': 'Deferido',
                        'indeferido': 'Indeferido'
                    }
                    
                    # Exibir disciplinas
                    if disciplinas:
                        st.subheader("Disciplinas")
                        for i, disc in enumerate(disciplinas):
                            with st.expander(f"{disc['nome_disciplina']} ({disc['codigo_disciplina'] or 'Sem código'})"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Créditos:** {disc['creditos'] or 0}")
                                    st.write(f"**Instituição:** {disc['instituicao'] or '-'}")
                                    st.write(f"**Status:** {status_map.get(disc['status'], disc['status'])}")
                                with col2:
                                    st.write(f"**Processo:** {disc['numero_processo'] or '-'}")
                                    st.write(f"**Observações:** {disc['observacoes'] or '-'}")
                                    if disc['link_documentos']:
                                        st.write(f"**Documentos:** [Link]({disc['link_documentos']})")
                                
                                # Botões de ação
                                col1, col2 = st.columns([1, 5])
                                with col1:
                                    if st.button("Editar", key=f"edit_disc_{disc['id']}"):
                                        st.session_state.show_aproveitamento_form = True
                                        st.session_state.editing_aproveitamento = disc
                                        st.rerun()
                    
                    # Exibir idiomas
                    if idiomas:
                        st.subheader("Idiomas")
                        for i, idioma in enumerate(idiomas):
                            with st.expander(f"{idioma['idioma']} (Nota: {idioma['nota'] or '-'})"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Instituição:** {idioma['instituicao'] or '-'}")
                                    st.write(f"**Status:** {status_map.get(idioma['status'], idioma['status'])}")
                                with col2:
                                    st.write(f"**Processo:** {idioma['numero_processo'] or '-'}")
                                    st.write(f"**Observações:** {idioma['observacoes'] or '-'}")
                                    if idioma['link_documentos']:
                                        st.write(f"**Documentos:** [Link]({idioma['link_documentos']})")
                                
                                # Botões de ação
                                col1, col2 = st.columns([1, 5])
                                with col1:
                                    if st.button("Editar", key=f"edit_idioma_{idioma['id']}"):
                                        st.session_state.show_aproveitamento_form = True
                                        st.session_state.editing_aproveitamento = idioma
                                        st.rerun()
    
    elif st.session_state.current_page == 'dashboard':
        st.title("Dashboard")
        
        # Selecionar aluno
        conn = sqlite3.connect('ppgop.db')
        alunos_df = pd.read_sql_query("SELECT id, nome FROM alunos ORDER BY nome", conn)
        conn.close()
        
        if alunos_df.empty:
            st.warning("Nenhum aluno cadastrado. Cadastre um aluno primeiro.")
        else:
            aluno_options = alunos_df['nome'].tolist()
            aluno_ids = alunos_df['id'].tolist()
            
            selected_aluno_name = st.selectbox("Selecione um aluno", aluno_options)
            selected_aluno_index = aluno_options.index(selected_aluno_name)
            selected_aluno_id = aluno_ids[selected_aluno_index]
            
            # Obter dados do aluno
            aluno = get_aluno(selected_aluno_id)
            
            if aluno:
                # Obter resumo de aproveitamentos
                resumo = get_resumo_aproveitamentos(selected_aluno_id)
                
                # Botão para exportar PDF
                if st.button("📄 Exportar PDF"):
                    try:
                        pdf_bytes = gerar_pdf_dashboard(aluno, resumo)
                        st.markdown(get_download_link(pdf_bytes, f"dashboard_{aluno['nome']}.pdf"), unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF: {str(e)}")
                
                # Exibir dados do aluno
                st.subheader("Dados do Aluno")
                col1, col2 = st.columns(2)
                
                # Formatar datas
                data_ingresso = datetime.datetime.strptime(aluno['data_ingresso'], '%Y-%m-%d').strftime('%d/%m/%Y') if aluno['data_ingresso'] else 'Não informada'
                prazo_projeto = datetime.datetime.strptime(aluno['prazo_defesa_projeto'], '%Y-%m-%d').strftime('%d/%m/%Y') if aluno['prazo_defesa_projeto'] else 'Não informado'
                prazo_tese = datetime.datetime.strptime(aluno['prazo_defesa_tese'], '%Y-%m-%d').strftime('%d/%m/%Y') if aluno['prazo_defesa_tese'] else 'Não informado'
                
                with col1:
                    st.write(f"**Nome:** {aluno['nome']}")
                    st.write(f"**Matrícula:** {aluno['matricula'] or 'Não informada'}")
                    st.write(f"**Email:** {aluno['email']}")
                    st.write(f"**Orientador:** {aluno['orientador'] or 'Não informado'}")
                    st.write(f"**Linha de Pesquisa:** {aluno['linha_pesquisa'] or 'Não informada'}")
                
                with col2:
                    st.write(f"**Data de Ingresso:** {data_ingresso}")
                    st.write(f"**Turma:** {aluno['turma'] or 'Não informada'}")
                    st.write(f"**Nível:** {aluno['nivel'] or 'Não informado'}")
                    st.write(f"**Prazo Defesa Projeto:** {prazo_projeto}")
                    st.write(f"**Prazo Defesa Tese:** {prazo_tese}")
                
                # Exibir resumo de aproveitamentos
                st.subheader("Resumo de Aproveitamentos")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("### Disciplinas")
                    st.write(f"**Total de disciplinas:** {resumo['disciplinas']['total']}")
                    st.write(f"**Créditos aproveitados:** {resumo['disciplinas']['creditos']}")
                    st.write(f"**Horas aproveitadas:** {resumo['disciplinas']['horas']}")
                    st.write(f"**Disciplinas deferidas:** {resumo['disciplinas']['deferidos']}")
                    st.write(f"**Disciplinas pendentes:** {resumo['disciplinas']['pendentes']}")
                
                with col2:
                    st.write("### Idiomas")
                    st.write(f"**Total de idiomas:** {resumo['idiomas']['total']}")
                    st.write(f"**Idiomas aprovados:** {resumo['idiomas']['aprovados']}")
                    st.write(f"**Idiomas pendentes:** {resumo['idiomas']['pendentes']}")
                
                # Gráficos
                if resumo['disciplinas']['total'] > 0 or resumo['idiomas']['total'] > 0:
                    st.subheader("Gráficos")
                    col1, col2 = st.columns(2)
                    
                    # Gráfico de disciplinas
                    if resumo['disciplinas']['total'] > 0:
                        with col1:
                            fig, ax = plt.subplots()
                            labels = ['Deferidas', 'Pendentes']
                            sizes = [resumo['disciplinas']['deferidos'], resumo['disciplinas']['pendentes']]
                            colors = ['#0A4C92', '#EBF5FF']
                            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                            ax.axis('equal')
                            plt.title('Status das Disciplinas')
                            st.pyplot(fig)
                    
                    # Gráfico de idiomas
                    if resumo['idiomas']['total'] > 0:
                        with col2:
                            fig, ax = plt.subplots()
                            labels = ['Aprovados', 'Pendentes']
                            sizes = [resumo['idiomas']['aprovados'], resumo['idiomas']['pendentes']]
                            colors = ['#0A4C92', '#EBF5FF']
                            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                            ax.axis('equal')
                            plt.title('Status dos Idiomas')
                            st.pyplot(fig)
                
                # Detalhes dos aproveitamentos
                st.subheader("Detalhes dos Aproveitamentos")
                
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
                    st.write("### Disciplinas")
                    
                    # Criar DataFrame para exibição
                    disc_df = pd.DataFrame(resumo['detalhes']['disciplinas'])
                    disc_df['status'] = disc_df['status'].map(lambda x: status_map.get(x, x))
                    disc_df['horas'] = disc_df['creditos'] * 15
                    
                    # Renomear colunas
                    disc_df = disc_df.rename(columns={
                        'nome': 'Disciplina',
                        'codigo': 'Código',
                        'creditos': 'Créditos',
                        'horas': 'Horas',
                        'instituicao': 'Instituição',
                        'status': 'Status',
                        'processo': 'Processo'
                    })
                    
                    # Selecionar colunas para exibição
                    display_cols = ['Disciplina', 'Código', 'Créditos', 'Horas', 'Instituição', 'Status', 'Processo']
                    st.dataframe(disc_df[display_cols])
                else:
                    st.info("Nenhuma disciplina cadastrada para este aluno.")
                
                # Idiomas
                if resumo['detalhes']['idiomas']:
                    st.write("### Idiomas")
                    
                    # Criar DataFrame para exibição
                    idioma_df = pd.DataFrame(resumo['detalhes']['idiomas'])
                    idioma_df['status'] = idioma_df['status'].map(lambda x: status_map.get(x, x))
                    
                    # Renomear colunas
                    idioma_df = idioma_df.rename(columns={
                        'idioma': 'Idioma',
                        'nota': 'Nota',
                        'instituicao': 'Instituição',
                        'status': 'Status',
                        'processo': 'Processo'
                    })
                    
                    # Selecionar colunas para exibição
                    display_cols = ['Idioma', 'Nota', 'Instituição', 'Status', 'Processo']
                    st.dataframe(idioma_df[display_cols])
                else:
                    st.info("Nenhum idioma cadastrado para este aluno.")
    
    elif st.session_state.current_page == 'importar':
        st.title("Importação de Alunos")
        
        st.write("Esta funcionalidade permite importar alunos a partir de um arquivo Excel.")
        
        st.write("### Instruções:")
        st.write("- O arquivo Excel deve conter uma linha de cabeçalho com os campos: Matrícula, Nível, Nome, E-mail, Orientador(a), Linha de Pesquisa, Ingresso, Turma, Prazo defesa do Projeto, Prazo para Defesa da Tese")
        st.write("- Os alunos com e-mails já cadastrados serão ignorados para evitar duplicações")
        st.write("- Após o upload, será exibido um relatório com o resultado da importação")
        
        uploaded_file = st.file_uploader("Selecione o arquivo Excel", type=['xlsx', 'xls'])
        
        if uploaded_file is not None:
            if st.button("Importar Alunos"):
                stats = import_alunos_from_excel(uploaded_file)
                
                if "error" in stats:
                    st.error(stats["error"])
                else:
                    st.success(f"Importação concluída! {stats['importados']} alunos importados, {stats['ignorados']} ignorados.")
                    
                    if stats["erros"]:
                        st.write("### Detalhes dos erros")
                        for erro in stats["erros"]:
                            st.write(erro)
