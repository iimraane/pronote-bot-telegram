import json
import os
import asyncio
import time
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

BOT_TOKEN = "7876431851:AAEUeICZo-Fqdnd0IVVdiA7zAfzNxL2NIAA"
USERS_FILE = "users.json"
RAPPELS_FILE = "rappels.json"
EDT_CACHE_FILE = "edt_cache.json"
USERNAME, PASSWORD, HEURE, CONFIRM_RESET, LOGIN_USERNAME, LOGIN_PASSWORD = range(6)
rappels = {}

# ---------- Utilitaires JSON ----------
def load_json(path):
    return json.load(open(path)) if os.path.exists(path) else {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# ---------- Connexion Pronote ----------
def get_schedule_data(username, password):
    driver = webdriver.Chrome()
    driver.get("https://keycloak.moncollege-valdoise.fr/realms/CD95/protocol/cas/login?service=https:%2F%2F0950937C.index-education.net%2Fpronote%2Feleve.html")
    time.sleep(2)
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "kc-login").click()
    time.sleep(5)

    cours_list = driver.find_elements(By.CSS_SELECTOR, 'ul.liste-cours > li.flex-contain')
    premiere_matiere = heure_debut = derniere_heure = None

    for bloc in cours_list:
        try:
            matiere = bloc.find_element(By.CSS_SELECTOR, ".libelle-cours").text
            heures = bloc.find_elements(By.CSS_SELECTOR, ".container-heures > div")
            debut = heures[0].text if heures else None
            if not debut:
                continue
            if not premiere_matiere and "Pas de cours" not in matiere and "E-sport" not in matiere:
                premiere_matiere, heure_debut = matiere, debut
            if "E-sport" not in matiere:
                derniere_heure = debut
        except:
            continue

    driver.quit()
    return (heure_debut, premiere_matiere, derniere_heure) if all([heure_debut, premiere_matiere, derniere_heure]) else None

# ---------- Cache EDT ----------
def get_edt_cached(chat_id, username, password):
    data = get_schedule_data(username, password)
    if data:
        return {
            "heure_debut": data[0],
            "premier_cours": data[1],
            "heure_fin": data[2]
        }
    return None


# ---------- Commandes ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bienvenue sur le bot Pronote !\n\n"
        "📅 /edt – Voir ton emploi du temps de demain\n"
        "⏰ /rappel – Programmer un rappel automatique chaque jour\n"
        "🔁 /login – Definir tes identifiants\n"
        "🗑️ /reset – Supprimer toutes tes données\n"
        "ℹ️ /aide – Aide et commandes disponibles\n\n"
        "🆔 Tu ne donnes ton mot de passe qu'une seule fois !"
    )

async def edt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    users = load_json(USERS_FILE)
    
    if chat_id not in users:
        await update.message.reply_text("❌ Utilise /rappel pour t'enregistrer d'abord.")
        return

    # ⏳ Message de chargement
    loading_msg = await update.message.reply_text("🔄 Récupération de l'emploi du temps, un instant...")

    user = users[chat_id]
    data = get_edt_cached(chat_id, user['username'], user['password'])

    # ❌ Si erreur
    if not data:
        await context.bot.delete_message(chat_id=chat_id, message_id=loading_msg.message_id)
        await update.message.reply_text("⚠️ Échec de récupération de l'emploi du temps.")
        return

    # ✅ Si OK
    await context.bot.delete_message(chat_id=chat_id, message_id=loading_msg.message_id)
    msg = f"📅 Demain :\n🕗 Début : *{data['heure_debut']}*\n📘 Cours : *{data['premier_cours']}*"
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")


# ---------- Commande /rappel ----------
async def commencer_rappel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏰ À quelle heure veux-tu recevoir ton rappel ? (Format HH:MM)")
    return HEURE

async def enregistrer_heure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    heure = update.message.text.strip()
    if not re.match(r'^\d{2}:\d{2}$', heure):
        await update.message.reply_text("⚠️ Format invalide. Exemple : 07:45")
        return HEURE
    context.user_data["heure"] = heure

async def finaliser_rappel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    password = update.message.text.strip()
    users = load_json(USERS_FILE)
    users[chat_id] = {
        "username": context.user_data["username"],
        "password": password
    }
    save_json(USERS_FILE, users)
    rappels_data = load_json(RAPPELS_FILE)
    rappels_data[chat_id] = context.user_data["heure"]
    save_json(RAPPELS_FILE, rappels_data)
    planifier_rappel(chat_id, context.user_data["heure"], context.bot)
    await update.message.reply_text(f"✅ Rappel programmé chaque jour à {context.user_data['heure']} !")
    return ConversationHandler.END

# ---------- Commande /login ----------
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔁 Entrez votre nom d'utilisateur Pronote :")
    return LOGIN_USERNAME

async def login_get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_username"] = update.message.text.strip()
    await update.message.reply_text("🔐 Entrez maintenant votre mot de passe Pronote :")
    return LOGIN_PASSWORD

async def login_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    password = update.message.text.strip()
    await update.message.delete()
    users = load_json(USERS_FILE)
    users[chat_id] = {
        "username": context.user_data["new_username"],
        "password": password
    }
    save_json(USERS_FILE, users)
    await update.message.reply_text("✅ Identifiants enregistrés avec succès !")
    return ConversationHandler.END

# ---------- Commande /reset ----------
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ Es-tu sûr de vouloir supprimer toutes tes données ? (oui / non)")
    return CONFIRM_RESET

async def confirm_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if update.message.text.lower() in ["oui", "o", "yes", "y"]:
        for file in [USERS_FILE, RAPPELS_FILE, EDT_CACHE_FILE]:
            data = load_json(file)
            if chat_id in data:
                del data[chat_id]
                save_json(file, data)
        await update.message.reply_text("✅ Toutes tes données ont été supprimées. Tu peux recommencer avec /start.")
    else:
        await update.message.reply_text("❎ Suppression annulée.")
    return ConversationHandler.END

# ---------- Rappel automatique ----------
def planifier_rappel(chat_id, heure_str, bot):
    heures, minutes = map(int, heure_str.split(":"))
    now = datetime.now()
    target = now.replace(hour=heures, minute=minutes, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    delta = (target - now).total_seconds()

    async def boucle():
        await asyncio.sleep(delta)
        while True:
            users = load_json(USERS_FILE)
            if str(chat_id) in users:
                user = users[str(chat_id)]
                data = get_edt_cached(str(chat_id), user["username"], user["password"])
                if data:
                    msg1 = f"📅 Rappel pour demain :\n🕗 Début : *{data['heure_debut']}*\n📘 Cours : *{data['premier_cours']}*"
                    await bot.send_message(chat_id=chat_id, text=msg1, parse_mode="Markdown")
            await asyncio.sleep(86400)

    rappels[chat_id] = asyncio.create_task(boucle())

# ---------- Aide ----------
async def aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Commandes :\n/start – Introduction\n/edt – Emploi du temps\n/rappel – Programmer un rappel\n/login – Modifier ses identifiants\n/reset – Supprimer toutes tes données\n/aide – Cette aide",
        parse_mode="Markdown")

# ---------- Lancement du Bot ----------
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_rappel = ConversationHandler(
        entry_points=[CommandHandler("rappel", commencer_rappel)],
        states={
            HEURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enregistrer_heure)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, finaliser_rappel)],
        },
        fallbacks=[]
    )

    login_conv = ConversationHandler(
        entry_points=[CommandHandler("login", login)],
        states={
            LOGIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_get_password)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_save)],
        },
        fallbacks=[]
    )

    reset_conv = ConversationHandler(
        entry_points=[CommandHandler("reset", reset)],
        states={
            CONFIRM_RESET: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_reset)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("edt", edt))
    app.add_handler(CommandHandler("aide", aide))
    app.add_handler(conv_rappel)
    app.add_handler(login_conv)
    app.add_handler(reset_conv)

    print("🤖 Bot lancé")
    app.run_polling()
