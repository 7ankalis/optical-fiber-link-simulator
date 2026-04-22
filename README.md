# Optical Fiber Link Simulator

Simple desktop GUI for optical link feasibility, inspired by OptiSystem for lab use.

## Features

- Input sections for transmitter, fiber, and receiver parameters
- Computes:
  - Received power with full losses:
    - fiber attenuation
    - splices
    - connectors
  - Computed margin vs receiver sensitivity and required safety margin
  - Maximum distance from practical power budget
  - Total dispersion (chromatic + modal for gradient fiber)
  - Maximum bit rate with line-code coefficient (`NRZ=0.7`, `RZ=0.35`)
- Dynamic matplotlib graph: power vs distance
- Clean dark-mode interface (PySide6)

## Project Structure

- `main.py` - application entry point
- `ui/` - GUI components
- `core/` - simulation calculations
- `plot/` - plotting widget logic

## Run

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Launch:

```bash
python main.py
```

## Notes on Formulas

`core/calculations.py` now follows the model used in your provided simulator script:
- losses from attenuation + splices + connectors
- `delta_tau_total = sqrt(delta_tau_ch^2 + delta_tau_im^2)`
- `Bmax = coeff_code / delta_tau`

If your PDF contains stricter/official constants or additional constraints, they can be inserted in one place (`core/calculations.py`).
