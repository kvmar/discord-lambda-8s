from discord_lambda import Embedding, CommandRegistry, Interaction

def help(inter: Interaction, command: str = "help") -> None:
  embed = None
  # Send the help menu if requested
  if command == "help":
    embed = Embedding("Kali 8s Bot", "Use `/help <command>` to gain more information about that command :smiley:", color=0x00FF00)
    embed.add_field("Commands",
                    "`queue`\nCreate an 8s queue.\n",
                    False)
    embed.add_field("About",
                    "This bot was developed by kumar.\n"
                    "Please visit the [GitHub](https://github.com/novayammygang/discord-lambda-8s) to submit ideas or bugs.\n",
                    False)

  inter.send_response(embeds=[embed], ephemeral=False)


def setup(registry: CommandRegistry):
  registry.register_cmd(func=help, name="help", desc="Provides information on how to use the bot.", options=[])



