import discord
from discord.ext import commands
import asyncio
import re
import time
from random import randint
import requests
import Cogs.sessionsManager as sessionsManager

class DropdownView(discord.ui.View):
    def __init__(self, arg):
        super().__init__(timeout=30)
        self.add_item(arg)
        self.value = None

    async def on_timeout(self):
        self.value = "timeout"

class confirmView(discord.ui.View):

    def __init__(self, arg: asyncio.Task, ctx:commands.Context):
        super().__init__(timeout=30)
        self.value = None
        self.tasktocancel = arg
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction):
        return self.ctx.author.id == interaction.user.id

    @discord.ui.button(label="決定", emoji="✅", style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.tasktocancel.cancel()
        self.value = "confirmed"

    @discord.ui.button(label="準備を中断", emoji="❌", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.tasktocancel.cancel()
        self.value = "end"


class PlayModeSelect(discord.ui.Select):

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        options = [
            discord.SelectOption(
                label="通常モード", description="正答するたびに1ポイント獲得するモードです。", emoji="🔔", value="normal"),
            discord.SelectOption(
                label="タイムアタックモード", description="正答の速さで獲得ポイントが変動するモードです。", emoji="🕒", value="timeattack"),
            discord.SelectOption(
                label="クイックプレイ", description="すぐに通常モードを5ラウンドプレイします。", emoji="➡️", value="quickPlay"),
            discord.SelectOption(
                label="終了", description="イントロクイズの準備を中断します。", emoji="❌", value="end")
        ]
        super().__init__(placeholder='モードを選択', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.ctx.author.id == interaction.user.id:
            self.view.value = self.values[0]
            self.view.stop()
        else:
            await interaction.response.send_message(f"イントロクイズの設定はコマンド実行者のみ行えます!", ephemeral=True)


class searchModeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="アーティスト名で検索", description="アーティスト名で楽曲検索を行います。", value="artist"),
            discord.SelectOption(
                label="アルバムURLで検索", description="アルバムURLで楽曲検索を行います。", value="album"),
            discord.SelectOption(
                label="プレイリストURLで検索", description="SpotifyのプレイリストURLで楽曲検索を行います。", value="playlist"),
            discord.SelectOption(
                label="日本の人気曲を使用", description="検索を行わず、日本で人気の曲でプレイします。", value="noSearch"),
            discord.SelectOption(
                label="終了", description="イントロクイズの準備を中断します。", emoji="❌", value="end")
        ]
        super().__init__(placeholder='検索対象を選択', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.searchMode = self.values[0]
        self.view.stop()

    async def on_timeout(self):
        self.view.searchMode = None


class roundCountSelect(discord.ui.Select):
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        options = []
        for i in range(1, 6):
            options.append(discord.SelectOption(
                label=str(i*5), value=str(i*5)))
        options.append(discord.SelectOption(
            label="終了", description="イントロクイズの準備を中断します。", emoji="❌", value="end"))
        super().__init__(placeholder='ラウンド数を選択', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.ctx.author.id == interaction.user.id:
            self.view.value = self.values[0]
            self.view.stop()
        else:
            await interaction.response.send_message(f"イントロクイズの設定はコマンド実行者のみ行えます!", ephemeral=True)

    async def on_timeout(self):
        self.view.value = "timeout"


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
    async def downpanel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = "downed"
        self.stop()


class listeningView(discord.ui.View):
    def __init__(self, ctx, bot, times_remain, starttime, selectionEmbed, answerpos, sessions: sessionsManager.Session):
        super().__init__()
        self.value = None
        self.timesleft = None
        self.user = None
        self.ctx = ctx
        self.bot = bot
        self.starttime = starttime
        self.times_remain = times_remain
        self.selectionEmbed = selectionEmbed
        self.answerpos = answerpos
        self.session = sessions

    @discord.ui.button(label="解答", emoji="🔔", style=discord.ButtonStyle.blurple)
    async def answer(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not self.session.player_joined_check(interaction.user.id) :
            await interaction.response.send_message(f"{interaction.user.mention}さん、あなたはこのイントロクイズに参加していないため回答できません。\n"
                                                    "同じボイスチャンネルに接続して途中参加しましょう!", ephemeral=True)
            return
        if self.session.get_player(interaction.user.id).miss:
            await interaction.response.send_message(f"{interaction.user.mention}さん、あなたはこのラウンド中の回答権がありません!")
            await asyncio.sleep(5)
            await interaction.delete_original_message()
            return

        self.user = interaction.user.id
        self.timesleft = self.times_remain - (time.time() - self.starttime)
        self.ctx.voice_client.stop()
        self.ctx.voice_client.play(discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(source=f"./src/sounds/Answering.mp3"), volume=0.5))
        self.children[0].disabled = True
        view = answerView(interaction.user.id)
        await interaction.response.edit_message(content=f"{interaction.user.mention}さん、あなたが回答者です!**5秒以内に答えを選択してください!**",
                                                view=view, embed=self.selectionEmbed)
        await view.wait()
        if view.value == "timeup":
            self.value = "timeup"
        elif view.value == self.answerpos:
            self.value = "collect"
        else:
            self.value = "incollect"
        self.stop()

    def __call__(self, _):
        if not self.user:
            self.value = "timeout"
            self.stop()


class Quiz(commands.Cog):
    def __init__(self, bot, spotify, sessions: sessionsManager.SessionsGroup):
        self.bot: commands.Bot = bot
        self.spotify = spotify
        self.sessions = sessions

    async def disconnect(self, ctx):
        await ctx.voice_client.disconnect()
        self.sessions.remove_session(ctx.guild.id)

    @commands.command()
    async def start(self, ctx: commands.Context):
        global spotify, pannel_emojies
        self.bot.game_tasks[ctx.guild.id] = asyncio.current_task()
        botasmember = await ctx.guild.fetch_member(self.bot.user.id)
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
        if self.sessions.get_session(ctx.guild.id):
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

        session = self.sessions.add_session(guildid=ctx.guild.id, channelid=ctx.channel.id)
        for i in ctx.voice_client.channel.members:
            if not i.bot:
                session.join_player(i.id)
        # ゲームモード選択
        view = DropdownView(PlayModeSelect(ctx))
        msg = await ctx.send("イントロクイズを準備します!\n"
                            "以下のメニューからモードを選択してください。", view=view)
        while(not view.value):
            await view.wait()
        gamemode = view.value
        if gamemode == "end":
            await self.disconnect(ctx)
            await msg.edit("イントロクイズの準備を中断しました。", view=None)
            return
        elif gamemode == "timeout":
            await self.disconnect(ctx)
            await msg.edit("30秒間操作が行われなかったため終了しました。", view=None)
            return

        # 楽曲検索
        view = DropdownView(searchModeSelect())

        if gamemode != "quickPlay":
            await msg.edit("使用楽曲を選択します!\n"
                        "以下のメニューから検索対象を選択してください。\n"
                        "(検索にはSpotifyのApiを使用します)", view=view)
            await view.wait()
            searchMode = view.searchMode
            if searchMode == "timeout":
                await self.disconnect(ctx)
                await msg.edit("30秒間操作が行われなかったため終了しました。", view=None)
                return
            elif searchMode == "end":
                await self.disconnect(ctx)
                await msg.edit("イントロクイズの準備を中断しました。", view=None)
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
                msgwaittask = asyncio.create_task(self.bot.wait_for(
                    "message", check=lambda m: m.channel == ctx.channel and m.author == ctx.author))
                confview = confirmView(msgwaittask, ctx)
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
                            await self.disconnect(ctx)
                            await msg.edit("イントロクイズの準備を中断しました。", view=None)
                            return
                        elif confview.value == "confirmed":
                            break
                    else:
                        postedmsg = list(done)[0].result()
                elif pending:
                    await self.disconnect(ctx)
                    await msg.edit("30秒間操作されなかったためイントロクイズの準備を中断しました。", view=None)
                    return
                q = postedmsg.content
                await postedmsg.delete()
                if view.searchMode == "artist":
                    results = self.spotify.search(
                        q=f"artist:{q}", type="artist", limit=1, market="JP")
                    if not results["artists"]["items"]:
                        status = "notfound"
                        continue
                    artist = results["artists"]["items"][0]["name"]
                    tracks = self.spotify.search(
                        q="artist: " + artist, limit=50, type="track", market="JP")["tracks"]
                    result = f"**{artist}**"

                elif view.searchMode == "playlist":
                    m = re.match(r"https://open.spotify.com/playlist/.{22}", q)
                    if not m:
                        status = "invalidURL"
                        continue
                    playlist_id = m.group().split(
                        "https://open.spotify.com/playlist/")[1]
                    try:
                        playlist_info = self.spotify.playlist(playlist_id, market="JP")
                    except:
                        status = "notfound"
                        continue
                    else:
                        playlist_owner = playlist_info["owner"]["display_name"]
                        playlist_name = playlist_info["name"]
                        tracks = self.spotify.playlist_tracks(playlist_id, market="JP")
                        result = f"{playlist_owner}の**{playlist_name}**"

                elif view.searchMode == "album":
                    m = re.match(r"https://open.spotify.com/album/.{22}", q)
                    if not m:
                        status = "invalidURL"
                        continue
                    album_id = m.group().split(
                        "https://open.spotify.com/album/")[1]
                    try:
                        album_info = self.spotify.album(album_id)
                    except:
                        status = "notfound"
                        continue
                    else:
                        tracks = album_info["tracks"]
                        album_name = album_info["name"]
                        album_artist = album_info["artists"][0]["name"]
                        album_image_url = album_info["images"][0]["url"]
                        album_url = album_info["external_urls"]["spotify"]
                        result = f"{album_artist}の**{album_name}**"
                tracklist = []
                for i in tracks["items"]:
                    if "track" in i.keys():
                        i = i["track"]
                        print(i)
                    if i["preview_url"]:
                        data = {"name": i["name"], "artist": i["artists"][0]["name"],
                                "url": i["preview_url"]}
                        if "album" in i.keys():
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
                tracks = self.spotify.playlist("37i9dQZEVXbKXQ4mDTEBXq", market="JP")
                result = tracks["tracks"]["items"]
                for i in result:
                    if i["track"]["preview_url"]:
                        tracklist.append({"name": i["track"]["name"],
                                        "artist": i["track"]["artists"][0]["name"],
                                        "url": i["track"]["preview_url"],
                                        "image": i["track"]["album"]["images"][0]["url"],
                                        "albumname": i["track"]["album"]["name"],
                                        "albumurl": i["track"]["album"]["external_urls"]["spotify"]})
            # ラウンド数選択
            countview = DropdownView(roundCountSelect(ctx))
            await msg.edit("ラウンド数を指定してください。", view=countview)
            await countview.wait()
            if countview.value == "end":
                await self.disconnect(ctx)
                await msg.edit("イントロクイズの準備を中断しました。", view=None)
                return
            elif not countview.value:
                await self.disconnect(ctx)
                await msg.edit("30秒間操作が行われなかったため終了しました。", view=None)
                return
            else:
                roundcount = int(countview.value)
        else:
            tracklist = []
            tracks = self.spotify.playlist("37i9dQZEVXbKXQ4mDTEBXq", market="JP")
            result = tracks["tracks"]["items"]
            for i in result:
                if i["track"]["preview_url"]:
                    tracklist.append({"name": i["track"]["name"],
                                    "artist": i["track"]["artists"][0]["name"],
                                    "url": i["track"]["preview_url"],
                                    "image": i["track"]["album"]["images"][0]["url"],
                                    "albumname": i["track"]["album"]["name"],
                                    "albumurl": i["track"]["album"]["external_urls"]["spotify"]})
            roundcount = 5
            gamemode = "normal"
            searchMode = "noSearch"

        await msg.delete()
        session.join_waiters()

        quizinfoembed = discord.Embed(
            title="イントロクイズ", description="5秒後にイントロクイズを開始します!")
        quizinfoembed.add_field(name="参加者一覧", value="\n".join(
            [f"<@{i}>" for i in session.get_player_ids()]))
        quizinfoembed.set_footer(text="Powered by Spotify | 同じボイスチャンネルに接続して途中参加しましょう!")
        if gamemode == "normal":
            quizinfo = "モード: `通常モード`\n"
        elif gamemode == "timeattack":
            quizinfo = "モード: `タイムアタックモード`\n"
        quizinfo += f"ラウンド数: `{roundcount}`\n"
        if searchMode == "artist":
            quizinfo += f"使用楽曲のアーティスト: `{artist}`"
        elif searchMode == "playlist":
            quizinfo += f"使用するプレイリスト: `{playlist_name}`\nプレイリストの作成者: `{playlist_owner}`"
        elif searchMode == "album":
            quizinfo += f"使用するアルバム: `{album_name}`\nアルバムのアーティスト: `{album_artist}`"
        elif searchMode == "noSearch":
            quizinfo += f"使用するプレイリスト: `Tokyo Super Hits!`\nプレイリストの作成者: `Spotify`"
        

        quizinfoembed.add_field(name="ルール", value=quizinfo, inline=False)
        msg = await ctx.send(embed=quizinfoembed)
        await asyncio.sleep(1)

        def everyone_missed():
            for player in session.players:
                if not player.miss:
                    return False
            return True

        selectionsEmbed = None
        embed = None
        starttime = None
        times_remain = None

        embed = discord.Embed(
            title="イントロクイズ", description="この曲は何でしょうか?", color=0x00a6ff)
        embed.add_field(name="", value="")
        embed.set_footer(text="Powered by Spotify | 同じボイスチャンネルに接続して途中参加しましょう!")

        for i in range(roundcount):
            # 正解の曲の選曲
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
            # 誤答を選択
            choices = [answer]
            while(len(choices) < 4):
                wrongsong = tracklist[randint(0, len(tracklist) - 1)]["name"]
                while(wrongsong in choices):
                    wrongsong = tracklist[randint(0, len(tracklist) - 1)]["name"]
                choices.insert(randint(0, len(choices)), wrongsong)
            # embedの選択肢テキストを作成
            embedcontent = "1️⃣: " + choices[0] + "\n"
            embedcontent += "2️⃣: " + choices[1] + "\n"
            embedcontent += "3️⃣: " + choices[2] + "\n"
            embedcontent += "4️⃣: " + choices[3]
            selectionsEmbed = discord.Embed(title="選択肢", description=embedcontent)
            selectionsEmbed.set_footer(text="Powered by Spotify | 同じボイスチャンネルに接続して途中参加しましょう!")
            answerpos = choices.index(answer)

            # 再生音源をダウンロード
            r = requests.get(musicurl, stream=True)
            with open(f"./src/{ctx.guild.id}.m4a", mode="wb") as musicfile:
                musicfile.write(r.content)

            # 答えを表示するEmbedを作成
            answerEmbed = discord.Embed(
                title="答え", description=answer, color=0xffcc00)
            answerEmbed.add_field(name="アーティスト名", value=artistname)
            answerEmbed.add_field(
                name="アルバム", value=f"[{album_name}]({album_url})")
            answerEmbed.set_footer(text="Powered by Spotify | 同じボイスチャンネルに接続して途中参加しましょう!")
            if artworkurl:
                answerEmbed.set_thumbnail(url=artworkurl)
            # 回答権リセット
            session.refresh()
            session.join_waiters()

            showansview = showAnswerView()
            times_remain = 30
            text = f"**ラウンド{i + 1} / {roundcount}**: 制限時間は30秒です。"
            while(True):
                embed.set_field_at(index=0, name="回答権", value="\n".join(
                    [f"<@{player.id}>: ❌" if player.miss else f"<@{player.id}>: ⭕" for player in session.players]))
                starttime = time.time()

                view = listeningView(ctx, self.bot, times_remain, starttime, selectionsEmbed, answerpos, session)
                await msg.edit(content=text, embed=embed, view=view)
                ctx.voice_client.stop()
                ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(source=f"./src/{ctx.guild.id}.m4a",
                                    before_options=f"-ss {30 - times_remain}"), volume=0.5), after=view)
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
                    ctx.voice_client.play(discord.PCMVolumeTransformer(
                        discord.FFmpegPCMAudio(source=f"./src/sounds/Collect.mp3"), volume=0.5))
                    if gamemode == "normal":
                        earnedPoint = 1
                    else:
                        earnedPoint = round(times_remain + 1)
                    session.get_player(answedUser).add_score(earnedPoint)
                    await msg.edit(f"**<@{answedUser}>**さん、正解です!`{earnedPoint}`ポイントを獲得しました。\n"
                                "10秒後に次の問題に進みます。パネルを下に下げる場合は下のボタンをクリックしてください。", view=showansview, embed=answerEmbed)
                    break
                elif view.value == "incollect":
                    session.get_player(answedUser).miss = True
                    if everyone_missed():
                        await msg.edit(f"**<@{answedUser}>**さん、不正解です･･･。\n"
                                    "プレイヤー全員の回答権が無くなりました。誰もポイントを獲得しませんでした。\n"
                                    "10秒後に次の問題に進みます。パネルを下に下げる場合は下のボタンをクリックしてください。", view=showansview, embed=answerEmbed)
                        break
                    else:
                        text = f"**<@{answedUser}>**さん、不正解です･･･。あなたはこのラウンド中は回答できません!"
                elif view.value == "timeup":
                    session.get_player(answedUser).miss = True
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
        # リザルト
        sortedlist = sorted(list(session.players), key=lambda x: x.score, reverse=True)
        textlist = []
        rank = 1
        rankstodown = 1
        for i in range(len(sortedlist)):
            score = sortedlist[i].score
            if i != 0:
                if sortedlist[i-1].score == score:
                    rankstodown += 1
                else:
                    rank += rankstodown
                    rankstodown = 1
            textlist.append(f"{rank}位: <@{sortedlist[i].id}> {score}pts.")
        scoreboard = "\n".join(textlist)
        embed = discord.Embed(title="結果", description=scoreboard, color=0x00ff59)
        embed.set_footer(text="Powered by Spotify")
        await self.disconnect(ctx)
        await msg.edit(content="**全てのラウンドが終了しました!**\n結果は以下の通りです。お疲れ様でした!", embed=embed, view=None)
        
        

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        if before.channel == after.channel:
            return
        if before.channel:
            left_ch_guild = before.channel.guild
            if left_ch_guild.voice_client:
                if before.channel.id == left_ch_guild.voice_client.channel.id:
                    if left_ch_guild.id in self.sessions.sessions:
                        session = self.sessions.get_session(left_ch_guild.id)
                        if member not in before.channel.members and (member.id in session.get_player_ids() or member.id in session.waits):
                            channel = self.bot.get_channel(session.channelid)
                            await channel.send(f"{member.mention}さんがイントロクイズから退出しました。")
                            if member.id in session.get_player_ids():
                                session.remove_player(member.id)
                            if member.id in session.waits:
                                session.remove_waiting_player(member.id)
                            if not session.get_player_ids():
                                self.sessions.remove_session(left_ch_guild.id)
                                before.channel.guild.voice_client.stop()
                                await before.channel.guild.voice_client.disconnect()
                                self.bot.game_tasks[before.channel.guild.id].cancel()
                                del self.bot.game_tasks[before.channel.guild.id]
                                await channel.send("全ての参加者がボイスチャンネルから退出しました。\nイントロクイズは中止されました。")
        if not after.channel:
            return
        if self.bot.user in after.channel.members and not member.bot:
            session = self.sessions.get_session(after.channel.guild.id)
            textchannel = self.bot.get_channel(self.sessions.get_session(after.channel.guild.id).channelid)
            await textchannel.send(f"{member.mention}さんがイントロクイズに途中参加しました。次のラウンドから回答できます!")
            session.add_waiting_players(member.id)