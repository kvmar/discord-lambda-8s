from discord_lambda import Embedding, CommandRegistry, Interaction, CommandArg

def help(inter: Interaction, command: str = "help") -> None:
  embed = None
  # Send the help menu if requested
  if command == "help":
    embed = Embedding("ACE Stock Bot", "Use `/help <command>` to gain more information about that command :smiley:", color=0x00FF00)
    embed.add_field("Commands",
                    "`sentiment`\nPerforms sentiment data collection and analysis.\n",
                    False)
    embed.add_field("About",
                    "This bot was developed by UF ACE.\n" \
                    "Please visit the [GitHub](https://github.com/UF-ACE/stock-prediction) to submit ideas or bugs.\n",
                    False)
  inter.send_response(embeds=[embed])


def setup(registry: CommandRegistry):
  registry.register_cmd(func=help, name="help", desc="Provides information on how to use the bot.", options=[
    CommandArg("command", "the command to get help with", CommandArg.Types.STRING, required=False, choices=[
      CommandArg.Choice("help"),
    ])
  ])



