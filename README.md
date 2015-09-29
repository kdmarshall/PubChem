# PubChem
### A simple PubChem module

Usage:
```
import sys
try:
from pubchem import PubChem
except ImportError:
sys.exit("Failed to import PubChem module")

p = PubChem("C1C2=CN=C(N=C2C3=C(C=C(C=C3)Cl)C(=N1)C4=C(C=CC=C4F)F)NC5=CC=C(C=C5)C(=O)O")
print p.to_dict()
```