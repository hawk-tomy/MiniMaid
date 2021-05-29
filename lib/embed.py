from typing import TYPE_CHECKING, List

import discord
from discord import Embed, Colour

from lib.context import Context
from lib.database.models import Poll, UserVoicePreference, GuildVoicePreference, VoiceDictionary

if TYPE_CHECKING:
    from bot import MiniMaid
MESSAGE_URL_BASE = "https://discord.com/channels/{0}/{1}/{2}"
SYNTAX_MESSAGE = """
構文: `{prefix}poll [hidden] <投票のタイトル> [[絵文字 選択肢] [絵文字 選択肢]...]`
タイトルの前にhiddenと入力すると投票した瞬間にリアクションが消え投票を隠すことができます。
次に、投票のタイトルを入れてください。
その後に、投票の選択肢を20個までスペースを開けて入力してください。
選択肢と絵文字を交互に入力した場合、それぞれの選択肢に絵文字が反映されます。
絵文字を省略し選択肢のみを入力した場合、AからTまでの絵文字が代わりに使用されます。
両方省略した場合 \U00002b55️ \U0000274c の投票になります。
絵文字のみを入力した場合、選択肢も絵文字になります。

```
example:
    {prefix}poll 好きな果物 りんご みかん いちご

    {prefix}poll hidden 推しVTuber がうるぐら 委員長 船長

    {prefix}poll いちごは果物か？

    {prefix}poll ねこ 😸 😻 😹
```
"""
LIMITED_MESSAGE = """
構文: `{prefix}poll limited <投票可能最大数> [hidden] <投票のタイトル> [[絵文字 選択肢] [絵文字 選択肢]...]`
投票できる個数を制限した投票を作成します。投票最大可能数までの個数の選択肢に投票できます。
後の構文は基本的な構文と同じです。
```
example:
    poll limited 1 どのチームが優勝するか 楽天 巨人 広島

    poll limited 2 hidden 緯度が日本より上の国の２つはどれか？ 🇮🇹 イタリア 🇬🇧 イギリス 🇩🇪 ドイツ 🇫🇷 フランス
```
"""
HELP_MESSAGE = """
[コマンド一覧](https://github.com/sizumita/MiniMaid/blob/master/docs/Commands.md)
"""


def help_embed() -> Embed:
    return Embed(title="MiniMaid Help", description=HELP_MESSAGE, colour=Colour.blue())


def make_poll_help_embed(ctx: Context) -> Embed:
    """
    投票機能の説明のEmbedを生成します。

    :param ctx: Context
    :return: 生成したEmbed
    """
    embed = Embed(
        title="投票機能の使い方",
        colour=Colour.teal()
    )
    embed.add_field(
        name="投票の作成: 基本的な構文",
        value=SYNTAX_MESSAGE.format(prefix=ctx.prefix),
        inline=False
    )
    embed.add_field(
        name="投票の作成: 投票数を制限する",
        value=LIMITED_MESSAGE.format(prefix=ctx.prefix),
        inline=False
    )
    embed.add_field(
        name="投票の終了",
        value=f"`{ctx.prefix}poll end <投票ID>`\n投票を終了します。これ以降のリアクションの変更は無視されます。"
    )
    embed.add_field(
        name="投票の集計",
        value=f"`{ctx.prefix}poll result <投票ID>`\n投票の集計をします。投票を終了していた場合、終了時までの投票のみが集計されます。",
        inline=False
    )
    return embed


def make_poll_reserve_embed(ctx: Context) -> Embed:
    """
    投票の作成中のEmbedを生成します。

    :param ctx: Context
    :return: 生成したEmbed
    """
    embed = Embed(
        title="投票を作成中です",
        description="しばらくお待ちください。"
    )
    embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.replace(128, "png"))
    return embed


def make_poll_embed(ctx: Context, poll: Poll) -> Embed:
    """
    投票のEmbedを作成します。

    :param ctx: Context
    :param poll: 生成する投票
    :return: 生成したEmbed
    """
    description = f"{poll.limit}個まで投票できます。\n\n" if poll.limit is not None else ""
    for choice in poll.choices:
        if choice.emoji == choice.value:
            description += f"{choice.emoji}\n"
            continue
        description += f"{choice.emoji} {choice.value}\n"
    description \
        += f"\n\n投票ID: {poll.id}\n結果->`{ctx.prefix}poll result {poll.id}`\n終了->`{ctx.prefix}poll end {poll.id}`\n"
    embed = Embed(
        title=poll.title,
        description=description,
        colour=Colour.blue()
    )
    embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.replace(128, "png"))
    embed.set_footer(
        text="リアクションで投票できます。" + ("匿名投票のため、投票後はリアクションが削除されます。" if poll.hidden else "")
    )
    return embed


def make_poll_result_embed(bot: 'MiniMaid', ctx: Context, poll: Poll, choices: list) -> Embed:
    """
    投票結果のEmbedを生成します。

    :param bot: Botのインスタンス
    :param ctx: Context
    :param poll: 生成する投票
    :param choices: 表示する票数 (選択肢, 個数, パーセント)
    :return: 生成したEmbed
    """
    message_url = MESSAGE_URL_BASE.format(poll.guild_id, poll.channel_id, poll.message_id)
    user = bot.get_user(poll.owner_id)
    embed = Embed(
        description=f"**[{poll.title}]({message_url})**",
        colour=Colour.dark_orange()
    )
    embed.set_author(name=(str(user) if user is not None else str(poll.owner_id)),
                     icon_url=(user.avatar.replace(128, "png") if user is not None else None))
    embed.set_footer(text=f"{ctx.prefix}poll end {poll.id} で投票を終了できます。")

    for choice, count, percent in choices:
        graph = '\U00002b1c' * int(percent // 10)
        embed.add_field(
            name=f"{choice.emoji} {choice.value}  ({count}票)",
            value=f"{graph}  {int(percent)}%",
            inline=False
        )

    return embed


def change_footer(embed: Embed, text: str) -> Embed:
    """
    Embedのfooterを変更します。

    :param embed: 変更するEmbed
    :param text: 変更先の文字
    :return: 生成したEmbed
    """
    embed.set_footer(text=text)
    return embed


def user_voice_preference_embed(ctx: Context, preference: UserVoicePreference) -> Embed:
    """
    音声設定の表示用のEmbedを生成します。

    :param ctx: Context
    :param preference: 表示する設定
    :return: 生成したEmbed
    """
    embed = Embed(
        title=f"{ctx.author}さんのボイス設定",
        colour=Colour.blue()
    )
    embed.add_field(
        name="読み上げ速度",
        value=f"**{preference.speed}**\n\n`{ctx.prefix}pref speed <0.5 以上 2.0 以下>`で設定できます。",
        inline=False
    )
    embed.add_field(
        name="音量",
        value=f"**{preference.volume}**\n\n`{ctx.prefix}pref volume <-20.0以上 0.0 以下>`で設定できます。",
        inline=False
    )
    embed.add_field(
        name="トーン",
        value=f"**{preference.tone}**\n\n`{ctx.prefix}pref tone <-20.0以上 20.0 以下>`で設定できます。",
        inline=False
    )
    embed.add_field(
        name="イントネーション",
        value=f"**{preference.intone}**\n\n`{ctx.prefix}pref tone <0.0以上 4.0 以下>`で設定できます。",
        inline=False
    )
    embed.set_footer(text=f"{ctx.prefix}pref reset で設定をリセットできます。")
    return embed


def yesno(v: bool) -> str:
    """
    真偽値をはいかいいえに変換します。

    :param v: 変換する値
    :return: はい か いいえ
    """
    return "はい" if v else "いいえ"


def guild_voice_preference_embed(ctx: Context, preference: GuildVoicePreference) -> Embed:
    """
    ギルドの設定を表示するEmbedを生成します。

    :param ctx: Context
    :param preference: 表示する設定
    :return: 生成したEmbed
    """
    embed = Embed(
        title=f"{ctx.guild.name}のボイス設定",
        colour=Colour.blue()
    )

    embed.add_field(
        name="名前を読み上げるか",
        value=f"**{yesno(preference.read_name)}**\n\n`{ctx.prefix}gpref name`コマンドで変更できます。",
        inline=False
    )
    embed.add_field(
        name="ニックネームを読み上げるか",
        value=f"**{yesno(preference.read_nick)}**\n\n`{ctx.prefix}gpref nick`コマンドで変更できます。",
        inline=False
    )
    embed.add_field(
        name="Botのメッセージを読み上げるか",
        value=f"**{yesno(preference.read_bot)}**\n\n`{ctx.prefix}gpref bot`コマンドで変更できます。",
        inline=False
    )
    embed.add_field(
        name="ユーザーがボイスチャットに入ったことを通知するか",
        value=f"**{yesno(preference.read_join)}**\n\n`{ctx.prefix}gpref join`コマンドで変更できます。",
        inline=False
    )
    embed.add_field(
        name="ユーザーがボイスチャットから退出したことを通知するか",
        value=f"**{yesno(preference.read_leave)}**\n\n`{ctx.prefix}gpref leave`コマンドで変更できます。",
        inline=False
    )
    embed.add_field(
        name="読み上げ文字数の制限",
        value=f"**{preference.limit}文字**\n\n`{ctx.prefix}gpref limit <文字数>`コマンドで変更できます。"
    )

    return embed


def voice_dictionaries_embed(ctx: Context, dictionaries: List[VoiceDictionary]) -> Embed:
    """
    読み上げの辞書を表示するEmbedを生成します。

    :param ctx: Context
    :param dictionaries: 表示する辞書のリスト
    :return: 生成したEmbed
    """
    embed = Embed(
        title=f"{ctx.guild.name}の読み上げ用辞書一覧",
        description="\n".join([f"{dic.before} : {dic.after}" for dic in dictionaries])[:2000]
    )
    return embed
