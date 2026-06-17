import os
import threading
from flask import Flask, jsonify, request
from telebot import TeleBot, types
from supabase import create_client, Client

# ==========================================
# CONFIGURACIÓN (Reemplaza con tus datos)
# ==========================================
SUPABASE_URL = "TU_URL_DE_SUPABASE"
SUPABASE_KEY = "TU_CLAVE_ANONIMA_DE_SUPABASE"
BOT_TOKEN = "TU_TOKEN_DEL_BOT_DE_TELEGRAM"
WEBAPP_URL = "https://tu-usuario.github.io/tu-repo" # Tu link de GitHub Pages

bot = TeleBot(BOT_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# ==========================================
# LÓGICA DEL BOT DE TELEGRAM
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "Usuario"
    
    # Manejo de referidos (ej: /start ref_12345)
    referred_by = None
    if len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
        if ref_code.startswith("ref_"):
            referred_by = ref_code.split("_")[1]

    # Registrar o verificar usuario en Supabase
    try:
        # Intenta buscar al usuario primero
        res = supabase.table("users").select("*").eq("telegram_id", user_id).execute()
        if not res.data:
            # Si no existe, lo crea
            supabase.table("users").insert({
                "telegram_id": user_id, 
                "username": username,
                "referred_by": referred_by
            }).execute()
    except Exception as e:
        print(f"Error en base de datos: {e}")

    # Botón para abrir la Mini App en Telegram
    markup = types.InlineKeyboardMarkup()
    web_app_info = types.WebAppInfo(WEBAPP_URL)
    btn_app = types.InlineKeyboardButton(text="⚡ Abrir Minador", web_app=web_app_info)
    markup.add(btn_app)
    
    bot.reply_to(
        message, 
        f"¡Hola {username}! Bienvenido a la nueva era de minería.\n\n"
        f"Toca el botón abajo para abrir la aplicación y empezar a generar GHS.", 
        reply_markup=markup
    )

# ==========================================
# LÓGICA DE LA API (FLASK) PARA EL HTML
# ==========================================

# 1. Obtener datos completos del usuario
@app.route('/api/user/<telegram_id>', methods=['GET'])
def get_user_data(telegram_id):
    res = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
    if res.data:
        return jsonify(res.data[0]), 200
    return jsonify({"error": "Usuario no encontrado"}), 404

# 2. Guardar progreso de minería
@app.route('/api/sync', methods=['POST'])
def sync_balance():
    data = request.json
    tg_id = data.get("telegram_id")
    new_balance = data.get("current_ghs")
    
    # Actualiza el balance directamente en Supabase
    supabase.table("users").update({"ghs_balance": new_balance}).eq("telegram_id", tg_id).execute()
    return jsonify({"status": "Sincronizado"}), 200

# 3. Obtener lista de referidos
@app.route('/api/referrals/<telegram_id>', methods=['GET'])
def get_referrals(telegram_id):
    res = supabase.table("users").select("username").eq("referred_by", telegram_id).execute()
    return jsonify({"referrals": res.data, "count": len(res.data)}), 200

# ==========================================
# EJECUCIÓN SIMULTÁNEA
# ==========================================
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # Inicia el bot de Telegram en un hilo en segundo plano
    threading.Thread(target=run_bot, daemon=True).start()
    # Inicia el servidor de Flask en el hilo principal
    print("Servidor iniciado. Esperando conexiones...")
    app.run(host="0.0.0.0", port=5000)

