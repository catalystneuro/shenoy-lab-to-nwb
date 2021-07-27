from pathlib import Path
from typing import Union
from nwb_conversion_tools import MovieInterface

PathType = Union[str, Path]


class CoutMoviedataInterface(MovieInterface):

    def __init__(self, movie_filepath: PathType):
        assert Path(movie_filepath).suffix=='.avi', 'movie file path as avi not present'
        super().__init__(file_paths=[movie_filepath])