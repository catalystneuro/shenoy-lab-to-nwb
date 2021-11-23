# shenoy-lab-to-nwb

This repository hosts conversion pipelines and analysis/visualization pipelines for datasets associated with 3 experiments at Shenoy Lab, Stanford University. 

1. Conversion of center-out-reaching task. Datasets associated with the paper: 
__Even-Chen N*, Sheffer B*, Vyas S, Ryu SI, Shenoy KV (2019) Structure and variability of delay activity in premotor cortex. PLoS Computational Biology. 15(2): e1006808__
2. Conversion of electrophysiology/behavioral datasets of Neuropixels implanted in Monkeys. 
3. Conversion of maze-task. Datasets of the paper: 
__Churchland MM*, Cunningham JP*, Kaufman MT, Foster JD, Nuyujukian P, Ryu SI, Shenoy KV (2012) Neural population dynamics during reaching. Nature. 487:51-56__

### Instructions to directly stream nwb file from DANDI:

1. This conda environment contains only those files necessary to visualize an NWB file hosted 
on DANDI hub. Files for the aims 3 (maze task) are [here](https://dandiarchive.org/dandiset/000070/draft) and for aim 1 (center out task in
in monkeys) is [here](https://dandiarchive.org/dandiset/000121/0.210815.0703)
```shell
git clone https://github.com/catalystneuro/shenoy-lab-to-nwb.git
cd shenoy_lab_to_nwb
conda env create -f environment.yml
conda activate shenoy_lab_nwb
```

2. Open the jupyter notebook:

```shell
# add the conda environment to show up in a jupyter notebook
python -m ipykernel install --user --name=shenoy_lab_nwb
cd nwb_usage/
jupyter notebok analysis_script.ipynb
```

### Intructions to convert datasets to NWB:
Each of the three aims have a folder that houses the conversion modules
and `conversion_scipt.py`. The folder structure each conversion script expects is like
on [this google drive](https://drive.google.com/drive/folders/1mP3MCT_hk2v6sFdHnmP_6M0KEFg1r2g_)