import asyncio
import websockets
import json
import re
from typing import Dict, Any, List

class SelfBotListener:
    """
    A class to connect to the Discord Gateway as a user and listen for messages
    in a specific channel, classify them, and put them into a shared queue.
    """

    def __init__(self, token: str, channel_id: str, queue: asyncio.Queue):
        if not token:
            raise ValueError("A valid self-bot token must be provided.")
        self.token = token
        self.target_channel_id = channel_id
        self.queue = queue
        self.ws_connection = None
        self.heartbeat_interval = None
        self.last_sequence = None

        # --- Updated regex to capture rarity ---
        self.patterns = {
            'super_craft': re.compile(r"^A (Super|Ultra|Mythic|Legendary|Epic|Rare|Uncommon|Common) (.+?) has been crafted by (\S+)!$", re.IGNORECASE),
            'super_spawn': re.compile(r"^A Super (.+?) has spawned!$", re.IGNORECASE),
            'super_defeat': re.compile(r"^A super (.+?) has been defeated by (.+?)!$", re.IGNORECASE),
        }

    def _classify_message(self, text: str, message_id: str, timestamp_iso: str) -> Dict[str, Any]:
        """
        Classifies the given text into one of four categories based on regex patterns.
        Now includes more detailed craft info and the message timestamp.
        """
        first_letter_match = re.search(r'[a-zA-Z]', text)
        if first_letter_match:
            text = text[first_letter_match.start():]
        else:
            return {'category': 'unclassified', 'text': text, 'original_message_id': message_id, 'timestamp': timestamp_iso}

        # 1. Super Petal Craft (Updated)
        match = self.patterns['super_craft'].match(text)
        if match:
            return {
                'category': 'super_craft',
                'rarity': match.group(1).strip(),
                'petal': match.group(2).strip(),
                'player': match.group(3).strip(),
                'original_message_id': message_id,
                'timestamp': timestamp_iso
            }

        # 2. Super Mob Spawn
        match = self.patterns['super_spawn'].match(text)
        if match:
            return {
                'category': 'super_spawn',
                'mob': match.group(1).strip(),
                'original_message_id': message_id,
                'timestamp': timestamp_iso
            }

        # 3. Super Mob Defeat
        match = self.patterns['super_defeat'].match(text)
        if match:
            mob_name = match.group(1).strip()
            player_list_str = match.group(2).strip()
            player_list_str = player_list_str.replace(" and ", ", ")
            players = [p.strip() for p in player_list_str.split(',') if p.strip()]
            return {
                'category': 'super_defeat',
                'mob': mob_name,
                'players': players,
                'original_message_id': message_id,
                'timestamp': timestamp_iso
            }
        
        # 4. Unclassified
        return {
            'category': 'unclassified',
            'text': text,
            'original_message_id': message_id,
            'timestamp': timestamp_iso
        }

    async def _send_heartbeat(self):
        """Sends a heartbeat to keep the connection alive."""
        while True:
            await asyncio.sleep(self.heartbeat_interval / 1000)
            if self.ws_connection:
                payload = {"op": 1, "d": self.last_sequence}
                await self.ws_connection.send(json.dumps(payload))

    async def run(self):
        """Main execution loop to connect, identify, and listen for events."""
        gateway_url = "wss://gateway.discord.gg/?v=9&encoding=json"
        
        while True:
            try:
                print("[Self-Bot Listener] Connecting to Discord Gateway...")
                async with websockets.connect(gateway_url) as ws:
                    self.ws_connection = ws
                    
                    hello_payload = json.loads(await ws.recv())
                    self.heartbeat_interval = hello_payload['d']['heartbeat_interval']
                    
                    asyncio.create_task(self._send_heartbeat())

                    identify_payload = { "op": 2, "d": { "token": self.token, "properties": { "$os": "linux", "$browser": "pingslave_listener", "$device": "pingslave_listener" }}}
                    await ws.send(json.dumps(identify_payload))
                    print("[Self-Bot Listener] Connection established. Listening for messages...")

                    async for message in ws:
                        payload = json.loads(message)
                        
                        if 's' in payload and payload['s'] is not None:
                            self.last_sequence = payload['s']

                        if payload['op'] == 0 and payload['t'] == "MESSAGE_CREATE":
                            event_data = payload['d']
                            if event_data.get('channel_id') == self.target_channel_id and event_data.get('embeds'):
                                for embed in event_data['embeds']:
                                    body_text = embed.get('description')
                                    message_id = event_data.get('id')
                                    timestamp = event_data.get('timestamp')
                                    if body_text and message_id and timestamp:
                                        classified_data = self._classify_message(body_text, message_id, timestamp)
                                        await self.queue.put(classified_data)
            
            except websockets.exceptions.ConnectionClosed as e:
                print(f"[Self-Bot Listener] Connection closed: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[Self-Bot Listener] An unexpected error occurred: {e}. Reconnecting in 15 seconds...")
                await asyncio.sleep(15)