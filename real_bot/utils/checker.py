import json
import os

CONFIG_PATH = "real_bot/real_bot/config.json"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

def get_assigned_channel(guild_id):
    config = load_config()
    return config.get(str(guild_id), {}).get("channel_id")

def register_channel(guild_id, channel_id):
    config = load_config()
    if str(guild_id) not in config:
        config[str(guild_id)] = {}
    config[str(guild_id)]["channel_id"] = channel_id
    save_config(config)

def is_valid_channel(ctx):
    assigned_id = get_assigned_channel(ctx.guild.id)
    return str(ctx.channel.id) == str(assigned_id)
