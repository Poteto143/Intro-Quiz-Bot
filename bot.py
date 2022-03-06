# -*- coding: utf-8 -*- #1
import discord
import asyncio
from os import getenv
import sys
from discord.ext import commands
import time
from random import randint
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import traceback
import pprint
import Cogs.sessionsManager as sm
import csv

args = sys.argv
if(len(args) == 2):
    if(args[1] == "Production"):
        print("本番環境で起動しています")
        token = getenv("INTRO_KEY")
        prefix = "iq:"
    else:
        print("テスト環境で起動しています")
        token = getenv("INTRO_TEST_KEY")
        prefix = "it:"
else:
    print("テスト環境で起動しています")
    token = getenv("INTRO_TEST_KEY")
    prefix = "it:"

intents = discord.Intents.none()
intents.members = True
intents.voice_states = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True

bot = commands.Bot(command_prefix=prefix, intents=intents)
bot.remove_command("help")
bot.load_extension("jishaku")
client_credentials_manager = spotipy.oauth2.SpotifyClientCredentials(
    getenv("SPOTIFY_CLIENT_ID"), getenv("SPOTIFY_CLIENT_SECRET"))
spotify = spotipy.Spotify(
    client_credentials_manager=client_credentials_manager)

with open("./src/presetsJP.csv", encoding="utf-8") as f:
    reader = csv.reader(f)
    presetsJP = [row for row in reader]

with open("./src/presetsEN.csv", encoding="utf-8") as f:
    reader = csv.reader(f)
    presetsEN = [row for row in reader]


bot.sessions = sm.SessionsGroup()
bot.game_tasks = {}

import Cogs.quiz as quiz
import Cogs.search as search
bot.add_cog(quiz.Quiz(bot, spotify, bot.sessions, presetsJP, presetsEN))
bot.add_cog(search.Search(spotify))



descriptions = ["""まずは任意のボイスチャンネルに接続してください。
参加するメンバーがそろっていることを確認したら、`iq:start`を送信します。
その後はBotの指示に従って操作してください。""",
                """準備の後、ボイスチャンネルに曲が流れます。
曲名が分かったら、🔔のリアクションを押してください。
すると選択肢が表示されるので、正解だと思う曲名に対応する数字のリアクションを押してください。""",
                """正解すれば、回答者にポイントが入り、そのラウンドは終了です。
不正解だった場合は、ポイントは入らず、そのラウンドが続きます。
また、間違えてしまうとそのラウンド中は回答権がなくなります。
全員が間違えるとそのラウンドは終了です。""",
                """ここまでの流れを指定したラウンド数繰り返します。
そして終了時に最も得点の高かったメンバーが勝利です!""",
                """途中参加する場合は、同じボイスチャンネルに接続し、👋のリアクションを押してください。
次のラウンドから回答することが出来ます。""",
                """イントロクイズから退出する場合は、ボイスチャンネルから切断すると自動で退出されます。
ただし、スコアは保持されず、最終結果に表示されなくなるので注意して下さい。""",
                """タイムアタックモードでは、回答時の曲の残り再生時間に応じてスコアが増減します。
素早い回答で大量得点を狙いましょう!"""]


@bot.event
async def on_ready():
    print("準備完了")
    await bot.change_presence(activity=discord.Game(name=f"iq:help 導入サーバー数{len(bot.guilds)}"))

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="ヘルプ", description="当Botの使い方", color=0x69fa69)
    embed.add_field(name="help", value="このヘルプを表示します。")
    embed.add_field(name="start", value="イントロクイズを開始します。")
    embed.add_field(name="search [キーワード]", value="アーティスト名、SpotifyのアルバムURL、SpotifyのプレイリストURLを指定して、楽曲を検索します。", inline=False)
    embed.add_field(name="leave", value="イントロクイズを強制終了し、ボイスチャンネルから切断します。\n実行には管理者権限が必要です。", inline=False)
    embed.add_field(name="howtoplay", value="このBotの遊び方を確認します。")
    embed.add_field(name="ping", value="APIの遅延を確認します。")
    embed.add_field(name="必要な権限について", value="このBotで遊ぶには、Botに以下の権限が必要です:\n"
                    "```・テキストチャンネルの閲覧&ボイスチャンネルの表示\n"
                    "・メッセージを送信\n"
                    "・メッセージの管理\n"
                    "・メッセージ履歴を読む\n"
                    "・リアクションの追加\n"
                    "・接続\n"
                    "・発言```", inline=False)
    embed.add_field(
        name="既知の問題", value="""Botに使用しているプログラムの仕様上、表示されるアーティスト名が全て英語表記になっています。""", inline=False)
    embed.add_field(name="Botをサーバーに導入する",
                    value="[こちら](https://discord.com/api/oauth2/authorize?client_id=691547356100952096&permissions=3222592&scope=bot)からどうぞ!")
    embed.add_field(
        name="お問い合わせ", value="バグや不具合を見つけた場合は[サポートサーバー](https://discord.gg/6bAEhQr)へお問い合わせください。")
    await ctx.send(embed=embed)


@bot.command()
async def ping(ctx):
    start = time.time()
    msg = await ctx.send("しばらくお待ちください")
    ping = time.time() - start
    await msg.edit(content="結果: **" + str(round(ping * 1000)) + "ms**")


@bot.command()
async def howtoplay(ctx):
    global descriptions
    page = 0
    embed = discord.Embed(title="イントロクイズBotの遊び方: ページ" +
                          str(page + 1), description=descriptions[page])
    embed.set_footer(text="120秒間操作がされなかった場合、ページは変更できなくなります。")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("⬅️")
    await msg.add_reaction("➡️")
    while(True):
        try:
            reaction, user = await bot.wait_for("reaction_add", check=lambda r, u: str(r.emoji) in ["➡️", "⬅️"] and r.message.channel == ctx.channel and u == ctx.author, timeout=120)
        except:
            return
        else:
            await msg.remove_reaction(reaction.emoji, user)
            if str(reaction.emoji) == "➡️":
                if page == len(descriptions) - 1:
                    page = 0
                else:
                    page += 1
            if str(reaction.emoji) == "⬅️":
                if page == 0:
                    page = len(descriptions) - 1
                else:
                    page -= 1
            embed = discord.Embed(
                title="イントロクイズBotの遊び方: ページ" + str(page + 1), description=descriptions[page])
            embed.set_footer(text="120秒間操作がされなかった場合、ページは変更できなくなります。")
            await msg.edit(embed=embed)

@commands.has_permissions(administrator=True)
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        if ctx.guild.id in bot.sessions:
            del bot.sessions[ctx.guild.id]
            bot.game_tasks[ctx.guild.id].cancel()
            del bot.game_tasks[ctx.guild.id]
        await ctx.send(f"**{ctx.voice_client.channel.name}**から切断しました。")
    else:
        await ctx.send("このサーバーでボイスチャンネルに接続していません!")


@bot.command()
async def end(ctx):
    if ctx.author.id not in [431805523969441803]:
        return
    await ctx.send("終了します…👋")
    for i in bot.sessions :
        bot.game_tasks[i].cancel()
        channel = bot.get_channel(bot.sessions[i]["channel"])
        await channel.send("オーナーがBotを停止させます。再起動までしばらくお待ち下さい…")
    await bot.close()


@bot.command()
async def showses(ctx):
    pprint.pprint(bot.sessions)

@bot.event
async def on_guild_join(guild):
    channel = bot.get_channel(719164706832515132)
    await channel.send(f"`{guild.name}`に参加しました。\nサーバーメンバー数・`{guild.member_count}`")
    await bot.change_presence(activity=discord.Game(name=f"iq:help 導入サーバー数{len(bot.guilds)}"))


@bot.event
async def on_guild_remove(guild):
    channel = bot.get_channel(719164706832515132)
    await channel.send(f"`{guild.name}`から退出しました。")
    await bot.change_presence(activity=discord.Game(name=f"iq:help 導入サーバー数{len(bot.guilds)}"))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("コマンドに必要な引数が不足しています!")
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("このコマンドの実行にはあなたが管理者権限を持っている必要があります!")
        return
    elif isinstance(error, asyncio.CancelledError):
        pass
    if ctx.command.name == "start":
        await ctx.send("イントロクイズ中に何らかのエラーが発生しました。\nイントロクイズは中断されました。")
        if bot.sessions.get_session(ctx.guild.id):
            bot.sessions.remove_session(ctx.guild.id)
            if ctx.guild.voice_client:
                await ctx.guild.voice_client.disconnect()
    ch = bot.get_channel(733972172250415104)
    embed = discord.Embed(
        title="例外発生", description=f"{ctx.command.name}で例外が発生しました")
    embed.add_field(name="内容", value=f"```{error}```")
    traceback.print_exception(type(error), error, error.__traceback__)
    await ch.send(embed=embed)

bot.run(token)
