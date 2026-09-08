import discord

OWNER_PERMS = discord.PermissionOverwrite(
    view_channel=True,
    connect=True,
    speak=True,
    stream=True,
    use_voice_activation=True,
    use_embedded_activities=True,
    mute_members=True,
    deafen_members=True,
    move_members=True,
    manage_channels=True,
    manage_permissions=True,
)
