# -*- coding: utf-8 -*- #
import discord
import asyncio
import requests
import json
from discord.ext import commands
import time
import ffmpeg
from random import randint
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import traceback
import pprint
import re
import gettoken
intents = discord.Intents.none()
intents.members = True
intents.voice_states = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True

bot = commands.Bot(command_prefix="it:", intents=intents)
bot.remove_command("help")
bot.load_extension("jishaku")
bot.voice = {}
client_id = "8abef6fcb95849eca0d34fd019f497d3"
client_secret = "cb3692bc9f59480aa1f69cdd7bec4e93"
client_credentials_manager = spotipy.oauth2.SpotifyClientCredentials(client_id, client_secret)
spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

pannel_emojies = ["🔔", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "➡", "⬇️", "👋"]

bot.sessions = {}
game_tasks = {}

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
    embed.add_field(name="コマンド一覧", value="> **help**\n"
    "このヘルプを表示します。\n"
    "> **start** [任意で引数]\n"
    "イントロクイズを開始します。\n"
    "引数に`quick`を渡すと、5ラウンドをすぐにプレイ出来ます。\n"
    "> **tracks**\n"
    "イントロクイズで使用できる曲を確認できます。\n"
    "アーティスト名の検索で表示される件数は最大で30件です。\n"
    "> **artist [アーティスト名]**\n"
    "アーティスト名を指定して、使用できる楽曲を表示します。\n"
    "日本語で検索可能です。\n"
    "> **playlist** [URL]\n"
    "Spotifyのプレイリストから使用できる楽曲の一覧を取得します。\n"
    "> **album** [URL]\n"
    "Spotifyのアルバムから使用できる楽曲の一覧を取得します。\n"
    "> **leave**\n"
    "強制的にイントロクイズを終了し、ボイスチャンネルから切断します。\n"
    "管理者権限が必要です。\n"
    "> **howtoplay**\n"
    "このBotの遊び方を確認します。\n"
    "> **ranking**\n"
    "チャレンジモードのランキングを表示します。\n"
    "> **ping**\n"
    "APIの遅延を確認します。", inline=False)
    embed.add_field(name="必要な権限について", value="このBotで遊ぶには、Botに以下の権限が必要です:\n"
    "```・テキストチャンネルの閲覧&ボイスチャンネルの表示・メッセージを送信\n"
    "・メッセージの管理・メッセージ履歴を読む・リアクションの追加\n"
    "・接続・発言```", inline=False)
    embed.add_field(name="既知の問題", value="""Botに使用しているプログラムの仕様上、表示されるアーティスト名が全て英語表記になっています。""", inline=False)
    embed.add_field(name="Botをサーバーに導入する",value="[こちら](https://discord.com/api/oauth2/authorize?client_id=691547356100952096&permissions=3222592&scope=bot)からどうぞ!")
    embed.add_field(name="お問い合わせ",value="[サポートサーバー](https://discord.gg/6bAEhQr)へお問い合わせください。")
    await ctx.send(embed=embed)

@bot.command()
async def start(ctx, arg:str=""):
    global spotify, pannel_emojies, game_tasks
    game_tasks[ctx.guild.id] = asyncio.current_task()
    botasmember = await ctx.guild.fetch_member(bot.user.id)
    bot_perms = ctx.channel.permissions_for(botasmember)
    missing_perms = []
    if not bot_perms.view_channel:
        missing_perms.append("テキストチャンネルの閲覧&ボイスチャンネルの表示")
    if not bot_perms.send_messages:
        missing_perms.append("メッセージを送信")
    if not bot_perms.manage_messages:
        missing_perms.append("メッセージの管理")
    if not bot_perms.read_message_history:
        missing_perms.append("メッセージ履歴を読む")
    if not bot_perms.add_reactions:
        missing_perms.append("リアクションの追加")
    if missing_perms:
        await ctx.send("以下の権限がBotにありません!\n権限の設定を確認して再度実行してください。" + "\n".join(missing_perms))
        return

    if ctx.guild.id in list(bot.sessions.keys()):
        await ctx.send("このサーバで既にイントロクイズが開始されています!")
        return

    if not ctx.author.voice:
        await ctx.send("あなたがボイスチャンネルに接続していません!\nイントロクイズを開始するボイスチャンネルに接続した状態で再度実行してください。")
        return
    
    class DropdownView(discord.ui.View):
        def __init__(self, arg):
            super().__init__(timeout=30)
            self.add_item(arg)

    class confirmView(discord.ui.view):
        def __init__(self):
            super().__init__(timeout=30)
        @discord.ui.button(label="決定", emoji="✅", style=discord.ButtonStyle.green)
        async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.view.value = "confirmed"
        @discord.ui.button(label="再検索", emoji="🔎", style=discord.ButtonStyle.gray)
        async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.view.value = "redo"
        @discord.ui.button(label="準備を中断", emoji="❌", style=discord.ButtonStyle.red)
        async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.view.value = "end"

    class cancelView(discord.ui.view):
        def __init__(self):
            super().__init__(timeout=30)
        @discord.ui.button(label="準備を中断", emoji="❌", style=discord.ButtonStyle.red)
        async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.view.value = "end"

    class PlayModeSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="通常モード", description="正答するたびに1ポイント獲得するモードです。", emoji="🔔", value="normal"),
                discord.SelectOption(label="タイムアタックモード", description="正答の速さで獲得ポイントが変動するモードです。", emoji="🕒", value="timeattack"),
                discord.SelectOption(label="チャレンジモード", description="一人専用のタイムアタックモードです。", emoji="🎖️", value="challenge"),
                discord.SelectOption(label="終了", description="イントロクイズボットの準備を中断します。", emoji="❌" , value="end")
            ]
            super().__init__(placeholder='モードを選択', min_values=1, max_values=1, options=options)
        async def callback(self, interaction: discord.Interaction):
            
            self.view.gamemode = self.values[0]
            self.view.stop()
        async def on_timeout(self):
            self.view.gamemode = None

    class searchModeSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="アーティスト名で検索", description="アーティスト名で楽曲検索を行います。", value="artist"),
                discord.SelectOption(label="アルバム名で検索", description="アルバム名で楽曲検索を行います。", value="album"),
                discord.SelectOption(label="プレイリスト名で検索", description="プレイリスト名で楽曲検索を行います。", value="playlist"),
                discord.SelectOption(label="日本の人気曲を使用", description="検索を行わず、日本で人気の曲でプレイします。", value="noSearch"),
                discord.SelectOption(label="終了", description="イントロクイズボットの準備を中断します。", emoji="❌", value="end")
            ]
            super().__init__(placeholder='検索対象を選択', min_values=1, max_values=1, options=options)
        async def callback(self, interaction: discord.Interaction):
            self.view.searchMode = self.values[0]
            self.view.stop()
        async def on_timeout(self):
            self.view.searchMode = None

    #ゲームモード選択
    view = DropdownView(PlayModeSelect())
    msg = await ctx.send("イントロクイズを準備します！\n"
                    "以下のメニューからモードを選択してください。", view=view)
    await view.wait()
    gamemode = view.gamemode

    #楽曲検索
    if gamemode in ["normal", "timeattack"]:
        view = DropdownView(searchModeSelect())
        await msg.edit("使用楽曲を選択します！\n"
                       "以下のメニューから検索対象を選択してください。\n"
                       "(検索にはSpotifyのApiを使用します)", view=view)
        await view.wait()
    elif gamemode == "challenge":
        pass
    elif gamemode == "end":
        await msg.edit("イントロクイズの準備を中断しました。",view=None)
        return
    else:
        await msg.edit("一定時間操作が行われなかったため終了しました。",view=None)
        return

    if gamemode in ["normal", "timeattack"]:
        if view.searchMode == "artist":
            confview = confirmView()
            cancview = cancelView()
            await msg.edit("アーティストを検索します。\n"
            "検索したいアーティスト名をこのチャンネルに送信してください。", view=cancview)
            while(True):
                try:
                    msg = await bot.wait_for("message", check=lambda m: m.channel == ctx.channel and m.author == ctx.author, timeout=30)
                except asyncio.TimeoutError:
                    await ctx.send("30秒間操作されなかったためイントロクイズの準備を中断しました。")
                    return
                else:
                    await msg.delete()
                results = spotify.search(q=f"artist:{msg.content}", type="artist", limit=1, market="JP")
                if len(results["artists"]["items"]) == 0:
                    await ctx.send("指定したアーティストが見つかりませんでした。\n"
                    "キーワードを変えて再度送信してください。", view=cancview)
                    continue
                artist = results["artists"]["items"][0]["name"]
                tracks = spotify.search(q="artist: " + artist, limit=30,type="track",market="JP")
                tracklist = []
                for i in tracks["tracks"]["items"]:
                    if i["preview_url"]:
                        tracklist.append({"name": i["name"], "artist": i["artists"][0]["name"],
                        "url": i["preview_url"], "image": i["album"]["images"][0]["url"],
                        "albumname": i["album"]["name"], "albumurl": i["album"]["external_urls"]["spotify"]})
                if len(tracklist) > 3:
                    await ctx.send(f"**{artist}**が見つかりました!取得した曲数は`{str(len(tracklist))}`です。\n"
                    "これらの楽曲を使用しますか?", view=confview)
                    await view.wait()
                    if view.value == "confirmed":
                        break
                    elif view.value == "redo":
                        continue

                else:
                    await ctx.send(f"**{artist}**が見つかりましたが、使用可能な曲が不十分です。\n"
                    "キーワードを変えて再度送信し検索してください。", view=cancelView)







        return

        try:
            bot.voice[ctx.guild.id] = await ctx.author.voice.channel.connect(timeout=3)
        except:
            await ctx.send("ボイスチャンネルに参加できませんでした。以下を確認してください:\n・「接続」権限がBotにあるか\n・Botにボイスチャンネルが見えているか")
            return


        while(True):
            try:
                msg = await bot.wait_for("message", check=lambda m: m.channel == ctx.channel and m.author == ctx.author, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send("60秒間操作されなかったため終了しました。")
                await bot.voice[ctx.guild.id].disconnect()
                return
            else:
                if msg.content in ["1", "2", "3"]:
                    gamemode = msg.content
                    break
                else:
                    await ctx.send("終了しました。")
                    await bot.voice[ctx.guild.id].disconnect()
                    return
        if gamemode in ["1", "2"]:
            await ctx.send("アーティストを検索する場合は`1`、\n"
            "プレイリストを検索する場合は`2`、\n"
            "アルバムを検索する場合は`3`を送信してください。\n"
            "日本で人気の曲を使う場合は`0`と送信してください。\n"
            "終了する場合はそれ以外を送信してください。")
            try:
                msg = await bot.wait_for("message", check=lambda m: m.channel == ctx.channel and m.author == ctx.author, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send("60秒間操作されなかったため終了しました。")
                return
            if msg.content in ["1", "2", "3", "0"]:
                search_mode = msg.content
            else:
                await ctx.send("終了しました。")
                await bot.voice[ctx.guild.id].disconnect()
                return     
            is_searched = False
            if search_mode == "1": #アーティスト検索
                pass
            elif search_mode == "2": #プレイリスト検索
                await ctx.send("Spotifyのプレイリストから楽曲を取得します。プレイリストのURLを送信してください。\n"
                "キャンセルする場合は`cancel`と送信してください。\n"
                "終了する場合は`end`と送信してください。")
                while(True):
                    try:
                        msg = await bot.wait_for("message", check=lambda m: m.channel == ctx.channel and m.author == ctx.author, timeout=60)
                    except asyncio.TimeoutError:
                        await ctx.send("60秒間操作されなかったため終了しました。")
                        await bot.voice[ctx.guild.id].disconnect()
                        return
                    
                    if is_searched and msg.content == "yes":
                        break
                    if msg.content == "cancel":
                        search_mode = "0"
                        break
                    elif msg.content == "end":
                        await ctx.send("終了しました。")
                        await bot.voice[ctx.guild.id].disconnect()
                        return
                    m = re.match(r"https://open.spotify.com/playlist/.{22}",msg.content)
                    if not m:
                        await ctx.send("URLが正しくありません!再送信してください。\n"
                        "キャンセルする場合は`cancel`と送信してください。\n"
                        "終了する場合は`end`を送信してください。")
                        is_searched = False
                        continue
                    playlist_id = m.group().split("https://open.spotify.com/playlist/")[1]
                    playlist_info = spotify.playlist(playlist_id, market="JP")
                    playlist_name = playlist_info["name"]
                    playlist_owner = playlist_info["owner"]
                    tracklist = []
                    for i in playlist_info["tracks"]["items"]:
                        if i["track"]["preview_url"]:
                            tracklist.append({"name": i["track"]["name"], "artist": i["track"]["artists"][0]["name"],
                            "url": i["track"]["preview_url"], "image": i["track"]["album"]["images"][0]["url"],
                            "albumname": i["track"]["album"]["name"], "albumurl": i["track"]["album"]["external_urls"]["spotify"]})
                    if len(tracklist) > 3:
                        await ctx.send(f"{playlist_owner['display_name']}さんの**{playlist_name}**が見つかりました!\n"
                        f"使用できる楽曲数は{len(tracklist)}です。\n"
                        "このアルバムの楽曲を使用する場合は`yes`と送信してください。\n"
                        "キャンセルする場合は`cancel`と送信してください。\n"
                        "終了する場合は`end`を送信してください。"
                        "それ以外を送信すると再度検索できます。")
                        is_searched = True
                    else:
                        await ctx.send(f"{playlist_owner['display_name']}さんの**{playlist_name}**が見つかりましたが、使用できる楽曲が不十分です。\n"
                        "他のURLを入力してください。\n"
                        "キャンセルする場合は`cancel`と送信してください。\n"
                        "終了する場合は`end`を送信してください。")
                        is_searched = False

            elif search_mode == "3": #アルバム検索
                await ctx.send("Spotifyのアルバムから楽曲を取得します。アルバムのURLを送信してください。\n"
                "キャンセルする場合は`cancel`と送信してください。\n"
                "終了する場合は`end`を送信してください。")
                while(True):
                    try:
                        msg = await bot.wait_for("message", check=lambda m: m.channel == ctx.channel and m.author == ctx.author, timeout=60)
                    except asyncio.TimeoutError:
                        await ctx.send("60秒間操作されなかったため終了しました。")
                        await bot.voice[ctx.guild.id].disconnect()
                        return
                    if is_searched and msg.content == "yes":
                        break
                    if msg.content == "cancel":
                        search_mode = "0"
                        break
                    elif msg.content == "end":
                        await ctx.send("終了しました。")
                        await bot.voice[ctx.guild.id].disconnect()
                        return
                    m = re.match(r"https://open.spotify.com/album/.{22}",msg.content)
                    if not m:
                        await ctx.send("URLが正しくありません!再送信してください。\n"
                        "キャンセルする場合は`cancel`と送信してください。")
                        is_searched = False
                        continue
                    album_id = m.group().split("https://open.spotify.com/album/")[1]
                    album_info = spotify.album(album_id)
                    album_name = album_info["name"]
                    album_artist = album_info["artists"][0]["name"]
                    tracklist = []
                    for i in album_info["tracks"]["items"]:
                        if i["preview_url"]:
                            tracklist.append({"name": i["name"], "artist": i["artists"][0]["name"],
                            "url": i["preview_url"], "image": album_info["images"][0]["url"],
                            "albumname": album_name, "albumurl": msg.content})
                    if len(tracklist) > 3:
                        await ctx.send(f"{album_artist}の**{album_name}**が見つかりました!\n"
                        f"使用できる楽曲数は{len(tracklist)}です。\n"
                        "このアルバムの楽曲を使用する場合は`yes`と送信してください。\n"
                        "キャンセルする場合は`cancel`と送信してください。\n"
                        "終了する場合は`end`を送信してください。\n"
                        "それ以外を送信すると再度検索できます。")
                        is_searched = True
                    else:
                        await ctx.send(f"{album_artist}の**{album_name}**が見つかりましたが、使用できる楽曲が不十分です。\n"
                        "他のURLを入力してください。\n"
                        "キャンセルする場合は`cancel`と送信してください。\n"
                        "終了する場合は`end`を送信してください。")
                        is_searched = False

            await ctx.send("ラウンド数を1~15で指定してください。\n終了する場合は60秒待つか0を指定してください。")
            while(True):    
                try:
                    msg = await bot.wait_for("message", check=lambda m: m.channel == ctx.channel, timeout=60)
                    roundcount = int(msg.content)
                except asyncio.TimeoutError:
                    await ctx.send("60秒間操作が無かったため終了しました。")
                    await bot.voice[ctx.guild.id].disconnect()
                    return
                except:
                    await ctx.send("入力方法が正しくありません!")
                else:
                    if roundcount == 0:
                        await ctx.send("終了されました。")
                        await bot.voice[ctx.guild.id].disconnect()
                        return
                    elif roundcount > 15 and roundcount < 1:
                        await ctx.send("設定できないラウンド数です!")
                    else:
                        break 
        else:
            await ctx.send("チャレンジモードは、日本で人気の10曲の問題をタイムアタックモードで行います。\n"
            "参加できるのは現在Botを操作している一人のみです。\n"
            "良い結果を残せば、ランキングに登録されます。より上位を目指しましょう!\n"
            "始める場合は`start`を送信してください。キャンセルする場合はそれ以外を送信するか60秒待ってください。")
            try:
                msg = await bot.wait_for("message", check=lambda m: m.channel == ctx.channel and m.author == ctx.author, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send("60秒間操作されなかったため終了しました。")
                await bot.voice[ctx.guild.id].disconnect()
                return
            else:
                if msg.content == "start":
                    search_mode = "0"
                    roundcount = 10
                    gamemode = "3"
                else:
                    await ctx.send("キャンセルされました。")
                    return
        
    else:
        search_mode = "0"
        roundcount = 5
        gamemode = "1"
    if search_mode == "0":
        tracklist = []
        tracks = spotify.playlist("37i9dQZEVXbKXQ4mDTEBXq", market="JP")
        result = tracks["tracks"]["items"]
        for i in result:
            if i["track"]["preview_url"]:
                tracklist.append({"name": i["track"]["name"], "artist": i["track"]["artists"][0]["name"],
                "url": i["track"]["preview_url"], "image": i["track"]["album"]["images"][0]["url"],
                "albumname": i["track"]["album"]["name"], "albumurl": i["track"]["album"]["external_urls"]["spotify"]})

    bot.sessions[ctx.guild.id] = {"players":{}, "wait": [], "channel": ctx.channel.id, "gamemode": gamemode}
    if gamemode != "3":
        for i in bot.voice[ctx.guild.id].channel.members:
            if i != bot.user or not i.bot:
                bot.sessions[ctx.guild.id]["players"][i] = {}
                bot.sessions[ctx.guild.id]["players"][i]["score"] = 0
                bot.sessions[ctx.guild.id]["players"][i]["miss"] = False
    else:
        bot.sessions[ctx.guild.id]["players"][ctx.author] = {}
        bot.sessions[ctx.guild.id]["players"][ctx.author]["score"] = 0
        bot.sessions[ctx.guild.id]["players"][ctx.author]["miss"] = False
    setting = discord.Embed(title="準備中･･･",description="しばらくお待ちください")
    msg = await ctx.send(embed=setting)

    for i in pannel_emojies:
        if i == "👋" and gamemode == "3":
            continue
        await msg.add_reaction(i)

    question = discord.Embed(title="イントロクイズ", description="流れているこの曲は何でしょうか?\n**分かったら🔔を押して回答!!!**", color=0x00a6ff)
    if gamemode != "3":
        question.set_footer(text="Powered by Spotify\n途中参加する場合は👋をクリック!")
    else:
        question.set_footer(text="Powered by Spotify")
    question.add_field(name="",value="")

    def reset_miss():
        for j in bot.sessions[ctx.guild.id]["players"]:
            bot.sessions[ctx.guild.id]["players"][j]["miss"] = False
        for j in bot.sessions[ctx.guild.id]["wait"]:
            bot.sessions[ctx.guild.id]["players"][j] = {}
            bot.sessions[ctx.guild.id]["players"][j]["score"] = 0
            bot.sessions[ctx.guild.id]["players"][j]["miss"] = False
            del bot.sessions[ctx.guild.id]["wait"][(bot.sessions[ctx.guild.id]["wait"].index(j))]
    async def roundend(text):
        nonlocal msg, answer, artworkurl, artistname, album_name, album_url
        embed = discord.Embed(title="イントロクイズ",description="答え:", color=0xffcc00)
        embed.add_field(name="曲名", value=answer)
        embed.add_field(name="アーティスト名", value=artistname)
        embed.add_field(name="アルバム", value=f"[{album_name}]({album_url})")
        if artworkurl:
            embed.set_thumbnail(url=artworkurl)       
        await msg.edit(content=f"{text}\n➡を押すか20秒経過で次に進みます。パネルを下げる場合は⬇️を押してください。",embed=embed)
        try:
            reaction, user = await bot.wait_for("reaction_add", check=lambda r, user: str(r.emoji) in ["➡", "⬇️"] and r.message.id == msg.id ,timeout=20)
        except asyncio.TimeoutError:
            reset_miss()
        else:
            if str(reaction.emoji) == "⬇️":
                await msg.delete()
                msg = await ctx.send(content="パネルを下に下げました。", embed=setting)
                for i in pannel_emojies:
                    await msg.add_reaction(i)
                reset_miss()
            else:
                await msg.remove_reaction(reaction.emoji, user)
                reset_miss()

    def everyone_missed():
        for j in bot.sessions[ctx.guild.id]["players"]:
            if bot.sessions[ctx.guild.id]["players"][j]["miss"]:
                pass
            else:
                return False
        return True
    def reset_field():
        ans_perms = ""
        for j in list(bot.sessions[ctx.guild.id]["players"].keys()):
            if bot.sessions[ctx.guild.id]["players"][j]["miss"]:
                ans_perms += j.mention + ": ❌\n"
            else:
                ans_perms += j.mention + ": ⭕\n"
        return ans_perms

    for i in range(roundcount):
        selector = randint(0, len(tracklist) - 1)
        answer = tracklist[selector]["name"]
        artistname = tracklist[selector]["artist"]
        musicurl = tracklist[selector]["url"]
        album_name = tracklist[selector]["albumname"]
        album_url = tracklist[selector]["albumurl"]
        if tracklist[selector]["image"] != "none":
            artworkurl = tracklist[selector]["image"]

        choices = [answer]
        while(len(choices) < 4):
            wrongsong = tracklist[randint(0, len(tracklist) - 1)]["name"]
            while(wrongsong in choices):
                wrongsong = tracklist[randint(0, len(tracklist) - 1)]["name"]
            choices.insert(randint(0, len(choices)), wrongsong)

        answerpos = choices.index(answer)
        embedcontent = "1️⃣:" + choices[0] + "\n"
        embedcontent += "2️⃣:" + choices[1] + "\n"
        embedcontent += "3️⃣:" + choices[2] + "\n"
        embedcontent += "4️⃣:" + choices[3]

        r = requests.get(musicurl, stream=True)
        with open("result.m4a", mode="wb") as musicfile:
            musicfile.write(r.content)
        question.set_field_at(index=0,name="回答権",value=reset_field())
        
        await msg.edit(content="**ラウンド" + str(i + 1) + "**: 制限時間は30秒です。", embed=question)
        menu = discord.Embed(title="イントロクイズ", description=embedcontent, color=0xffcc00)
        if gamemode != "3":
            menu.set_footer(text="Powered by Spotify\n途中参加する場合は同じボイスチャンネルに接続して👋をクリック!")
        else:
            menu.set_footer(text="Powered by Spotify")
        bot.voice[ctx.guild.id].play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(source="result.m4a"), volume=0.5))
        times_remain = 30
        while(True):
            if everyone_missed():
                bot.voice[ctx.guild.id].stop()
                await roundend("**全員の回答権が無くなりました。**")
                break 
            bot.voice[ctx.guild.id].resume()
            start_time = time.time()
            try:
                reaction, respondent = await bot.wait_for("reaction_add",check=lambda r, user: str(r.emoji) == "🔔" and user in bot.voice[ctx.guild.id].channel.members and (not bot.sessions[ctx.guild.id]["players"][user]["miss"]) and r.message.id == msg.id and user in bot.sessions[ctx.guild.id]["players"], timeout=times_remain)
            except asyncio.TimeoutError:
                await roundend("**時間切れです･･･**")
                break

            await msg.remove_reaction(reaction.emoji, respondent)
            times_remain -= time.time() - start_time
            bot.voice[ctx.guild.id].pause()
            await msg.edit(content=respondent.mention + "、あなたが回答者です!**\n5秒以内に答えを選択してください!**",embed=menu)
            try:
                reaction, user = await bot.wait_for("reaction_add",check=lambda r, user: str(r.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣"] and user == respondent and r.message.id == msg.id ,timeout=5)
            except asyncio.TimeoutError:
                bot.sessions[ctx.guild.id]["players"][respondent]["miss"] = True
                question.set_field_at(index=0,name="回答権",value=reset_field())
                if everyone_missed():
                    await roundend(f"{respondent.mention}、**時間切れです･･･**\n全員の回答権が無くなりました。")
                    break
                else:
                    await msg.edit(content= f"{respondent.mention}、時間切れです･･･\n**このラウンド中は回答できません!**", embed=question)
            
            else:
                await msg.remove_reaction(reaction.emoji, user)
                if (reaction.emoji == "1️⃣" and answerpos == 0) or (reaction.emoji == "2️⃣" and answerpos == 1) or (reaction.emoji == "3️⃣" and answerpos == 2) or (reaction.emoji == "4️⃣" and answerpos == 3):
                    bot.voice[ctx.guild.id].stop()
                    if gamemode == "1" :
                        bot.sessions[ctx.guild.id]["players"][respondent]["score"] += 1
                        await roundend(f"{respondent.mention}、**正解です!**`1`ポイントを取得しました。")
                    else:
                        bot.sessions[ctx.guild.id]["players"][respondent]["score"] += round(times_remain + 1)
                        await roundend(f"{respondent.mention}、**正解です!**`{round(times_remain + 1)}`ポイントを取得しました。")
                    break
                else:
                    bot.sessions[ctx.guild.id]["players"][respondent]["miss"] = True
                    question.set_field_at(index=0,name="回答権",value=reset_field())
                    if everyone_missed():
                        await roundend(f"{respondent.mention}、不正解です･･･\n**全員の回答権が無くなりました。**")
                        break
                    else:
                        await msg.edit(content=respondent.mention + "、不正解です･･･\n**このラウンド中は回答できません!**", embed=question)
    if gamemode != "3":      
        sortedlist = sorted(list(bot.sessions[ctx.guild.id]["players"].items()), key=lambda x:x[1]["score"], reverse=True)
        scoreboard = ""
        rank = 1
        tie_count = 0
        score_before = sortedlist[0][1]["score"]
        for i in sortedlist:
            if score_before == i[1]["score"]:
                tie_count += 1
            else:
                rank += tie_count
                tie_count = 0
                score_before =  i[1]["score"]
            score_before = i[1]["score"]
            scoreboard +=  str(rank) + "位: **" + i[0].mention + "** " + str(i[1]["score"]) + " pts\n"
        embed = discord.Embed(title="結果", description=scoreboard, color=0x00ff59)
        await msg.edit(content="**ゲーム終了!**お疲れ様でした!結果は以下の通りです。", embed=embed)
    else:
        score = bot.sessions[ctx.guild.id]["players"][ctx.author]["score"]
        rankinglist = await bot.loop.run_in_executor(None, loadjson)
        rankinglist = sorted(rankinglist, key=lambda x: x[1], reverse=True)
        pos = 0
        for i in rankinglist:
            if i[1] >= score:
                pos += 1
            else:
                
                break
        rankinglist.insert(pos, [f"{ctx.author.name}#{ctx.author.discriminator}", score])
        rankinglist = rankinglist[0:20] 
        embedcontent = []
        index = 0
        for i in rankinglist:
            index += 1
            embedcontent.append(f"{index}位: {i[0]} {i[1]}pts")
        if pos <= 20:
            embed = discord.Embed(title="結果", description=f"あなたの総合スコアは**{score}**点です。\n"
            "おめでとうございます！ランキングに登録されました。\n"
            f"あなたの順位は**{pos + 1}位**です!\n" + "\n".join(embedcontent))
        else:
            embed = discord.Embed(title="結果", description=f"あなたの総合スコアは**{score}**点です。\n"
            "残念･･･ランキングに登録されませんでした。\n" + "\n".join(embedcontent))
        await msg.edit(content="**全てのラウンドが終了しました。**お疲れ様でした!結果は以下の通りです。\n", embed=embed)
        await bot.loop.run_in_executor(None, savejson, rankinglist)
    await bot.voice[ctx.guild.id].disconnect()
    del bot.sessions[ctx.guild.id]
    del game_tasks[ctx.guild.id]

def loadjson():
    with open("ranking.json", encoding="UTF-8") as f:
        jsonfile = json.load(f)
    return jsonfile

def savejson(li):
    with open("ranking.json", "w", encoding="UTF-8") as f:
        json.dump(li, f, indent=4)

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
    embed = discord.Embed(title="イントロクイズBotの遊び方: ページ" + str(page + 1), description=descriptions[page])
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
            if str(reaction.emoji) ==  "➡️":
                if page == len(descriptions) - 1:
                    page = 0
                else:
                    page += 1
            if str(reaction.emoji) ==  "⬅️":
                if page == 0:
                    page = len(descriptions) - 1
                else:
                    page -= 1
            embed = discord.Embed(title="イントロクイズBotの遊び方: ページ" + str(page + 1), description=descriptions[page])
            embed.set_footer(text="120秒間操作がされなかった場合、ページは変更できなくなります。")
            await msg.edit(embed=embed)
                
@bot.command()
async def tracks(ctx):
    global spotify
    num = 0
    tracks = spotify.playlist("37i9dQZEVXbKXQ4mDTEBXq", market="JP")
    result = tracks["tracks"]["items"]
    tracklist = []
    for i in result:
        if i["track"]["preview_url"]:
            num += 1
            tracklist.append(f"{num}: {i['track']['name']} / {i['track']['artists'][0]['name']}")
    embed = discord.Embed(title="現在のトラックリスト: 日本で人気の曲", description="\n".join(tracklist))
    await ctx.send(embed=embed)

@bot.command()
async def artist(ctx, *,name):
    artist = spotify.search(q=f"artist:{name}", type="artist", limit=1, market="JP")
    if len(artist["artists"]["items"]) == 0:
        await ctx.send("指定したアーティストが見つかりませんでした。\nキーワードを変えて再度お試し下さい。")
        return
    tracks = spotify.search(q="artist: " + artist["artists"]["items"][0]["name"] ,limit=30,type="track",market="JP")
    result = tracks["tracks"]["items"]
    num = 0
    tracklist = []
    for i in result:
        if i["preview_url"]:
            num += 1
            tracklist.append(f"{num}: {i['name']}")
    if len(tracklist) > 0:
        embed = discord.Embed(title="現在のトラックリスト: " + artist["artists"]["items"][0]["name"], description="\n".join(tracklist))
    else:
        embed = discord.Embed(title="現在のトラックリスト: " + artist["artists"]["items"][0]["name"], description="使用できる楽曲はありませんでした。")
    await ctx.send(embed=embed)

@bot.command()
async def playlist(ctx, url):
    global spotify
    m = re.match(r"https://open.spotify.com/playlist/.{22}",url)
    if not m:
        await ctx.send("URLが正しくありません!")
        return
    playlist_id = m.group().split("https://open.spotify.com/playlist/")[1]
    try:
        results = playlist_info = spotify.playlist(playlist_id, market="JP")
    except spotipy.exceptions.SpotifyException:
        await ctx.send("プレイリストが見つかりませんでした。\nURLを変えて再度お試し下さい。")
        return
    num = 0
    tracklist = []
    for i in results["tracks"]["items"]:
        if i["track"]["preview_url"]:
            num += 1
            tracklist.append(f"{num}: {i['track']['name']} / {i['track']['artists'][0]['name']}")
    if len(tracklist) > 0:
        embed = discord.Embed(title=f"プレイリストの楽曲: {playlist_info['name']}(作成者:{playlist_info['owner']['display_name']})" , description="\n".join(tracklist))
    else:
        embed = discord.Embed(title=f"プレイリストの楽曲: {playlist_info['name']}(作成者:{playlist_info['owner']['display_name']})" , description="使用できる楽曲はありませんでした。")
    await ctx.send(embed=embed)

@bot.command()
async def album(ctx, url):
    global spotify
    m = re.match(r"https://open.spotify.com/album/.{22}",url)
    if not m:
        await ctx.send("URLが正しくありません!")
        return
    album_id = m.group().split("https://open.spotify.com/album/")[1]
    try:
        album_info = spotify.album(album_id)
    except spotipy.exceptions.SpotifyException:
        await ctx.send("アルバムが見つかりませんでした。\nURLを変えて再度お試し下さい。")
        return
    num = 0
    tracklist = []
    for i in album_info["tracks"]["items"]:
        if i["preview_url"]:
            num += 1
            tracklist.append(f"{num}: {i['name']} / {i['artists'][0]['name']}") 
    if len(tracklist) > 0:
        embed = discord.Embed(title=f"アルバムの楽曲: {album_info['artists'][0]['name']} / {album_info['name']}" , description="\n".join(tracklist))
    else:
        embed = discord.Embed(title=f"アルバムの楽曲: {album_info['artists'][0]['name']} / {album_info['name']}" , description="使用できる楽曲はありませんでした。")
    await ctx.send(embed=embed)

@commands.has_permissions(administrator=True)
@bot.command()
async def leave(ctx):
    global game_tasks
    if ctx.guild.id in bot.voice.keys():
        await bot.voice[ctx.guild.id].disconnect()
        if ctx.guild.id in bot.sessions:
            del bot.sessions[ctx.guild.id]
            game_tasks[ctx.guild.id].cancel()
            del game_tasks[ctx.guild.id]
        await ctx.send(f"**{bot.voice[ctx.guild.id].channel.name}**から切断しました。")
        del bot.voice[ctx.guild.id]
    else:
        await ctx.send("このサーバーでボイスチャンネルに接続していません!")

@bot.command()
async def ranking(ctx):
    rankinglist = await bot.loop.run_in_executor(None, loadjson)
    index = 0
    embedcontent = []
    for i in rankinglist:
        index += 1
        embedcontent.append(f"{index}位: {i[0]} {i[1]}pts")
    if not embedcontent:
        embedcontent.append("ランキングには何も登録されていません。")
    embed = discord.Embed(title="現在のランキング", description="\n".join(embedcontent))
    embed.add_field(name="ランキングの仕様について", value="記録は最大で20位まで登録され、それを下回った記録は消去されます。\n"
    "同じスコアになった場合は先に登録された記録が上位となります。")
    await ctx.send(embed=embed)

@bot.command()
async def end(ctx):
    global game_tasks
    if ctx.author.id not in [431805523969441803,462765491325501445]:#Poteto143のID, T-takuのID
        return
    await ctx.send("終了します…👋")
    for i in bot.sessions:
        game_tasks[i].cancel()
        channel = bot.get_channel(bot.sessions[i]["channel"])
        await channel.send("オーナーがBotを停止させます。再起動までしばらくお待ち下さい…")
    await bot.logout()

@bot.event
async def on_reaction_add(reaction, user):
    if reaction.message.guild:
        if reaction.message.guild.id in list(bot.sessions.keys()):
            if str(reaction.emoji) == "👋" and user != bot.user: 
                if user in bot.voice[reaction.message.guild.id].channel.members:
                    if not user in bot.sessions[reaction.message.guild.id]["players"] and bot.sessions[reaction.message.guild.id]["gamemode"] != 3:
                        await reaction.message.channel.send(user.mention + "さんが参加しました。次のラウンドから回答できます!")
                        bot.sessions[reaction.message.guild.id]["wait"].append(user)
                else:
                    await reaction.message.channel.send(user.mention + "、**あなたはイントロクイズが行われているボイスチャットに接続していません!**\nボイスチャットに接続してから参加してください。")
                    await reaction.message.remove_reaction(reaction.emoji, user)

@bot.event
async def on_voice_state_update(member, before, after):
    global game_tasks
    if before.channel:
        if before.channel.guild.id in list(bot.sessions.keys()):
            if (not member in before.channel.members) and member in bot.sessions[before.channel.guild.id]["players"]:
                channel = bot.get_channel(bot.sessions[before.channel.guild.id]["channel"])
                await channel.send(member.mention + "さんがイントロクイズから退出しました。")
                del bot.sessions[before.channel.guild.id]["players"][member]
                if not bot.sessions[before.channel.guild.id]["players"]:
                    del bot.sessions[before.channel.guild.id]
                    bot.voice[before.channel.guild.id].stop()
                    await bot.voice[before.channel.guild.id].disconnect()
                    del bot.voice[before.channel.guild.id]
                    game_tasks[before.channel.guild.id].cancel()
                    del game_tasks[before.channel.guild.id]
                    await channel.send("全ての参加者がボイスチャンネルから退出しました。\nイントロクイズは中止されました。")
            
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
        if ctx.guild.id in bot.sessions:
            del bot.sessions[ctx.guild.id]
            if ctx.guild.id in bot.voice.keys():
                bot.voice[ctx.guild.id].disconnect()
                del bot.voice[ctx.guild.id]
    ch = bot.get_channel(733972172250415104)
    embed = discord.Embed(title="例外発生", description=f"{ctx.command.name}で例外が発生しました")
    embed.add_field(name="内容", value=f"```{error}```")
    traceback.print_exception(type(error), error, error.__traceback__)
    await ch.send(embed=embed)
    
bot.run(gettoken.get(True))