#!/bin/bash

module load applications/gpu/python/conda-25.1.1-python-3.9.21

conda env list 
echo conda activate ml-a
conda activate /scratch/kenet/local/matambo/localscratch/conda_local/envs/ml-a1
rm -rf ml-A  ml-A1 ml-B
echo "# Prepare inputs, (code +data)"
echo mkdir ml-A
mkdir ml-A
echo cp download_data.py   model.py  train.py  ml-A
cp download_data.py   model.py  train.py  ml-A
echo cd ml-A
cd ml-A
echo "# Download CIFAR10 data"
echo python download_data.py
python download_data.py

echo "# Create multiple copies of the starting state for comparison"
echo cd ../
cd ../
echo cp -rf ml-A ml-A1
echo cp -rf ml-A ml-B
cp -rf ml-A ml-A1
cp -rf ml-A ml-B

echo "#=== ML-A:Run (binary compatibility break between NumPy and compiled extensions ) ==="
echo conda activate ml-a
conda activate /scratch/kenet/local/matambo/localscratch/conda_local/envs/ml-a
cd ml-A
echo "# Snapshot captures DECLARED inputs at a point in time"
echo "# Step 1: Creating snapshot of current state."
echo reprohash snapshot ./  -o input_snapshot.json
reprohash snapshot ./  -o input_snapshot.json
echo "# Step 2: Running training... "
echo reprohash run   --input-hash "$(python3 -c "import json; print(json.load(open('input_snapshot.json'))['content_hash'])")"   --exec  "python train.py"   --env-plugin pip   -o runrecord.json   --reproducibility-class stochastic 
reprohash run   --input-hash "$(python3 -c "import json; print(json.load(open('input_snapshot.json'))['content_hash'])")"   --exec  "python train.py"   --env-plugin pip   -o runrecord.json   --reproducibility-class stochastic 
echo "# Step 3: Creating verification bundle "
echo reprohash create-bundle   --input-snapshot input_snapshot.json   --runrecord runrecord.json   -o bundle/ 
reprohash create-bundle   --input-snapshot input_snapshot.json   --runrecord runrecord.json   -o bundle/ 
echo "# Step 4: Verifying bundle against current directory..."
reprohash verify-bundle bundle/  

echo "# === ML-A1:Run (Baseline) ==="
echo "# Activating a separate virtualenv"
echo conda activate ml-a1
conda activate /scratch/kenet/local/matambo/localscratch/conda_local/envs/ml-a1
echo cd ../ml-A1
cd ../ml-A1
echo "# Snapshot captures DECLARED inputs at a point in time"
echo "# Step 1: Creating snapshot of current state."
echo reprohash snapshot ./  -o input_snapshot.json
reprohash snapshot . -o input_snapshot.json
echo "# Step 2: Running training... "
echo reprohash run   --input-hash "$(python3 -c "import json; print(json.load(open('input_snapshot.json'))['content_hash'])")"   --exec  "python train.py" --env-plugin pip  -o runrecord.json   --reproducibility-class stochastic
reprohash run   --input-hash "$(python3 -c "import json; print(json.load(open('input_snapshot.json'))['content_hash'])")"   --exec  "python train.py" --env-plugin pip   -o runrecord.json   --reproducibility-class stochastic
echo "# Step 3: Creating verification bundle "
echo reprohash create-bundle   --input-snapshot input_snapshot.json   --runrecord runrecord.json   -o bundle/ 
reprohash create-bundle  --input-snapshot input_snapshot.json    --runrecord runrecord.json  -o bundle
echo "# Step 4: Verifying bundle against current directory..."
echo reprohash verify-bundle bundle/ -d .
reprohash verify-bundle bundle/ -d .

echo "# Can we understand why one succeded and the other failed?"
echo "# Compare environments between Run ML-A and ML-A1, --env pip plugin collects information from python virtualenvs"
reprohash compare-environments ../ml-A/runrecord.json  ./runrecord.json


echo "cd ../"
cd ../
echo "# === ML-B:Run Hidden Code Drift Test ==="
conda activate /scratch/kenet/local/matambo/localscratch/conda_local/envs/ml-a1
echo "cd ml-B/"
cd  ml-B

echo "# Make changes to model.py to simulate code drift"
echo sed -i 's/nn.Conv2d(3, 16,/nn.Conv2d(3, 32,/' model.py
echo sed -i 's/nn.Conv2d(16, 32,/nn.Conv2d(32, 32,/' model.py
sed -i 's/nn.Conv2d(3, 16,/nn.Conv2d(3, 32,/' model.py
sed -i 's/nn.Conv2d(16, 32,/nn.Conv2d(32, 32,/' model.py
echo "# Verify changed inputs against bundle generated from unchanged inputs. "
echo reprohash verify-bundle ../ml-A1/bundle/ -d . # verify detection of changes to inputs
reprohash verify-bundle ../ml-A1/bundle/ -d . # verify detection of changes to inputs

echo "# The change is detected, however, the reverse is true, generating a bundle from the new code will fail when compared with bundle from prior state" 
echo "# Snapshot captures DECLARED inputs at a point in time"
echo "# Step 1: Creating snapshot of current state."
echo reprohash snapshot ./  -o input_snapshot.json
reprohash snapshot . -o input_snapshot.json
echo reprohash run   --input-hash "$(python3 -c "import json; print(json.load(open('input_snapshot.json'))['content_hash'])")"   --exec  "python train.py"   --env-plugin pip  -o runrecord.json   --reproducibility-class stochastic
reprohash run   --input-hash "$(python3 -c "import json; print(json.load(open('input_snapshot.json'))['content_hash'])")"   --exec  "python train.py"   --env-plugin pip  -o runrecord.json   --reproducibility-class stochastic
echo "# Step 3: Creating verification bundle "
echo reprohash create-bundle   --input-snapshot input_snapshot.json   --runrecord runrecord.json   -o bundle/ 
reprohash create-bundle  --input-snapshot input_snapshot.json   --runrecord runrecord.json  -o bundle
echo "# Step 4: Verifying bundle against current directory..."
echo reprohash verify-bundle bundle/ -d .
reprohash verify-bundle bundle/ -d .

echo "# check new bundle with new inputs  vs prior unchanged inputs:"
echo reprohash verify-bundle bundle/ -d ../ml-A1
reprohash verify-bundle bundle/ -d ../ml-A1

echo "Key principle:"
echo "  • Snapshot = declaration of input state at time T"
echo "  • Working dir = actual files at time T+Δt"
echo "  • Verification = does working dir match snapshot?"
echo "  • If someone modifies files without re-snapshotting → FAIL"
echo ""
echo "# END"
