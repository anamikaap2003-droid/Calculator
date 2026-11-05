# Calculator — Python + Streamlit

A calculator-style Streamlit application supporting full multi-step expressions, standard operator precedence, parentheses, scientific functions, calculation history, and CSV export.

## Features

- Enter complete expressions with more than two values, e.g. `12 + 3 * (8 - 2) / 4`
- Standard operator precedence and parentheses
- Calculator-style keypad: digits, decimal point, operators, AC, backspace, brackets and equals
- Square, square root, percentage/remainder, pi and scientific functions
- Supported operators: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- Supported functions: `sqrt`, `abs`, `round`, `sin`, `cos`, `tan`, `log`, `ln`
- Constants: `pi`, `e`
- Calculation history and CSV download
- Error messages for invalid expressions, division by zero, invalid roots and oversized expressions
- Safe expression parsing using Python's AST; does not use `eval()`

## Project structure

```text
realistic_calculator_streamlit/
├── app.py
├── calculator.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Run locally

```bash
python -m venv .venv
```

Windows:
```bash
.venv\\Scripts\\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Install and run:
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

1. Push all files to a GitHub repository.
2. Visit https://share.streamlit.io/
3. Create an app using your repository and select `app.py` as the main file.
4. Deploy and test the public URL.

## Notes

- `%` is the modulo/remainder operator, like many programming-style calculators. Example: `17 % 5 = 2`.
- Trigonometric functions use radians.
- History is kept in the current Streamlit session, not a permanent database.
