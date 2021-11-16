## Instructions to convert center out task files to nwb:
1. Download the folder containing the relevant data files. The folder structure format is 
expected to be [like in this folder](https://drive.google.com/drive/folders/1bYnIV7DH7leNshBGM0uHPp27YuxRKHKI)
2. Get the location of the specific data to convert:
```python
from pathlib import Path
from .center_out_task.conversion_script import convert
source_folder = "location/of/file" # example: r"~Downloads\3Ring\01/19/2017"
convert(source_folder)
```
This should create a nwb file beside the .mat files in the data folder.
This nwb file can now be opened and explored using the jupyter notebook in
__/jupyternotebook/nwb_usage.ipynwb__