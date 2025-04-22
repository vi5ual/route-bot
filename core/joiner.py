# core/joiner.py
from telethon.errors.rpcerrorlist import UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest

async def join_channels(client, channels):
    for ch in channels:
        try:
            await client(JoinChannelRequest(ch))
            print(f"[JOIN] Joined: {ch}")
        except UserAlreadyParticipantError:
            print(f"[JOIN] Already joined: {ch}")
        except Exception as e:
            print(f"[JOIN] Failed to join {ch}: {e}")
