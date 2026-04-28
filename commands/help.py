from discord_lambda import Embedding, CommandRegistry, Interaction

def help(inter: Interaction, command: str = "help") -> None:
  embed = None
  if command == "help":
    embed = Embedding("⚡ 8s Bot Help", "Competitive queue management for Discord", color=0x7c3aed)
    embed.add_field("📋 Commands",
                    "`/queue` — Join or create a competitive 8v8 queue\n"
                    "`/leaderboard` — View season rankings and stats",
                    False)
    embed.add_field("🎮 How It Works",
                    "1️⃣ Use `/queue` to join\n"
                    "2️⃣ Get 8 players total\n"
                    "3️⃣ Start match when ready\n"
                    "4️⃣ Report winner\n"
                    "5️⃣ SR updates automatically",
                    False)
    embed.add_field("📖 About",
                    "Developed by kumar • [GitHub](https://github.com/novayammygang/discord-lambda-8s)",
                    False)

  inter.send_response(embeds=[embed], ephemeral=False)


def setup(registry: CommandRegistry):
  registry.register_cmd(func=help, name="help", desc="Provides information on how to use the bot.", options=[])



