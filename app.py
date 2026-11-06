"""Responsive Standard + Scientific calculator built with Streamlit.

Works with the existing calculator.py (AST based evaluator). Only this file
changed: calculator.py, requirements.txt and README.md are used as they are.
"""

from __future__ import annotations

import csv
import html
import inspect
import io
import json
import re
from datetime import datetime

import streamlit as st

from calculator import (
    MAX_EXPRESSION_LENGTH,
    CalculatorError,
    evaluate_expression,
    format_result,
)

st.set_page_config(
    page_title="Calculator",
    page_icon="🧮",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

def _system_prefers_dark() -> bool:
    """Start in the visitor's own theme when Streamlit can tell us."""
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


DEFAULTS = {
    "expression": "",        # text in the display (typed or built with the keypad)
    "history": [],
    "ans": None,             # previous result, used by the Ans key
    "last_expression": "",   # small line above the display, e.g. "2 + 3 ="
    "notice": None,          # ("error" | "warning", message)
    "just_evaluated": False,
}
for _key, _value in DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _value
if "dark" not in st.session_state:
    st.session_state["dark"] = _system_prefers_dark()


def _stretch(widget) -> dict:
    """Full-width kwargs that work on old and new Streamlit versions."""
    try:
        params = inspect.signature(widget).parameters
    except (TypeError, ValueError):
        params = {}
    return {"width": "stretch"} if "width" in params else {"use_container_width": True}


try:
    from streamlit.components.v1 import html as _components_html
except Exception:  # pragma: no cover
    _components_html = None

# Runs in the browser. Streamlit cannot filter keystrokes or keep focus by
# itself, so a small script is installed ONCE into the page (not into the input
# element, which Streamlit may replace after a rerun). It
#   (a) blocks every typed or pasted character that is not a digit, operator,
#       bracket, dot or comma (event delegation, so it survives re-renders),
#   (b) cleans the value as a safety net for keyboards that skip key events,
#   (c) puts the cursor back in the display after every rerun and click.
_PAGE_GUARD_JS = r"""
(function () {
  if (window.__calcGuard) return;
  var doc = document;
  var SEL = 'input[aria-label="Expression"]';
  var OKCH = /^[0-9+\-*\/^%().,\s×÷−]*$/;
  var NOTOK = /[^0-9+\-*\/^%().,\s×÷−]/g;
  var BADCH = /[^A-Za-z0-9+\-*\/^%().,\s×÷−]/g;
  var WORDS = {sin:1, cos:1, tan:1, log:1, ln:1, sqrt:1, abs:1, round:1, pi:1, e:1, ans:1};
  var coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
  var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;

  function find() { return doc.querySelector(SEL); }
  function isCalc(el) { return !!(el && el.matches && el.matches(SEL)); }
  function focusEnd(input) {
    input.focus({ preventScroll: true });
    var n = input.value.length;
    try { input.setSelectionRange(n, n); } catch (e) {}
  }

  doc.addEventListener('keydown', function (e) {
    if (!isCalc(e.target) || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key && e.key.length === 1 && !OKCH.test(e.key)) e.preventDefault();
  }, true);

  doc.addEventListener('beforeinput', function (e) {
    if (isCalc(e.target) && e.data && !OKCH.test(e.data)) e.preventDefault();
  }, true);

  doc.addEventListener('paste', function (e) {
    var input = e.target;
    if (!isCalc(input)) return;
    e.preventDefault();
    var text = ((e.clipboardData || window.clipboardData).getData('text') || '').replace(NOTOK, '');
    if (!text) return;
    input.setRangeText(text, input.selectionStart, input.selectionEnd, 'end');
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }, true);

  doc.addEventListener('drop', function (e) {
    if (isCalc(e.target)) e.preventDefault();
  }, true);

  // Safety net: any user-originated change is cleaned. Keypad-inserted text such
  // as "sin(" never fires an input event, and whole function names are kept.
  doc.addEventListener('input', function (e) {
    var input = e.target;
    if (!isCalc(input)) return;
    var v = input.value;
    var c = v.replace(BADCH, '').replace(/[A-Za-z]+/g, function (w) {
      return WORDS[w.toLowerCase()] ? w : '';
    });
    if (c === v) return;
    var pos = Math.max((input.selectionStart || 0) - (v.length - c.length), 0);
    setter.call(input, c);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    try { input.setSelectionRange(pos, pos); } catch (err) {}
  }, true);

  // Clicking anywhere that is not another field returns the cursor to the display.
  doc.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest('input, textarea, select, a, summary')) return;
    var input = find();
    if (input) setTimeout(function () { focusEnd(input); }, 0);
  });

  // Phones: use the keypad instead of the on-screen keyboard.
  if (coarse) {
    new MutationObserver(function () {
      var input = find();
      if (input && input.getAttribute('inputmode') !== 'none') input.setAttribute('inputmode', 'none');
    }).observe(doc.body, { childList: true, subtree: true });
  }

  window.__calcReady = function () {
    var input = find();
    if (!input) return;
    if (coarse) input.setAttribute('inputmode', 'none');
    if (doc.activeElement !== input) focusEnd(input);
  };
  window.__calcGuard = true;
})();
"""

_IFRAME_JS = (
    "<script>(function () { try {"
    " var p = window.parent, d = p.document;"
    " if (!p.__calcGuard) {"
    "   var s = d.createElement('script'); s.textContent = " + json.dumps(_PAGE_GUARD_JS) + ";"
    "   d.head.appendChild(s); }"
    " [0, 60, 200, 500].forEach(function (t) {"
    "   setTimeout(function () { if (p.__calcReady) p.__calcReady(); }, t); });"
    " } catch (err) {} })();</script>"
)


def keep_input_ready() -> None:
    """Install the page guard once and refocus after every rerun (nonce forces reload)."""
    if _components_html is None:
        return
    try:
        _components_html(f"<!-- {datetime.now().timestamp()} -->{_IFRAME_JS}", height=0)
    except Exception:
        pass


STRETCH_SUBMIT = _stretch(st.form_submit_button)
STRETCH_BUTTON = _stretch(st.button)
STRETCH_DOWNLOAD = _stretch(st.download_button)


# --------------------------------------------------
# INPUT CLEANING AND EVALUATION
# --------------------------------------------------

# Names that calculator.py understands, plus "ans" (resolved in this file).
ALLOWED_NAMES = {"sqrt", "abs", "round", "sin", "cos", "tan", "log", "ln", "pi", "e", "ans"}

_SYMBOLS = str.maketrans({"×": "*", "÷": "/", "−": "-", "–": "-", "—": "-", "π": "pi"})
_TOKEN_RE = re.compile(
    r"""
      (?P<space>\s+)
    | (?P<num>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)
    | (?P<name>[A-Za-z]+)
    | (?P<sym>\*\*|//|[-+*/^%(),.])
    """,
    re.VERBOSE,
)


def clean_expression(text: str) -> tuple[str, list[str]]:
    """Keep numbers, operators, brackets and supported names; report the rest."""
    text = text.translate(_SYMBOLS)
    kept: list[str] = []
    removed: list[str] = []
    pos = 0
    while pos < len(text):
        match = _TOKEN_RE.match(text, pos)
        if match is None:
            removed.append(text[pos])
            pos += 1
            continue
        pos = match.end()
        token = match.group()
        if match.lastgroup == "name" and token.lower() not in ALLOWED_NAMES:
            removed.append(token)
        else:
            kept.append(token.lower() if match.lastgroup == "name" else token)
    return "".join(kept).strip(), list(dict.fromkeys(removed))


def prettify(expression: str) -> str:
    """Show an expression the way a calculator display would."""
    out = expression.replace("**", "^").replace("*", "×").replace("/", "÷")
    out = out.replace("××", "^").replace("÷÷", "//")
    out = re.sub(r"(?<!\de)-", "−", out)
    return re.sub(r"(?<![A-Za-z])pi(?![A-Za-z])", "π", out)


def plain(value) -> str:
    """Result as text that can be typed back into the display (no commas)."""
    return format_result(value).replace(",", "")


def evaluate(cleaned: str):
    """Resolve Ans, ^ and open brackets, then use calculator.py."""
    text = cleaned.replace("^", "**")
    if re.search(r"(?<![A-Za-z])ans(?![A-Za-z])", text):
        if st.session_state.ans is None:
            raise CalculatorError("There is no previous answer yet.")
        text = re.sub(r"(?<![A-Za-z])ans(?![A-Za-z])", f"({plain(st.session_state.ans)})", text)
    depth = text.count("(") - text.count(")")
    if depth < 0:
        raise CalculatorError("Unmatched ')'.")
    return evaluate_expression(text + ")" * depth)


# --------------------------------------------------
# KEYPAD LOGIC
# --------------------------------------------------

OPS = "+-*/^×÷−%"            # single-character binary operators
OP_TOKENS = set(OPS) | {"//"}
MINUS = "-−"
HIGH_OPS = "*/^×÷%"           # operators after which a minus is a sign, e.g. 5×-3
FUNC_TOKENS = {"sin(", "cos(", "tan(", "log(", "ln(", "sqrt(", "abs(", "round("}
POSTFIX = {"SQ": "^2"}
CONTINUE_TOKENS = OP_TOKENS | set(POSTFIX)
CONSTANT_TOKENS = {"pi", "e", "ans"}


def press(token: str) -> None:
    """Handle one calculator key the way a real calculator would."""
    s = st.session_state
    s.notice = None
    expr = s.expression

    if s.just_evaluated:
        s.just_evaluated = False
        if token in CONTINUE_TOKENS:
            pass                                   # keep going from the result
        elif token in FUNC_TOKENS:
            s.expression = f"{token}{expr})"       # apply the function to the result
            return
        elif token in (")", ","):
            s.just_evaluated = True                # nothing to close / separate
            return
        else:
            expr = ""                              # digit, "(", constant: start fresh

    last = expr[-1] if expr else ""

    if token.isdigit():
        segment = re.search(r"\d*\.?\d*$", expr).group()
        if segment == "0":
            expr = expr[:-1] + token               # 0 then 5 -> 5, not 05
        else:
            expr += token

    elif token == ".":
        segment = re.search(r"\d*\.?\d*$", expr).group()
        if "." in segment:
            return                                 # one decimal point per number
        if segment:
            expr += "."
        elif last == ")" or last.isalpha():
            expr += "×0."
        else:
            expr += "0."

    elif token in OP_TOKENS:
        if not expr or last in "(,":
            if token in MINUS:
                expr += token                      # leading minus is a sign
        elif last in OPS:
            if token in MINUS and last in HIGH_OPS:
                expr += token                      # 5×-3
            else:                                  # changed your mind: replace operator
                base = expr.rstrip(OPS)
                if base:
                    expr = base + token
                elif token in MINUS:
                    expr = token
        else:
            expr += token

    elif token in POSTFIX:
        if expr and last not in OPS and last not in "(,":
            expr += POSTFIX[token]

    elif token == ",":
        if expr and last not in OPS and last not in "(,":
            expr += token

    elif token == "(":
        expr += token

    elif token == ")":
        opened = expr.count("(") - expr.count(")")
        if opened > 0 and last not in OPS and last not in "(,":
            expr += token

    elif token in FUNC_TOKENS or token in CONSTANT_TOKENS:
        expr += token

    if len(expr) <= MAX_EXPRESSION_LENGTH:
        s.expression = expr


def backspace() -> None:
    s = st.session_state
    s.notice = None
    s.just_evaluated = False
    # Remove "sin(", "pi", "ans" as one unit, otherwise a single character.
    match = re.search(r"(?:[a-z]+\(|ans|pi)$", s.expression)
    s.expression = s.expression[: match.start()] if match else s.expression[:-1]


def clear_all() -> None:
    s = st.session_state
    s.expression = ""
    s.last_expression = ""
    s.notice = None
    s.just_evaluated = False


def on_key(token: str) -> None:
    if token == "AC":
        clear_all()
    elif token == "BACK":
        backspace()
    else:
        press(token)


def run_calculation() -> None:
    """Runs on the = key and on the Enter key."""
    s = st.session_state
    if not s.expression.strip():
        return

    cleaned, removed = clean_expression(s.expression)
    if removed:
        s.expression = cleaned
        s.just_evaluated = False
        s.notice = (
            "warning",
            "Removed unsupported input: " + ", ".join(f"'{r}'" for r in removed)
            + ". Only numbers, operators and the listed functions are allowed.",
        )
        return

    try:
        value = evaluate(cleaned)
    except CalculatorError as exc:
        s.notice = ("error", str(exc))
        s.just_evaluated = False
        return
    except Exception:
        s.notice = ("error", "Unable to calculate this expression.")
        s.just_evaluated = False
        return

    s.history.insert(0, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expression": prettify(cleaned),
        "raw": cleaned,
        "result": format_result(value),
    })
    s.history = s.history[:100]
    s.ans = value
    s.last_expression = prettify(cleaned) + " ="
    s.expression = plain(value)
    s.just_evaluated = True
    s.notice = None


def load_history(index: int) -> None:
    s = st.session_state
    s.expression = s.history[index]["raw"]
    s.just_evaluated = False
    s.notice = None


def clear_history() -> None:
    st.session_state.history = []


def live_preview() -> str:
    """Result shown while typing, like phone calculators do."""
    s = st.session_state
    if not s.expression.strip() or s.just_evaluated:
        return ""
    cleaned, removed = clean_expression(s.expression)
    if removed:
        return ""
    try:
        value = evaluate(cleaned)
    except Exception:
        return ""
    text = plain(value)
    return "" if text == cleaned.replace(" ", "") else f"= {format_result(value)}"


# --------------------------------------------------
# THEME
# --------------------------------------------------

if st.session_state.dark:
    palette = {
        "scheme": "dark", "bg": "#0f172a", "panel": "#1e293b",
        "text": "#f1f5f9", "muted": "#94a3b8", "input": "#0f172a",
        "key": "#334155", "key_fn": "#475569", "border": "#475569",
        "accent": "#60a5fa", "equals": "#2563eb",
    }
else:
    palette = {
        "scheme": "light", "bg": "#f4f6fb", "panel": "#ffffff",
        "text": "#111827", "muted": "#6b7280", "input": "#ffffff",
        "key": "#ffffff", "key_fn": "#e5e7eb", "border": "#d1d5db",
        "accent": "#2563eb", "equals": "#2563eb",
    }

st.markdown(
    f"""
<style>
:root {{
  color-scheme: {palette['scheme']};
  --bg: {palette['bg']};       --panel: {palette['panel']};
  --text: {palette['text']};   --muted: {palette['muted']};
  --input: {palette['input']}; --key: {palette['key']};
  --key-fn: {palette['key_fn']}; --border: {palette['border']};
  --accent: {palette['accent']}; --equals: {palette['equals']};
}}

/* ---------- page ---------- */
html, body, .stApp,
[data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stHeader"] {{ background: var(--bg) !important; }}
[data-testid="stHeader"] {{ color: var(--text) !important; }}
.stApp, .stApp p, .stApp label, .stApp li,
.stApp h1, .stApp h2, .stApp h3 {{ color: var(--text); }}
.block-container, [data-testid="stMainBlockContainer"] {{
  max-width: 600px; padding: 4.5rem 1rem 3rem !important; }}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {{ color: var(--muted) !important; }}

/* ---------- heading ---------- */
.calc-title {{ font-size: clamp(1.7rem, 6vw, 2.4rem); font-weight: 800;
               line-height: 1.15; color: var(--text); }}
.calc-subtitle {{ color: var(--muted); font-size: .9rem; margin-top: .15rem; }}

/* ---------- display panel ---------- */
.st-key-display_panel {{ background: var(--panel); border: 1px solid var(--border);
  border-radius: 18px; padding: 1rem 1rem .75rem; margin-bottom: .5rem; }}
.calc-prev {{ text-align: right; color: var(--muted); font-size: .95rem;
              min-height: 1.4rem; overflow-wrap: anywhere; }}
.calc-preview {{ text-align: right; color: var(--muted); font-size: 1.05rem;
                 min-height: 1.6rem; margin-top: .35rem; overflow-wrap: anywhere; }}

[data-testid="stTextInput"] div[data-baseweb="input"],
[data-testid="stTextInput"] div[data-baseweb="base-input"],
[data-testid="stTextInput"] input {{
  background: var(--input) !important; color: var(--text) !important; }}
[data-testid="stTextInput"] div[data-baseweb="input"] {{
  border: 1px solid var(--border) !important; border-radius: 14px !important; }}
[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {{
  border-color: var(--accent) !important; box-shadow: 0 0 0 1px var(--accent) !important; }}
[data-testid="stTextInput"] input {{
  text-align: right; font-size: clamp(1.3rem, 5vw, 1.8rem); font-weight: 600;
  font-variant-numeric: tabular-nums; min-height: 3.2rem;
  caret-color: var(--accent); }}
[data-testid="stTextInput"] input::placeholder {{ color: var(--muted); opacity: 1; }}
[data-testid="InputInstructions"] {{ display: none !important; }}

/* ---------- forms ---------- */
[data-testid="stForm"] {{ border: 0 !important; padding: 0 !important;
                          background: transparent !important; }}

/* ---------- keys ---------- */
[data-testid="stButton"] button,
[data-testid="stFormSubmitButton"] button,
[data-testid="stDownloadButton"] button {{
  background: var(--key) !important; color: var(--text) !important;
  border: 1px solid var(--border) !important; border-radius: 13px !important;
  min-height: 3.2rem; font-weight: 650; }}
[data-testid="stButton"] button p,
[data-testid="stFormSubmitButton"] button p,
[data-testid="stDownloadButton"] button p {{ color: inherit !important; font-size: 1.05rem; }}
[data-testid="stButton"] button:hover,
[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stDownloadButton"] button:hover {{
  border-color: var(--accent) !important; color: var(--accent) !important; }}
[class*="st-key-fn_"] button, [class*="st-key-sci_"] button {{
  background: var(--key-fn) !important; }}
[class*="st-key-op_"] button {{ color: var(--accent) !important; font-weight: 800; }}
[class*="st-key-hist_"] button {{ min-height: 2.5rem; font-weight: 500;
  justify-content: flex-start; text-align: left; }}
button[kind="primaryFormSubmit"], button[data-testid="stBaseButton-primaryFormSubmit"],
button[kind="primary"] {{
  background: var(--equals) !important; border-color: var(--equals) !important;
  color: #ffffff !important; }}
button[kind="primaryFormSubmit"]:hover,
button[data-testid="stBaseButton-primaryFormSubmit"]:hover {{
  color: #ffffff !important; filter: brightness(1.1); }}

/* ---------- expanders ---------- */
[data-testid="stExpander"] {{ border: 0 !important; background: transparent !important; }}
[data-testid="stExpander"] details {{ background: var(--panel) !important;
  border: 1px solid var(--border) !important; border-radius: 12px !important; }}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {{
  color: var(--text) !important; }}

/* ---------- hide the zero-height helper iframe ---------- */
div[data-testid="stElementContainer"]:has(iframe[height="0"]) {{
  position: absolute; height: 0; margin: 0; padding: 0; overflow: hidden; }}

/* ---------- keep the keypad a grid on phones ---------- */
div[data-testid="stHorizontalBlock"] {{ gap: .5rem; }}
@media (max-width: 640px) {{
  div[data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; }}
  div[data-testid="stColumn"], div[data-testid="column"] {{
    min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }}
  .block-container, [data-testid="stMainBlockContainer"] {{
    padding: 4rem .6rem 2rem !important; }}
  [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button {{
    min-height: 3rem; padding: .25rem .1rem; }}
}}
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------
# HEADER
# --------------------------------------------------

head_left, head_right = st.columns([3, 2], vertical_alignment="center")
with head_left:
    st.markdown(
        '<div class="calc-title">🧮 Calculator</div>'
        '<div class="calc-subtitle">Standard • Scientific</div>',
        unsafe_allow_html=True,
    )
with head_right:
    st.toggle("Dark mode", key="dark")


# --------------------------------------------------
# DISPLAY + KEYPAD (one form: Enter key == "=" key)
# --------------------------------------------------

KEYPAD = [
    [("AC", "AC", "fn_ac"), ("⌫", "BACK", "fn_back"), ("(", "(", "fn_lp"), (")", ")", "fn_rp")],
    [("7", "7", "n7"), ("8", "8", "n8"), ("9", "9", "n9"), ("÷", "÷", "op_div")],
    [("4", "4", "n4"), ("5", "5", "n5"), ("6", "6", "n6"), ("×", "×", "op_mul")],
    [("1", "1", "n1"), ("2", "2", "n2"), ("3", "3", "n3"), ("−", "−", "op_sub")],
    [("0", "0", "n0"), (".", ".", "ndot"), ("%", "%", "op_mod"), ("+", "+", "op_add")],
]

SCIENTIFIC = [
    [("sin", "sin(", "sci_sin"), ("cos", "cos(", "sci_cos"), ("tan", "tan(", "sci_tan")],
    [("log", "log(", "sci_log"), ("ln", "ln(", "sci_ln"), ("|x|", "abs(", "sci_abs")],
    [("√", "sqrt(", "sci_sqrt"), ("round", "round(", "sci_round"), (",", ",", "sci_comma")],
    [("x²", "SQ", "sci_sq"), ("xʸ", "^", "sci_pow"), ("//", "//", "sci_floor")],
    [("π", "pi", "sci_pi"), ("e", "e", "sci_e"), ("Ans", "ans", "sci_ans")],
]


def submit_button(label: str, key: str, **kwargs) -> None:
    """form_submit_button with a fallback for Streamlit versions without `key`."""
    try:
        st.form_submit_button(label, key=key, **kwargs, **STRETCH_SUBMIT)
    except TypeError:
        st.form_submit_button(label, **kwargs, **STRETCH_SUBMIT)


def key_button(label: str, token: str, key: str) -> None:
    submit_button(label, key, on_click=on_key, args=(token,))


def display_panel():
    """Styled panel. Must be created inside the form so its buttons belong to it."""
    try:
        return st.container(key="display_panel")
    except TypeError:  # older Streamlit: no container keys, use the built-in border
        return st.container(border=True)


with st.form("calculator", clear_on_submit=False):

    with display_panel():
        previous = html.escape(st.session_state.last_expression) or "&nbsp;"
        st.markdown(f'<div class="calc-prev">{previous}</div>', unsafe_allow_html=True)

        display_col, equals_col = st.columns([4, 1], vertical_alignment="center")
        with display_col:
            st.text_input(
                "Expression",
                key="expression",
                label_visibility="collapsed",
                placeholder="0",
                max_chars=MAX_EXPRESSION_LENGTH,
                autocomplete="off",
            )
        with equals_col:
            # Must be the first submit button in the form: Enter triggers it.
            submit_button("=", "equals", type="primary", on_click=run_calculation)

        notice = st.session_state.notice
        if notice:
            (st.error if notice[0] == "error" else st.warning)(notice[1])
        else:
            hint = live_preview()
            st.markdown(
                f'<div class="calc-preview">{html.escape(hint) or "&nbsp;"}</div>',
                unsafe_allow_html=True,
            )

    for row in KEYPAD:
        for column, (label, token, key) in zip(st.columns(4), row):
            with column:
                key_button(label, token, key)

    with st.expander("Scientific functions", expanded=False):
        for row in SCIENTIFIC:
            for column, (label, token, key) in zip(st.columns(3), row):
                with column:
                    key_button(label, token, key)

keep_input_ready()

st.caption(
    "Type numbers and operators or tap keys, press Enter or = to calculate. "
    "Functions (sin, cos, tan, log, ln, √, round, |x|, π, e, Ans) come from the "
    "Scientific keys. Supported: + − × ÷ ^ // % (remainder) and brackets."
)


# --------------------------------------------------
# HISTORY
# --------------------------------------------------

with st.expander("History", expanded=False):
    history = st.session_state.history
    if not history:
        st.caption("Your calculations will appear here.")
    else:
        st.caption(f"{len(history)} saved. Tap an entry to reuse it.")
        for index, item in enumerate(history[:20]):
            st.button(
                f"{item['expression']} = {item['result']}",
                key=f"hist_{index}",
                on_click=load_history,
                args=(index,),
                **STRETCH_BUTTON,
            )

        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=["time", "expression", "result"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(history)
        st.download_button(
            "Download history as CSV",
            data=buffer.getvalue(),
            file_name="calculator_history.csv",
            mime="text/csv",
            **STRETCH_DOWNLOAD,
        )
        st.button("Clear history", on_click=clear_history, **STRETCH_BUTTON)