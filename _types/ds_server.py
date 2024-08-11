from dataclasses import dataclass, field

from disnake import VoiceClient, Message

from .music_info import MusicInfo


@dataclass
class DSServer:
    id: int
    music_queue: list[MusicInfo] = field(default_factory=lambda: [])
    voice_client: VoiceClient = None
    player_message: Message = None

    def __repr__(self) -> str:
        return f'DSServer(id={self.id}, voice_client={self.voice_client})'
