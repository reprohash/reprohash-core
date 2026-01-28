#!/usr/bin/env python3
"""
Download CIFAR-10 dataset to a fixed on-disk location.

This script intentionally performs no preprocessing.
It exists solely to materialize training inputs so they can be snapshotted.
"""

from torchvision import datasets
from pathlib import Path

DATA_ROOT = Path("data/cifar10")

def main():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    # Train split
    datasets.CIFAR10(
        root=DATA_ROOT,
        train=True,
        download=True,
    )

    # Test split
    datasets.CIFAR10(
        root=DATA_ROOT,
        train=False,
        download=True,
    )

    print(f"CIFAR-10 downloaded to {DATA_ROOT.resolve()}")

if __name__ == "__main__":
    main()

