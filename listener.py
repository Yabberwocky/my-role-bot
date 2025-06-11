# listener.py
import asyncio
import websockets
import json
import re
from typing import Dict, Any, Optional
import random

class SelfBotListener:
    """
    Connects to the Discord Gateway as a user to listen for and classify
    specific game announcements in a target channel.
    """

    def __init__(self, token: str, channel_id: str, queue: asyncio.Queue):
        if not token:
            raise ValueError("A valid self-bot token must be provided.")
        self.token = token
        self.target_channel_id = str(channel_id)
        self.queue = queue
        self.ws_connection = None
        self.heartbeat_interval = None
        self.last_sequence = None
        self.session_id = None
        self.resume_gateway_url = None

        rarities_pattern = r"(Unique|Super|Ultra|Mythic|Legendary|Epic|Rare|Uncommon|Common)"
        
        self.patterns = {
            # --- THIS IS THE FIX ---
            # Now accepts "The", "A", or "An" at the beginning of a craft message.
            'petal_craft': re.compile(
                fr"^\s*(?:The|A|An) {rarities_pattern} (.+?) has been (?:forged|crafted)(?: by (\S+))?!$",
                re.IGNORECASE
            ),
            # --- END OF FIX ---
            'mob_spawn_standard': re.compile(
                fr"^\s*A {rarities_pattern} (.+?) has spawned!$",
                re.IGNORECASE
            ),
            'mob_defeat': re.compile(
                fr"^\s*A {rarities_pattern} (.+?) has been defeated by (.+?)!$",
                re.IGNORECASE
            )
        }

        self.special_spawn_messages = {
            "Something mountain-like appears in the distance...": "rock", "A tower of thorns rises from the sands...": "cactus",
            "A big yellow spot shows up in the distance...": "hornet", "You hear lightning strikes coming from a far distance...": "jellyfish",
            "There's a bright light in the horizon...": "firefly", "You sense ominous vibrations coming from a different realm...": "beetle_hel",
            "You hear someone whisper faintly... \"just... one more game...\"": "gambler"
        }

    def _extract_server(self, footer_text: Optional[str]) -> Optional[str]:
        if not footer_text: return None
        match = re.search(r"\((AS|EU|US)\)", footer_text, re.IGNORECASE)
        return match.group(1).upper() if match else None

    def _classify_message(self, embed: Dict[str, Any], event_type: str) -> Optional[Dict[str, Any]]:
        raw_description = embed.get('description', '')
        description = raw_description.replace('\u200b', '').strip()
        
        footer_text = embed.get('footer', {}).get('text')
        message_id = embed.get('_message_id')
        timestamp = embed.get('_timestamp')
        server = self._extract_server(footer_text)

        match = self.patterns['mob_defeat'].match(description)
        if match:
            player_list_str = match.group(3).strip().replace(" and ", ", ")
            players = [p.strip() for p in player_list_str.split(',') if p.strip()]
            return {'category': 'super_defeat', 'rarity': match.group(1), 'mob': match.group(2).strip(), 'players': players, 'server': server, 'original_message_id': message_id, 'timestamp': timestamp}

        match = self.patterns['petal_craft'].match(description)
        if match:
            # Group 1 is now the article ("The"/"A"), Group 2 is the rarity, Group 3 is the petal, Group 4 is the player
            return {'category': 'super_craft', 'rarity': match.group(2), 'petal': match.group(3).strip(), 'player': match.group(4).strip() if match.group(4) else None, 'server': server, 'original_message_id': message_id, 'timestamp': timestamp}
        
        match = self.patterns['mob_spawn_standard'].match(description)
        if match:
            return {'category': 'super_spawn', 'rarity': match.group(1), 'mob': match.group(2).strip(), 'server': server, 'original_message_id': message_id, 'timestamp': timestamp}

        for spawn_text, mob_name in self.special_spawn_messages.items():
            if spawn_text in description:
                return {'category': 'super_spawn', 'rarity': "Super", 'mob': mob_name, 'server': server, 'original_message_id': message_id, 'timestamp': timestamp}

        if event_type == "MESSAGE_UPDATE": return None
        return {'category': 'unclassified', 'text': raw_description, 'original_message_id': message_id, 'timestamp': timestamp, 'footer': footer_text}

    async def _send_heartbeat(self):
        while True:
            await asyncio.sleep(self.heartbeat_interval / 1000)
            if self.ws_connection and self.ws_connection.state == websockets.protocol.State.OPEN:
                payload = {"op": 1, "d": self.last_sequence}
                await self.ws_connection.send(json.dumps(payload))
            else:
                print("[Self-Bot Listener] Heartbeat skipped: WebSocket is not open.")
                break

    async def _handle_event(self, payload: Dict[str, Any]):
        op_code = payload['op']
        if op_code == 10:
            self.heartbeat_interval = payload['d']['heartbeat_interval']
            asyncio.create_task(self._send_heartbeat())
            if self.session_id: await self._send_resume()
            else: await self._send_identify()
        
        elif op_code == 0:
            self.last_sequence = payload.get('s')
            event_type = payload.get('t')
            
            if event_type == 'READY':
                self.session_id = payload['d']['session_id']
                self.resume_gateway_url = payload['d']['resume_gateway_url']
                print(f"[Self-Bot Listener] READY. Session ID: {self.session_id}")
            
            elif event_type in ["MESSAGE_CREATE", "MESSAGE_UPDATE"]:
                event_data = payload.get('d', {})
                if str(event_data.get('channel_id')) == self.target_channel_id and event_data.get('embeds'):
                    for embed in event_data['embeds']:
                        embed['_message_id'] = event_data.get('id')
                        embed['_timestamp'] = event_data.get('timestamp')
                        classified_data = self._classify_message(embed, event_type)
                        if classified_data:
                            await self.queue.put(classified_data)
                            
        elif op_code == 7:
            print("[Self-Bot Listener] Received Reconnect request. Closing and reconnecting.")
            await self.ws_connection.close()

        elif op_code == 9:
            can_resume = payload.get('d', False)
            print(f"[Self-Bot Listener] Invalid Session. Can resume: {can_resume}. Reconnecting.")
            if not can_resume:
                self.session_id = None; self.last_sequence = None
            await asyncio.sleep(random.uniform(1, 5))
            if self.ws_connection: await self.ws_connection.close()

    async def _send_identify(self):
        payload = {"op": 2, "d": {"token": self.token, "properties": {"$os": "linux", "$browser": "pingslave_listener", "$device": "pingslave_listener"}}}
        await self.ws_connection.send(json.dumps(payload))
        print("[Self-Bot Listener] Sent Identify payload.")

    async def _send_resume(self):
        payload = {"op": 6, "d": {"token": self.token, "session_id": self.session_id, "seq": self.last_sequence}}
        await self.ws_connection.send(json.dumps(payload))
        print(f"[Self-Bot Listener] Sent Resume payload for session {self.session_id}.")

    async def run(self):
        gateway_url = "wss://gateway.discord.gg/?v=9&encoding=json"
        while True:
            try:
                connect_url = self.resume_gateway_url or gateway_url
                print(f"[Self-Bot Listener] Connecting to {connect_url}...")
                async with websockets.connect(connect_url, close_timeout=10, ping_interval=None) as ws:
                    self.ws_connection = ws
                    async for message in ws:
                        await self._handle_event(json.loads(message))
            except (websockets.exceptions.ConnectionClosed, asyncio.TimeoutError) as e:
                print(f"[Self-Bot Listener] Connection lost: {type(e).__name__}. Reconnecting...")
            except Exception as e:
                print(f"[Self-Bot Listener] An unexpected error occurred: {type(e).__name__}. Reconnecting...")
            
            self.ws_connection = None
            await asyncio.sleep(random.uniform(3, 7))