from core import QueueManager
from discord_lambda import Embedding, CommandRegistry, Interaction, CommandArg

def help(inter: Interaction, command: str = "help") -> None:
  embed = None
  # Send the help menu if requested
  if command == "help":
    embed = Embedding("Kali 8s Bot", "Use `/help <command>` to gain more information about that command :smiley:", color=0x00FF00)
    embed.add_field("Commands",
                    "`queue`\nCreate an 8s queue.\n",
                    False)
    embed.add_field("About",
                    "This bot was developed by kumar.\n" \
                    "Please visit the [GitHub](https://github.com/novayammygang/discord-lambda-8s) to submit ideas or bugs.\n",
                    False)
  if command == "queue":
    embed = QueueManager.create_queue()

  inter.send_response(embeds=[embed])


def setup(registry: CommandRegistry):
  registry.register_cmd(func=help, name="help", desc="Provides information on how to use the bot.", options=[
    CommandArg("command", "the command to get help with", CommandArg.Types.STRING, required=False, choices=[
      CommandArg.Choice("help"),
      CommandArg.Choice("queue"),
    ])
  ])



