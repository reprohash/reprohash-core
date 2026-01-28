# ReproHash v2.1.8 - Zenodo Archive

This is the permanent archive of ReproHash version 2.1.8, corresponding to the  manuscript "ReproHash: A Verification Primitive for Computational Input Integrity".

## Citation

If you use this software in your research, please cite:

[Authors]. (2025). ReproHash: A Verification Primitive for Computational Input Integrity. , [volume], [pages]. doi:[to be assigned]

Software archive: 
[Authors]. (2025). ReproHash v2.1.8 [Software]. Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX

## Quick Start
```bash
# Install from PyPI
pip install reprohash-core==2.1.8

# Or install from this archive
pip install .
```

## Contents

- `reprohash/` - Core library implementation
- `tests/` - Comprehensive test suite
- `examples/` - Example workflows from the paper:
  - `ML_test/` - Machine learning environment incompatibility test
  - `dft_test/` - Density functional theory test
  - `qe_dft_test/` - Quantum ESPRESSO pseudopotential test
  - `rna_sequence_test/` - Bioinformatics reference genome test
- `docs/` - Complete documentation
- `spec/` - Formal specifications for canonical JSON and verification profiles

## Reproducibility

All test cases from the  Methods paper are included and can be verified:
```bash
# Run the test suite
pytest

# Verify specific test case
cd examples/ML_test
bash run.sh
```

## License

Apache License 2.0 - See LICENSE file

## Contact

For questions about this software, please open an issue on GitHub: https://github.com/reprohash/reprohash-core
