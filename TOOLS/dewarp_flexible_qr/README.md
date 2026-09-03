# dewarp_flexible_qr

Non-rigid thin-plate-spline dewarp for QR/barcode images photographed on
wrinkled or curved flexible surfaces (see the module docstring in
`dewarp_flexible_qr.py` for the full method and rejected approaches). Pure
Python + OpenCV/SciPy, unchanged logic from the Windows repo.

## Usage

```
python3 dewarp_flexible_qr.py INPUT.jpg [--crop X1,Y1,X2,Y2] [--decode] [--save-debug DIR]
```

## Requirements

```
pip install -r requirements.txt
sudo apt install libzbar0   # pyzbar needs this system shared library on Linux
```
