import discord.ext.commands
import discord
import logging
import pandas
from io import StringIO
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bot')


BOT_TOKEN = ''
COMMAND_CHANNEL_ID = 
ADMIN_ROLE_ID = 
JAMMER_ROLE_ID = 
STAFF_ROLE_ID = 
DATA_CHANNEL_ID = 
DATA_INITIAL_MESSAGE_ID = 
TEAM_SEARCHER_CHANNEL_ID = 
TEAM_NAME_PREFIX = 'Ekip '

client = discord.ext.commands.Bot(
    command_prefix='!', intents=discord.Intents.all(), help_command=None)

FIELDS = {
    0: "Oyun Tasarımı",
    1: "Programlama",
    2: "2D Sanat",
    3: "Piksel Sanat",
    4: "3D Sanat",
    5: "Ses",
    6: "Müzik",
}


def build_category_name(team_name):
    return f"🥪 {team_name}"


async def create_team(guild, team_name, owner):
    organizer_role = guild.get_role(STAFF_ROLE_ID)
    jammer_role = guild.get_role(JAMMER_ROLE_ID)
    role = await guild.create_role(
        name=team_name,
        permissions=discord.Permissions(),
        colour=discord.Colour.dark_blue(),
        hoist=True,
        mentionable=True,
        reason=f"Create team command by {owner}"
    )

    category_permissions = {
        role: discord.PermissionOverwrite.from_pair(
            discord.Permissions.all_channel(),  # allow
            discord.Permissions()  # deny
        ),
        organizer_role: discord.PermissionOverwrite.from_pair(
            discord.Permissions.all_channel(),  # allow
            discord.Permissions()  # deny
        ),
        jammer_role: discord.PermissionOverwrite.from_pair(
            discord.Permissions(view_channel=True),  # allow
            discord.Permissions()  # deny
        ),
        guild.default_role: discord.PermissionOverwrite.from_pair(
            discord.Permissions(),  # allow
            discord.Permissions(view_channel=True)  # deny
        )
    }

    category = await guild.create_category(
        name=build_category_name(team_name),
        overwrites=category_permissions,
        reason="Team creation"
    )
    await guild.create_text_channel(
        name=team_name,
        category=category,
        reason="Team creation"
    )
    await guild.create_voice_channel(
        name=team_name,
        category=category,
        reason="Team creation"
    )
    await owner.add_roles(role, reason="Create team command")


async def delete_team(team, channel):
    team_category = None
    for category in team.guild.categories:
        if category.name == build_category_name(team.name):
            team_category = category
            break

    if team_category is not None:
        for _channel in team_category.channels:
            await _channel.delete()
        await team_category.delete()

    await team.delete(reason=f"Empty team")
    await channel.send(f"{team.name} başarıyla silindi.")


def get_teams_of(member):
    roles = []
    for role in member.roles:
        if role.name.startswith(TEAM_NAME_PREFIX):
            if member in role.members:
                roles.append(role)
    return roles


def get_all_teams(guild):
    teams = []
    for role in guild.roles:
        if role.name.startswith(TEAM_NAME_PREFIX):
            teams.append(role)
    return teams


def team_exists(guild, name):
    return any([role.name.casefold() == name.casefold() for role in guild.roles])


async def check_command_context(context):
    if context.channel.id != COMMAND_CHANNEL_ID:
        await respond(context.channel, context.author, f"Lütfen <#{str(COMMAND_CHANNEL_ID)}> kanalı üzerinden komut veriniz.")
        return False
    return True


async def is_admin(context):
    admin_role = context.guild.get_role(ADMIN_ROLE_ID)
    return True if admin_role in context.author.roles else False


async def store_data(user, text):
    await delete_data(user)
    data_channel = client.get_channel(DATA_CHANNEL_ID)
    # Add entry to initial message
    initial_message = await data_channel.fetch_message(DATA_INITIAL_MESSAGE_ID)
    old_content = initial_message.content
    # new data entry format is 'user_id;message_id;embed_message_id&'
    message = await data_channel.send(f"{user.id}&{text}")
    embed_msg = await create_searcher_embed(user, text)
    await initial_message.edit(content=(old_content + str(user.id) + ";" + str(message.id) + ";" + str(embed_msg.id) + "&"))
    return embed_msg


async def delete_data(user):
    data_channel = client.get_channel(DATA_CHANNEL_ID)
    searcher_embed_channel = client.get_channel(TEAM_SEARCHER_CHANNEL_ID)
    initial_message = await data_channel.fetch_message(DATA_INITIAL_MESSAGE_ID)
    # Finds where the users id and corresponding message id is
    index = initial_message.content.find(str(user.id))
    if index == -1:
        return -1
    _, msg_id, embed_msg_id = initial_message.content[index:].split("&")[
        0].split(";")
    new_content = initial_message.content.replace(
        (str(user.id) + ";" + str(msg_id) + ";" + str(embed_msg_id) + "&"), "")
    await initial_message.edit(content=new_content)
    message = await data_channel.fetch_message(msg_id)
    await message.delete()
    embed_message = await searcher_embed_channel.fetch_message(embed_msg_id)
    await embed_message.delete()
    return


async def create_searcher_embed(user, text):
    searcher_embed_channel = client.get_channel(TEAM_SEARCHER_CHANNEL_ID)
    roles, note = text.split("&")
    user_tag = user.name + "#" + user.discriminator
    sub_embed = discord.Embed(title=(user_tag if user.name == user.display_name else (user.display_name + " • " + user_tag)), color=discord.Color.random(), description=(
        (note.replace("Not:", "**Notu:**\n") if note != "Not: [Yok]" else "")))
    sub_embed.add_field(name="Alanları: ", value=roles)
    sub_embed.set_thumbnail(url=user.avatar.url)
    embed_msg = await searcher_embed_channel.send(embed=sub_embed)
    return embed_msg


def ignore_context(context):
    return context.guild is None


async def respond(channel, user, message):
    await channel.send(f"<@!{user.id}> {message}")


@client.event
async def on_ready():
    logger.info("Logged in as %s (%s)", client.user.name, client.user.id)


@client.command(aliases=['admin', 'admin_yardım', 'admin_destek'])
async def admin_help(context):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)
    if ignore_context(context):
        return
    if not await is_admin(context):
        await _respond('Bu komutu çağırma yetkiniz yok!')
        return
    embed = discord.Embed(title="Yönetici Özel Komut Listesi",
                          color=discord.Color.dark_gold())
    embed.add_field(name="`!üyelere_rol_ver <rol_id'si> <üye_1 ismi> .... <üye_n ismi>`",
                    value="İsmi verilen her üyeye belirtilen rolü verir.", inline=False)
    embed.add_field(name="`!jamination_başlat`",
                    value="Jamination 7 başlangıcını belirten bir embed mesaj paylaşır.", inline=False)
    embed.add_field(name="`!ekipleşme_kanallarını_başlat`",
                    value=" Embedlerin atıldığı kanala da başlangıç embedini atar; sonrasında verilerin tutulduğu kanala ilk mesajı atar, bu mesajın id'sinin `DATA_INITIAL_MESSAGE_ID` değişkenine atanıp botun tekrar başlatılması gerekmektedir.", inline=False)
    embed.add_field(name="`!ekip_ve_üye_listesi`",
                    value="Bütün ekipleri ve ekiplerdeki üyelerin csv dosyasını verir. Toplam ekip ve katılımcı sayısını ve en kalabalık ekipteki üye sayısını verir.", inline=False)
    embed.add_field(name="`!sil <@ekip_rolü>`",
                    value="Etiketlenen ekibi siler.", inline=False)
    embed.add_field(name="`!benim_mensubu_olduklarım_da_dahil_bütün_ekipleri_imha_et`",
                    value="Oluşturulan bütün ekipleri siler.", inline=False)
    await context.channel.send(embed=embed)

@client.command('üyelere_rol_ver')
async def batch_add_role(ctx):
    async def _respond(msg):
        await respond(ctx.channel, ctx.message.author, msg)
    if not await is_admin(ctx):
        await _respond('Bu komutu çağırma yetkiniz yok!')
        return
    
    msg = ctx.message.clean_content 
    msg_split = msg.split() 

    if len(msg_split) < 3:
        await _respond("Bir rol id'si ve kullanıcı ismi listesi vermelisin.")
        return

    role_id = int(msg_split[1])
    members_specified = msg_split[2:]

    role = ctx.guild.get_role(role_id)

    if role is None:
        await _respond("Böyle bir rol bulunmamakta.")
        return

    for member_name in members_specified:
        member_name = member_name.strip()
        member = discord.utils.get(ctx.guild.members, name=member_name)
        if member:
            if role in member.roles:
                await ctx.channel.send(f"'{role.name}' rolü '{member.display_name}' kullanıcısında halihazırda mevcut.")
                continue
            await member.add_roles(role, reason=f"Added by {ctx.message.author}")
            await ctx.channel.send(f"'{role.name}' rolü '{member.display_name}' kullanıcısına başarıyla verildi.")
        else:
            await _respond(f"'{member_name}' isminde biri yok!")
    await ctx.channel.send("Komut çalıştı.")


@client.command('ekipleşme_kanallarını_başlat')
async def init_data_channel(context):
    if ignore_context(context):
        return
    data_channel = client.get_channel(DATA_CHANNEL_ID)
    embed_channel = client.get_channel(TEAM_SEARCHER_CHANNEL_ID)
    await data_channel.send("&")
    embed = discord.Embed(title="Ekip Arayanlar",
                          color=discord.Color.dark_gold())
    embed.description = 'Bu listede ekip arayan insanların listesini görebilirsiniz. İlgilendikleri alana göre kendilerini ilgili kanaldan etiketleyerek ekibinize dahil edebilirsiniz.'
    embed.set_footer(text='Jamination Ekipleşme Botu')
    embed.set_thumbnail(url=client.user.avatar.url)
    await embed_channel.send(embed=embed)
    await context.channel.send("Bütün kanallar başlatıldı!")

@client.command('ekip_ve_üye_listesi')
async def list_teams_and_members(ctx):
    async def _respond(msg):
        await respond(ctx.channel, ctx.message.author, msg)
    if not await is_admin(ctx):
        await _respond('Bu komutu çağırma yetkiniz yok!')
        return
    
    teams = get_all_teams(ctx.guild)

    team_list = []
    member_count = 0

    for team in teams:
        member_list = []
        member_list.append(f"{team}")
        for member in team.members:
            member_list.append(f"{member}")
            member_count += 1
        team_list.append(member_list)


    max_length = max(len(team) for team in team_list)
    padded_data = [team + [''] * (max_length - len(team)) for team in team_list]
    transposed_data = list(zip(*padded_data))  
    columns = [f'Ekip {i+1}' for i in range(len(team_list))]

    team_list_df = pandas.DataFrame(transposed_data, columns=columns)

    flattened_series = team_list_df.iloc[1:].stack()
    unique_members = flattened_series.nunique()

    csv_data = StringIO()
    team_list_df.to_csv(path_or_buf=csv_data, index=False)
    csv_data.seek(0)
    
    await ctx.channel.send(file=discord.File(csv_data, filename='ekip_listesi.csv'))
    await _respond(f"Bütün liste yazdırıldı. Toplamda {len(team_list)} ekip ve {unique_members-1} üye var. En kalabalık ekip {max_length - 1} üye içeriyor.")
    

@client.command('durum')
async def status(context):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)
    if ignore_context(context):
        return
    if not await check_command_context(context):
        return
    members = context.message.mentions

    if len(members) == 0:
        members = [context.message.author]

    for member in members:
        teams = get_teams_of(member)
        status = f"Bulunduğunuz ekipler: {'[Yok]' if teams == [] else ', '.join([team.name for team in teams])}"
        await _respond(status)


@client.command('oluştur')
async def create_team_cmd(context):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)
    if ignore_context(context):
        return

    if not await check_command_context(context):
        return

    owner = context.message.author

    if len(get_teams_of(owner)) >= 7:
        await _respond("Azami ekip sayısına ulaştınız!")
        return

    msg = context.message.clean_content
    msg_split = msg.split(maxsplit=1)

    if len(msg_split) == 1:
        await _respond("Sözdizimi: `!oluştur <ekip_adı>`")
        return
    else:
        name = msg_split[1]

    team_name = TEAM_NAME_PREFIX + name

    if team_exists(context.guild, team_name):
        await _respond(f"Halihazırda {name} adında bir ekip bulunmakta!")
        return

    await create_team(context.guild, team_name, owner)
    await _respond(f"Ekip {name} oluşturuldu!")


@client.command('ekle')
async def add_to_team_cmd(context):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)
    if ignore_context(context):
        return

    if not await check_command_context(context):
        return

    teams = get_teams_of(context.message.author)

    if teams is []:
        await _respond("Herhangi bir ekipte değilsin!")
        return

    members = context.message.mentions

    if len(members) == 0:
        await _respond("Kimseyi etiketlemedin! Sözdizimi: `!ekle @<kullanıcı>`")
        return

    msg = context.message.clean_content
    msg_split = msg.split(maxsplit=2)

    specified_index = 0

    if len(teams) > 1:

        index = 0
        team_list = ''

        for team in teams:
            team_list += team.name + ' ekibinin indeksi: `' + str(index) + '`\n'
            index += 1

        if len(msg_split) == 2:
            await _respond(f"Birden fazla ekibe dahil olduğunuz için eklemek istediğiniz ekibi belirtiniz.\n\n{team_list}\nSözdizimi: `!ekle @<kullanıcı> <ekip_indeksi>`")
            return
        else:
            if msg_split[2].isnumeric() and int(msg_split[2]) < index:
                specified_index = int(msg_split[2])
            else:
                await _respond(f"Geçersiz indeks, lütfen uygun bir ekip indeksi belirtiniz.\n\n{team_list}\Sözdizimi: `!ekle @<kullanıcı> <ekip_indeksi>`")
                return

    specified_team = teams[specified_index]

    for member in members:
        existing_teams = get_teams_of(member)

        if existing_teams == []:
            await member.add_roles(specified_team, reason=f"Added by {context.message.author}")
            await _respond(f"{member.name}, {specified_team.name} ekibine eklendi!")
            return
        elif specified_team in existing_teams:
            await _respond(f"{member.name} zaten {specified_team.name} ekibinde mevcut.")
            return
        else:
            await member.add_roles(specified_team, reason=f"Added by {context.message.author}")
            await _respond(f"{member.name}, {specified_team.name} ekibine eklendi!")


@client.command('ayrıl')
async def leave_team_cmd(context):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)
    if ignore_context(context):
        return
    if not await check_command_context(context):
        return

    user = context.message.author
    teams = get_teams_of(user)

    if teams is []:
        await _respond("Herhangi bir ekipte değilsin!")
        return

    specified_index = 0

    msg = context.message.clean_content
    msg_split = msg.split(maxsplit=1)

    if len(teams) > 1:

        index = 0
        team_list = ''

        for team in teams:
            team_list += team.name + 'ekibinin indeksi: `' + str(index) + '`\n'
            index += 1

        if len(msg_split) == 1:
            await _respond(f"Birden fazla ekibe dahil olduğunuz için ayrılmak istediğiniz ekibi belirtiniz.\n\n{team_list}\nSözdizimi: `!ayrıl <ekip_indeksi>`")
            return
        else:
            if msg_split[1].isnumeric() and int(msg_split[1]) < index:
                specified_index = int(msg_split[1])
            else:
                await _respond(f"Geçersiz indeks, lütfen uygun bir ekip indeksi belirtiniz.\n\n{team_list}\nSözdizimi: `!ayrıl <ekip_indeksi>`")
                return

    specified_team = teams[specified_index]

    await user.remove_roles(specified_team, reason=f"Leave command")
    await _respond(f"{specified_team.name} ekibinden ayrıldınız.")

    if len(specified_team.members) == 0:
        await context.channel.send(f"{specified_team.name} ekibinde kimse kalmadığı için siliniyor...")
        await delete_team(specified_team, context.channel)


@client.command('sil')
async def delete_team_cmd(context):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)
    if ignore_context(context):
        return
    if not await is_admin(context):
        await _respond('Bu komutu çağırma yetkiniz yok!')
        return

    teams = context.message.role_mentions

    if len(teams) == 0:
        await _respond('Herhangi bir ekip etiketlenmedi! Sözdizimi: `!sil @<ekip_rolü>`')
        return

    team = teams[0]

    if not team.name.startswith(TEAM_NAME_PREFIX):
        await _respond('Etiketlenen rol bir ekip rolü değil!')
        return

    await context.channel.send(f"{team.name} ekibi siliniyor...")
    await delete_team(team, context.channel)


@client.command('benim_mensubu_olduklarım_da_dahil_bütün_ekipleri_imha_et')
async def delete_team_all_cmd(context):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)
    if ignore_context(context):
        return
    if not await is_admin(context):
        await _respond('Bu komutu çağırma yetkiniz yok!')
        return

    teams = get_all_teams(context.guild)

    if len(teams) == 0:
        await context.channel.send("Herhangi bir ekip bulunamadı!")
        return

    await context.channel.send(f"{len(teams)} ekip bulundu.")

    for team in teams:
        _msg = await context.channel.send(f"{team.name} ekibi siliniyor")
        await delete_team(team, context.channel)
        await _msg.delete()

    await context.channel.send("Bütün ekipler imha edildi.")


@client.command(aliases=['yardım', 'destek'])
async def help(context):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)

    if ignore_context(context):
        return

    if not await check_command_context(context):
        return

    embed = discord.Embed(title="Komut Listesi",
                          color=discord.Color.dark_gold())
    embed.add_field(
        name="`!durum`", value="Hangi takımlarda bulunduğunuzu söyler.", inline=False)
    embed.add_field(name="`!oluştur <ekip_ismi>`",
                    value="Yeni bir takım oluşturmak için bir takım ismi yazarak bu komutu kullanabilirsiniz.", inline=False)
    embed.add_field(name="`!ekle <@kullanıcı>`",
                    value="Bulunduğunuz takıma arkadaşınızı eklemek için onu etiketleyerek bu komutu yazınız.", inline=False)
    embed.add_field(
        name="`!ayrıl`", value="Bulunduğunuz takımdan ayrılacak olursanız vedalaştıktan sonra kullanmanız için...", inline=False)
    embed.add_field(name="`!ekip_arıyorum <alan_indeksi> ... <alan_indeksi> <\"not\">`",
                    value="Uğraştığınız alanları ve varsa notunuzu belirterek üye arayan ekiplerin sizi bulmasını sağlar.", inline=False)
    embed.add_field(name="`!ekip_buldum`",
                    value="Eğer `!ekip_arıyorum` komutunu kullanarak ekip bulduysanız listeden isminizi çıkartır.", inline=False)
    embed.set_footer(text="Eğer birden fazla takımdaysanız !ekle ve !ayrıl komutları hangi takım ile ilgili aksiyon almak istediğinizi öğrenmek adına size bir liste verip  bir numara isteyecektir,  listeden ekip numaranızı seçerek belirtilen sırada komut verirseniz sıkıntısız çalışacaktır. İyi jamler!")
    await context.send(embed=embed)


@client.command('ekip_buldum')
async def end_searching_team(context):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)
    if ignore_context(context):
        return

    if not await check_command_context(context):
        return

    err_code = await delete_data(context.author)
    if err_code == -1:
        await _respond("Zaten bir ekip arayışı içerisinde değildiniz!")
    else:
        await _respond("Artık bir ekip aramıyorsunuz.")

@client.command('jamination_başlat')
async def send_jamination_embed(context):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)
    if ignore_context(context):
        return
    if not await is_admin(context):
        await _respond('Bu komutu çağırma yetkiniz yok!')
        return
    embed = discord.Embed(title="Jamination 7 Başlangıcı",
                          color=discord.Color.dark_gold())
    embed.set_image(url="https://cdn.discordapp.com/attachments/1035155574804983888/1238240580505440306/baslik.png?ex=663e90e7&is=663d3f67&hm=75880a0561ae33672b9d01e92c623deb4788731614af06384059544db59910a9&")
    await context.channel.send(embed=embed)
    await context.message.delete()

@client.command('ekip_arıyorum')
@discord.ext.commands.cooldown(1, 10, discord.ext.commands.BucketType.guild)
async def searching_for_team(context):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)
    if ignore_context(context):
        return

    if not await check_command_context(context):
        return

    embed = discord.Embed(title="Ekip Arıyorum Komutu",
                          color=discord.Color.dark_gold())
    embed.add_field(name="Sözdizimi",
                    value="!ekip_arıyorum <alan_indeksi> ... <alan_indeksi> <\"not\">", inline=False)
    embed_field_value = ""
    for i in range(len(FIELDS)):
        embed_field_value += FIELDS[i] + " indeksi: " + str(i) + "\n"
    embed.add_field(name="İndeks Listesi",
                    value=embed_field_value, inline=False)
    embed.add_field(
        name="Örnek", value="!ekip_arıyorum 0 1 \"Unity kullanıyorum, programlamanın yanında oyun tasarımı da yapabilirim.\"", inline=False)
    embed.set_footer(text="Eğer birden fazla alan ile uğraşıyorsanız her birinin indeksini boşluk bırakarak yazınız. En az bir alan seçmek zorunludur! Not kısmı isteğe bağlıdır, tırnak içerisinde olmasına dikkat ediniz.")

    msg = context.message.clean_content

    if len(msg.split()) == 1:  # if no arguments
        await context.send(embed=embed)
        return
    # Gets the note if exists

    split_message = msg.split("\"")
    note = split_message[-2].replace("\n",
                                     " ")[:512] if len(split_message) == 3 else None
    indexes = []

    for index in split_message[0].split()[1:]:
        # If arguments are numeric and in the valid range of roles
        if index.isnumeric() and int(index) in range(len(FIELDS)):
            indexes.append(index)
        else:
            embed.title = "HATA: Geçersiz alan indeksi!"
            await context.send(embed=embed)
            return

    if not indexes:  # if empty
        embed.title = "HATA: Herhangi bir alan indeksi belirtmediniz!"
        await context.send(embed=embed)
        return

    roles = []

    indexes = list(set(indexes))  # remove duplicates
    indexes.sort()

    for index in indexes:
        roles.append(FIELDS[int(index)])
    role_names = ", ".join(roles)

    embed_msg = await store_data(context.author, (role_names + "&Not: " + (note if note != None else "[Yok]")))
    await _respond("*Şu roller için takım arıyorsunuz:* **" + role_names + "**\n*Notunuz:* **" + (note if note != None else "[Yok]") + "**" + "\n*Bağlantınız:* " + embed_msg.jump_url)
    return


@client.event
async def on_command_error(context, error):
    async def _respond(msg):
        await respond(context.channel, context.message.author, msg)
    if isinstance(error, discord.ext.commands.CommandOnCooldown):
        await _respond(f"Bu komut güvenlik açısından bekleme süresine sahiptir. `{error.retry_after:.2f}` saniye sonra tekrar deneyiniz.")

client.run(BOT_TOKEN)
