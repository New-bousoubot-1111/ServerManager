import nextcord
import json
import os
import sys
import traceback
import sqlite3
import ast

# configの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

# SQLiteの接続設定（ローカルDB）
def get_db_connection():
    conn = sqlite3.connect('database.db')  # 'database.db'を使ってDBに接続
    conn.row_factory = sqlite3.Row  # レコードを辞書形式で取得
    return conn

def insert_returns(body):
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)

class eval_modal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("Eval")
        self.add_item(nextcord.ui.TextInput(
            label="Evalを実行したいコード",
            placeholder="print('HelloWorld')",
            style=nextcord.TextInputStyle.paragraph,
            min_length=1
        ))

    async def callback(self, interaction: nextcord.Interaction):
        try:
            cmd = self.children[0].value
            name = "_eval_expr"
            cmds = "\n".join(f"  {i}" for i in cmd.splitlines())
            body = f"async def {name}():\n{cmds}"
            parsed = ast.parse(body)
            body = parsed.body[0].body
            insert_returns(body)
            env = {
                "self": self,
                "nextcord": nextcord,
                "bot": interaction.client,
                "interaction": interaction,
                "ctx": interaction,
                "os": os,
                "__import__": __import__
            }
            exec(compile(parsed, filename="<ast>", mode="exec"), env)
            result = (await eval(f"{name}()", env))
            if result == None:
                result = "None"
            embed = nextcord.Embed(title="実行コード", description=f"```py\n{cmd}\n```", color=color)
            code = await interaction.channel.send(embed=embed)
            embed = nextcord.Embed(title="実行結果", description=f"```py\n{result}```", color=color)
            await code.reply(embed=embed)
        except:
            embed = nextcord.Embed(title="実行コード", description=f"```py\n{cmd}\n```", color=color)
            code = await interaction.channel.send(embed=embed)
            embed = nextcord.Embed(title="エラー", description=f"```py\n{traceback.format_exc()}```", color=color)
            await code.reply(embed=embed)

class devmenu_view(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    @nextcord.ui.button(label="Botを再起動", style=nextcord.ButtonStyle.green)
    async def restart(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if interaction.user.id in config['owners']:
            embed = nextcord.Embed(title="再起動", description="Botを再起動します\n再起動終了まで時間がかかる場合があります", color=color)
            await interaction.response.send_message(embed=embed)
            self.stop()
            res = sys.executable
            os.execl(res, res, *sys.argv)
        else:
            embed=util.creator_only()
            await interaction.response.send_message(embed=embed,ephemeral=True)

    @nextcord.ui.button(label="Evalを実行", style=nextcord.ButtonStyle.green)
    async def eval(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if interaction.user.id in config['owners']:
            await interaction.response.send_modal(eval_modal())
        else:
            embed=util.creator_only()
            await interaction.response.send_message(embed=embed,ephemeral=True)
# DBにデータを挿入する例
def insert_data_to_db(data):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("INSERT INTO users (name) VALUES (?)", (data,))
    conn.commit()
    conn.close()

# DBからデータを取得する例
def fetch_data_from_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    data = c.fetchall()
    conn.close()
    return data

# データ挿入の例
insert_data_to_db("test_user")
print(fetch_data_from_db())
