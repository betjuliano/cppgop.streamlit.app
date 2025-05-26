import sqlite3
import pandas as pd

DB_FILE = 		'/home/ubuntu/streamlit_app/ppgop.db'		
CSV_EXPORT_FILE = 		'/home/ubuntu/streamlit_app/export_com_nivel.csv'		

def export_alunos_to_csv():
    try:
        conn = sqlite3.connect(DB_FILE)
        # Use pandas to read the table directly into a DataFrame
        df = pd.read_sql_query("SELECT * FROM alunos", conn)
        conn.close()
        
        # Export DataFrame to CSV
        df.to_csv(CSV_EXPORT_FILE, index=False, encoding=		'utf-8-sig'		) # utf-8-sig for Excel compatibility
        print(f"Dados da tabela 		alunos		 exportados com sucesso para {CSV_EXPORT_FILE}")
        return True
    except Exception as e:
        print(f"Erro ao exportar dados para CSV: {e}")
        return False

if __name__ == "__main__":
    export_alunos_to_csv()

