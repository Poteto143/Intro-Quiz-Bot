import discord
from discord.ext import commands
import re
import spotipy

class Search(commands.Cog):
    def __init__(self, spotify):
        self.spotify = spotify
        super().__init__()

    @commands.command()
    async def tracks(self, ctx):
        num = 0
        tracks = self.spotify.playlist("37i9dQZEVXbKXQ4mDTEBXq", market="JP")
        result = tracks["tracks"]["items"]
        tracklist = []
        for i in result:
            if i["track"]["preview_url"]:
                num += 1
                tracklist.append(
                    f"{num}: {i['track']['name']} / {i['track']['artists'][0]['name']}")
        embed = discord.Embed(title="現在のトラックリスト: 日本で人気の曲",
                            description="\n".join(tracklist))
        await ctx.send(embed=embed)


    @commands.command()
    async def artist(self, ctx, *, name):
        artist = self.spotify.search(
            q=f"artist:{name}", type="artist", limit=1, market="JP")
        if len(artist["artists"]["items"]) == 0:
            await ctx.send("指定したアーティストが見つかりませんでした。\nキーワードを変えて再度お試し下さい。")
            return
        tracks = self.spotify.search(
            q="artist: " + artist["artists"]["items"][0]["name"], limit=50, type="track", market="JP")
        result = tracks["tracks"]["items"]
        num = 0
        tracklist = []
        for i in result:
            if i["preview_url"]:
                num += 1
                tracklist.append(f"{num}: {i['name']}")
        if len(tracklist) > 0:
            embed = discord.Embed(
                title="現在のトラックリスト: " + artist["artists"]["items"][0]["name"], description="\n".join(tracklist))
        else:
            embed = discord.Embed(
                title="現在のトラックリスト: " + artist["artists"]["items"][0]["name"], description="使用できる楽曲はありませんでした。")
        await ctx.send(embed=embed)


    @commands.command()
    async def playlist(self, ctx, url):
        m = re.match(r"https://open.spotify.com/playlist/.{22}", url)
        if not m:
            await ctx.send("URLが正しくありません!")
            return
        playlist_id = m.group().split("https://open.spotify.com/playlist/")[1]
        try:
            results = playlist_info = self.spotify.playlist(playlist_id, market="JP")
        except spotipy.exceptions.SpotifyException:
            await ctx.send("プレイリストが見つかりませんでした。\nURLを変えて再度お試し下さい。")
            return
        num = 0
        tracklist = []
        for i in results["tracks"]["items"]:
            if i["track"]["preview_url"]:
                num += 1
                tracklist.append(
                    f"{num}: {i['track']['name']} / {i['track']['artists'][0]['name']}")
        if len(tracklist) > 0:
            embed = discord.Embed(
                title=f"プレイリストの楽曲: {playlist_info['name']}(作成者:{playlist_info['owner']['display_name']})", description="\n".join(tracklist))
        else:
            embed = discord.Embed(
                title=f"プレイリストの楽曲: {playlist_info['name']}(作成者:{playlist_info['owner']['display_name']})", description="使用できる楽曲はありませんでした。")
        await ctx.send(embed=embed)


    @commands.command()
    async def album(self, ctx, url):
        m = re.match(r"https://open.spotify.com/album/.{22}", url)
        if not m:
            await ctx.send("URLが正しくありません!")
            return
        album_id = m.group().split("https://open.spotify.com/album/")[1]
        try:
            album_info = self.spotify.album(album_id)
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
            embed = discord.Embed(
                title=f"アルバムの楽曲: {album_info['artists'][0]['name']} / {album_info['name']}", description="\n".join(tracklist))
        else:
            embed = discord.Embed(
                title=f"アルバムの楽曲: {album_info['artists'][0]['name']} / {album_info['name']}", description="使用できる楽曲はありませんでした。")
        await ctx.send(embed=embed)
