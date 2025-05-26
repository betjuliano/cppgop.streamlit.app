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

# --- Configurações e Constantes ---
DB_FILE = 'ppgop.db'
HEADER_IMAGE_PATH = 'assets/header.jpg'
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf' # Caminho para fonte TTF que suporte caracteres especiais

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

# --- Funções de Banco de Dados ---

def init_db():
    """Inicializa o banco de dados, apagando o antigo e criando a nova estrutura."""
    # Remover banco de dados existente para garantir estrutura limpa
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
            print(f"Banco de dados antigo '{DB_FILE}' removido.")
        except OSError as e:
            print(f"Erro ao remover o banco de dados antigo: {e}")
            st.error(f"Erro ao tentar remover o banco de dados antigo. Verifique as permissões. Detalhes: {e}")
            return # Impede a continuação se não puder remover o DB antigo

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        # Tabela de usuários
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        ''')

        # Tabela de alunos (estrutura alinhada ao Excel)
        # Nomes das colunas normalizados (lowercase, sem espaços/acentos)
        c.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY,
            matricula TEXT UNIQUE,
            nivel TEXT, -- 'Mestrado' ou 'Doutorado'
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE, -- Email deve ser único
            orientador TEXT,
            linha_pesquisa TEXT,
            data_ingresso DATE, -- Data de Ingresso
            turma TEXT, -- Turma (pode ser ano ou outra identificação)
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
            tipo TEXT NOT NULL, -- 'disciplina' ou 'idioma'
            nome_disciplina TEXT,
            codigo_disciplina TEXT,
            creditos INTEGER,
            idioma TEXT,
            nota REAL,
            instituicao TEXT,
            observacoes TEXT,
            link_documentos TEXT,
            numero_processo TEXT,
            status TEXT DEFAULT 'solicitado', -- Usar StatusAproveitamento
            data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_aprovacao_coordenacao TIMESTAMP,
            data_aprovacao_colegiado TIMESTAMP,
            data_deferimento TIMESTAMP,
            FOREIGN KEY (aluno_id) REFERENCES alunos (id) ON DELETE CASCADE
        )
        ''')

        # Trigger para atualizar data_atualizacao na tabela alunos
        c.execute('''
        CREATE TRIGGER IF NOT EXISTS update_alunos_timestamp
        AFTER UPDATE ON alunos
        FOR EACH ROW
        BEGIN
            UPDATE alunos SET data_atualizacao = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        ''')

        # Inserir usuários padrão se não existirem
        users_to_insert = [
            ("Breno", "adm123"),
            ("PPGOP", "123curso")
        ]
        for username, password in users_to_insert:
            c.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
            if c.fetchone()[0] == 0:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))

        conn.commit()
        print("Banco de dados inicializado/atualizado com sucesso.")

    except sqlite3.Error as e:
        print(f"Erro durante a inicialização do banco de dados: {e}")
        st.error(f"Erro crítico ao inicializar o banco de dados: {e}")
    finally:
        conn.close()

def get_db_connection():
    """Retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row # Retorna dicionários em vez de tuplas
    return conn

def get_all_alunos():
    """Retorna todos os alunos ordenados por nome."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, nome FROM alunos ORDER BY nome")
    alunos = c.fetchall()
    conn.close()
    return alunos

def get_aluno(aluno_id):
    """Retorna os dados de um aluno específico."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM alunos WHERE id = ?", (aluno_id,))
    aluno = c.fetchone()
    conn.close()
    return dict(aluno) if aluno else None

def save_aluno(aluno_data, aluno_id=None):
    """Salva (insere ou atualiza) os dados de um aluno."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Garantir que as datas sejam None se vazias
        for key in ['data_ingresso', 'prazo_defesa_projeto', 'prazo_defesa_tese']:
            if key in aluno_data and not aluno_data[key]:
                aluno_data[key] = None

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
                prazo_defesa_tese = ?
                -- data_atualizacao é atualizada pelo trigger
            WHERE id = ?
            """, (
                aluno_data.get('matricula'),
                aluno_data.get('nivel'),
                aluno_data.get('nome'),
                aluno_data.get('email'),
                aluno_data.get('orientador'),
                aluno_data.get('linha_pesquisa'),
                aluno_data.get('data_ingresso'),
                aluno_data.get('turma'),
                aluno_data.get('prazo_defesa_projeto'),
                aluno_data.get('prazo_defesa_tese'),
                aluno_id
            ))
            print(f"Aluno ID {aluno_id} atualizado.")
        else:  # Inserir
            c.execute("""
            INSERT INTO alunos (
                matricula, nivel, nome, email, orientador, linha_pesquisa,
                data_ingresso, turma, prazo_defesa_projeto, prazo_defesa_tese
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                aluno_data.get('matricula'),
                aluno_data.get('nivel'),
                aluno_data.get('nome'),
                aluno_data.get('email'),
                aluno_data.get('orientador'),
                aluno_data.get('linha_pesquisa'),
                aluno_data.get('data_ingresso'),
                aluno_data.get('turma'),
                aluno_data.get('prazo_defesa_projeto'),
                aluno_data.get('prazo_defesa_tese')
            ))
            aluno_id = c.lastrowid # Pega o ID do aluno inserido
            print(f"Novo aluno inserido com ID {aluno_id}.")

        conn.commit()
        return aluno_id # Retorna o ID do aluno salvo/atualizado

    except sqlite3.IntegrityError as e:
        conn.rollback() # Desfaz a transação em caso de erro
        print(f"Erro de integridade ao salvar aluno: {e}")
        if "UNIQUE constraint failed: alunos.email" in str(e):
            st.error(f"Erro: Já existe um aluno cadastrado com o e-mail '{aluno_data.get('email')}'.")
        elif "UNIQUE constraint failed: alunos.matricula" in str(e):
            st.error(f"Erro: Já existe um aluno cadastrado com a matrícula '{aluno_data.get('matricula')}'.")
        else:
            st.error(f"Erro ao salvar aluno: {e}")
        return None
    except Exception as e:
        conn.rollback()
        print(f"Erro inesperado ao salvar aluno: {e}")
        st.error(f"Ocorreu um erro inesperado ao salvar o aluno: {e}")
        return None
    finally:
        conn.close()

def delete_aluno(aluno_id):
    """Exclui um aluno e seus aproveitamentos associados."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Excluir o aluno (ON DELETE CASCADE cuidará dos aproveitamentos)
        c.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
        conn.commit()
        print(f"Aluno ID {aluno_id} excluído.")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Erro ao excluir aluno ID {aluno_id}: {e}")
        st.error(f"Erro ao excluir aluno: {e}")
        return False
    finally:
        conn.close()

def save_aproveitamento(aproveitamento_data, aproveitamento_id=None):
    """Salva (insere ou atualiza) um aproveitamento."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
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
                -- Datas são atualizadas conforme o fluxo
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
                aproveitamento_data.get('status', StatusAproveitamento.SOLICITADO.value),
                aproveitamento_id
            ))
            print(f"Aproveitamento ID {aproveitamento_id} atualizado.")
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
                aproveitamento_data.get('status', StatusAproveitamento.SOLICITADO.value)
            ))
            aproveitamento_id = c.lastrowid
            print(f"Novo aproveitamento inserido com ID {aproveitamento_id}.")

        conn.commit()
        return aproveitamento_id
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar aproveitamento: {e}")
        st.error(f"Erro ao salvar aproveitamento: {e}")
        return None
    finally:
        conn.close()

def get_aproveitamentos(aluno_id):
    """Retorna todos os aproveitamentos de um aluno."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM aproveitamentos WHERE aluno_id = ? ORDER BY data_solicitacao DESC", (aluno_id,))
    aproveitamentos = [dict(row) for row in c.fetchall()]
    conn.close()
    return aproveitamentos

def get_resumo_aproveitamentos(aluno_id):
    """Calcula e retorna um resumo dos aproveitamentos de um aluno."""
    aproveitamentos = get_aproveitamentos(aluno_id)
    resumo = {
        'disciplinas': {'total': 0, 'creditos': 0, 'horas': 0, 'deferidos': 0, 'pendentes': 0},
        'idiomas': {'total': 0, 'aprovados': 0, 'pendentes': 0},
        'detalhes': {'disciplinas': [], 'idiomas': []}
    }

    for aprov in aproveitamentos:
        if aprov['tipo'] == TipoAproveitamento.DISCIPLINA.value:
            creditos = aprov['creditos'] or 0
            horas = creditos * 15
            resumo['detalhes']['disciplinas'].append({
                'id': aprov['id'], 'nome': aprov['nome_disciplina'], 'codigo': aprov['codigo_disciplina'],
                'creditos': creditos, 'horas': horas, 'instituicao': aprov['instituicao'],
                'status': aprov['status'], 'processo': aprov['numero_processo']
            })
            resumo['disciplinas']['total'] += 1
            if aprov['status'] == StatusAproveitamento.DEFERIDO.value:
                resumo['disciplinas']['deferidos'] += 1
                resumo['disciplinas']['creditos'] += creditos
                resumo['disciplinas']['horas'] += horas
            else:
                resumo['disciplinas']['pendentes'] += 1
        elif aprov['tipo'] == TipoAproveitamento.IDIOMA.value:
            resumo['detalhes']['idiomas'].append({
                'id': aprov['id'], 'idioma': aprov['idioma'], 'nota': aprov['nota'],
                'instituicao': aprov['instituicao'], 'status': aprov['status'], 'processo': aprov['numero_processo']
            })
            resumo['idiomas']['total'] += 1
            if aprov['status'] == StatusAproveitamento.DEFERIDO.value:
                resumo['idiomas']['aprovados'] += 1
            else:
                resumo['idiomas']['pendentes'] += 1
    return resumo

# --- Funções de Importação ---

def normalize_column_name(name):
    """Normaliza nomes de colunas: lowercase, remove espaços extras e acentos básicos."""
    if not isinstance(name, str):
        return str(name)
    name = name.strip().lower()
    # Mapeamento simples para remover acentos comuns e substituir espaços
    replacements = {
        ' ': '_', '(': '', ')': '', 'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'â': 'a', 'ê': 'e', 'ô': 'o', 'ã': 'a', 'õ': 'o', 'ç': 'c', '?': '', '/': '_'
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name

def import_alunos_from_excel(uploaded_file):
    """Importa alunos do arquivo Excel, tratando nomes de colunas e dados."""
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Erro ao ler o arquivo Excel: {e}")
        return {"total": 0, "importados": 0, "ignorados": 0, "erros": [f"Falha na leitura do Excel: {e}"]}

    # Normalizar nomes das colunas do DataFrame
    df.columns = [normalize_column_name(col) for col in df.columns]

    # Mapeamento esperado (normalizado) para colunas do DB
    column_mapping = {
        'matricula': 'matricula',
        'nivel': 'nivel',
        'nome': 'nome',
        'e-mail': 'email', # Normalizado do Excel
        'orientadora': 'orientador', # Normalizado do Excel
        'linha_de_pesquisa': 'linha_pesquisa', # Normalizado do Excel
        'ingresso': 'data_ingresso', # Normalizado do Excel
        'turma': 'turma',
        'prazo_defesa_do_projeto': 'prazo_defesa_projeto', # Normalizado do Excel
        'prazo_para_defesa_da_tese': 'prazo_defesa_tese' # Normalizado do Excel
    }

    # Verificar se as colunas essenciais existem (após normalização)
    required_cols_normalized = ['nome', 'e-mail', 'ingresso'] # Adicione outras se necessário
    missing_cols = [col for col in required_cols_normalized if col not in df.columns]
    if missing_cols:
        st.error(f"Erro: Colunas obrigatórias não encontradas no Excel (após normalização): {', '.join(missing_cols)}. Colunas encontradas: {', '.join(df.columns)}")
        return {"total": 0, "importados": 0, "ignorados": 0, "erros": [f"Colunas faltando: {', '.join(missing_cols)}"]}

    df = df[df["nome"].notna()] # Remover linhas sem nome
    conn = get_db_connection()
    cursor = conn.cursor()
    stats = {"total": len(df), "importados": 0, "ignorados": 0, "erros": []}

    for index, row in df.iterrows():
        aluno_data = {}
        valid = True
        error_details = []

        # Mapear dados da linha para o formato do banco
        for excel_col, db_col in column_mapping.items():
            if excel_col in df.columns:
                aluno_data[db_col] = row[excel_col] if pd.notna(row[excel_col]) else None
            else:
                aluno_data[db_col] = None # Coluna não encontrada no Excel

        # Validações e Formatações
        if not aluno_data.get('nome'):
            error_details.append("Nome ausente")
            valid = False
        if not aluno_data.get('email'):
            error_details.append("E-mail ausente")
            valid = False

        # Tratar Nível (capitalizar se for 'mestrado' ou 'doutorado')
        nivel_val = str(aluno_data.get('nivel', '')).strip().capitalize()
        if nivel_val in ['Mestrado', 'Doutorado']:
            aluno_data['nivel'] = nivel_val
        else:
            aluno_data['nivel'] = None # Ou um valor padrão, ou erro
            # error_details.append(f"Nível inválido: '{aluno_data.get('nivel')}'")
            # valid = False # Descomente se nível for obrigatório

        # Tratar Datas
        for col_name in ['data_ingresso', 'prazo_defesa_projeto', 'prazo_defesa_tese']:
            date_val = aluno_data.get(col_name)
            if pd.notna(date_val):
                try:
                    # Tenta converter para datetime e depois formata
                    aluno_data[col_name] = pd.to_datetime(date_val).strftime('%Y-%m-%d')
                except Exception as e:
                    error_details.append(f"Formato de data inválido para {col_name}: {date_val} ({e})")
                    aluno_data[col_name] = None # Define como None se inválido
                    # valid = False # Descomente se a data for obrigatória
            else:
                 aluno_data[col_name] = None

        # Se houver erros de validação, registrar e pular
        if not valid:
            stats["ignorados"] += 1
            stats["erros"].append(f"Erro na linha {index+2} ({aluno_data.get('nome', 'Nome não encontrado')}): {'; '.join(error_details)}")
            continue

        # Tentar inserir no banco
        try:
            # Verificar duplicidade por e-mail antes de inserir
            cursor.execute("SELECT id FROM alunos WHERE email = ?", (aluno_data['email'],))
            if cursor.fetchone():
                stats["ignorados"] += 1
                stats["erros"].append(f"E-mail já cadastrado: {aluno_data['email']} (Aluno: {aluno_data['nome']})")
                continue

            # Verificar duplicidade por matrícula (se houver)
            if aluno_data.get('matricula'):
                 cursor.execute("SELECT id FROM alunos WHERE matricula = ?", (aluno_data['matricula'],))
                 if cursor.fetchone():
                    stats["ignorados"] += 1
                    stats["erros"].append(f"Matrícula já cadastrada: {aluno_data['matricula']} (Aluno: {aluno_data['nome']})")
                    continue

            # Preparar tupla de valores na ordem da tabela
            values = (
                aluno_data.get('matricula'), aluno_data.get('nivel'), aluno_data.get('nome'),
                aluno_data.get('email'), aluno_data.get('orientador'), aluno_data.get('linha_pesquisa'),
                aluno_data.get('data_ingresso'), aluno_data.get('turma'),
                aluno_data.get('prazo_defesa_projeto'), aluno_data.get('prazo_defesa_tese')
            )

            cursor.execute("""
            INSERT INTO alunos (
                matricula, nivel, nome, email, orientador, linha_pesquisa,
                data_ingresso, turma, prazo_defesa_projeto, prazo_defesa_tese
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
            stats["importados"] += 1

        except sqlite3.IntegrityError as e:
            stats["ignorados"] += 1
            stats["erros"].append(f"Erro de integridade (provável duplicidade) para {aluno_data['nome']}: {e}")
        except Exception as e:
            stats["ignorados"] += 1
            stats["erros"].append(f"Erro inesperado ao importar {aluno_data['nome']}: {e}")

    conn.commit()
    conn.close()
    return stats

# --- Funções de Geração de PDF ---

class PDF(fpdf.FPDF):
    def header(self):
        # Adicionar fonte que suporte caracteres especiais
        if os.path.exists(FONT_PATH):
            self.add_font('DejaVu', '', FONT_PATH, uni=True)
            self.set_font('DejaVu', '', 12)
        else:
            self.set_font('Arial', '', 12)
            print(f"Aviso: Fonte Dejavu não encontrada em {FONT_PATH}. Usando Arial.")

        # Logo (se existir)
        # self.image('logo.png', 10, 8, 33)
        self.set_font('DejaVu', '', 16)
        self.cell(0, 10, 'Dashboard do Aluno', 0, 1, 'C')
        self.set_font('DejaVu', '', 10)
        self.cell(0, 6, 'Programa de Pós-Graduação em Gestão de Organizações Públicas', 0, 1, 'C')
        self.cell(0, 6, f'Relatório gerado em: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        if os.path.exists(FONT_PATH):
             self.set_font('DejaVu', '', 8)
        else:
            self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, title):
        if os.path.exists(FONT_PATH):
             self.set_font('DejaVu', '', 14)
        else:
            self.set_font('Arial', 'B', 14)
        self.set_fill_color(200, 220, 255) # Azul claro
        self.cell(0, 8, title, 0, 1, 'L', True)
        self.ln(4)

    def chapter_body(self, data):
        if os.path.exists(FONT_PATH):
             self.set_font('DejaVu', '', 10)
        else:
            self.set_font('Times', '', 10)

        for key, value in data.items():
            label = key.replace('_', ' ').capitalize() + ':'
            val_str = str(value) if value is not None else 'Não informado'
            # Formatar datas
            if isinstance(value, str) and '-' in value and len(value) == 10:
                 try:
                     val_str = datetime.datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
                 except ValueError:
                     pass # Mantém a string original se não for data YYYY-MM-DD

            self.set_font('DejaVu', '', 10)
            self.cell(40, 6, label, 0, 0, 'L')
            self.set_font('DejaVu', '', 10)
            self.multi_cell(0, 6, val_str, 0, 'L') # MultiCell para quebrar linha se necessário
        self.ln()

    def add_table(self, title, headers, data):
        if not data:
            self.ln(5)
            self.cell(0, 10, f"Nenhum registro de {title.lower()} encontrado.", 0, 1)
            self.ln(5)
            return

        self.chapter_title(title)
        if os.path.exists(FONT_PATH):
             self.set_font('DejaVu', '', 10)
        else:
            self.set_font('Arial', 'B', 10)
        self.set_fill_color(230, 230, 230) # Cinza claro
        col_widths = [max(self.get_string_width(h), 20) + 6 for h in headers] # Largura mínima + padding
        total_width = sum(col_widths)
        # Ajustar larguras se excederem a página
        page_width = self.w - 2 * self.l_margin
        if total_width > page_width:
            scale_factor = page_width / total_width
            col_widths = [w * scale_factor for w in col_widths]

        # Cabeçalho da tabela
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, header, 1, 0, 'C', True)
        self.ln()

        # Dados da tabela
        if os.path.exists(FONT_PATH):
             self.set_font('DejaVu', '', 9)
        else:
            self.set_font('Arial', '', 9)
        self.set_fill_color(255, 255, 255)
        fill = False
        for row in data:
            # Verificar altura da linha antes de desenhar
            max_h = 7
            for i, item in enumerate(row):
                h = self.get_string_width(str(item)) / col_widths[i] * 5 # Estimativa de altura
                max_h = max(max_h, h)

            if self.get_y() + max_h > self.h - self.b_margin:
                self.add_page()
                # Redesenhar cabeçalho na nova página
                if os.path.exists(FONT_PATH):
                    self.set_font('DejaVu', '', 10)
                else:
                    self.set_font('Arial', 'B', 10)
                self.set_fill_color(230, 230, 230)
                for i, header in enumerate(headers):
                    self.cell(col_widths[i], 7, header, 1, 0, 'C', True)
                self.ln()
                if os.path.exists(FONT_PATH):
                    self.set_font('DejaVu', '', 9)
                else:
                    self.set_font('Arial', '', 9)
                self.set_fill_color(255, 255, 255)

            # Desenhar células da linha
            x_start = self.get_x()
            y_start = self.get_y()
            for i, item in enumerate(row):
                self.multi_cell(col_widths[i], max_h, str(item) if item is not None else '', border=1, align='L', fill=fill)
                self.set_xy(x_start + sum(col_widths[:i+1]), y_start)
            self.ln(max_h)
            fill = not fill
        self.ln(5)

def gerar_pdf_dashboard(aluno, resumo):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Dados do Aluno
    pdf.chapter_title('Dados Cadastrais')
    dados_aluno_pdf = {
        'Nome': aluno.get('nome'),
        'Matrícula': aluno.get('matricula'),
        'Nível': aluno.get('nivel'),
        'E-mail': aluno.get('email'),
        'Orientador(a)': aluno.get('orientador'),
        'Linha de Pesquisa': aluno.get('linha_pesquisa'),
        'Data de Ingresso': aluno.get('data_ingresso'),
        'Turma': aluno.get('turma'),
        'Prazo Projeto': aluno.get('prazo_defesa_projeto'),
        'Prazo Tese': aluno.get('prazo_defesa_tese'),
    }
    pdf.chapter_body(dados_aluno_pdf)

    # Resumo Aproveitamentos
    pdf.chapter_title('Resumo dos Aproveitamentos')
    resumo_pdf = {
        'Disciplinas - Total': resumo['disciplinas']['total'],
        'Disciplinas - Créditos Deferidos': resumo['disciplinas']['creditos'],
        'Disciplinas - Horas Deferidas': resumo['disciplinas']['horas'],
        'Disciplinas - Pendentes': resumo['disciplinas']['pendentes'],
        'Idiomas - Total': resumo['idiomas']['total'],
        'Idiomas - Aprovados': resumo['idiomas']['aprovados'],
        'Idiomas - Pendentes': resumo['idiomas']['pendentes'],
    }
    pdf.chapter_body(resumo_pdf)

    # Tabela de Disciplinas
    headers_disciplinas = ['Nome', 'Código', 'Créditos', 'Horas', 'Instituição', 'Status', 'Processo']
    data_disciplinas = [
        [d['nome'], d['codigo'], d['creditos'], d['horas'], d['instituicao'], d['status'], d['processo']]
        for d in resumo['detalhes']['disciplinas']
    ]
    pdf.add_table('Detalhes das Disciplinas Aproveitadas', headers_disciplinas, data_disciplinas)

    # Tabela de Idiomas
    headers_idiomas = ['Idioma', 'Nota', 'Instituição', 'Status', 'Processo']
    data_idiomas = [
        [i['idioma'], i['nota'], i['instituicao'], i['status'], i['processo']]
        for i in resumo['detalhes']['idiomas']
    ]
    pdf.add_table('Detalhes dos Idiomas Aproveitados', headers_idiomas, data_idiomas)

    # Salvar PDF em memória
    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

# --- Funções da Interface Streamlit ---

def display_header():
    """Exibe o cabeçalho padrão da aplicação."""
    if os.path.exists(HEADER_IMAGE_PATH):
        try:
            header_image = Image.open(HEADER_IMAGE_PATH)
            st.image(header_image, use_container_width=True)
        except Exception as e:
            st.warning(f"Não foi possível carregar a imagem do cabeçalho: {e}")
    else:
        st.warning(f"Arquivo de cabeçalho não encontrado em {HEADER_IMAGE_PATH}")

def login_page():
    """Exibe a página de login e processa a autenticação."""
    st.header("Login - Sistema de Gestão PPGOP")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        conn.close()

        if result:
            stored_password_hash = result['password_hash']
            input_password_hash = hashlib.sha256(password.encode()).hexdigest()
            if input_password_hash == stored_password_hash:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.success(f"Bem-vindo, {username}!")
                st.experimental_rerun() # Recarrega a página para mostrar o menu principal
            else:
                st.error("Senha incorreta.")
        else:
            st.error("Usuário não encontrado.")

def cadastro_alunos_page():
    """Página para cadastrar ou editar alunos."""
    st.header("Cadastro e Edição de Alunos")

    alunos_list = get_all_alunos()
    alunos_dict = {aluno['nome']: aluno['id'] for aluno in alunos_list}
    alunos_nomes = ["Novo Aluno"] + list(alunos_dict.keys())

    # Selecionar modo: Novo ou Editar
    selected_aluno_nome = st.selectbox("Selecione um aluno para editar ou escolha 'Novo Aluno'", alunos_nomes)

    aluno_data = {}
    aluno_id_to_edit = None

    if selected_aluno_nome == "Novo Aluno":
        st.subheader("Cadastrar Novo Aluno")
        aluno_id_to_edit = None
        # Valores padrão para campos de data podem ser definidos aqui se necessário
        default_date = None # Ou datetime.date.today()
        default_nivel = 'Doutorado' # Ou None
    else:
        st.subheader(f"Editando: {selected_aluno_nome}")
        aluno_id_to_edit = alunos_dict[selected_aluno_nome]
        aluno_data = get_aluno(aluno_id_to_edit)
        if not aluno_data:
            st.error("Erro ao carregar dados do aluno selecionado.")
            return
        # Converter datas de string para objeto date para os widgets
        default_date = None
        for key in ['data_ingresso', 'prazo_defesa_projeto', 'prazo_defesa_tese']:
            if aluno_data.get(key):
                try:
                    aluno_data[key] = datetime.datetime.strptime(aluno_data[key], '%Y-%m-%d').date()
                except (ValueError, TypeError):
                     aluno_data[key] = None # Define como None se a conversão falhar
            else:
                 aluno_data[key] = None
        default_nivel = aluno_data.get('nivel')

    # Formulário de Cadastro/Edição
    with st.form(key='aluno_form'):
        # Usar colunas para melhor layout
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome Completo*", value=aluno_data.get('nome', ''))
            matricula = st.text_input("Matrícula", value=aluno_data.get('matricula', ''))
            email = st.text_input("E-mail*", value=aluno_data.get('email', ''))
            nivel_options = ["Mestrado", "Doutorado"]
            nivel = st.selectbox("Nível*", nivel_options, index=nivel_options.index(default_nivel) if default_nivel in nivel_options else 0)
            orientador = st.text_input("Orientador(a)", value=aluno_data.get('orientador', ''))

        with col2:
            linha_pesquisa = st.text_input("Linha de Pesquisa", value=aluno_data.get('linha_pesquisa', ''))
            turma = st.text_input("Turma", value=aluno_data.get('turma', ''))
            data_ingresso = st.date_input("Data de Ingresso*", value=aluno_data.get('data_ingresso', default_date))
            prazo_defesa_projeto = st.date_input("Prazo Defesa do Projeto", value=aluno_data.get('prazo_defesa_projeto', default_date))
            prazo_defesa_tese = st.date_input("Prazo Defesa da Tese", value=aluno_data.get('prazo_defesa_tese', default_date))

        submitted = st.form_submit_button("Salvar Aluno")

        if submitted:
            # Validações básicas
            if not nome or not email or not nivel or not data_ingresso:
                st.error("Por favor, preencha todos os campos obrigatórios (*).")
            else:
                # Preparar dados para salvar (converter datas de volta para string YYYY-MM-DD)
                data_to_save = {
                    'nome': nome,
                    'matricula': matricula if matricula else None,
                    'email': email,
                    'nivel': nivel,
                    'orientador': orientador if orientador else None,
                    'linha_pesquisa': linha_pesquisa if linha_pesquisa else None,
                    'turma': turma if turma else None,
                    'data_ingresso': data_ingresso.strftime('%Y-%m-%d') if data_ingresso else None,
                    'prazo_defesa_projeto': prazo_defesa_projeto.strftime('%Y-%m-%d') if prazo_defesa_projeto else None,
                    'prazo_defesa_tese': prazo_defesa_tese.strftime('%Y-%m-%d') if prazo_defesa_tese else None
                }

                saved_id = save_aluno(data_to_save, aluno_id=aluno_id_to_edit)
                if saved_id:
                    st.success(f"Aluno '{nome}' salvo com sucesso!")
                    # Limpar formulário ou recarregar dados? Por enquanto, apenas sucesso.
                    # Poderia redirecionar para o dashboard do aluno salvo/editado
                    # st.session_state['selected_page'] = 'Dashboard'
                    # st.session_state['selected_aluno_id_dashboard'] = saved_id
                    # st.experimental_rerun()
                # Mensagem de erro já é exibida por save_aluno

    # --- Listagem e Exclusão de Alunos ---
    st.divider()
    st.subheader("Alunos Cadastrados")
    alunos_list_full = get_all_alunos() # Recarrega a lista completa

    if not alunos_list_full:
        st.info("Nenhum aluno cadastrado ainda.")
    else:
        # Usar colunas para Nome e Botão de Excluir
        col_nome, col_acao = st.columns([4, 1])
        col_nome.write("**Nome**")
        col_acao.write("**Ação**")

        for aluno in alunos_list_full:
            col_nome, col_acao = st.columns([4, 1])
            col_nome.write(aluno['nome'])
            # Botão de exclusão único para cada aluno
            if col_acao.button("🗑️ Excluir", key=f"del_{aluno['id']}"):
                # Adicionar confirmação
                if 'confirm_delete' not in st.session_state:
                    st.session_state['confirm_delete'] = {}
                st.session_state['confirm_delete'][aluno['id']] = True

            # Lógica de confirmação
            if st.session_state.get('confirm_delete', {}).get(aluno['id']):
                st.warning(f"Tem certeza que deseja excluir {aluno['nome']}? Esta ação não pode ser desfeita.")
                col_confirm, col_cancel = st.columns(2)
                if col_confirm.button("Sim, excluir", key=f"confirm_del_{aluno['id']}"):
                    if delete_aluno(aluno['id']):
                        st.success(f"Aluno {aluno['nome']} excluído com sucesso.")
                        del st.session_state['confirm_delete'][aluno['id']]
                        st.experimental_rerun()
                    else:
                        st.error("Erro ao excluir o aluno.")
                if col_cancel.button("Cancelar", key=f"cancel_del_{aluno['id']}"):
                     del st.session_state['confirm_delete'][aluno['id']]
                     st.experimental_rerun()

def aproveitamento_page():
    """Página para registrar e gerenciar aproveitamentos."""
    st.header("Registro de Aproveitamentos")

    alunos_list = get_all_alunos()
    if not alunos_list:
        st.warning("Nenhum aluno cadastrado. Cadastre um aluno primeiro.")
        return

    alunos_dict = {aluno['nome']: aluno['id'] for aluno in alunos_list}
    selected_aluno_nome = st.selectbox("Selecione o Aluno", list(alunos_dict.keys()))
    aluno_id = alunos_dict[selected_aluno_nome]

    st.subheader(f"Registrar novo aproveitamento para: {selected_aluno_nome}")

    with st.form(key='aproveitamento_form'):
        tipo = st.radio("Tipo de Aproveitamento", [t.value.capitalize() for t in TipoAproveitamento], horizontal=True)
        tipo_db = TipoAproveitamento.DISCIPLINA.value if tipo == 'Disciplina' else TipoAproveitamento.IDIOMA.value

        # Campos comuns
        instituicao = st.text_input("Instituição de Origem")
        numero_processo = st.text_input("Número do Processo SEI/Administrativo")
        link_documentos = st.text_input("Link para Documentos (Google Drive, etc.)")
        observacoes = st.text_area("Observações")

        # Campos específicos
        if tipo_db == TipoAproveitamento.DISCIPLINA.value:
            nome_disciplina = st.text_input("Nome da Disciplina*")
            codigo_disciplina = st.text_input("Código da Disciplina")
            creditos = st.number_input("Créditos", min_value=0, step=1)
            idioma = None
            nota = None
        else: # Idioma
            idioma = st.text_input("Idioma*")
            nota = st.number_input("Nota/Conceito", step=0.1)
            nome_disciplina = None
            codigo_disciplina = None
            creditos = None

        submitted = st.form_submit_button("Registrar Aproveitamento")

        if submitted:
            # Validação básica
            is_valid = True
            if tipo_db == TipoAproveitamento.DISCIPLINA.value and not nome_disciplina:
                st.error("O nome da disciplina é obrigatório.")
                is_valid = False
            if tipo_db == TipoAproveitamento.IDIOMA.value and not idioma:
                st.error("O idioma é obrigatório.")
                is_valid = False

            if is_valid:
                data_to_save = {
                    'aluno_id': aluno_id,
                    'tipo': tipo_db,
                    'nome_disciplina': nome_disciplina,
                    'codigo_disciplina': codigo_disciplina,
                    'creditos': creditos,
                    'idioma': idioma,
                    'nota': nota,
                    'instituicao': instituicao,
                    'observacoes': observacoes,
                    'link_documentos': link_documentos,
                    'numero_processo': numero_processo,
                    'status': StatusAproveitamento.SOLICITADO.value # Status inicial
                }
                if save_aproveitamento(data_to_save):
                    st.success("Aproveitamento registrado com sucesso!")
                # Erro já tratado em save_aproveitamento

    # --- Listagem de Aproveitamentos do Aluno Selecionado ---
    st.divider()
    st.subheader(f"Aproveitamentos Registrados para: {selected_aluno_nome}")
    aproveitamentos = get_aproveitamentos(aluno_id)

    if not aproveitamentos:
        st.info("Nenhum aproveitamento registrado para este aluno.")
    else:
        df_aprov = pd.DataFrame(aproveitamentos)
        # Selecionar e renomear colunas para exibição
        df_display = df_aprov[[
            'tipo', 'nome_disciplina', 'codigo_disciplina', 'creditos', 'idioma', 'nota',
            'instituicao', 'numero_processo', 'status', 'data_solicitacao'
        ]].rename(columns={
            'tipo': 'Tipo', 'nome_disciplina': 'Disciplina', 'codigo_disciplina': 'Código',
            'creditos': 'Créditos', 'idioma': 'Idioma', 'nota': 'Nota',
            'instituicao': 'Instituição', 'numero_processo': 'Processo', 'status': 'Status',
            'data_solicitacao': 'Data Solicitação'
        })
        # Formatar data
        df_display['Data Solicitação'] = pd.to_datetime(df_display['Data Solicitação']).dt.strftime('%d/%m/%Y')
        st.dataframe(df_display, use_container_width=True)
        # Adicionar opção de editar/excluir aproveitamentos aqui se necessário

def import_page():
    """Página para importar alunos de arquivo Excel."""
    st.header("Importação de Alunos via Excel")
    st.markdown("""
    Esta funcionalidade permite importar alunos a partir de um arquivo Excel.

    **Instruções:**
    - O arquivo Excel deve conter uma linha de cabeçalho.
    - As colunas esperadas (nomes podem variar ligeiramente, o sistema tentará normalizar):
      `Matrícula`, `Nível`, `Nome`, `E-mail`, `Orientador(a)`, `Linha de Pesquisa`, `Ingresso`, `Turma`, `Prazo defesa do Projeto`, `Prazo para Defesa da tese`
    - Colunas essenciais: `Nome`, `E-mail`, `Ingresso`.
    - Alunos com e-mails ou matrículas já cadastrados serão ignorados.
    - Após o upload, será exibido um relatório com o resultado da importação.
    """)

    uploaded_file = st.file_uploader("Selecione o arquivo Excel", type=["xlsx", "xls"])

    if uploaded_file is not None:
        st.write(f"Arquivo selecionado: {uploaded_file.name}")
        if st.button("Iniciar Importação"):
            with st.spinner("Processando importação... Aguarde."):
                # Chamar init_db() ANTES da importação para garantir que o DB está limpo e com a estrutura correta
                # init_db() # CUIDADO: Isso apagará TODOS os dados existentes!
                # Removido daqui - deve ser chamado uma vez no início ou manualmente.
                # Se o objetivo é APENAS importar, não se deve apagar o banco aqui.

                stats = import_alunos_from_excel(uploaded_file)

            st.success(f"Importação concluída! {stats['importados']} alunos importados, {stats['ignorados']} ignorados/erros.")

            if stats["erros"]:
                st.subheader("Detalhes dos Erros/Alertas da Importação")
                # Usar expander para não poluir a tela
                with st.expander("Clique para ver os detalhes"):
                    for erro in stats["erros"]:
                        st.warning(erro)
            # Recarregar a lista de alunos em outras páginas se necessário
            st.experimental_rerun()

def dashboard_page():
    """Página do dashboard para visualização de dados do aluno."""
    st.header("Dashboard do Aluno")

    alunos_list = get_all_alunos()
    if not alunos_list:
        st.warning("Nenhum aluno cadastrado para exibir no dashboard.")
        return

    alunos_dict = {aluno['nome']: aluno['id'] for aluno in alunos_list}
    # Manter o aluno selecionado no estado da sessão
    if 'selected_aluno_id_dashboard' not in st.session_state:
        st.session_state['selected_aluno_id_dashboard'] = alunos_list[0]['id'] # Seleciona o primeiro por padrão

    # Obter o nome do aluno correspondente ao ID selecionado
    selected_aluno_nome = next((nome for nome, id_ in alunos_dict.items() if id_ == st.session_state['selected_aluno_id_dashboard']), list(alunos_dict.keys())[0])

    # Selectbox para escolher o aluno
    aluno_selecionado_nome_atual = st.selectbox(
        "Selecione o Aluno",
        list(alunos_dict.keys()),
        index=list(alunos_dict.keys()).index(selected_aluno_nome)
    )

    # Atualizar o ID selecionado no estado da sessão se o nome mudar
    if aluno_selecionado_nome_atual != selected_aluno_nome:
        st.session_state['selected_aluno_id_dashboard'] = alunos_dict[aluno_selecionado_nome_atual]
        st.experimental_rerun() # Recarrega para atualizar os dados

    aluno_id = st.session_state['selected_aluno_id_dashboard']
    aluno = get_aluno(aluno_id)
    resumo = get_resumo_aproveitamentos(aluno_id)

    if not aluno:
        st.error("Erro ao carregar dados do aluno.")
        return

    # Botões de Ação: Editar e Exportar PDF
    col_btn1, col_btn2, _ = st.columns([1, 1, 5])
    if col_btn1.button("✏️ Editar Dados do Aluno", key="edit_dash"):
        # Navegar para a página de cadastro/edição com este aluno selecionado
        st.session_state['selected_page'] = 'Cadastro de Alunos'
        # Precisamos passar o nome para o selectbox da página de cadastro
        st.session_state['edit_aluno_nome'] = aluno['nome'] # Passa o nome para pré-selecionar
        st.experimental_rerun()

    pdf_bytes = gerar_pdf_dashboard(aluno, resumo)
    col_btn2.download_button(
        label="📄 Exportar PDF",
        data=pdf_bytes,
        file_name=f"dashboard_{aluno['nome'].replace(' ', '_')}.pdf",
        mime="application/pdf",
        key="pdf_dash"
    )

    st.divider()

    # Exibição dos Dados
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Dados Cadastrais")
        st.markdown(f"**Nome:** {aluno.get('nome', 'N/A')}")
        st.markdown(f"**Matrícula:** {aluno.get('matricula', 'N/A')}")
        st.markdown(f"**Nível:** {aluno.get('nivel', 'N/A')}")
        st.markdown(f"**E-mail:** {aluno.get('email', 'N/A')}")
        st.markdown(f"**Orientador(a):** {aluno.get('orientador', 'N/A')}")
        st.markdown(f"**Linha de Pesquisa:** {aluno.get('linha_pesquisa', 'N/A')}")
        # Formatar datas para exibição
        data_ingresso_str = datetime.datetime.strptime(aluno['data_ingresso'], '%Y-%m-%d').strftime('%d/%m/%Y') if aluno.get('data_ingresso') else 'N/A'
        prazo_proj_str = datetime.datetime.strptime(aluno['prazo_defesa_projeto'], '%Y-%m-%d').strftime('%d/%m/%Y') if aluno.get('prazo_defesa_projeto') else 'N/A'
        prazo_tese_str = datetime.datetime.strptime(aluno['prazo_defesa_tese'], '%Y-%m-%d').strftime('%d/%m/%Y') if aluno.get('prazo_defesa_tese') else 'N/A'
        st.markdown(f"**Data de Ingresso:** {data_ingresso_str}")
        st.markdown(f"**Turma:** {aluno.get('turma', 'N/A')}")
        st.markdown(f"**Prazo Projeto:** {prazo_proj_str}")
        st.markdown(f"**Prazo Tese:** {prazo_tese_str}")

    with col2:
        st.subheader("Resumo dos Aproveitamentos")
        st.metric("Disciplinas Aproveitadas (Créditos)", resumo['disciplinas']['creditos'])
        st.metric("Disciplinas Aproveitadas (Horas)", resumo['disciplinas']['horas'])
        st.metric("Idiomas Aprovados", resumo['idiomas']['aprovados'])

        # Gráfico de Pizza - Status Disciplinas
        labels_disc = ['Deferidos', 'Pendentes']
        sizes_disc = [resumo['disciplinas']['deferidos'], resumo['disciplinas']['pendentes']]
        if sum(sizes_disc) > 0:
            fig1, ax1 = plt.subplots()
            ax1.pie(sizes_disc, labels=labels_disc, autopct='%1.1f%%', startangle=90, colors=['#4CAF50', '#FFC107'])
            ax1.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
            st.pyplot(fig1)
        else:
            st.caption("Nenhuma disciplina registrada.")

    st.divider()
    st.subheader("Detalhes dos Aproveitamentos")

    # Tabela de Disciplinas
    st.markdown("**Disciplinas**")
    if resumo['detalhes']['disciplinas']:
        df_disciplinas = pd.DataFrame(resumo['detalhes']['disciplinas'])
        st.dataframe(df_disciplinas[['nome', 'codigo', 'creditos', 'horas', 'instituicao', 'status', 'processo']], use_container_width=True)
    else:
        st.info("Nenhuma disciplina aproveitada registrada.")

    # Tabela de Idiomas
    st.markdown("**Idiomas**")
    if resumo['detalhes']['idiomas']:
        df_idiomas = pd.DataFrame(resumo['detalhes']['idiomas'])
        st.dataframe(df_idiomas[['idioma', 'nota', 'instituicao', 'status', 'processo']], use_container_width=True)
    else:
        st.info("Nenhum idioma aproveitado registrado.")

# --- Controle Principal da Aplicação ---

# Inicializar o banco de dados na primeira execução
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state['db_initialized'] = True

# Verificar estado de login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Exibir cabeçalho em todas as páginas, exceto login
if st.session_state['logged_in']:
    display_header()

# Roteamento de páginas
if not st.session_state['logged_in']:
    login_page()
else:
    st.sidebar.subheader(f"Usuário: {st.session_state['username']}")
    # Menu de navegação
    pages = {
        "Dashboard": dashboard_page,
        "Cadastro de Alunos": cadastro_alunos_page,
        "Aproveitamentos": aproveitamento_page,
        "Importar Alunos": import_page
    }

    # Manter a página selecionada no estado da sessão
    if 'selected_page' not in st.session_state:
        st.session_state['selected_page'] = "Dashboard"

    selected_page_label = st.sidebar.radio("Navegação", list(pages.keys()), index=list(pages.keys()).index(st.session_state['selected_page']))

    # Atualizar a página selecionada no estado da sessão
    if selected_page_label != st.session_state['selected_page']:
        st.session_state['selected_page'] = selected_page_label
        # Limpar estado de edição ao mudar de página
        if 'edit_aluno_nome' in st.session_state:
            del st.session_state['edit_aluno_nome']
        st.experimental_rerun()

    # Chamar a função da página selecionada
    page_function = pages[st.session_state['selected_page']]

    # Passar o nome do aluno para pré-selecionar na página de cadastro, se vindo do dashboard
    if st.session_state['selected_page'] == 'Cadastro de Alunos' and 'edit_aluno_nome' in st.session_state:
        # A lógica dentro de cadastro_alunos_page já usa st.selectbox com o nome
        # Apenas garantimos que a variável de estado existe
        pass

    page_function()

    # Botão de Logout
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        # Limpar outros estados da sessão se necessário
        if 'selected_page' in st.session_state: del st.session_state['selected_page']
        if 'username' in st.session_state: del st.session_state['username']
        if 'selected_aluno_id_dashboard' in st.session_state: del st.session_state['selected_aluno_id_dashboard']
        if 'edit_aluno_nome' in st.session_state: del st.session_state['edit_aluno_nome']
        st.experimental_rerun()

