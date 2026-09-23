import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import json
import os

# Configuration des intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

# Création du bot
bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIGURATION DU SERVEUR DE DESTINATION ---
SERVEUR_CIBLE_ID = 1468679807192666154  # <-- Remplace par l'ID du serveur TITOK
SALON_CIBLE_ID = 1552315195538538558    # <-- Remplace par l'ID du salon de TITOK

# --- FICHIERS DE SAUVEGARDE ---
INVITES_FILE = 'invites_data.json'
MESSAGES_FILE = 'messages_tracker.json'
invites_cache = {}

def load_json(file):
    if not os.path.exists(file):
        return {}
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

# --- CLASSE POUR LE BOUTON DE COPIE ---
class CopyView(discord.ui.View):
    def __init__(self, texte_copiable, embed):
        super().__init__(timeout=120)
        self.texte_copiable = texte_copiable
        self.embed = embed

    @discord.ui.button(label="Copier la fiche", style=discord.ButtonStyle.primary, emoji="📋")
    async def copy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.user.send(embed=self.embed)
            await interaction.user.send(f"Voici la fiche copiable pour ta recherche :\n```\n{self.texte_copiable}\n```")
            await interaction.response.send_message("✅ Je t'ai envoyé la fiche en message privé !", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Je ne peux pas t'envoyer de message privé. Vérifie tes paramètres.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    for guild in bot.guilds:
        try:
            invites_cache[guild.id] = await guild.invites()
        except:
            invites_cache[guild.id] = []
    try:
        synced = await bot.tree.sync()
        print(f"Commandes Slash synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur de synchronisation : {e}")

@bot.event
async def on_member_join(member):
    guild = member.guild
    old_invites = invites_cache.get(guild.id, [])
    try:
        new_invites = await guild.invites()
    except:
        return

    used_invite = None
    for new_inv in new_invites:
        for old_inv in old_invites:
            if new_inv.code == old_inv.code and new_inv.uses > old_inv.uses:
                used_invite = new_inv
                break
        if used_invite:
            break

    if used_invite and used_invite.inviter:
        data = load_json(INVITES_FILE)
        data[str(member.id)] = used_invite.inviter.id
        save_json(INVITES_FILE, data)
    invites_cache[guild.id] = new_invites

# --- LA COMMANDE SLASH ---
@bot.tree.command(name="lookup", description="Affiche le profil d'un utilisateur (mention ou ID)")
@app_commands.describe(utilisateur="Mentionne l'utilisateur ou colle son ID")
async def lookup(interaction: discord.Interaction, utilisateur: discord.User):
    await interaction.response.defer()

    try:
        user = await bot.fetch_user(utilisateur.id)
    except Exception as e:
        return await interaction.followup.send(f"❌ Impossible de trouver cet utilisateur : {e}")

    member = interaction.guild.get_member(user.id) if interaction.guild else None

    # --- RÉCUPÉRATION DE L'INVITEUR ---
    invites_data = load_json(INVITES_FILE)
    inviter_id = invites_data.get(str(user.id))
    invite_info = "Inconnu (le bot n'était pas là lors de son arrivée)"
    
    if inviter_id:
        try:
            inviter = await bot.fetch_user(int(inviter_id))
            invite_info = f"{inviter.mention} (`{inviter.id}`)"
        except:
            invite_info = f"ID Inconnu (`{inviter_id}`)"

    # --- CRÉATION DE L'EMBED ---
    couleur = user.accent_color.value if user.accent_color else 0x2b2d31
    embed = discord.Embed(title=f"👤 Profil de {user.display_name}", color=couleur)
    embed.description = f"**Mention :** {user.mention}\n🔗 Lien du profil : <https://discord.com/users/{user.id}>"

    if user.banner:
        embed.set_image(url=user.banner.with_size(1024).url)
    else:
        embed.set_image(url=user.display_avatar.with_size(1024).url)
        
    embed.set_thumbnail(url=user.display_avatar.url)

    embed.add_field(name="🆔 User ID", value=f"`{user.id}`", inline=False)
    embed.add_field(name="👤 Pseudo", value=user.name, inline=True)
    embed.add_field(name="✨ Nom d'affichage", value=user.display_name, inline=True)
    embed.add_field(name="🎭 Type", value="👤 Utilisateur", inline=True)
    
    date_creation = user.created_at.strftime("%d/%m/%Y à %H:%M")
    embed.add_field(name="📅 Compte créé le", value=f"{date_creation}", inline=True)
    embed.add_field(name="🏆 Badges", value="Aucun badge public", inline=True)

    # --- GESTION PRÉCISE DU STATUT SERVEUR ---
    if member:
        date_arrivee = member.joined_at.strftime("%d/%m/%Y à %H:%M") if member.joined_at else "Inconnue"
        roles_list = [role.mention for role in member.roles if role.name != "@everyone"]
        roles = ", ".join(roles_list) if roles_list else "Aucun"
        
        statut_map = {"online": "🟢 En ligne", "offline": "⚫ Hors ligne", "idle": "🌙 Inactif", "dnd": "⛔ Ne pas déranger"}
        statut = statut_map.get(str(member.status), "⚫ Hors ligne")
        
        activite = "Aucune"
        if member.activities:
            for act in member.activities:
                if isinstance(act, discord.Spotify):
                    activite = f"🎵 Écoute **{act.title}** de {act.artist}"
                    break
                elif act.type == discord.ActivityType.playing:
                    activite = f"🎮 Joue à **{act.name}**"
                    break

        embed.add_field(name="\u200b", value="**📋 Infos serveur**", inline=False)
        embed.add_field(name="📥 A rejoint le serveur", value=date_arrivee, inline=True)
        embed.add_field(name="📡 Statut", value=statut, inline=True)
        embed.add_field(name="🎭 Rôles", value=roles, inline=True)
        embed.add_field(name="🎮 Activité", value=activite, inline=True)
        embed.add_field(name="📨 Invité par", value=invite_info, inline=True)
        
        texte_copiable = f"""👤 Profil de {user.display_name}
Mention : {user.mention}
🆔 User ID
{user.id}
👤 Pseudo
{user.name}
✨ Nom d'affichage
{user.display_name}
📅 Compte créé le
{date_creation}

📋 Infos serveur
📥 A rejoint le serveur
{date_arrivee}
🎭 Rôles ({len(roles_list)})
{roles}
📡 Statut
{statut}
🎮 Activité
{activite}
📨 Invité par
{invite_info}"""
    else:
        statut_serveur = "❓ Statut inconnu"
        try:
            await interaction.guild.fetch_ban(user)
            statut_serveur = "🔨 **Banni du serveur**"
        except discord.NotFound:
            statut_serveur = "🚪 **A quitté le serveur**"
        except discord.Forbidden:
            statut_serveur = "🚪 A quitté le serveur (ou banni, permissions insuffisantes)"

        embed.add_field(name="\u200b", value="**⚠️ Statut serveur**", inline=False)
        embed.add_field(name="📥 A rejoint le serveur", value="❌ N'est plus sur le serveur", inline=False)
        embed.add_field(name="🚨 Raison", value=statut_serveur, inline=True)
        embed.add_field(name="📨 Invité par", value=invite_info, inline=True)
        
        texte_copiable = f"""👤 Profil de {user.display_name}
Mention : {user.mention}
🆔 User ID
{user.id}
👤 Pseudo
{user.name}
✨ Nom d'affichage
{user.display_name}
📅 Compte créé le
{date_creation}

⚠️ Statut serveur
📥 A rejoint le serveur
❌ N'est plus sur le serveur
🚨 Raison
{statut_serveur}
📨 Invité par
{invite_info}"""

    embed.set_footer(text=f"Recherché par {interaction.user.name} • {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    texte_copiable += f"\n\n🌙 Recherché par {interaction.user.name} • {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    texte_copiable += f"\n🔗 Lien du profil : <https://discord.com/users/{user.id}>"

    # =========================================================================
    # 1. GESTION SUR LE SERVEUR ACTUEL (LA CinéClub)
    # =========================================================================
    messages_data = load_json(MESSAGES_FILE)
    user_key = str(user.id)
    
    # On crée une clé unique pour le serveur actuel
    current_guild_key = f"guild_{interaction.guild.id}"
    
    # Suppression des anciens messages sur LA CinéClub
    if current_guild_key in messages_data and user_key in messages_data[current_guild_key]:
        for msg_id in messages_data[current_guild_key][user_key]:
            try:
                old_msg = await interaction.channel.fetch_message(msg_id)
                await old_msg.delete()
            except:
                pass # Le message a déjà été supprimé ou est introuvable
                
    # Envoi de la nouvelle fiche
    view = CopyView(texte_copiable, embed)
    msg1_main = await interaction.followup.send(embed=embed, view=view)
    msg2_main = await interaction.followup.send(f"📋 **Fiche copiable :**\n```\n{texte_copiable}\n```")
    
    # Sauvegarde des IDs pour LA CinéClub
    if current_guild_key not in messages_data:
        messages_data[current_guild_key] = {}
    messages_data[current_guild_key][user_key] = [msg1_main.id, msg2_main.id]
    
    # =========================================================================
    # 2. GESTION SUR LE SERVEUR DE DESTINATION (TITOK)
    # =========================================================================
    try:
        target_guild = bot.get_guild(SERVEUR_CIBLE_ID)
        target_channel = target_guild.get_channel(SALON_CIBLE_ID) if target_guild else None
        
        if target_channel:
            target_guild_key = f"guild_{target_guild.id}"
            
            # Suppression des anciens messages sur TITOK
            if target_guild_key in messages_data and user_key in messages_data[target_guild_key]:
                for msg_id in messages_data[target_guild_key][user_key]:
                    try:
                        old_msg = await target_channel.fetch_message(msg_id)
                        await old_msg.delete()
                    except:
                        pass
            
            # Envoi de la nouvelle fiche sur TITOK
            msg1_titok = await target_channel.send(embed=embed)
            msg2_titok = await target_channel.send(f"📋 **Fiche copiable :**\n```\n{texte_copiable}\n```")
            
            # Sauvegarde des IDs pour TITOK
            if target_guild_key not in messages_data:
                messages_data[target_guild_key] = {}
            messages_data[target_guild_key][user_key] = [msg1_titok.id, msg2_titok.id]
            
    except Exception as e:
        print(f"Erreur lors de l'envoi vers TITOK : {e}")

    # On sauvegarde le fichier JSON une seule fois à la fin
    save_json(MESSAGES_FILE, messages_data)

# --- LANCE LE BOT ---
import os
bot.run(os.getenv('DISCORD_TOKEN'))