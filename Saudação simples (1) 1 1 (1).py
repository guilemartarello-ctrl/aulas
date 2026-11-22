import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from cryptography.fernet import Fernet

# ----------------------------------------------------------------------
# CHAVE DE CRIPTOGRAFIA
# ----------------------------------------------------------------------
def carregar_ou_gerar_chave():
    try:
        with open("secret.key", "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        key = Fernet.generate_key()
        with open("secret.key", "wb") as key_file:
            key_file.write(key)
        return key

chave = carregar_ou_gerar_chave()
cipher = Fernet(chave)

# ----------------------------------------------------------------------
# BANCO DE DADOS (MySQL / XAMPP)
# ----------------------------------------------------------------------
def conectar():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # XAMPP padrão não tem senha
        database="cofre_db"
    )

def inicializar_banco():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credenciais (
            id INT AUTO_INCREMENT PRIMARY KEY,
            servico VARCHAR(255) NOT NULL,
            usuario VARCHAR(255) NOT NULL,
            senha BLOB NOT NULL
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# ----------------------------------------------------------------------
# INTERFACE GRÁFICA (Tkinter)
# ----------------------------------------------------------------------
class CofreApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cofre de Credenciais Pessoal")
        self.root.geometry("600x480")

        self.id_edicao = None  # Armazena o ID do registro que está sendo editado

        inicializar_banco()
        self.criar_componentes()
        self.atualizar_tabela()

    def criar_componentes(self):
        # Form
        frame_form = ttk.LabelFrame(self.root, text=" Dados da Credencial ", padding=10)
        frame_form.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_form, text="Serviço/Site:").grid(row=0, column=0, sticky="w", pady=2)
        self.ent_servico = ttk.Entry(frame_form, width=30)
        self.ent_servico.grid(row=0, column=1, pady=2, padx=5)

        ttk.Label(frame_form, text="Usuário/E-mail:").grid(row=1, column=0, sticky="w", pady=2)
        self.ent_usuario = ttk.Entry(frame_form, width=30)
        self.ent_usuario.grid(row=1, column=1, pady=2, padx=5)

        ttk.Label(frame_form, text="Senha:").grid(row=2, column=0, sticky="w", pady=2)
        self.ent_senha = ttk.Entry(frame_form, show="*", width=30)
        self.ent_senha.grid(row=2, column=1, pady=2, padx=5)

        # Frame de botões do formulário
        frame_btn_form = ttk.Frame(frame_form)
        frame_btn_form.grid(row=3, column=0, columnspan=2, pady=8)

        btn_salvar = ttk.Button(frame_btn_form, text="Salvar Novo", command=self.salvar_credencial)
        btn_salvar.pack(side="left", padx=3)

        btn_atualizar = ttk.Button(frame_btn_form, text="Atualizar", command=self.atualizar_credencial)
        btn_atualizar.pack(side="left", padx=3)

        btn_limpar = ttk.Button(frame_btn_form, text="Limpar", command=self.limpar_campos)
        btn_limpar.pack(side="left", padx=3)

        # Tabela
        frame_tabela = ttk.Frame(self.root, padding=10)
        frame_tabela.pack(fill="both", expand=True)

        cols = ("ID", "Serviço", "Usuário")
        self.tabela = ttk.Treeview(frame_tabela, columns=cols, show="headings", selectmode="browse")
        
        self.tabela.heading("ID", text="ID")
        self.tabela.column("ID", width=40, anchor="center")
        self.tabela.heading("Serviço", text="Serviço")
        self.tabela.heading("Usuário", text="Usuário")

        self.tabela.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Botoes de acao da tabela
        frame_acoes = ttk.Frame(self.root, padding=10)
        frame_acoes.pack(fill="x")

        btn_revelar = ttk.Button(frame_acoes, text="Revelar Senha", command=self.revelar_senha)
        btn_revelar.pack(side="left", padx=5)

        btn_editar = ttk.Button(frame_acoes, text="Carregar p/ Editar", command=self.carregar_para_edicao)
        btn_editar.pack(side="left", padx=5)

        btn_excluir = ttk.Button(frame_acoes, text="Excluir", command=self.excluir_credencial)
        btn_excluir.pack(side="left", padx=5)

    def limpar_campos(self):
        self.ent_servico.delete(0, tk.END)
        self.ent_usuario.delete(0, tk.END)
        self.ent_senha.delete(0, tk.END)
        self.id_edicao = None

    def salvar_credencial(self):
        servico = self.ent_servico.get().strip()
        usuario = self.ent_usuario.get().strip()
        senha = self.ent_senha.get().strip()

        if not servico or not usuario or not senha:
            messagebox.showwarning("Aviso", "Preencha todos os campos!")
            return

        senha_encriptada = cipher.encrypt(senha.encode('utf-8'))

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO credenciais (servico, usuario, senha) VALUES (%s, %s, %s)",
            (servico, usuario, senha_encriptada)
        )
        conn.commit()
        cursor.close()
        conn.close()

        self.limpar_campos()
        self.atualizar_tabela()
        messagebox.showinfo("Sucesso", "Credencial salva com sucesso!")

    def carregar_para_edicao(self):
        item_selecionado = self.tabela.selection()
        if not item_selecionado:
            messagebox.showwarning("Aviso", "Selecione um item da tabela para editar!")
            return

        id_item = self.tabela.item(item_selecionado)["values"][0]

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT servico, usuario, senha FROM credenciais WHERE id = %s", (id_item,))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()

        if resultado:
            servico, usuario, senha_encriptada = resultado
            if isinstance(senha_encriptada, str):
                senha_encriptada = senha_encriptada.encode('utf-8')
                
            try:
                senha_descriptografada = cipher.decrypt(bytes(senha_encriptada)).decode('utf-8')
            except Exception:
                senha_descriptografada = ""

            # Preenche os campos do formulário
            self.ent_servico.delete(0, tk.END)
            self.ent_servico.insert(0, servico)

            self.ent_usuario.delete(0, tk.END)
            self.ent_usuario.insert(0, usuario)

            self.ent_senha.delete(0, tk.END)
            self.ent_senha.insert(0, senha_descriptografada)

            self.id_edicao = id_item
            messagebox.showinfo("Editar", "Dados carregados no formulário. Altere e clique em 'Atualizar'.")

    def atualizar_credencial(self):
        if self.id_edicao is None:
            messagebox.showwarning("Aviso", "Selecione um registro na tabela e clique em 'Carregar p/ Editar' primeiro!")
            return

        servico = self.ent_servico.get().strip()
        usuario = self.ent_usuario.get().strip()
        senha = self.ent_senha.get().strip()

        if not servico or not usuario or not senha:
            messagebox.showwarning("Aviso", "Preencha todos os campos!")
            return

        senha_encriptada = cipher.encrypt(senha.encode('utf-8'))

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE credenciais SET servico = %s, usuario = %s, senha = %s WHERE id = %s",
            (servico, usuario, senha_encriptada, self.id_edicao)
        )
        conn.commit()
        cursor.close()
        conn.close()

        self.limpar_campos()
        self.atualizar_tabela()
        messagebox.showinfo("Sucesso", "Registro atualizado com sucesso!")

    def atualizar_tabela(self):
        for item in self.tabela.get_children():
            self.tabela.delete(item)

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT id, servico, usuario FROM credenciais")
        registros = cursor.fetchall()
        cursor.close()
        conn.close()

        for reg in registros:
            self.tabela.insert("", "end", values=reg)

    def revelar_senha(self):
        item_selecionado = self.tabela.selection()
        if not item_selecionado:
            messagebox.showwarning("Aviso", "Selecione um item da tabela!")
            return

        id_item = self.tabela.item(item_selecionado)["values"][0]

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT senha FROM credenciais WHERE id = %s", (id_item,))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()

        if resultado:
            senha_encriptada = resultado[0]
            if isinstance(senha_encriptada, str):
                senha_encriptada = senha_encriptada.encode('utf-8')
                
            try:
                senha_descriptografada = cipher.decrypt(bytes(senha_encriptada)).decode('utf-8')
                messagebox.showinfo("Senha", f"A senha é: {senha_descriptografada}")
            except Exception:
                messagebox.showerror("Erro", "Não foi possível descriptografar esta senha com a chave atual.")

    def excluir_credencial(self):
        item_selecionado = self.tabela.selection()
        if not item_selecionado:
            messagebox.showwarning("Aviso", "Selecione um item para excluir!")
            return

        if not messagebox.askyesno("Confirmar", "Deseja realmente excluir este registro?"):
            return

        id_item = self.tabela.item(item_selecionado)["values"][0]

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM credenciais WHERE id = %s", (id_item,))
        conn.commit()
        cursor.close()
        conn.close()

        self.limpar_campos()
        self.atualizar_tabela()
        messagebox.showinfo("Sucesso", "Registro excluído!")

if __name__ == "__main__":
    root = tk.Tk()
    app = CofreApp(root)
    root.mainloop()