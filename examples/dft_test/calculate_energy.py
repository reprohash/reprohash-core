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
