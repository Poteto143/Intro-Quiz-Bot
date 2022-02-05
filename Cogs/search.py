import discord
from discord.ext import commands
import re
import spotipy

class Search(commands.Cog):
    def __init__(self, spotify: spotipy.Spotify):
        self.spotify = spotify
        super().__init__()

    def makeTracklist(self, data):
        num = 0
        tracklist = []
        for i in data:
            if "track" in i.keys():
                if i["track"]["preview_url"]:
                    num += 1
                    tracklist.append(discord.utils.escape_markdown(f"{num}: {i['track']['name']} / {i['track']['artists'][0]['name']}"))
            else:
                if i["preview_url"]:
                    num += 1
                    tracklist.append(discord.utils.escape_markdown(f"{num}: {i['name']} / {i['artists'][0]['name']}"))

        if tracklist:
            return "\n".join(tracklist)
        else:
            return "使用できる楽曲は見つかりませんでした。"


    @commands.command()
    async def search(self, ctx, *, arg: str=""):
        m = re.match(r"https://open.spotify.com/playlist/.{1,22}", arg)
        if m:
            q = m.group(0).split("https://open.spotify.com/playlist/")[1]
            try:
                results = self.spotify.playlist(q)
            except spotipy.exceptions.SpotifyException:
                await ctx.send("プレイリストが見つかりませんでした。\nURLを確かめて再度お試し下さい。")
                return
            playlistinfo = results
            results = self.spotify.playlist_tracks(q, market="JP")
            embed = discord.Embed(
                title=f"プレイリストの楽曲: {playlistinfo['name']}(作成者:{playlistinfo['owner']['display_name']})", description=self.makeTracklist(results["items"]))
            await ctx.send(embed=embed)
            return

        m = re.match(r"https://open.spotify.com/album/.{22}", arg)
        if m:
            q = m.group(0).split("https://open.spotify.com/album/")[1]
            try:
                results = self.spotify.album(q)
            except spotipy.exceptions.SpotifyException:
                await ctx.send("アルバムが見つかりませんでした。\nURLを確かめて再度お試し下さい。")
                return
            embed = discord.Embed(
                title=f"アルバムの楽曲: {results['artists'][0]['name']} / {results['name']}", description=self.makeTracklist(results["tracks"]["items"]))
            await ctx.send(embed=embed)
            return

        if arg:
            artist = self.spotify.search(
                q=f"artist:{arg}", type="artist", limit=1, market="JP")
            if len(artist["artists"]["items"]) == 0:
                await ctx.send("アーティストが見つかりませんでした。\nキーワードを確かめて再度お試し下さい。")
                return
            artistname = artist["artists"]["items"][0]["name"]
            tracks = self.spotify.search(
                q=f"artist: {artistname}", limit=50, type="track", market="JP")

            embed = discord.Embed(
                title=f"アーティストの楽曲: {artistname}", description=self.makeTracklist(tracks["tracks"]["items"]))
            await ctx.send(embed=embed)
            return

        tracks = self.spotify.playlist("37i9dQZEVXbKXQ4mDTEBXq", market="JP")
        result = tracks["tracks"]["items"]
        embed = discord.Embed(title="現在のトラックリスト: 日本で人気の曲",
                            description=self.makeTracklist(result))
        await ctx.send(embed=embed)