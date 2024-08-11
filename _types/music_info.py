from dataclasses import dataclass


@dataclass
class MusicInfo:
    title: str
    author: str
    url: str

    def __repr__(self):
        return f'`{self.title}` by `{self.author}`'
