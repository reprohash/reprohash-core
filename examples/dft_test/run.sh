#!/bin/bash

  module load applications/gpu/python/conda-25.1.1-python-3.9.21 
  conda activate ml-a
  echo "Creating calculate_energy.py" 
  cat > calculate_energy.py << 'EOF'
"""Calculate energy of H2 molecule using EMT calculator"""
from ase import Atoms
from ase.calculators.emt import EMT
from ase.optimize import BFGS
import json

# Read structure
atoms = Atoms('H2', positions=[(0, 0, 0), (0, 0, 0.74)])
atoms.calc = EMT()

# Optimize
opt = BFGS(atoms, logfile='opt.log')
opt.run(fmax=0.01)

# Calculate energy
energy = atoms.get_potential_energy()

# Save result
result = {
    'energy_eV': energy,
    'positions': atoms.positions.tolist(),
    'converged': True
}

with open('result.json', 'w') as f:
    json.dump(result, f, indent=2)

print(f"Final energy: {energy:.6f} eV")
EOF


 echo "Creating structure.xyz" 
 cat > structure.xyz << 'EOF'
2
H2 molecule
H 0.0 0.0 0.0
H 0.0 0.0 0.74
EOF

  echo "Running mkdir -p test_A/inputs"
  mkdir -p test_A/inputs   
  echo "Copying structure and .py file to  test_A/inputs"
  cp structure.xyz test_A/inputs/ 
  cp calculate_energy.py test_A/inputs/
  echo "cd test_A"
  cd test_A
  echo "Running reprohash init "
  echo "reprohash snapshot inputs/ -o input_snapshot.json"
  reprohash snapshot inputs/ -o input_snapshot.json
  echo "prospective capture of run"
  echo reprohash run   --input-hash "$(python3 -c "import json; print(json.load(open('input_snapshot.json'))['content_hash'])")"   --exec "cd inputs && python calculate_energy.py"   --env-plugin pip   -o runrecord.json   --reproducibility-class deterministic 
  reprohash run   --input-hash "$(python3 -c "import json; print(json.load(open('input_snapshot.json'))['content_hash'])")"   --exec "cd inputs && python calculate_energy.py"   --env-plugin pip   -o runrecord.json   --reproducibility-class deterministic 
  echo "Creating verification bundle"
  echo reprohash create-bundle   --input-snapshot input_snapshot.json   --runrecord runrecord.json   -o bundle
  reprohash create-bundle   --input-snapshot input_snapshot.json   --runrecord runrecord.json   -o bundle
  echo "Running verification "
  reprohash verify-bundle bundle/ -d inputs/  
  echo "cd ../ "
  cd ../
  echo "Running mkdir -p test_B/inputs"
  mkdir -p test_B/inputs
  echo "Copying  .py file to  test_B/inputs"
  cp calculate_energy.py test_B/inputs/
  echo "Creating modified  structure in test_B/inputs"
  cat > test_B/inputs/structure.xyz << 'EOF'
2
H2 molecule - stretched
H 0.0 0.0 0.0
H 0.0 0.0 0.80
EOF

  echo "cd test_B"
  cd test_B
  echo "Try to verify with bundle from test_A"
  echo reprohash verify-bundle ../test_A/bundle/ -d inputs/  
  reprohash verify-bundle ../test_A/bundle/ -d inputs/  
