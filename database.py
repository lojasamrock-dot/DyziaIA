"""
database.py
Camada de acesso a dados (SQLite) do Perfil Físico Corporal IA.

Tabelas:
  usuarios       -> login e dados pessoais fixos
  avaliacoes     -> uma linha por avaliação (medidas + índices calculados)
  metas          -> metas de medidas/peso por usuário
  fotos          -> caminho das fotos vinculadas a uma avaliação

IMPORTANTE SOBRE HOSPEDAGEM:
Em algumas hospedagens gratuitas (ex.: Streamlit Community Cloud), a pasta
do próprio app é somente-leitura ou é recriada do zero a cada reinício/deploy.
Por isso, na primeira importação deste módulo, testamos se dá para escrever
ao lado do código-fonte; se não der, caímos automaticamente para uma pasta
gravável no diretório temporário do sistema. Nesse segundo caso, os dados
(contas, avaliações, fotos) NÃO são permanentes — eles somem quando o app
reinicia. Para persistência de verdade, hospede em um servidor próprio
(VPS/Docker) com um volume gravável, ou troque o SQLite por um banco externo.
"""

import sqlite3
import hashlib
import os
import tempfile
from datetime import datetime
from contextlib import contextmanager


def _resolver_diretorio_dados():
    preferido = os.path.dirname(os.path.abspath(__file__))
    try:
        teste = os.path.join(preferido, ".write_test")
        with open(teste, "w") as f:
            f.write("ok")
        os.remove(teste)
        return preferido
    except Exception:
        alternativo = os.path.join(tempfile.gettempdir(), "perfil_fisico_ia_dados")
        os.makedirs(alternativo, exist_ok=True)
        return alternativo


DIRETORIO_DADOS = _resolver_diretorio_dados()
ARMAZENAMENTO_PERMANENTE = (DIRETORIO_DADOS == os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DIRETORIO_DADOS, "perfil_fisico.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        pass  # alguns sistemas de arquivos de rede não suportam WAL; segue no modo padrão
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                nome TEXT,
                idade INTEGER,
                sexo TEXT,               -- 'M' ou 'F'
                altura_cm REAL,
                tempo_treino_meses INTEGER,
                natural_hormonizado TEXT, -- 'Natural' ou 'Hormonizado'
                objetivo TEXT,
                foto_perfil TEXT,         -- caminho da foto de perfil (opcional)
                criado_em TEXT
            );

            CREATE TABLE IF NOT EXISTS avaliacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                data_avaliacao TEXT NOT NULL,
                peso_kg REAL,
                pescoco_cm REAL,
                ombros_cm REAL,
                peitoral_cm REAL,
                cintura_cm REAL,
                abdomen_cm REAL,
                quadril_cm REAL,
                braco_dir_cm REAL,
                braco_esq_cm REAL,
                antebraco_cm REAL,
                coxa_cm REAL,
                panturrilha_cm REAL,
                imc REAL,
                percentual_gordura REAL,
                massa_gorda_kg REAL,
                massa_magra_kg REAL,
                ffmi REAL,
                razao_ombro_cintura REAL,
                razao_cintura_altura REAL,
                simetria_pct REAL,
                indice_estetico REAL,
                indice_hipertrofia REAL,
                indice_definicao REAL,
                nota_geral REAL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS metas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                campo TEXT NOT NULL,     -- ex: 'peso_kg', 'peitoral_cm'
                valor_atual REAL,
                valor_meta REAL,
                prazo_meses REAL,
                criado_em TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS fotos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                avaliacao_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,      -- 'antes' ou 'depois'
                caminho TEXT NOT NULL,
                FOREIGN KEY (avaliacao_id) REFERENCES avaliacoes(id) ON DELETE CASCADE
            );
            """
        )
        # Migração leve: adiciona a coluna foto_perfil se o banco já existia
        # de uma versão anterior sem esse campo. Protegido contra corrida entre
        # múltiplas sessões do Streamlit inicializando ao mesmo tempo.
        colunas = [row["name"] for row in conn.execute("PRAGMA table_info(usuarios)")]
        if "foto_perfil" not in colunas:
            try:
                conn.execute("ALTER TABLE usuarios ADD COLUMN foto_perfil TEXT")
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise


# ---------- Usuários ----------

def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def criar_usuario(username, senha, nome, idade, sexo, altura_cm,
                   tempo_treino_meses, natural_hormonizado, objetivo, foto_perfil=None):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO usuarios
               (username, senha_hash, nome, idade, sexo, altura_cm,
                tempo_treino_meses, natural_hormonizado, objetivo, foto_perfil, criado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (username, hash_senha(senha), nome, idade, sexo, altura_cm,
             tempo_treino_meses, natural_hormonizado, objetivo, foto_perfil,
             datetime.now().isoformat()),
        )
        return cur.lastrowid


def autenticar(username, senha):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE username = ?", (username,)
        ).fetchone()
        if row and row["senha_hash"] == hash_senha(senha):
            return dict(row)
    return None


def atualizar_usuario(usuario_id, **campos):
    if not campos:
        return
    sets = ", ".join(f"{k} = ?" for k in campos)
    valores = list(campos.values()) + [usuario_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE usuarios SET {sets} WHERE id = ?", valores)


def get_usuario(usuario_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        return dict(row) if row else None


# ---------- Avaliações ----------

def salvar_avaliacao(usuario_id, medidas: dict, indices: dict, data_avaliacao=None):
    data_avaliacao = data_avaliacao or datetime.now().isoformat()
    campos = {**medidas, **indices}
    colunas = ", ".join(campos.keys())
    placeholders = ", ".join(["?"] * len(campos))
    with get_conn() as conn:
        cur = conn.execute(
            f"""INSERT INTO avaliacoes (usuario_id, data_avaliacao, {colunas})
                VALUES (?, ?, {placeholders})""",
            [usuario_id, data_avaliacao] + list(campos.values()),
        )
        return cur.lastrowid


def listar_avaliacoes(usuario_id, dias=None):
    query = "SELECT * FROM avaliacoes WHERE usuario_id = ?"
    params = [usuario_id]
    if dias is not None:
        limite = datetime.now().timestamp() - dias * 86400
        query += " AND datetime(data_avaliacao) >= datetime(?, 'unixepoch')"
        params.append(limite)
    query += " ORDER BY data_avaliacao ASC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def ultima_avaliacao(usuario_id):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT * FROM avaliacoes WHERE usuario_id = ?
               ORDER BY data_avaliacao DESC LIMIT 1""",
            (usuario_id,),
        ).fetchone()
        return dict(row) if row else None


# ---------- Metas ----------

def salvar_meta(usuario_id, campo, valor_atual, valor_meta, prazo_meses):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO metas (usuario_id, campo, valor_atual, valor_meta,
               prazo_meses, criado_em) VALUES (?,?,?,?,?,?)""",
            (usuario_id, campo, valor_atual, valor_meta, prazo_meses,
             datetime.now().isoformat()),
        )


def listar_metas(usuario_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM metas WHERE usuario_id = ? ORDER BY criado_em DESC",
            (usuario_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def limpar_metas(usuario_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM metas WHERE usuario_id = ?", (usuario_id,))


# ---------- Fotos ----------

def salvar_foto(avaliacao_id, tipo, caminho):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO fotos (avaliacao_id, tipo, caminho) VALUES (?,?,?)",
            (avaliacao_id, tipo, caminho),
        )


def listar_fotos(avaliacao_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM fotos WHERE avaliacao_id = ?", (avaliacao_id,)
        ).fetchall()
        return [dict(r) for r in rows]
