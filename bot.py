# -*- coding: utf-8 -*- #
import aiohttp
import discord
import asyncio
import requests
from os import getenv
import sys
from discord.ext import commands
import time
import ffmpeg
from random import randint
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import traceback
import pprint
import re

args = sys.argv
if(len(args) == 2):
    if(args[1] == "Production"):
        print("本番環境で起動しています")
        token = getenv("INTRO_KEY")
    else:
        print("テスト環境で起動しています")
        token = getenv("INTRO_TEST_KEY")
else:
    print("テスト環境で起動しています")
    token = getenv("INTRO_TEST_KEY")

intents = discord.Intents.none()
intents.members = True
intents.voice_states = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True


bot = commands.Bot(command_prefix="iq:", intents=intents)
bot.remove_command("help")
bot.load_extension("jishaku")
client_credentials_manager = spotipy.oauth2.SpotifyClientCredentials(getenv("SPOTIFY_CLIENT_ID"), getenv("SPOTIFY_CLIENT_SECRET"))
spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

pannel_emojies = ["🔔", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "➡", "⬇️", "👋"]

bot.sessions = {}
bot.game_tasks = {}

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

async def disconnect(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        del(bot.sessions[ctx.guild.id])

@bot.after_invoke(disconnect)
@bot.command()
async def start(ctx, arg:str=""):
    global spotify, pannel_emojies
    bot.game_tasks[ctx.guild.id] = asyncio.current_task()
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
        await ctx.send("このサーバーで既にイントロクイズが開始されています!")
        return
    if not ctx.author.voice:
        await ctx.send("あなたがボイスチャンネルに接続していません!\nイントロクイズを開始するボイスチャンネルに接続した状態で再度実行してください。")
        return
    try:
        await ctx.author.voice.channel.connect(timeout=3)
    except:
        await ctx.send("ボイスチャンネルに参加できませんでした。以下を確認してください:\n・「接続」権限がBotにあるか\n・Botにボイスチャンネルが見えているか")
        return

    class DropdownView(discord.ui.View):
        def __init__(self, arg):
            super().__init__(timeout=30)
            self.add_item(arg)
            self.value = None
        async def on_timeout(self):
            self.value = "timeout"

    class confirmView(discord.ui.View):
        nonlocal ctx
        def __init__(self, arg: asyncio.Task, status):
            super().__init__(timeout=30)
            self.value = None
            self.tasktocancel = arg
            self.status = status
        async def interaction_check(self, interaction: discord.Interaction):
            return ctx.author.id == interaction.user.id
        @discord.ui.button(label="決定", emoji="✅", style=discord.ButtonStyle.green)
        async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.tasktocancel.cancel()
            self.value = "confirmed"
            
        @discord.ui.button(label="準備を中断", emoji="❌", style=discord.ButtonStyle.red)
        async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.tasktocancel.cancel()
            self.value = "end"

    class PlayModeSelect(discord.ui.Select):
        nonlocal ctx
        def __init__(self):
            options = [
                discord.SelectOption(label="通常モード", description="正答するたびに1ポイント獲得するモードです。", emoji="🔔", value="normal"),
                discord.SelectOption(label="タイムアタックモード", description="正答の速さで獲得ポイントが変動するモードです。", emoji="🕒", value="timeattack"),
                discord.SelectOption(label="クイックプレイ", description="すぐに通常モードを5ラウンドプレイします。", emoji= "➡️", value="quickPlay"),
                discord.SelectOption(label="終了", description="イントロクイズの準備を中断します。", emoji="❌" , value="end")
            ]
            super().__init__(placeholder='モードを選択', min_values=1, max_values=1, options=options)
        async def callback(self, interaction: discord.Interaction):
            if ctx.author.id == interaction.user.id:
                self.view.value = self.values[0]
                self.view.stop()
            else:
                await interaction.response.send_message(f"イントロクイズの設定はコマンド実行者のみ行えます!", ephemeral=True)

    class searchModeSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="アーティスト名で検索", description="アーティスト名で楽曲検索を行います。", value="artist"),
                discord.SelectOption(label="アルバムURLで検索", description="アルバムURLで楽曲検索を行います。", value="album"),
                discord.SelectOption(label="プレイリストURLで検索", description="SpotifyのプレイリストURLで楽曲検索を行います。", value="playlist"),
                discord.SelectOption(label="日本の人気曲を使用", description="検索を行わず、日本で人気の曲でプレイします。", value="noSearch"),
                discord.SelectOption(label="終了", description="イントロクイズの準備を中断します。", emoji="❌", value="end")
            ]
            super().__init__(placeholder='検索対象を選択', min_values=1, max_values=1, options=options)
        async def callback(self, interaction: discord.Interaction):
            self.view.searchMode = self.values[0]
            self.view.stop()
        async def on_timeout(self):
            self.view.searchMode = None

    class roundCountSelect(discord.ui.Select):
        def __init__(self):
            options = []
            for i in range(5, 21):
                options.append(discord.SelectOption(label=str(i), value=str(i)))
            options.append(discord.SelectOption(label="終了", description="イントロクイズの準備を中断します。", emoji="❌", value="end"))
            super().__init__(placeholder='ラウンド数を選択', min_values=1, max_values=1, options=options)
        async def callback(self, interaction: discord.Interaction):
            if ctx.author.id == interaction.user.id:
                self.view.value = self.values[0]
                self.view.stop()
            else:
                await interaction.response.send_message(f"イントロクイズの設定はコマンド実行者のみ行えます!", ephemeral=True)
        async def on_timeout(self):
            self.view.value = "timeout"

    bot.sessions[ctx.guild.id] = {"players":{}, "wait": [], "channel": ctx.channel.id}

    for i in ctx.voice_client.channel.members:
        if not i.bot:
            bot.sessions[ctx.guild.id]["players"][i.id] = {}
            bot.sessions[ctx.guild.id]["players"][i.id]["score"] = 0
            bot.sessions[ctx.guild.id]["players"][i.id]["miss"] = False
    #ゲームモード選択
    view = DropdownView(PlayModeSelect())
    msg = await ctx.send("イントロクイズを準備します!\n"
                    "以下のメニューからモードを選択してください。", view=view)
    while(not view.value):
        await view.wait()
    gamemode = view.value
    if gamemode == "end":
        await msg.edit("イントロクイズの準備を中断しました。",view=None)
        return
    elif gamemode == "timeout":
        await msg.edit("30秒間操作が行われなかったため終了しました。",view=None)
        return
    bot.sessions[ctx.guild.id]["gamemode"] = gamemode

    #楽曲検索
    view = DropdownView(searchModeSelect())

    if gamemode != "quickPlay": 
        await msg.edit("使用楽曲を選択します!\n"
                        "以下のメニューから検索対象を選択してください。\n"
                        "(検索にはSpotifyのApiを使用します)", view=view)
        await view.wait()
        searchMode = view.searchMode
        if  searchMode == "timeout":
            await msg.edit("30秒間操作が行われなかったため終了しました。",view=None)
            return
        elif searchMode == "end":
            await msg.edit("イントロクイズの準備を中断しました。",view=None)
            return
        elif searchMode == "artist":
            searching = "アーティスト"
        elif searchMode == "playlist":
            searching = "プレイリスト"
        elif searchMode == "album":
            searching = "アルバム"
        status = "first"
        while(True):
            if searchMode in ["noSearch", "quickPlay"]:
                break
            msgwaittask = asyncio.create_task(bot.wait_for("message", check=lambda m: m.channel == ctx.channel and m.author == ctx.author))
            confview = confirmView(msgwaittask, status)
            if status == "found":
                confview.children[0].disabled = False
            else:
                confview.children[0].disabled = True
            if status == "first":
                if searching == "アーティスト":
                    await msg.edit(f"{searching}を検索します。\n"
                    f"検索したい{searching}名をこのチャンネルに送信してください。", view=confview)
                else:
                    await msg.edit(f"{searching}を検索します。\n"
                    f"検索したい{searching}のURLをこのチャンネルに送信してください。", view=confview)
            elif status == "notfound":
                await msg.edit(f"{searching}が見つかりませんでした。\n"
                "キーワードを変えて再度送信してください。", view=confview)
            elif status == "found":
                await msg.edit(f"{result}が見つかりました!使用できる楽曲数は`{str(len(tracklist))}`です。\n"
                "これらの楽曲を使用する場合は「決定」をクリックしてください。\n"
                f"再検索する場合は再度検索したい{searching}名を送信してください。", view=confview)
            elif status == "notenough":
                await msg.edit(f"{result}が見つかりましたが、使用できる楽曲が不十分です。\n"
                "キーワードを変えて再度送信し検索してください。", view=confview)
            elif status == "invalidURL":
                await msg.edit("送信されたURLが正しくありません!\n"
                "正しいURLが入力されているか確認してください。", view=confview)
            done, pending = await asyncio.wait([msgwaittask], timeout=30, return_when=asyncio.ALL_COMPLETED)
            if done:
                if msgwaittask.cancelled():
                    if confview.value == "end":
                        await msg.edit("イントロクイズの準備を中断しました。", view=None)
                        return
                    elif confview.value == "confirmed":
                        break
                else:
                    postedmsg = list(done)[0].result()
            elif pending:
                await msg.edit("30秒間操作されなかったためイントロクイズの準備を中断しました。", view=None)
                return
            q = postedmsg.content
            await postedmsg.delete()
            if view.searchMode == "artist":
                results = spotify.search(q=f"artist:{q}", type="artist", limit=1, market="JP")
                if not results["artists"]["items"]:
                    status = "notfound"
                    continue
                artist = results["artists"]["items"][0]["name"]
                tracks = spotify.search(q="artist: " + artist, limit=50,type="track",market="JP")
                result = f"**{artist}**"

            elif view.searchMode == "playlist":
                m = re.match(r"https://open.spotify.com/playlist/.{22}", q)
                if not m:
                    status = "invalidURL"
                    continue
                playlist_id = m.group().split("https://open.spotify.com/playlist/")[1]
                try:
                    playlist_info = spotify.playlist(playlist_id, market="JP")
                except:
                    status = "notfound"
                    continue
                else:
                    tracks = playlist_info
                    playlist_name = playlist_info["name"]
                    playlist_owner = playlist_info["owner"]["display_name"]
                    result = f"{playlist_owner}の**{playlist_name}**"

            elif view.searchMode == "album":
                m = re.match(r"https://open.spotify.com/album/.{22}", q)
                if not m:
                    status = "invalidURL"
                    continue
                album_id = m.group().split("https://open.spotify.com/album/")[1]
                try:
                    album_info = spotify.album(album_id)
                except:
                    status = "notfound"
                    continue
                else:
                    tracks = album_info
                    album_name = album_info["name"]
                    album_artist = album_info["artists"][0]["name"]
                    album_image_url = album_info["images"][0]["url"]
                    album_url = album_info["external_urls"]["spotify"]
                    result = f"{album_artist}の**{album_name}**"
            tracklist = []
            for i in tracks["tracks"]["items"]:
                if "preview_url" not in list(i.keys()):
                    continue
                else:
                    data = {"name": i["name"], "artist": i["artists"][0]["name"],
                    "url": i["preview_url"]}
                    if "album" in list(i.keys()):
                        data["image"] = i["album"]["images"][0]["url"]
                        data["albumurl"] = i["album"]["external_urls"]["spotify"]
                        data["albumname"] = i["album"]["name"]
                    else:
                        data["image"] = album_image_url
                        data["albumurl"] = album_url
                        data["albumname"] = album_name
                    tracklist.append(data)         
            if len(tracklist) > 3:
                status = "found"
            else:
                status = "notenough"
        if searchMode == "noSearch":
            tracklist = []
            tracks = spotify.playlist("37i9dQZEVXbKXQ4mDTEBXq", market="JP")
            result = tracks["tracks"]["items"]
            for i in result:
                if i["track"]["preview_url"]:
                    tracklist.append({"name": i["track"]["name"], "artist": i["track"]["artists"][0]["name"],
                    "url": i["track"]["preview_url"], "image": i["track"]["album"]["images"][0]["url"],
                    "albumname": i["track"]["album"]["name"], "albumurl": i["track"]["album"]["external_urls"]["spotify"]})
        #ラウンド数選択
        countview = DropdownView(roundCountSelect())
        await msg.edit("ラウンド数を指定してください。", view=countview)
        await countview.wait()
        if countview.value == "end":
            await msg.edit("イントロクイズの準備を中断しました。",view=None)
            return
        elif not countview.value:
            await msg.edit("30秒間操作が行われなかったため終了しました。",view=None)
            return
        else:
            roundcount = int(countview.value)
    else:
        tracklist = []
        tracks = spotify.playlist("37i9dQZEVXbKXQ4mDTEBXq", market="JP")
        result = tracks["tracks"]["items"]
        for i in result:
            if i["track"]["preview_url"]:
                tracklist.append({"name": i["track"]["name"], "artist": i["track"]["artists"][0]["name"],
                "url": i["track"]["preview_url"], "image": i["track"]["album"]["images"][0]["url"],
                "albumname": i["track"]["album"]["name"], "albumurl": i["track"]["album"]["external_urls"]["spotify"]})
        roundcount = 5
        gamemode = "normal"
        searchMode = "noSearch"

    await msg.delete()
    for j in bot.sessions[ctx.guild.id]["wait"]:
        bot.sessions[ctx.guild.id]["players"][j] = {}
        bot.sessions[ctx.guild.id]["players"][j]["score"] = 0
        bot.sessions[ctx.guild.id]["players"][j]["miss"] = False
        del bot.sessions[ctx.guild.id]["wait"][(bot.sessions[ctx.guild.id]["wait"].index(j))]

    quizinfoembed = discord.Embed(title="イントロクイズ",description="5秒後にイントロクイズを開始します!")
    quizinfoembed.add_field(name="参加者一覧", value="\n".join([f"<@{i}>" for i in list(bot.sessions[ctx.guild.id]["players"].keys())]))
    if searchMode == "artist":
        quizinfo = f"使用楽曲のアーティスト: `{artist}`"
    elif searchMode == "playlist":
        quizinfo = f"使用するプレイリスト: `{playlist_name}`\nプレイリストの作成者: `{playlist_owner}`"
    elif searchMode == "album":
        quizinfo = f"使用するアルバム: `{album_name}`\nアルバムのアーティスト: `{album_artist}`"
    elif searchMode == "noSearch":
        quizinfo = f"使用するプレイリスト: `Tokyo Super Hits!`\nプレイリストの作成者: `Spotify`"
    quizinfo += f"\nラウンド数: `{roundcount}`"
    if gamemode == "normal":
        quizinfo += "\nモード: `通常モード`"
    elif gamemode == "timeattack":
        quizinfo += "\nモード: `タイムアタックモード`"
    quizinfoembed.add_field(name="ルール", value=quizinfo, inline=False)
    msg = await ctx.send(embed=quizinfoembed)
    await asyncio.sleep(5)

    def everyone_missed():
        for j in bot.sessions[ctx.guild.id]["players"]:
            if bot.sessions[ctx.guild.id]["players"][j]["miss"]:
                pass
            else:
                return False
        return True

    selectionsEmbed = None
    embed = None
    starttime = None
    times_remain = None
    class listeningView(discord.ui.View):
        nonlocal ctx, msg, embed, selectionsEmbed, starttime, times_remain
        def __init__(self):
            super().__init__()
            self.value = None
            self.timesleft = None
            self.user = None

        @discord.ui.button(label="解答", emoji="🔔", style=discord.ButtonStyle.blurple)
        async def answer(self, button: discord.ui.Button, interaction: discord.Interaction):
            if interaction.user.id not in list(bot.sessions[ctx.guild.id]["players"].keys()):
                await interaction.response.send_message(f"{interaction.user.mention}さん、あなたはこのイントロクイズに参加していないため回答できません。\n"
                "同じボイスチャンネルに接続して途中参加しましょう!", ephemeral=True)
                return
            if bot.sessions[ctx.guild.id]["players"][interaction.user.id]["miss"]:
                await interaction.response.send_message(f"{interaction.user.mention}さん、あなたはこのラウンド中の回答権がありません!")
                await asyncio.sleep(5)
                await interaction.delete_original_message()
                return

            self.user = interaction.user.id
            self.timesleft = times_remain - (time.time() - starttime) 
            ctx.voice_client.stop()
            ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(source=f"./src/sounds/Answering.mp3"), volume=0.7))
            self.children[0].disabled = True
            view = answerView(interaction.user.id)
            await interaction.response.edit_message(content=f"{interaction.user.mention}さん、あなたが回答者です!**5秒以内に答えを選択してください!**",
                                                    view=view, embed=selectionsEmbed)
            await view.wait()
            if view.value == "timeup":
                self.value = "timeup"
            elif view.value == answerpos:
                self.value = "collect"
            else:
                self.value = "incollect"
            self.stop()
        def __call__(self, _):
            if not self.user:
                self.value = "timeout"
                self.stop()
            
    class answerView(discord.ui.View):
        def __init__(self, user):
            super().__init__(timeout=5)
            self.value = "timeup"
            self.user = user
        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user.id == self.user
        @discord.ui.button(emoji="1️⃣", style=discord.ButtonStyle.grey)
        async def select1(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.value = 0
            self.stop()
        @discord.ui.button(emoji="2️⃣", style=discord.ButtonStyle.grey)
        async def select2(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.value = 1
            self.stop()
        @discord.ui.button(emoji="3️⃣", style=discord.ButtonStyle.grey)
        async def select3(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.value = 2
            self.stop()
        @discord.ui.button(emoji="4️⃣", style=discord.ButtonStyle.grey)
        async def select4(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.value = 3   
            self.stop()

    class showAnswerView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=10)
            self.value = None
        @discord.ui.button(emoji="⬇️", label="パネルを下に下げる", style=discord.ButtonStyle.grey)
        async def select4(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.value = "downed"
            self.stop()

    embed = discord.Embed(title="イントロクイズ", description="この曲は何でしょうか?", color=0x00a6ff)
    embed.add_field(name="",value="")
    embed.set_footer(text="Powered by Spotify | 同じボイスチャンネルに接続して途中参加しましょう!")

    for i in range(roundcount):
        #正解の曲の選曲
        selector = randint(0, len(tracklist) - 1)
        selectedTrack = tracklist[selector]
        answer = selectedTrack["name"]
        artistname = selectedTrack["artist"]
        musicurl = selectedTrack["url"]
        album_name = selectedTrack["albumname"]
        album_url = selectedTrack["albumurl"]
        if selectedTrack["image"] != "none":
            artworkurl = selectedTrack["image"]
        else:
            artworkurl = None
        #誤答を選択
        choices = [answer]
        while(len(choices) < 4):
            wrongsong = tracklist[randint(0, len(tracklist) - 1)]["name"]
            while(wrongsong in choices):
                wrongsong = tracklist[randint(0, len(tracklist) - 1)]["name"]
            choices.insert(randint(0, len(choices)), wrongsong)
        #embedの選択肢テキストを作成
        embedcontent = "1️⃣: " + choices[0] + "\n"
        embedcontent += "2️⃣: " + choices[1] + "\n"
        embedcontent += "3️⃣: " + choices[2] + "\n"
        embedcontent += "4️⃣: " + choices[3]
        selectionsEmbed = discord.Embed(title="選択肢", description=embedcontent)
        answerpos = choices.index(answer)

        #再生音源をダウンロード
        r = requests.get(musicurl, stream=True)
        players = bot.sessions[ctx.guild.id]["players"]
        with open(f"./src/{ctx.guild.id}.m4a", mode="wb") as musicfile:
            musicfile.write(r.content)

        #答えを表示するEmbedを作成
        answerEmbed = discord.Embed(title="答え",description=answer, color=0xffcc00)
        answerEmbed.add_field(name="アーティスト名", value=artistname)
        answerEmbed.add_field(name="アルバム", value=f"[{album_name}]({album_url})")
        if artworkurl:
            answerEmbed.set_thumbnail(url=artworkurl)
        #回答権リセット
        for j in bot.sessions[ctx.guild.id]["players"]:
            bot.sessions[ctx.guild.id]["players"][j]["miss"] = False
        for j in bot.sessions[ctx.guild.id]["wait"]:
            bot.sessions[ctx.guild.id]["players"][j] = {}
            bot.sessions[ctx.guild.id]["players"][j]["score"] = 0
            bot.sessions[ctx.guild.id]["players"][j]["miss"] = False
            del bot.sessions[ctx.guild.id]["wait"][(bot.sessions[ctx.guild.id]["wait"].index(j))]
        showansview = showAnswerView()
        times_remain = 30
        text = f"**ラウンド{i + 1}**: 制限時間は30秒です。"
        while(True):
            embed.set_field_at(index=0, name="回答権", value=
                              "\n".join([f"<@{i}>: ❌" if players[i]["miss"] else f"<@{i}>: ⭕" for i in list(players.keys())]))
            starttime = time.time()
            
            view = listeningView()
            ctx.voice_client.stop()
            ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(source=f"./src/{ctx.guild.id}.m4a",
                                  before_options=f"-ss {30 - times_remain}"), volume=0.7), after=view)
            await msg.edit(content=text, embed=embed, view=view)
            while(not view.user):
                await view.wait()
                if view.value:
                    break
            times_remain = view.timesleft
            answedUser = view.user

            if not times_remain:
                await msg.edit(f"時間切れです…。誰もポイントを獲得しませんでした。\n"
                "10秒後に次の問題に進みます。パネルを下に下げる場合は下のボタンをクリックしてください。", view=showansview, embed=answerEmbed)
                break
            if view.value == "collect":
                ctx.voice_client.stop()
                ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(source=f"./src/sounds/Collect.mp3"), volume=0.7))
                if gamemode == "normal":
                    earnedPoint = 1
                else:
                    earnedPoint = round(times_remain + 1)
                bot.sessions[ctx.guild.id]["players"][answedUser]["score"] += earnedPoint
                await msg.edit(f"**<@{answedUser}>**さん、正解です!`{earnedPoint}`ポイントを獲得しました。\n"
                "10秒後に次の問題に進みます。パネルを下に下げる場合は下のボタンをクリックしてください。", view=showansview, embed=answerEmbed)
                break
            elif view.value == "incollect":
                bot.sessions[ctx.guild.id]["players"][answedUser]["miss"] = True
                if everyone_missed():
                    await msg.edit(f"**<@{answedUser}>**さん、不正解です･･･。\n"
                    "プレイヤー全員の回答権が無くなりました。誰もポイントを獲得しませんでした。\n"
                    "10秒後に次の問題に進みます。パネルを下に下げる場合は下のボタンをクリックしてください。", view=showansview, embed=answerEmbed)
                    break
                else:
                    text = f"**<@{answedUser}>**さん、不正解です･･･。あなたはこのラウンド中は回答できません!"
            elif view.value == "timeup":
                bot.sessions[ctx.guild.id]["players"][answedUser]["miss"] = True
                if everyone_missed():
                    await msg.edit(f"**<@{answedUser}>**さん、時間切れです･･･。\n"
                    "プレイヤー全員の回答権が無くなりました。誰もポイントを獲得しませんでした。\n"
                    "10秒後に次の問題に進みます。パネルを下に下げる場合は下のボタンをクリックしてください。", view=showansview, embed=answerEmbed)
                    break
                else:
                    text = f"**<@{answedUser}>**さん、時間切れです･･･。あなたはこのラウンド中は回答できません!"          

        await showansview.wait()
        if showansview.value == "downed":
            await msg.delete()
            msg = await ctx.send("パネルを下に下げました。", embed=quizinfoembed)
            await asyncio.sleep(5)
    #リザルト
    sortedlist = sorted(list(bot.sessions[ctx.guild.id]["players"].items()), key=lambda x:x[1]["score"], reverse=True)
    textlist = []
    rank = 1
    rankstodown = 1
    for i in range(len(sortedlist)):
        score = sortedlist[i][1]['score']
        if i != 0:
            if sortedlist[i-1][1]["score"] == score:
                rankstodown += 1
            else:
                rank += rankstodown
                rankstodown = 1
        textlist.append(f"{rank}位: <@{sortedlist[i][0]}> {score}pts.")
    scoreboard = "\n".join(textlist)
    embed = discord.Embed(title="結果", description=scoreboard, color=0x00ff59)
    await msg.edit(content="**全てのラウンドが終了しました!**\n結果は以下の通りです。お疲れ様でした!", embed=embed, view=None)

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
    if ctx.author.id not in [431805523969441803,462765491325501445]:#Poteto143のID, T-takuのID
        return
    await ctx.send("終了します…👋")
    for i in bot.sessions:
        bot.game_tasks[i].cancel()
        channel = bot.get_channel(bot.sessions[i]["channel"])
        await channel.send("オーナーがBotを停止させます。再起動までしばらくお待ち下さい…")
    await bot.close()

@bot.event
async def on_voice_state_update(member, before: discord.VoiceState, after: discord.VoiceState):
    if member.bot:
        return
    if before.channel == after.channel:
        return
    if before.channel:
        if before.channel.guild.voice_client:
            if before.channel.id == before.channel.guild.voice_client.channel.id:
                if before.channel.guild.id in list(bot.sessions.keys()):
                    if member not in before.channel.members and (member.id in list(bot.sessions[before.channel.guild.id]["players"].keys()) or member.id in bot.sessions[before.channel.guild.id]["wait"]):
                        channel = bot.get_channel(bot.sessions[before.channel.guild.id]["channel"])
                        await channel.send(member.mention + "さんがイントロクイズから退出しました。")
                        if member.id in list(bot.sessions[before.channel.guild.id]["players"].keys()):
                            del bot.sessions[before.channel.guild.id]["players"][member.id]
                        if member.id in bot.sessions[before.channel.guild.id]["wait"]:
                            del bot.sessions[before.channel.guild.id]["wait"][member.id]
                        if not bot.sessions[before.channel.guild.id]["players"]:
                            del bot.sessions[before.channel.guild.id]
                            before.channel.guild.voice_client.stop()
                            await before.channel.guild.voice_client.disconnect()
                            bot.game_tasks[before.channel.guild.id].cancel()
                            del bot.game_tasks[before.channel.guild.id]
                            await channel.send("全ての参加者がボイスチャンネルから退出しました。\nイントロクイズは中止されました。")
    if not after.channel:
        return
    if bot.user in after.channel.members and not member.bot:
        textchannel = bot.get_channel(bot.sessions[after.channel.guild.id]["channel"])
        await textchannel.send(member.mention + "さんがイントロクイズに途中参加しました。次のラウンドから回答できます!")
        bot.sessions[after.channel.guild.id]["wait"].append(member.id)
            
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
            if ctx.guild.voice_client:
                await ctx.guild.voice_client.disconnect()
    ch = bot.get_channel(733972172250415104)
    embed = discord.Embed(title="例外発生", description=f"{ctx.command.name}で例外が発生しました")
    embed.add_field(name="内容", value=f"```{error}```")
    traceback.print_exception(type(error), error, error.__traceback__)
    await ch.send(embed=embed)
    
bot.run(token)