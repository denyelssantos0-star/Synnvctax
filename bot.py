import os
import random
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import random
import time
import sqlite3
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import aiohttp

# ===== SISTEMA DE XP =====

xp_db = sqlite3.connect("experiencia.db")
xp_cursor = xp_db.cursor()

xp_cursor.execute("""
CREATE TABLE IF NOT EXISTS experiencia (
    user_id INTEGER PRIMARY KEY,
    xp INTEGER DEFAULT 0,
    nivel INTEGER DEFAULT 0
)
""")

xp_db.commit()

cooldowns_xp = {}
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
ID_SERVIDOR = 1562425457905770518
CANAL_AGENDA_ID = 1564639801452527697
CANAL_XP_ID = 1564877652760858696
NOME_CANAL_ALISTAMENTO = "alistamento"
CARGOS_ALISTAMENTO = [1555754432925405194, 1557070129085550672]
MODELO_ALISTAMENTO = "<@&1555754432925405194> <@&1557070129085550672>\n\nNome:\nID:\nPlataforma:\nPrint info:"
# CONFIGURAÇÕES DE CAMPEONATO
CANAL_CAMPEONATO = "campeonato"
CANAL_CAMPEONATO_ID = 1564639833400414300
LIMITE_CAMPEONATO = 8
JOGADORES_POR_EQUIPE = 4
# DADOS DOS CAMPEONATOS ATIVOS
campeonatos_ativos = {}
# DADOS DOS GRUPOS E PARTIDAS
grupos_campeonato = {}
resultados_campeonato = {}
classificacao_campeonato = {}
mata_mata_campeonato = {}
TIPOS_CAMPEONATO = [
    "Individual",
    "Equipes"
]

FORMATO_CAMPEONATO = "Fase de grupos e mata-mata"
# CONFIGURAÇÃO DOS GRUPOS
QUANTIDADE_GRUPOS = 2
PARTICIPANTES_POR_GRUPO = 4
CLASSIFICADOS_POR_GRUPO = 2

@bot.event
async def on_ready():
    try:

        guild = discord.Object(id=1562425457905770518)

        comandos_globais = await bot.tree.fetch_commands()
        comandos_servidor = await bot.tree.fetch_commands(guild=guild)

        print("=== RANK GLOBAL ===")
        for c in comandos_globais:
            if c.name == "rank":
                print(c.id, c.name, repr(c.description))

        print("=== RANK DO SERVIDOR ===")
        for c in comandos_servidor:
            if c.name == "rank":
                print(c.id, c.name, repr(c.description))

        synced = await bot.tree.sync(guild=guild)
        globais = await bot.tree.fetch_commands()

        print("=== COMANDOS GLOBAIS REGISTRADOS NO DISCORD ===")
        for comando in globais:
            print(comando.name, repr(comando.description), comando.id)

        print(f"✅ {len(synced)} comandos sincronizados no servidor.")

        for comando in synced:
            print(f"➡️ /{comando.name}")

        await preparar_canal_logs()

        for servidor in bot.guilds:
            await atualizar_contador(servidor)

        for servidor in bot.guilds:
            canal_alistamento = discord.utils.get(
                servidor.text_channels,
                name=NOME_CANAL_ALISTAMENTO
            )

            if canal_alistamento is not None:
                mensagens_recentes = [
                    mensagem async for mensagem in canal_alistamento.history(limit=20)
                    if mensagem.author == bot.user
                ]

                if not any(
                    m.content.strip() == MODELO_ALISTAMENTO.strip()
                    for m in mensagens_recentes
                ):
                    await enviar_formulario_alistamento(canal_alistamento)

    except Exception as erro:
        print(f"❌ Erro ao sincronizar ou iniciar: {erro}")


@bot.tree.command(name="ping", description="Mostra a latência do bot.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


@bot.tree.command(name="avatar", description="Mostra o avatar de um usuário.")
@app_commands.describe(usuario="Usuário que você deseja visualizar")
async def avatar(
    interaction: discord.Interaction,
    usuario: discord.Member = None
):
    usuario = usuario or interaction.user

    embed = discord.Embed(
        title=f"🖼️ Avatar de {usuario.display_name}",
        color=discord.Color.purple()
    )

    embed.set_image(url=usuario.display_avatar.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="serverinfo", description="Mostra informações do servidor.")
async def serverinfo(interaction: discord.Interaction):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"📊 {guild.name}",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="👥 Membros",
        value=guild.member_count,
        inline=True
    )

    embed.add_field(
        name="👑 Dono",
        value=guild.owner.mention if guild.owner else "Desconhecido",
        inline=True
    )

    embed.add_field(
        name="🆔 ID",
        value=guild.id,
        inline=False
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await interaction.response.send_message(embed=embed)


# =========================
# BOAS-VINDAS
# =========================

CANAL_BOAS_VINDAS = 1562425458971246666
CANAL_CONTADOR = 1564635552685494272

async def atualizar_contador(guild):
    # Primeiro procura no cache; se necessário, consulta o Discord pela API.
    canal = guild.get_channel(CANAL_CONTADOR)

    if canal is None:
        try:
            canal = await bot.fetch_channel(CANAL_CONTADOR)
        except discord.NotFound:
            print(f"❌ Canal do contador {CANAL_CONTADOR} não encontrado. Confira o ID.")
            return
        except discord.Forbidden:
            print("❌ O bot não tem acesso ao canal do contador.")
            return
        except discord.HTTPException as erro:
            print(f"❌ Não foi possível buscar o canal do contador: {erro}")
            return

    if not hasattr(canal, "edit") or not hasattr(canal, "name"):
        print("❌ O ID do contador não corresponde a um canal editável.")
        return

    quantidade = guild.member_count
    if quantidade is None:
        try:
            quantidade = (await guild.fetch_member_count())
        except (AttributeError, discord.HTTPException):
            print("❌ Não foi possível obter a quantidade atual de membros.")
            return

    novo_nome = f"👥 Membros: {quantidade}"

    try:
        if canal.name != novo_nome:
            await canal.edit(name=novo_nome, reason="Atualização automática do contador de membros")
            print(f"✅ Contador atualizado: {novo_nome}")
    except discord.Forbidden:
        print("❌ O bot não tem permissão para editar o canal do contador. Verifique Gerenciar canais.")
    except discord.HTTPException as erro:
        print(f"❌ Erro ao atualizar o contador: {erro}")

@bot.event
async def on_member_join(member):
    await atualizar_contador(member.guild)
        # 🎭 Cargo automático
    cargo = member.guild.get_role(1562426482897461278)


    if cargo:
        try:
            await member.add_roles(
                cargo,
                reason="Cargo automático ao entrar no servidor"
            )
            print(f"✅ Cargo automático dado para {member}")
        except discord.Forbidden:
            print("❌ O bot não tem permissão para dar o cargo.")
        except Exception as erro:
            print(f"❌ Erro no autorole: {erro}")
    else:
        print("❌ Cargo do autorole não encontrado.") 
    
    # Busca o canal pelo ID; se não estiver no cache, tenta buscar pela API.
    canal = bot.get_channel(CANAL_BOAS_VINDAS)
    if canal is None:
        try:
            canal = await bot.fetch_channel(CANAL_BOAS_VINDAS)
        except discord.NotFound:
            print(f"❌ Canal de boas-vindas {CANAL_BOAS_VINDAS} não encontrado. Confira o ID.")
            return
        except discord.Forbidden:
            print("❌ O bot não tem acesso ao canal de boas-vindas.")
            return
        except discord.HTTPException as erro:
            print(f"❌ Não foi possível buscar o canal de boas-vindas: {erro}")
            return

    if not hasattr(canal, "send"):
        print("❌ O ID configurado para boas-vindas não é um canal que aceita mensagens.")
        return
    mensagens_boas_vindas = [
    f"🖤 {member.mention} acabou de chegar na **Community Originais**. Seja bem-vindo(a)!",
    f"👑 Abram espaço! {member.mention} chegou nos **Originais**.",
    f"🔥 Mais um Original na área! Salve, {member.mention}!",
    f"🥷 {member.mention} apareceu por aqui... seja bem-vindo(a) aos **Originais**.",
    f"⚡ Reforço chegando! Bem-vindo(a), {member.mention}!",
    f"🎉 Recebam {member.mention}! A família **Originais** está crescendo.",
    f"🫡 Salve, {member.mention}! Seja bem-vindo(a) à **Community Originais**.",
    f"💀 Atenção: {member.mention} acaba de entrar no território dos **Originais**.",
    f"🚀 {member.mention} entrou no servidor. Aproveite a comunidade!",
    f"🖤 A família cresceu! Bem-vindo(a), {member.mention}.",

    f"🏙️ Novo player na cidade: {member.mention}! Seja bem-vindo(a).",
    f"🚘 {member.mention} acabou de spawnar na **Community Originais**!",
    f"🎮 Player conectado: {member.mention}. Bem-vindo(a) aos **Originais**!",
    f"📡 Conexão estabelecida! {member.mention} entrou no servidor.",
    f"🏁 Chegou mais um! Seja bem-vindo(a), {member.mention}.",
    f"🔑 {member.mention} recebeu acesso à **Community Originais**. Bem-vindo(a)!",
    f"🌃 Mais um pela cidade! Salve, {member.mention}!",
    f"🚨 Novo membro detectado: {member.mention}. Recebam nosso novo Original!",
    f"💨 Do nada apareceu {member.mention} 😂 Seja bem-vindo(a)!",
    f"🎯 {member.mention} encontrou o servidor certo. Bem-vindo(a)!",

    f"👀 Olha quem chegou... {member.mention}!",
    f"😂 Alguém abriu o portão e {member.mention} entrou. Bem-vindo(a)!",
    f"🍷 Chegou com estilo! Bem-vindo(a), {member.mention}.",
    f"🤝 Recebam bem {member.mention}! Agora ele(a) faz parte da comunidade.",
    f"🛬 Pousou nos **Originais**! Bem-vindo(a), {member.mention}!",
    f"✨ Temos companhia nova! Salve, {member.mention}!",
    f"🔔 Ding dong! {member.mention} chegou na **Community Originais**.",
    f"🕶️ Novo Original identificado: {member.mention}. Seja bem-vindo(a)!",
    f"🏆 Seja bem-vindo(a), {member.mention}! Você é o membro **#{member.guild.member_count}**.",
    f"🖤 Bem-vindo(a) à família, {member.mention}. **Uma vez Original, sempre Original.**"
]
    mensagem = random.choice(mensagens_boas_vindas)
    try:
        await canal.send(mensagem)
        print(f"✅ Boas-vindas enviada para {member} no canal #{canal.name}.")
    except discord.Forbidden:
        print("❌ Sem permissão para enviar mensagens no canal de boas-vindas. Confira Ver canal e Enviar mensagens.")
    except discord.HTTPException as erro:
        print(f"❌ Erro ao enviar boas-vindas: {erro}")
@bot.event
async def on_member_remove(member):
    await atualizar_contador(member.guild)

# ==========================================
# 🛡️ SISTEMA DE MODERAÇÃO - OS ORIGINAIS
# ==========================================

from datetime import timedelta


# /clear
@bot.tree.command(name="clear", description="Apaga mensagens do canal.")
@app_commands.describe(quantidade="Quantidade de mensagens para apagar")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, quantidade: int):

    if quantidade < 1 or quantidade > 100:
        await interaction.response.send_message(
            "❌ Escolha uma quantidade entre 1 e 100.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        apagadas = await interaction.channel.purge(
            limit=quantidade
        )
        await enviar_log_moderacao(
    titulo="🧹 Mensagens apagadas",
    moderador=interaction.user,
    detalhes=(
        f"📍 Canal: {interaction.channel.mention}\n"
        f"🗑️ Quantidade: {len(apagadas)}"
    )
)

        await interaction.followup.send(
            f"🧹 **{len(apagadas)} mensagens foram apagadas!**",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Eu não tenho permissão para apagar mensagens neste canal.",
            ephemeral=True
        )

    except Exception as erro:
        print(f"❌ ERRO NO /CLEAR: {erro}")

        await interaction.followup.send(
            "❌ Ocorreu um erro ao apagar as mensagens. Veja o CMD.",
            ephemeral=True
        )


# /kick
@bot.tree.command(name="kick", description="Expulsa um membro do servidor.")
@app_commands.describe(
    membro="Membro que será expulso",
    motivo="Motivo da expulsão"
)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(
    interaction: discord.Interaction,
    membro: discord.Member,
    motivo: str = "Nenhum motivo informado"
):
    if membro == interaction.user:
        await interaction.response.send_message(
            "❌ Você não pode expulsar você mesmo.",
            ephemeral=True
        )
        return

    try:
        await membro.kick(reason=motivo)
        await enviar_log_moderacao(
    titulo="👢 Membro expulso",
    moderador=interaction.user,
    usuario=membro,
    motivo=motivo
)

        embed = discord.Embed(
            title="👢 Membro expulso",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Usuário",
            value=f"{membro} (`{membro.id}`)",
            inline=False
        )

        embed.add_field(
            name="🛡️ Moderador",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="📝 Motivo",
            value=motivo,
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Não tenho permissão para expulsar esse membro.",
            ephemeral=True
        )


# /ban
@bot.tree.command(name="ban", description="Bane um membro do servidor.")
@app_commands.describe(
    membro="Membro que será banido",
    motivo="Motivo do banimento"
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(
    interaction: discord.Interaction,
    membro: discord.Member,
    motivo: str = "Nenhum motivo informado"
):
    if membro == interaction.user:
        await interaction.response.send_message(
            "❌ Você não pode banir você mesmo.",
            ephemeral=True
        )
        return

    try:
        await membro.ban(reason=motivo)
        await enviar_log_moderacao(
    titulo="🔨 Membro banido",
    moderador=interaction.user,
    usuario=membro,
    motivo=motivo
)

        embed = discord.Embed(
            title="🔨 Membro banido",
            color=discord.Color.red()
        )

        embed.add_field(
            name="👤 Usuário",
            value=f"{membro} (`{membro.id}`)",
            inline=False
        )

        embed.add_field(
            name="🛡️ Moderador",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="📝 Motivo",
            value=motivo,
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Não tenho permissão para banir esse membro.",
            ephemeral=True
        )


# /timeout
@bot.tree.command(name="timeout", description="Coloca um membro de castigo.")
@app_commands.describe(
    membro="Membro que receberá timeout",
    minutos="Duração em minutos",
    motivo="Motivo do timeout"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(
    interaction: discord.Interaction,
    membro: discord.Member,
    minutos: int,
    motivo: str = "Nenhum motivo informado"
):
    if minutos < 1 or minutos > 40320:
        await interaction.response.send_message(
            "❌ Escolha entre 1 e 40320 minutos.",
            ephemeral=True
        )
        return

    if membro == interaction.user:
        await interaction.response.send_message(
            "❌ Você não pode aplicar timeout em você mesmo.",
            ephemeral=True
        )
        return

    try:
        await membro.timeout(
            timedelta(minutes=minutos),
            reason=motivo
        )

        # Envia para o canal de logs
        await enviar_log_moderacao(
            titulo="🔇 Timeout aplicado",
            moderador=interaction.user,
            usuario=membro,
            motivo=motivo,
            detalhes=f"⏱️ Duração: {minutos} minutos"
        )

        # Resposta do comando
        embed = discord.Embed(
            title="🔇 Timeout aplicado",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Usuário",
            value=membro.mention,
            inline=True
        )

        embed.add_field(
            name="⏱️ Tempo",
            value=f"{minutos} minutos",
            inline=True
        )

        embed.add_field(
            name="📝 Motivo",
            value=motivo,
            inline=False
        )

        embed.set_footer(
            text=f"Aplicado por {interaction.user}"
        )

        await interaction.response.send_message(embed=embed)

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Não tenho permissão para dar timeout nesse membro.",
            ephemeral=True
        )

    except Exception as erro:
        print(f"❌ ERRO NO /TIMEOUT: {erro}")

        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao aplicar o timeout.",
                ephemeral=True
            )
# /lock
@bot.tree.command(name="lock", description="Tranca o canal atual.")
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):

    canal = interaction.channel

    overwrite = canal.overwrites_for(
        interaction.guild.default_role
    )

    overwrite.send_messages = False

    await canal.set_permissions(
        interaction.guild.default_role,
        overwrite=overwrite
    )

    await interaction.response.send_message(
        "🔒 **Canal trancado.**"
    )


# /unlock
@bot.tree.command(name="unlock", description="Destranca o canal atual.")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):

    canal = interaction.channel

    overwrite = canal.overwrites_for(
        interaction.guild.default_role
    )

    overwrite.send_messages = None

    await canal.set_permissions(
        interaction.guild.default_role,
        overwrite=overwrite
    )

    await interaction.response.send_message(
        "🔓 **Canal destrancado.**"
    )


# Mensagem para quem tentar usar comando sem permissão
@bot.tree.error
async def erro_comando(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        if interaction.response.is_done():
            await interaction.followup.send(
                "❌ Você não tem permissão para usar esse comando.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar esse comando.",
                ephemeral=True
            )
# ...todos os códigos acima...

# ==========================================
# 📋 LOGS - OS ORIGINAIS
# ==========================================

# O bot procura o canal "logs" automaticamente.
# Se ele não existir, tenta criar o canal.
CANAL_LOGS = None
NOME_CANAL_LOGS = "logs"


async def preparar_canal_logs():
    global CANAL_LOGS

    for guild in bot.guilds:
        canal = discord.utils.get(guild.text_channels, name=NOME_CANAL_LOGS)

        if canal is None:
            try:
                canal = await guild.create_text_channel(
                    NOME_CANAL_LOGS,
                    reason="Criação automática do canal de logs do bot"
                )
                print(f"✅ Canal #{NOME_CANAL_LOGS} criado no servidor {guild.name}.")
            except discord.Forbidden:
                print(f"❌ Não tenho permissão para criar o canal #{NOME_CANAL_LOGS} em {guild.name}.")
                continue
            except discord.HTTPException as erro:
                print(f"❌ Erro ao criar o canal #{NOME_CANAL_LOGS}: {erro}")
                continue

        CANAL_LOGS = canal.id
        print(f"✅ Canal de logs configurado: #{canal.name} ({canal.id})")
        return canal

    print("❌ Não foi possível encontrar/criar o canal de logs.")
    return None


def pegar_canal_logs():
    if CANAL_LOGS is None:
        return None
    return bot.get_channel(CANAL_LOGS)


# 🗑️ MENSAGEM APAGADA
@bot.event
async def on_message_delete(message):

    if message.author.bot:
        return

    canal_logs = pegar_canal_logs()

    if canal_logs is None:
        print("❌ Canal de logs não encontrado.")
        return

    conteudo = message.content or "Sem conteúdo de texto."

    # Evita embed gigante
    if len(conteudo) > 1000:
        conteudo = conteudo[:1000] + "..."

    embed = discord.Embed(
        title="🗑️ Mensagem apagada",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="👤 Autor",
        value=f"{message.author.mention}\n`{message.author.id}`",
        inline=True
    )

    embed.add_field(
        name="📍 Canal",
        value=message.channel.mention,
        inline=True
    )

    embed.add_field(
        name="💬 Mensagem",
        value=conteudo,
        inline=False
    )

    embed.set_thumbnail(
        url=message.author.display_avatar.url
    )

    embed.set_footer(
        text=f"Mensagem ID: {message.id}"
    )

    await canal_logs.send(embed=embed)


# ✏️ MENSAGEM EDITADA
@bot.event
async def on_message_edit(before, after):

    if before.author.bot:
        return

    # Não cria log se o conteúdo não mudou
    if before.content == after.content:
        return

    canal_logs = pegar_canal_logs()

    if canal_logs is None:
        return

    antes = before.content or "Sem conteúdo."
    depois = after.content or "Sem conteúdo."

    if len(antes) > 900:
        antes = antes[:900] + "..."

    if len(depois) > 900:
        depois = depois[:900] + "..."

    embed = discord.Embed(
        title="✏️ Mensagem editada",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="👤 Autor",
        value=f"{before.author.mention}\n`{before.author.id}`",
        inline=True
    )

    embed.add_field(
        name="📍 Canal",
        value=before.channel.mention,
        inline=True
    )

    embed.add_field(
        name="📝 Antes",
        value=antes,
        inline=False
    )

    embed.add_field(
        name="📝 Depois",
        value=depois,
        inline=False
    )

    embed.add_field(
        name="🔗 Ir para mensagem",
        value=f"[Clique aqui]({after.jump_url})",
        inline=False
    )

    embed.set_thumbnail(
        url=before.author.display_avatar.url
    )

    await canal_logs.send(embed=embed)

async def enviar_log_moderacao(
    titulo,
    moderador,
    usuario=None,
    motivo=None,
    detalhes=None
):
    canal = bot.get_channel(CANAL_LOGS)

    if canal is None:
        print("❌ Canal de logs não encontrado.")
        return

    embed = discord.Embed(
        title=titulo,
        color=discord.Color.purple(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="🛡️ Moderador",
        value=f"{moderador.mention}\n`{moderador.id}`",
        inline=True
    )

    if usuario:
        embed.add_field(
            name="👤 Usuário",
            value=f"{usuario.mention}\n`{usuario.id}`",
            inline=True
        )

    if motivo:
        embed.add_field(
            name="📝 Motivo",
            value=motivo,
            inline=False
        )

    if detalhes:
        embed.add_field(
            name="📋 Detalhes",
            value=detalhes,
            inline=False
        )

    embed.set_footer(text="Os Originais • Sistema de Moderação")

    await canal.send(embed=embed)

# ==========================================
# 📢 SISTEMA DE EMBED - OS ORIGINAIS
# ==========================================

@bot.tree.command(
    name="embed",
    description="Envia uma mensagem personalizada em embed."
)
@app_commands.describe(
    titulo="Título do embed",
    mensagem="Texto principal",
    canal="Canal onde o embed será enviado",
    imagem="Link de uma imagem (opcional)",
    rodape="Texto no final do embed (opcional)",
    miniatura="Link de uma miniatura (opcional)",
cor="Cor do embed: roxo, vermelho, azul, verde, preto..."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def criar_embed(
    interaction: discord.Interaction,
    titulo: str,
    mensagem: str,
    canal: discord.TextChannel,
    imagem: str = None,
    rodape: str = "Os Originais",
    miniatura: str = None,
    cor: str = "roxo"):
    cores = {
        "roxo": discord.Color.purple(),
        "vermelho": discord.Color.red(),
        "azul": discord.Color.blue(),
        "verde": discord.Color.green(),
        "amarelo": discord.Color.yellow(),
        "laranja": discord.Color.orange(),
        "preto": discord.Color.from_rgb(0, 0, 0),
        "rosa": discord.Color.from_rgb(255, 105, 180),
        "branco": discord.Color.from_rgb(255, 255, 255)
    }

    cor_embed = cores.get(cor.lower(), discord.Color.purple())

    try:
        embed = discord.Embed(
            title=titulo,
            description=mensagem,
            color=cor_embed,
            timestamp=discord.utils.utcnow()
        )
        # Mostra quem criou
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

                # Imagem opcional
        if imagem:
            if imagem.startswith(("http://", "https://")):
                embed.set_image(url=imagem)
                # Miniatura opcional
                
        if miniatura:
            if miniatura.startswith(("http://", "https://")):
                embed.set_thumbnail(url=miniatura)
            else:
                await interaction.response.send_message(
                    "❌ O campo miniatura precisa ser um link começando com http:// ou https://",
                    ephemeral=True
                )
                return
        # Rodapé
        if rodape:
            embed.set_footer(text=rodape)

        # Envia
        await canal.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Embed enviado em {canal.mention}!",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Não tenho permissão para enviar mensagens nesse canal.",
            ephemeral=True
        )

    except Exception as erro:
        print(f"❌ ERRO NO /EMBED: {erro}")

        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao criar o embed.",
                ephemeral=True
            )

# ==========================================
# 👤 USERINFO
# ==========================================

@bot.tree.command(
    name="userinfo",
    description="Mostra informações de um membro."
)
@app_commands.describe(
    usuario="Membro que você deseja consultar"
)
async def userinfo(
    interaction: discord.Interaction,
    usuario: discord.Member = None
):
    usuario = usuario or interaction.user

    # Cargos, removendo @everyone
    cargos = [
        cargo.mention
        for cargo in usuario.roles
        if cargo != interaction.guild.default_role
    ]

    cargos.reverse()

    if cargos:
        texto_cargos = " ".join(cargos)

        if len(texto_cargos) > 1000:
            texto_cargos = texto_cargos[:1000] + "..."
    else:
        texto_cargos = "Nenhum cargo."

    embed = discord.Embed(
        title=f"👤 Informações de {usuario.display_name}",
        color=discord.Color.purple(),
        timestamp=discord.utils.utcnow()
    )

    embed.set_thumbnail(
        url=usuario.display_avatar.url
    )

    embed.add_field(
        name="🏷️ Usuário",
        value=usuario.mention,
        inline=True
    )

    embed.add_field(
        name="🆔 ID",
        value=f"`{usuario.id}`",
        inline=True
    )

    embed.add_field(
        name="🤖 É bot?",
        value="Sim" if usuario.bot else "Não",
        inline=True
    )

    embed.add_field(
        name="📅 Conta criada",
        value=discord.utils.format_dt(
            usuario.created_at,
            style="F"
        ),
        inline=False
    )

    if usuario.joined_at:
        embed.add_field(
            name="📥 Entrou no servidor",
            value=discord.utils.format_dt(
                usuario.joined_at,
                style="F"
            ),
            inline=False
        )

    embed.add_field(
        name=f"🎭 Cargos ({len(cargos)})",
        value=texto_cargos,
        inline=False
    )

    embed.set_footer(
        text="Os Originais • User Info"
    )

    await interaction.response.send_message(
        embed=embed
    )


# ==========================================
# 💬 SAY
# ==========================================

@bot.tree.command(
    name="say",
    description="Faz o bot enviar uma mensagem."
)
@app_commands.describe(
    mensagem="Mensagem que será enviada",
    canal="Canal onde a mensagem será enviada"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def say(
    interaction: discord.Interaction,
    mensagem: str,
    canal: discord.TextChannel
):
    try:
        await canal.send(mensagem)

        await interaction.response.send_message(
            f"✅ Mensagem enviada em {canal.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Não tenho permissão para enviar mensagens nesse canal.",
            ephemeral=True
        )

    except Exception as erro:
        print(f"❌ ERRO NO /SAY: {erro}")

        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao enviar a mensagem.",
                ephemeral=True
            )



# ==========================================
# 📋 SISTEMA DE ALISTAMENTO - OS ORIGINAIS
# ==========================================

async def enviar_formulario_alistamento(canal):
    try:
        await canal.send(
            MODELO_ALISTAMENTO,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        print(f"✅ Formulário de alistamento enviado em #{canal.name}.")
    except discord.Forbidden:
        print("❌ Sem permissão para enviar o formulário ou mencionar os cargos no #alistamento.")
    except discord.HTTPException as erro:
        print(f"❌ Erro ao enviar formulário de alistamento: {erro}")

# ===== CARGOS DE RECOMPENSA POR NÍVEL =====
CARGOS_POR_NIVEL = {
    5: 1564684591741010011,   # Membro Ativo
    10: 1564684715305341049,  # Veterano
    20: 1564684811342188564,  # Elite
    30: 1564684883199000716   # Lenda
}

async def entregar_cargo_por_nivel(membro, nivel):
    for nivel_recompensa, cargo_id in CARGOS_POR_NIVEL.items():
        if nivel >= nivel_recompensa:
            cargo = membro.guild.get_role(cargo_id)

            if cargo is not None and cargo not in membro.roles:
                await membro.add_roles(
                    cargo,
                    reason=f"Recompensa por alcançar o nível {nivel}"
                )



@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # ===== SISTEMA DE XP =====
    if message.guild is not None:
        usuario_id = message.author.id
        agora = time.time()

        if agora - cooldowns_xp.get(usuario_id, 0) >= 60:
            ganho = random.randint(15, 25)

            xp_cursor.execute(
                "SELECT xp, nivel FROM experiencia WHERE user_id = ?",
                (usuario_id,)
            )
            dados = xp_cursor.fetchone()

            if dados is None:
                xp_atual = ganho
                nivel_atual = 0

                xp_cursor.execute(
                    "INSERT INTO experiencia (user_id, xp, nivel) VALUES (?, ?, ?)",
                    (usuario_id, xp_atual, nivel_atual)
                )
            else:
                xp_atual = dados[0] + ganho
                nivel_atual = dados[1]

                xp_cursor.execute(
                    "UPDATE experiencia SET xp = ? WHERE user_id = ?",
                    (xp_atual, usuario_id)
                )

            xp_db.commit()
            cooldowns_xp[usuario_id] = agora

            novo_nivel = int(xp_atual ** 0.5 / 5)

            if novo_nivel > nivel_atual:
                xp_cursor.execute(
                    "UPDATE experiencia SET nivel = ? WHERE user_id = ?",
                    (novo_nivel, usuario_id)
                )
                xp_db.commit()
                
                if isinstance(message.author, discord.Member):
                    try:
                        await entregar_cargo_por_nivel(
                            message.author, novo_nivel
                        )
                    except discord.Forbidden:
                        print("❌ Sem permissão para entregar cargos.")
                    except discord.HTTPException as erro:
                        print(f"❌ Erro ao entregar cargo: {erro}")


                canal_xp = bot.get_channel(CANAL_XP_ID)

                if canal_xp is not None:
                    await canal_xp.send(
                        f"🎉 Parabéns, {message.author.mention}! "
                        f"Você chegou ao nível **{novo_nivel}**!"
                    )
                else:
                    print("❌ Canal de XP não encontrado. Confira o ID.")

    # ===== FORMULÁRIO DE ALISTAMENTO =====
    if (
        isinstance(message.channel, discord.TextChannel)
        and message.channel.name == NOME_CANAL_ALISTAMENTO
    ):
        texto = message.content.strip()

        if texto != MODELO_ALISTAMENTO.strip():
            await enviar_formulario_alistamento(message.channel)

    # Mantém os comandos tradicionais funcionando
    await bot.process_commands(message)



@bot.event
async def on_ready_alistamento():
    pass



async def criar_imagem_rank(usuario, nivel, xp_atual, porcentagem):
    largura, altura = 900, 300

    imagem = Image.new("RGB", (largura, altura), (10, 6, 22))
    desenho = ImageDraw.Draw(imagem)

    # Borda neon roxa
    desenho.rounded_rectangle(
        (5, 5, largura - 5, altura - 5),
        radius=28,
        outline=(155, 60, 255),
        width=4
    )

    # Cartao principal
    desenho.rounded_rectangle(
        (15, 15, largura - 15, altura - 15),
        radius=24,
        fill=(22, 16, 40),
        outline=(75, 35, 115),
        width=2
    )

    # Fontes
    try:
        fonte_titulo = ImageFont.truetype("arial.ttf", 30)
        fonte_nome = ImageFont.truetype("arial.ttf", 27)
        fonte_normal = ImageFont.truetype("arial.ttf", 21)
        fonte_pequena = ImageFont.truetype("arial.ttf", 17)
    except OSError:
        fonte_titulo = ImageFont.load_default()
        fonte_nome = ImageFont.load_default()
        fonte_normal = ImageFont.load_default()
        fonte_pequena = ImageFont.load_default()

    # Titulo
    desenho.text(
        (260, 35),
        "RANK DO JOGADOR",
        font=fonte_titulo,
        fill=(210, 150, 255)
    )

    # Nome do usuario
    desenho.text(
        (260, 85),
        usuario.display_name[:25],
        font=fonte_nome,
        fill=(255, 255, 255)
    )

    # Nivel e XP
    desenho.text(
        (260, 130),
        f"NIVEL {nivel}   |   {xp_atual} XP",
        font=fonte_normal,
        fill=(195, 175, 225)
    )

    # Barra de XP
    x1, y1, x2, y2 = 260, 190, 820, 220

    desenho.rounded_rectangle(
        (x1, y1, x2, y2),
        radius=14,
        fill=(48, 37, 68)
    )

    porcentagem_segura = max(0, min(100, porcentagem))
    preenchimento = int((x2 - x1) * porcentagem_segura / 100)

    if preenchimento > 0:
        desenho.rounded_rectangle(
            (x1, y1, x1 + preenchimento, y2),
            radius=14,
            fill=(170, 70, 255)
        )

    # Porcentagem da barra
    desenho.text(
        (260, 230),
        f"{porcentagem_segura:.1f}% para o proximo nivel",
        font=fonte_pequena,
        fill=(190, 160, 220)
    )

    # Borda do avatar
    desenho.ellipse(
        (45, 55, 220, 230),
        fill=(120, 35, 190)
    )

    # Buscar avatar
    try:
        async with aiohttp.ClientSession() as sessao:
            async with sessao.get(usuario.display_avatar.url) as resposta:
                if resposta.status == 200:
                    avatar_bytes = await resposta.read()
                    avatar = Image.open(
                        BytesIO(avatar_bytes)
                    ).convert("RGBA")

                    avatar = avatar.resize((155, 155))

                    mascara = Image.new("L", (155, 155), 0)
                    ImageDraw.Draw(mascara).ellipse(
                        (0, 0, 155, 155),
                        fill=255
                    )

                    imagem.paste(avatar, (55, 65), mascara)
    except Exception as erro:
        print(f"Erro ao carregar avatar: {erro}")

    # Salvar imagem
    arquivo = BytesIO()
    imagem.save(arquivo, format="PNG")
    arquivo.seek(0)

    return discord.File(arquivo, filename="rank.png")



async def criar_imagem_top(bot, resultados):
    largura, altura = 900, 760

    imagem = Image.new("RGB", (largura, altura), (10, 6, 22))
    draw = ImageDraw.Draw(imagem)

    try:
        fonte_titulo = ImageFont.truetype("arial.ttf", 36)
        fonte_texto = ImageFont.truetype("arial.ttf", 22)
        fonte_pequena = ImageFont.truetype("arial.ttf", 17)
        fonte_podio = ImageFont.truetype("arial.ttf", 25)
    except OSError:
        fonte_titulo = ImageFont.load_default()
        fonte_texto = ImageFont.load_default()
        fonte_pequena = ImageFont.load_default()
        fonte_podio = ImageFont.load_default()

    # Fundo principal com borda neon
    draw.rounded_rectangle(
        (5, 5, largura - 5, altura - 5),
        radius=28,
        fill=(15, 8, 30),
        outline=(155, 60, 255),
        width=4
    )

    draw.rounded_rectangle(
        (15, 15, largura - 15, altura - 15),
        radius=24,
        fill=(22, 16, 40),
        outline=(75, 35, 115),
        width=2
    )

    # Cabecalho
    draw.text(
        (40, 28),
        "RANKING GERAL",
        font=fonte_titulo,
        fill=(210, 150, 255)
    )

    draw.text(
        (43, 75),
        "TOP 10  |  LENDAS DO SERVIDOR",
        font=fonte_pequena,
        fill=(175, 145, 205)
    )

    # Linha decorativa
    draw.rounded_rectangle(
        (40, 105, 860, 109),
        radius=2,
        fill=(135, 50, 220)
    )

    async with aiohttp.ClientSession() as session:
        for posicao, (user_id, xp, nivel) in enumerate(
            resultados[:10], start=1
        ):
            y = 125 + (posicao - 1) * 58

            # Cores especiais para o podio
            if posicao == 1:
                cor = (255, 210, 70)
                fundo = (48, 35, 20)
                medalha = "1º LUGAR"
            elif posicao == 2:
                cor = (220, 225, 240)
                fundo = (32, 32, 48)
                medalha = "2º LUGAR"
            elif posicao == 3:
                cor = (235, 155, 100)
                fundo = (48, 28, 25)
                medalha = "3º LUGAR"
            else:
                cor = (190, 130, 255)
                fundo = (25, 17, 43)
                medalha = f"{posicao}º"

            # Cartao do jogador
            draw.rounded_rectangle(
                (35, y, largura - 35, y + 49),
                radius=12,
                fill=fundo,
                outline=cor if posicao <= 3 else (100, 45, 150),
                width=3 if posicao == 1 else 2
            )

            membro = bot.get_user(user_id)

            if membro is None:
                try:
                    membro = await bot.fetch_user(user_id)
                except discord.HTTPException:
                    membro = None

            # Avatar circular
            if membro is not None:
                try:
                    url_avatar = str(
                        membro.display_avatar.replace(size=64).url
                    )

                    async with session.get(url_avatar) as resposta:
                        if resposta.status == 200:
                            dados = await resposta.read()
                            avatar = Image.open(
                                BytesIO(dados)
                            ).convert("RGBA")
                            avatar = avatar.resize((40, 40))

                            mascara = Image.new("L", (40, 40), 0)
                            ImageDraw.Draw(mascara).ellipse(
                                (0, 0, 40, 40),
                                fill=255
                            )

                            imagem.paste(
                                avatar,
                                (42, y + 4),
                                mascara
                            )
                except Exception:
                    pass

            # Posicao
            draw.text(
                (92, y + 10),
                medalha,
                font=fonte_podio if posicao == 1 else fonte_texto,
                fill=cor
            )

            # Nome
            nome = (
                membro.display_name
                if membro
                else f"Membro {user_id}"
            )

            draw.text(
                (250, y + 5),
                nome[:22],
                font=fonte_texto,
                fill=(255, 255, 255)
            )

            # Nivel e XP
            draw.text(
                (250, y + 28),
                f"Nivel {nivel}  |  {xp} XP",
                font=fonte_pequena,
                fill=(190, 170, 220)
            )

    # Rodape
    draw.text(
        (40, 710),
        "Continue conversando para subir no ranking!",
        font=fonte_pequena,
        fill=(190, 145, 230)
    )

    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer



@bot.tree.command(
    name="rank",

    description="Veja seu nível e XP",
    guild=discord.Object(id=1562425457905770518)
)
async def rank(interaction: discord.Interaction):
    await interaction.response.defer()

    xp_cursor.execute(
        "SELECT xp, nivel FROM experiencia WHERE user_id = ?",
        (interaction.user.id,)
    )
    dados = xp_cursor.fetchone()


    if dados is None:
        xp_atual = 0
        nivel = 0
    else:
        xp_atual, nivel = dados

    # XP necessário para o próximo nível
    xp_proximo = ((nivel + 1) * 5) ** 2
    xp_anterior = (nivel * 5) ** 2

    xp_no_nivel = xp_atual - xp_anterior
    xp_necessario = xp_proximo - xp_anterior

    progresso = min(1, max(0, xp_no_nivel / xp_necessario))
    porcentagem = int(progresso * 100)

    # Barra visual de progresso
    blocos = 10
    preenchidos = int(progresso * blocos)
    barra = "🟩" * preenchidos + "⬛" * (blocos - preenchidos)

    faltam = max(0, xp_proximo - xp_atual)

    # Próximo cargo de recompensa
    cargos_recompensa = {
        5: "Membro Ativo",
        10: "Veterano",
        20: "Elite",
        30: "Lenda"
    }

    proximo_cargo = next(
        (
            nome
            for nivel_recompensa, nome in sorted(cargos_recompensa.items())
            if nivel < nivel_recompensa
        ),
        "Todos os cargos de recompensa alcançados! 🏆"
    )

    embed = discord.Embed(
        title="🏆 Seu Ranking",
        description=(
            f"👤 **Membro:** {interaction.user.mention}\n"
            f"⭐ **Nível:** {nivel}\n"
            f"✨ **XP total:** {xp_atual}\n\n"
            f"📊 **Progresso para o nível {nivel + 1}**\n"
            f"{barra} **{porcentagem}%**\n"
            f"✨ Faltam **{faltam} XP**\n\n"
            f"🎁 **Próximo cargo:** {proximo_cargo}"
        ),
        color=discord.Color.from_rgb(0, 0, 0)
    )


    embed.set_footer(text="Converse no servidor para ganhar XP!")
    print("DEBUG: começando a criar imagem do rank")

    arquivo_rank = await criar_imagem_rank(
        interaction.user,
        nivel,
        xp_atual,
        porcentagem
    )
    print("DEBUG: imagem do rank criada")

    embed.set_image(url="attachment://rank.png")
    print("DEBUG: enviando resposta ao Discord")
    await interaction.followup.send(embed=embed, file=arquivo_rank)


@bot.tree.command(
    name="top",
    description="Veja os 10 membros com mais XP",
    guild=discord.Object(id=1562425457905770518)
)
async def top(interaction: discord.Interaction):
    await interaction.response.defer()

    xp_cursor.execute("""
        SELECT user_id, xp, nivel
        FROM experiencia
        ORDER BY xp DESC, nivel DESC
        LIMIT 10
    """)

    resultados = xp_cursor.fetchall()

    if not resultados:
        await interaction.response.send_message(
            "📊 Ainda não há membros no ranking de XP!"
        )
        return

    medalhas = ["🥇", "🥈", "🥉"]
    linhas = []

    for posicao, (user_id, xp, nivel) in enumerate(resultados, start=1):
        medalha = (
            medalhas[posicao - 1]
            if posicao <= 3
            else f"`{posicao}º`"
        )

        linhas.append(
            f"{medalha} <@{user_id}>\n"
            f"　⭐ Nível **{nivel}** · ✨ **{xp} XP**"
        )

    embed = discord.Embed(
        title="🏆 RANKING GERAL — DE XP",
        description="\n\n".join(linhas),
        color=discord.Color.from_rgb(0, 0, 0)
    )

    embed.set_footer(
        text="Continue conversando para ganhar XP!"
    )

    arquivo_top = await criar_imagem_top(bot, resultados)
    arquivo_discord = discord.File(arquivo_top, filename="top.png")
    embed.set_image(url="attachment://top.png")
    await interaction.followup.send(embed=embed, file=arquivo_discord)



    
# ===== MENU DE CARGOS ORIGINAIS =====


class CargosSelect(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Gartic", emoji="🎨"),
            discord.SelectOption(label="Free Fire", emoji="🔥"),
            discord.SelectOption(label="Minecraft", emoji="⛏️"),
            discord.SelectOption(label="Outros Jogos", emoji="🕹️"),
            discord.SelectOption(label="Samp", emoji="💣"),
        ]

        super().__init__(
            placeholder="🎮 Escolha seus cargos!",
            min_values=1,
            max_values=5,
            options=opcoes
        )

    async def callback(self, interaction: discord.Interaction):
        # Apenas registra a seleção; ainda não entrega os cargos.
        await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild

        if guild is None:
            await interaction.followup.send(
                "Este botão só funciona dentro do servidor.",
                ephemeral=True
            )
            return
        self.view.escolhidos[interaction.user.id] = list(self.values)

        await interaction.followup.send(
            "🎮 Seleção salva! Clique em **✅ Confirmar cargos** "
            "para receber seus cargos.",
            ephemeral=True
        )


class ConfirmarCargosButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Confirmar cargos",
            emoji="✅",
            style=discord.ButtonStyle.success
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "Este botão só funciona dentro do servidor.",
                ephemeral=True
            )
            return

        view = self.view
        selecionados = view.escolhidos.get(interaction.user.id)

        if not selecionados:
            await interaction.response.send_message(
                "⚠️ Primeiro selecione pelo menos um jogo no menu.",
                ephemeral=True
            )
            return

        nomes = ["Gartic", "Free Fire", "Minecraft", "Outros Jogos", "Samp"]

        cargos = {
            nome: discord.utils.get(guild.roles, name=nome)
            for nome in nomes
        }

        if any(cargo is None for cargo in cargos.values()):
            await interaction.response.send_message(
                "❌ Confira se os cinco cargos existem e se os nomes "
                "estão exatamente iguais aos do código.",
                ephemeral=True
            )
            return

        membro = interaction.user
        escolhidos = [cargos[nome] for nome in selecionados]

        remover = [
            cargo for cargo in cargos.values()
            if cargo in membro.roles and cargo not in escolhidos
        ]

        adicionar = [
            cargo for cargo in escolhidos
            if cargo not in membro.roles
        ]

        try:
            if remover:
                await membro.remove_roles(
                    *remover,
                    reason="Atualização dos cargos pelo menu"
                )

            if adicionar:
                await membro.add_roles(
                    *adicionar,
                    reason="Cargos escolhidos no menu"
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não consigo gerenciar esses cargos. Verifique se "
                "tenho a permissão **Gerenciar cargos** e se meu cargo "
                "está acima dos cargos de jogos.",
                ephemeral=True
            )
            return

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ O Discord não conseguiu atualizar os cargos. "
                "Tente novamente.",
                ephemeral=True
            )
            return

        view.escolhidos.pop(interaction.user.id, None)

        await interaction.response.send_message(
            "💜 Seus cargos foram atualizados com sucesso!",
            ephemeral=True
        )


class CargosView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.escolhidos = {}
        self.add_item(CargosSelect())
        self.add_item(ConfirmarCargosButton())


@bot.tree.command(
    name="cargos",
    description="Escolha seus cargos.",
    guild=discord.Object(id=1562425457905770518)
)
@app_commands.default_permissions(administrator=True)
async def cargos(interaction: discord.Interaction):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Somente administradores podem usar o comando /cargos.",
            ephemeral=True
        )
        return

    # Mantenha aqui o restante original do comando
    embed = discord.Embed(
        title="*__ESCOLHA SEUS CARGOS__*",
        description=(
            "*Bem-vindo à Gaming Community!*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"

            "***🎮 PERSONALIZE SUA EXPERIÊNCIA***\n"
            "*Escolha abaixo os jogos que você curte e encontre pessoas para jogar com você.*\n\n"
            "***🎨 Gartic***\n"
            "*Para quem gosta de desenho, criatividade e diversão.*\n\n"
            "***🔥 Free Fire***\n"
            "*Para quem curte ação e partidas competitivas.*\n\n"
            "***⛏️ Minecraft***\n"
            "*Para quem gosta de construir, explorar e sobreviver.*\n\n"
            "***🕹️ Outros Jogos***\n"
            "*Para jogadores de outros títulos e estilos.*\n\n"
            "***💣 Samp***\n"
            "*Para quem curte San Andreas Multiplayer.*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "***👇 COMO ESCOLHER***\n"
            "*• Abra o menu abaixo desta mensagem.*\n"
            "*• Selecione um ou mais jogos.*\n"
            "*• Clique em **✅ __Confirmar cargos__** para salvar.*\n\n"
            "*✨ Você pode escolher mais de um jogo!*"
        ),
        color=discord.Color.from_rgb(0, 0, 0)
    )

    embed.set_footer(text="Gaming Community")

    await interaction.response.send_message(
        embed=embed,
        view=CargosView()
    )

class ParticiparEvento(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.participantes = set()

    @discord.ui.button(
        label="Participar (0)",
        style=discord.ButtonStyle.success,
        emoji="🙋",
        custom_id="evento:participar"
    )
    async def participar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        usuario_id = interaction.user.id

        if usuario_id in self.participantes:
            self.participantes.remove(usuario_id)
            mensagem = "Você saiu da lista de participantes."
        else:
            self.participantes.add(usuario_id)
            mensagem = "Você confirmou presença no evento!"

        button.label = f"Participar ({len(self.participantes)})"

        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            mensagem,
            ephemeral=True
        )


@bot.tree.command(
    name="evento",
    description="Publica um evento na agenda do servidor",
    guild=discord.Object(id=1562425457905770518)
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    nome="Nome do evento",
    data="Data e horário do evento",
    descricao="Descrição do evento"
)
async def evento(
    interaction: discord.Interaction,
    nome: str,
    data: str,
    descricao: str
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Você não tem permissão para criar eventos!",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    canal = interaction.guild.get_channel(CANAL_AGENDA_ID)

    if canal is None:
        await interaction.followup.send(
            "❌ Não encontrei o canal da agenda. Confere o ID.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"📅・{nome}",
        description=(
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{descricao}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(0, 0, 0)
    )

    embed.add_field(
        name="📆 DATA E HORÁRIO",
        value=f"```fix\n{data}\n```",
        inline=False
    )

    embed.add_field(
        name="🙋 PARTICIPAÇÃO",
        value="Clique no botão abaixo para confirmar sua presença!",
        inline=False
    )

    embed.set_footer(
        text=f"Evento organizado por {interaction.user.display_name} • Agenda Oficial",
        icon_url=interaction.user.display_avatar.url
    )
    embed.set_thumbnail(
    url="https://i.ibb.co/ycGWk78y/Emblema-Neon-SYNNVCTAX.png"
)

    view = InscricaoCampeonato(nome)

    mensagem = await canal.send(
        embed=embed,
        view=view
    )

    campeonatos_ativos[nome]["view"] = view
    campeonatos_ativos[nome]["mensagem_id"] = mensagem.id

    await interaction.followup.send(
        f"✅ Evento **{nome}** publicado no canal {canal.mention}!",
        ephemeral=True
    )

class FormularioEquipe(discord.ui.Modal, title="Inscrever equipe"):
    def __init__(self, nome_campeonato):
        super().__init__()
        self.nome_campeonato = nome_campeonato

    nome_equipe = discord.ui.TextInput(
        label="Nome da equipe",
        placeholder="Digite o nome da equipe",
        max_length=50
    )

    jogador2 = discord.ui.TextInput(
        label="ID do jogador 2",
        placeholder="ID numérico do Discord",
        max_length=20
    )

    jogador3 = discord.ui.TextInput(
        label="ID do jogador 3",
        placeholder="ID numérico do Discord",
        max_length=20
    )

    jogador4 = discord.ui.TextInput(
        label="ID do jogador 4",
        placeholder="ID numérico do Discord",
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        campeonato = campeonatos_ativos.get(self.nome_campeonato)

        if campeonato is None:
            await interaction.response.send_message(
                "❌ Campeonato não encontrado.",
                ephemeral=True
            )
            return

        equipes = campeonato["equipes"]

        if len(equipes) >= campeonato["limite"]:
            await interaction.response.send_message(
                "❌ As inscrições de equipes estão lotadas!",
                ephemeral=True
            )
            return

        try:
            ids_jogadores = [
                interaction.user.id,
                int(self.jogador2.value),
                int(self.jogador3.value),
                int(self.jogador4.value)
            ]
        except ValueError:
            await interaction.response.send_message(
                "❌ Os IDs dos jogadores precisam ser números.",
                ephemeral=True
            )
            return

        if len(set(ids_jogadores)) != 4:
            await interaction.response.send_message(
                "❌ Cada equipe precisa ter quatro jogadores diferentes.",
                ephemeral=True
            )
            return

        for equipe in equipes:
            if any(
                jogador_id in equipe["jogadores"]
                for jogador_id in ids_jogadores
            ):
                await interaction.response.send_message(
                    "❌ Um ou mais jogadores já estão inscritos em outra equipe.",
                    ephemeral=True
                )
                return

        equipes.append({
            "nome": self.nome_equipe.value,
            "capitao": interaction.user.id,
            "jogadores": ids_jogadores
        })
        view = campeonato.get("view")
        print("Equipes cadastradas:", len(equipes))
        print("ID da mensagem:", campeonato.get("mensagem_id"))
        mensagem_id = campeonato.get("mensagem_id")

        if view is not None and mensagem_id is not None:
            for botao in view.children:
                if isinstance(botao, discord.ui.Button):
                    botao.label = (
                        f"Inscrever-se ({len(equipes)}/{campeonato['limite']})"
                    )

            try:
                mensagem = await interaction.channel.fetch_message(
                    mensagem_id
                )
                await mensagem.edit(view=view)
                print(f"Contador atualizado para {len(equipes)} equipes")
            except (discord.NotFound, discord.HTTPException) as erro:
                print(f"Erro ao atualizar contador de equipes: {erro}")
        await interaction.response.send_message(
            f"✅ Equipe **{self.nome_equipe.value}** inscrita com sucesso!",
            ephemeral=True
        )


class InscricaoCampeonato(discord.ui.View):
    def __init__(self, nome_campeonato):
        super().__init__(timeout=None)
        self.nome_campeonato = nome_campeonato

    @discord.ui.button(
        label="Inscrever-se (0/8)",
        style=discord.ButtonStyle.success,
        emoji="📝",
        custom_id="campeonato:inscrever"
    )
    async def inscrever(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        campeonato = campeonatos_ativos.get(self.nome_campeonato)

        if campeonato is None:
            await interaction.response.send_message(
                "❌ Este campeonato não foi encontrado.",
                ephemeral=True
            )
            return

        usuario_id = interaction.user.id
        participantes = campeonato["participantes"]
        if campeonato["tipo"] == "Equipes":
            await interaction.response.send_modal(
                FormularioEquipe(self.nome_campeonato)
            )
            return

        if usuario_id in participantes:
            await interaction.response.send_message(
                "Você já está inscrito neste campeonato!",
                ephemeral=True
            )
            return

        if len(participantes) >= campeonato["limite"]:
            await interaction.response.send_message(
                "❌ As inscrições estão lotadas!",
                ephemeral=True
            )
            return

        participantes.append(usuario_id)
        button.label = (
            f"Inscrever-se ({len(participantes)}/{campeonato['limite']})"
        )

        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            "✅ Você foi inscrito no campeonato!",
            ephemeral=True
        )

@bot.tree.command(
    name="sortear_grupos",
    description="Sortear os inscritos nos grupos A e B",
    guild=discord.Object(id=1562425457905770518)
)
@app_commands.default_permissions(administrator=True)

@app_commands.describe(
    nome="Nome exato do campeonato"
)
async def sortear_grupos(
    interaction: discord.Interaction,
    nome: str
):
    campeonato = campeonatos_ativos.get(nome)

    if campeonato is None:
        await interaction.response.send_message(
            "❌ Não encontrei esse campeonato.",
            ephemeral=True
        )
        return

    if campeonato["tipo"] == "Equipes":
        participantes = campeonato["equipes"]
    else:
        participantes = campeonato["participantes"]

    if len(participantes) != LIMITE_CAMPEONATO:
        await interaction.response.send_message(
            f"❌ São necessários exatamente {LIMITE_CAMPEONATO} inscritos. "
            f"Atualmente: {len(participantes)}.",
            ephemeral=True
        )
        return

    sorteados = participantes.copy()
    random.shuffle(sorteados)

    grupos_campeonato[nome] = {
        "Grupo A": sorteados[:PARTICIPANTES_POR_GRUPO],
        "Grupo B": sorteados[PARTICIPANTES_POR_GRUPO:]
    }
    if campeonato["tipo"] == "Equipes":
        classificacao_campeonato[nome] = {
            nome_grupo: {
                equipe["nome"]: {
                    "pontos": 0,
                    "vitorias": 0,
                    "derrotas": 0
                }
                for equipe in equipes_grupo
            }
            for nome_grupo, equipes_grupo
            in grupos_campeonato[nome].items()
        }
    else:
        classificacao_campeonato[nome] = {
            nome_grupo: {
                usuario_id: {
                    "pontos": 0,
                    "vitorias": 0,
                    "derrotas": 0
                }
                for usuario_id in participantes_grupo
            }
            for nome_grupo, participantes_grupo
            in grupos_campeonato[nome].items()
        }

    embed = discord.Embed(
        title=f"🏆 Grupos — {nome}",
        color=discord.Color.from_rgb(0, 0, 0)
    )

    for nome_grupo, participantes_grupo in grupos_campeonato[nome].items():
        if campeonato["tipo"] == "Equipes":
            membros = "\n".join(
                f"• **{equipe['nome']}**\n"
                + "\n".join(
                    f"  - <@{jogador_id}>"
                    for jogador_id in equipe["jogadores"]
                )
                for equipe in participantes_grupo
            )
        else:
            membros = "\n".join(
                f"• <@{usuario_id}>"
                for usuario_id in participantes_grupo
            )

        embed.add_field(
            name=f"⚔️ {nome_grupo}",
            value=membros,
            inline=True
        )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(
    name="classificacao",
    description="Ver a classificação dos grupos",
    guild=discord.Object(id=1562425457905770518)
)
@app_commands.describe(
    nome="Nome exato do campeonato"
)
async def classificacao(
    interaction: discord.Interaction,
    nome: str
):
    classificacao = classificacao_campeonato.get(nome)
    campeonato = campeonatos_ativos.get(nome)

    if classificacao is None or campeonato is None:
        await interaction.response.send_message(
            "❌ Os grupos ainda não foram sorteados para esse campeonato.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"🏆 Classificação — {nome}",
        color=discord.Color.from_rgb(0, 0, 0)
    )

    for nome_grupo, participantes in classificacao.items():
        linhas = []

        ordenados = sorted(
            participantes.items(),
            key=lambda item: (
                item[1]["pontos"],
                item[1]["vitorias"]
            ),
            reverse=True
        )

        for posicao, (identificador, dados) in enumerate(ordenados, start=1):
            if campeonato["tipo"] == "Equipes":
                nome_participante = identificador
            else:
                nome_participante = f"<@{identificador}>"

            linhas.append(
                f"**{posicao}.** {nome_participante} — "
                f"**{dados['pontos']} pts** | "
                f"V: {dados['vitorias']} | D: {dados['derrotas']}"
            )

        embed.add_field(
            name=f"⚔️ {nome_grupo}",
            value="\n".join(linhas) or "Sem participantes.",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(
    name="resultado_partida",
    description="Registrar o resultado de uma partida",
    guild=discord.Object(id=1562425457905770518)
)
@app_commands.default_permissions(administrator=True)

@app_commands.describe(
    nome="Nome exato do campeonato",
    grupo="Grupo A ou Grupo B",
    vencedor="Nome da equipe vencedora ou jogador vencedor",
    perdedor="Nome da equipe perdedora ou jogador perdedor"
)
@app_commands.choices(
    grupo=[
        app_commands.Choice(name="Grupo A", value="Grupo A"),
        app_commands.Choice(name="Grupo B", value="Grupo B")
    ]
)
async def resultado_partida(
    interaction: discord.Interaction,
    nome: str,
    grupo: app_commands.Choice[str],
    vencedor: str,
    perdedor: str
):
    campeonato = campeonatos_ativos.get(nome)
    classificacao = classificacao_campeonato.get(nome)

    if campeonato is None or classificacao is None:
        await interaction.response.send_message(
            "❌ Campeonato não encontrado ou grupos ainda não sorteados.",
            ephemeral=True
        )
        return

    jogadores = classificacao.get(grupo.value, {})

    if campeonato["tipo"] == "Equipes":
        vencedor_nome = vencedor.strip()
        perdedor_nome = perdedor.strip()

        if vencedor_nome == perdedor_nome:
            await interaction.response.send_message(
                "❌ As equipes precisam ser diferentes.",
                ephemeral=True
            )
            return

        if vencedor_nome not in jogadores or perdedor_nome not in jogadores:
            await interaction.response.send_message(
                "❌ Os nomes precisam corresponder às equipes do grupo escolhido.",
                ephemeral=True
            )
            return

        jogadores[vencedor_nome]["pontos"] += 3
        jogadores[vencedor_nome]["vitorias"] += 1
        jogadores[perdedor_nome]["derrotas"] += 1

        mensagem_vencedor = vencedor_nome
        mensagem_perdedor = perdedor_nome

    else:
        try:
            vencedor_id = int(vencedor.strip("<@!>"))
            perdedor_id = int(perdedor.strip("<@!>"))
        except ValueError:
            await interaction.response.send_message(
                "❌ Informe os IDs dos jogadores ou mencione-os no modo Individual.",
                ephemeral=True
            )
            return

        if vencedor_id == perdedor_id:
            await interaction.response.send_message(
                "❌ O vencedor e o perdedor precisam ser diferentes.",
                ephemeral=True
            )
            return

        if vencedor_id not in jogadores or perdedor_id not in jogadores:
            await interaction.response.send_message(
                "❌ Os dois jogadores precisam pertencer ao grupo escolhido.",
                ephemeral=True
            )
            return

        jogadores[vencedor_id]["pontos"] += 3
        jogadores[vencedor_id]["vitorias"] += 1
        jogadores[perdedor_id]["derrotas"] += 1

        mensagem_vencedor = f"<@{vencedor_id}>"
        mensagem_perdedor = f"<@{perdedor_id}>"

    await interaction.response.send_message(
        f"✅ Resultado registrado no **{grupo.value}**!\n"
        f"🏆 Vencedor: {mensagem_vencedor} — +3 pontos\n"
        f"❌ Derrotado: {mensagem_perdedor}",
        ephemeral=False
    )
@bot.tree.command(
    name="campeonato",
    description="Criar um campeonato no servidor",
    guild=discord.Object(id=1562425457905770518)
)
@app_commands.default_permissions(administrator=True)

@app_commands.describe(
    nome="Nome do campeonato",
    tipo="Individual ou equipes",
    jogo="Jogo do campeonato"
)
@app_commands.choices(
    tipo=[
        app_commands.Choice(name="Individual", value="Individual"),
        app_commands.Choice(name="Equipes", value="Equipes")
    ]
)
async def campeonato(
    interaction: discord.Interaction,
    nome: str,
    tipo: app_commands.Choice[str],
    jogo: str
):
    await interaction.response.defer(ephemeral=True)

    campeonatos_ativos[nome] = {
        "nome": nome,
        "tipo": tipo.value,
        "jogo": jogo,
        "participantes": [],
        "equipes": [],
        "limite": LIMITE_CAMPEONATO
    }


    canal = interaction.guild.get_channel(CANAL_CAMPEONATO_ID)

    if canal is None:
        await interaction.followup.send(
            "❌ Não encontrei o canal #campeonato. Confere o ID.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"🏆 {nome}",
        description=(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚔️ **INSCRIÇÕES ABERTAS**\n\n"
            f"🎮 **Jogo:** {jogo}\n"
            f"👥 **Formato:** {tipo.value}\n"
            f"📋 **Limite:** {LIMITE_CAMPEONATO}\n"
            "🏅 **Etapas:** Fase de grupos e mata-mata\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(0, 0, 0)
    )

    embed.set_footer(text="SYNNVCTAX • Campeonatos")

    view = InscricaoCampeonato(nome)

    mensagem = await canal.send(
        embed=embed,
        view=view
    )

    campeonatos_ativos[nome]["view"] = view
    campeonatos_ativos[nome]["mensagem_id"] = mensagem.id
    await interaction.followup.send(
        f"✅ Campeonato **{nome}** publicado em {canal.mention}!",
        ephemeral=True
    )



@bot.tree.command(
    name="criar_semifinais",
    description="Classificar os melhores e criar as semifinais",
    guild=discord.Object(id=1562425457905770518)
)
@app_commands.default_permissions(administrator=True)

@app_commands.describe(
    nome="Nome exato do campeonato"
)
async def criar_semifinais(
    interaction: discord.Interaction,
    nome: str
):
    classificacao = classificacao_campeonato.get(nome)
    campeonato = campeonatos_ativos.get(nome)

    if classificacao is None or campeonato is None:
        await interaction.response.send_message(
            "❌ Sorteie os grupos e registre os resultados primeiro.",
            ephemeral=True
        )
        return

    if nome in mata_mata_campeonato:
        await interaction.response.send_message(
            "❌ As semifinais deste campeonato já foram criadas.",
            ephemeral=True
        )
        return

    if any(
        dados["vitorias"] + dados["derrotas"] == 0
        for jogadores in classificacao.values()
        for dados in jogadores.values()
    ):
        await interaction.response.send_message(
            "❌ Registre os resultados das partidas dos grupos antes.",
            ephemeral=True
        )
        return

    grupos_ordenados = {}

    for nome_grupo, jogadores in classificacao.items():
        ordenados = sorted(
            jogadores.items(),
            key=lambda item: (
                item[1]["pontos"],
                item[1]["vitorias"]
            ),
            reverse=True
        )
        grupos_ordenados[nome_grupo] = ordenados

    grupo_a = grupos_ordenados.get("Grupo A", [])
    grupo_b = grupos_ordenados.get("Grupo B", [])

    if len(grupo_a) < 2 or len(grupo_b) < 2:
        await interaction.response.send_message(
            "❌ Cada grupo precisa ter pelo menos dois participantes.",
            ephemeral=True
        )
        return

    mata_mata_campeonato[nome] = {
        "Semifinal 1": {
            "jogador1": grupo_a[0][0],
            "jogador2": grupo_b[1][0],
            "vencedor": None
        },
        "Semifinal 2": {
            "jogador1": grupo_b[0][0],
            "jogador2": grupo_a[1][0],
            "vencedor": None
        },
        "Final": {
            "jogador1": None,
            "jogador2": None,
            "vencedor": None
        }
    }

    if campeonato["tipo"] == "Equipes":
        semifinal1 = (
            f"**{grupo_a[0][0]}** × **{grupo_b[1][0]}**"
        )
        semifinal2 = (
            f"**{grupo_b[0][0]}** × **{grupo_a[1][0]}**"
        )
    else:
        semifinal1 = (
            f"<@{grupo_a[0][0]}> × <@{grupo_b[1][0]}>"
        )
        semifinal2 = (
            f"<@{grupo_b[0][0]}> × <@{grupo_a[1][0]}>"
        )

    embed = discord.Embed(
        title=f"🏆 Semifinais — {nome}",
        description=(
            f"⚔️ **Semifinal 1**\n{semifinal1}\n\n"
            f"⚔️ **Semifinal 2**\n{semifinal2}"
        ),
        color=discord.Color.from_rgb(0, 0, 0)
    )

    await interaction.response.send_message(embed=embed)



@bot.tree.command(
    name="resultado_semifinal",
    description="Registrar o vencedor de uma semifinal",
    guild=discord.Object(id=1562425457905770518)
)
@app_commands.default_permissions(administrator=True)

@app_commands.describe(
    nome="Nome exato do campeonato",
    semifinal="Escolha a semifinal",
    vencedor="Mencione o jogador vencedor"
)
@app_commands.choices(
    semifinal=[
        app_commands.Choice(name="Semifinal 1", value="Semifinal 1"),
        app_commands.Choice(name="Semifinal 2", value="Semifinal 2")
    ]
)
async def resultado_semifinal(
    interaction: discord.Interaction,
    nome: str,
    semifinal: app_commands.Choice[str],
    vencedor: str
):
    mata_mata = mata_mata_campeonato.get(nome)
    campeonato = campeonatos_ativos.get(nome)

    if mata_mata is None or campeonato is None:
        await interaction.response.send_message(
            "❌ Crie as semifinais primeiro.",
            ephemeral=True
        )
        return

    partida = mata_mata[semifinal.value]

    if partida["vencedor"] is not None:
        await interaction.response.send_message(
            "❌ O resultado dessa semifinal já foi registrado.",
            ephemeral=True
        )
        return

    vencedor_informado = vencedor.strip()

    if campeonato["tipo"] == "Equipes":
        if vencedor_informado not in (
            partida["jogador1"],
            partida["jogador2"]
        ):
            await interaction.response.send_message(
                "❌ Informe exatamente o nome de uma das equipes dessa semifinal.",
                ephemeral=True
            )
            return

        vencedor_id = vencedor_informado
        mensagem_vencedor = vencedor_informado

    else:
        try:
            vencedor_id = int(vencedor_informado.strip("<@!>"))
        except ValueError:
            await interaction.response.send_message(
                "❌ Informe o ID ou a menção do jogador vencedor.",
                ephemeral=True
            )
            return

        if vencedor_id not in (
            partida["jogador1"],
            partida["jogador2"]
        ):
            await interaction.response.send_message(
                "❌ O vencedor precisa ser um dos jogadores dessa semifinal.",
                ephemeral=True
            )
            return

        mensagem_vencedor = f"<@{vencedor_id}>"

    partida["vencedor"] = vencedor_id

    outra_semifinal = (
        "Semifinal 2"
        if semifinal.value == "Semifinal 1"
        else "Semifinal 1"
    )

    outro_vencedor = mata_mata[outra_semifinal]["vencedor"]

    if outro_vencedor is not None:
        mata_mata["Final"]["jogador1"] = mata_mata["Semifinal 1"]["vencedor"]
        mata_mata["Final"]["jogador2"] = mata_mata["Semifinal 2"]["vencedor"]

        await interaction.response.send_message(
            f"✅ Vencedor registrado: **{mensagem_vencedor}**!\n"
            "🏆 As duas semifinais foram concluídas. A final está pronta!"
        )
    else:
        await interaction.response.send_message(
            f"✅ Vencedor da {semifinal.value}: **{mensagem_vencedor}**!\n"
            "Aguardando o resultado da outra semifinal."
        )

@bot.tree.command(
    name="resultado_final",
    description="Registrar o campeão do campeonato",
    guild=discord.Object(id=1562425457905770518)
)
@app_commands.default_permissions(administrator=True)

@app_commands.describe(
    nome="Nome exato do campeonato",
    vencedor="Mencione o jogador campeão"
)
async def resultado_final(
    interaction: discord.Interaction,
    nome: str,
    vencedor: str
):
    mata_mata = mata_mata_campeonato.get(nome)
    campeonato = campeonatos_ativos.get(nome)

    if mata_mata is None or campeonato is None:
        await interaction.response.send_message(
            "❌ Crie as semifinais primeiro.",
            ephemeral=True
        )
        return

    final = mata_mata["Final"]

    if final["jogador1"] is None or final["jogador2"] is None:
        await interaction.response.send_message(
            "❌ Registre os vencedores das duas semifinais primeiro.",
            ephemeral=True
        )
        return

    vencedor_informado = vencedor.strip()

    if campeonato["tipo"] == "Equipes":
        if vencedor_informado not in (
            final["jogador1"],
            final["jogador2"]
        ):
            await interaction.response.send_message(
                "❌ Informe exatamente o nome de uma das equipes finalistas.",
                ephemeral=True
            )
            return

        vencedor_id = vencedor_informado
        mensagem_vencedor = f"**{vencedor_informado}**"

    else:
        try:
            vencedor_id = int(vencedor_informado.strip("<@!>"))
        except ValueError:
            await interaction.response.send_message(
                "❌ Informe o ID ou a menção do jogador vencedor.",
                ephemeral=True
            )
            return

        if vencedor_id not in (
            final["jogador1"],
            final["jogador2"]
        ):
            await interaction.response.send_message(
                "❌ O campeão precisa ser um dos finalistas.",
                ephemeral=True
            )
            return

        mensagem_vencedor = f"<@{vencedor_id}>"

    if final["vencedor"] is not None:
        await interaction.response.send_message(
            "❌ O campeão deste campeonato já foi registrado.",
            ephemeral=True
        )
        return

    final["vencedor"] = vencedor_id

    embed = discord.Embed(
        title="🏆 CAMPEÃO DO SYNNVCTAX!",
        description=(
            f"🎉 Parabéns, {mensagem_vencedor}!\n\n"
            f"Você venceu o campeonato **{nome}**!"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text="SYNNVCTAX • Campeonatos")

    await interaction.response.send_message(embed=embed)
    
bot.run(TOKEN)