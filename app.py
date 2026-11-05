"""Responsive Calculator App with Basic and Scientific Functions."""

from datetime import datetime
import csv
import io
import re

import streamlit as st
from calculator import CalculatorError, evaluate_expression, format_result


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Calculator",
    page_icon="🧮",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

DEFAULTS = {
    "expression": "",
    "history": [],
    "last_result": None,
    "last_error": "",
    "just_evaluated": False,
    "appearance": "Light",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# Supported scientific functions and constants
ALLOWED_NAMES = {
    "sqrt", "sin", "cos", "tan",
    "log", "ln", "abs", "pi", "e"
}

ALLOWED_OPERATORS = {
    "+", "-", "*", "/", "%", "**"
}


# --------------------------------------------------
# INPUT VALIDATION
# --------------------------------------------------

def sanitize_expression():
    """Allow numbers, operators and supported scientific functions."""

    raw = st.session_state.expression

    # Remove unsupported symbols
    cleaned = re.sub(
        r"[^0-9A-Za-z+\-*/().%\s]",
        "",
        raw
    )

    # Remove unsupported words but retain valid functions
    # cleaned = re.sub(
    #     r"[A-Za-z]+",
    #     lambda match: (
    #         match.group(0)
    #         if match.group(0) in ALLOWED_NAMES
    #         else ""
    #     ),
    #     cleaned
    # )

    # Update only if input actually changed.
    # This helps prevent unnecessary cursor repositioning.
    if cleaned != raw:
        st.session_state.expression = cleaned


# --------------------------------------------------
# CALCULATOR FUNCTIONS
# --------------------------------------------------

def add_token(token: str):
    """Add a number, operator or scientific function."""

    if st.session_state.just_evaluated:

        if token not in ALLOWED_OPERATORS:
            st.session_state.expression = ""

    st.session_state.expression += token

    st.session_state.just_evaluated = False
    st.session_state.last_error = ""


def clear_all():
    """Clear calculator display."""

    st.session_state.expression = ""
    st.session_state.last_result = None
    st.session_state.last_error = ""
    st.session_state.just_evaluated = False


def backspace():
    """Delete the last character."""

    st.session_state.expression = (
        st.session_state.expression[:-1]
    )

    st.session_state.last_error = ""
    st.session_state.just_evaluated = False


def wrap_sqrt():
    """Insert square root function."""

    current = st.session_state.expression.strip()

    if current:
        st.session_state.expression = f"sqrt({current})"
    else:
        st.session_state.expression = "sqrt("

    st.session_state.just_evaluated = False
    st.session_state.last_error = ""


def square_expression():
    """Square the current expression."""

    current = st.session_state.expression.strip()

    if current:
        st.session_state.expression = f"({current})**2"

    st.session_state.just_evaluated = False
    st.session_state.last_error = ""


def insert_answer():
    """Insert the previous calculation result."""

    if st.session_state.last_result is not None:

        add_token(str(st.session_state.last_result))

    else:
        st.session_state.last_error = (
            "There is no previous answer yet."
        )


# --------------------------------------------------
# CALCULATION
# --------------------------------------------------

def run_calculation():

    expression = st.session_state.expression.strip()

    try:

        if not expression:
            raise CalculatorError(
                "Enter an expression first."
            )

        result = evaluate_expression(expression)

        result_text = format_result(result)

        st.session_state.last_result = result
        st.session_state.last_error = ""

        # Save calculation history
        st.session_state.history.insert(
            0,
            {
                "time": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "expression": expression,
                "result": result_text,
            }
        )

        # Keep only the latest 100 calculations
        st.session_state.history = (
            st.session_state.history[:100]
        )

        st.session_state.expression = str(result)

        st.session_state.just_evaluated = True

    except CalculatorError as exc:

        st.session_state.last_error = str(exc)
        st.session_state.last_result = None
        st.session_state.just_evaluated = False

    except Exception:

        st.session_state.last_error = (
            "Unable to calculate this expression."
        )

        st.session_state.last_result = None
        st.session_state.just_evaluated = False


def clear_history():
    st.session_state.history = []


# --------------------------------------------------
# APPEARANCE SELECTOR
# --------------------------------------------------

head_left, head_right = st.columns([3, 1])

with head_left:

    st.markdown(
        '<div class="calc-title", font-size: 40px'
        '>🧮 Calculator</div>',
        unsafe_allow_html=True
    )
    

    st.markdown(
        '<div class="calc-subtitle">'
        'Standard • Scientific Calculator'
        '</div>',
        unsafe_allow_html=True
    )

with head_right:
    st.selectbox(
        "Appearance",
        options=["Light", "Dark"],
        key="appearance",
        label_visibility="collapsed"
    )


    # st.selectbox(
    #     "Appearance",
    #     ["Light", "Dark"],
    #     key="appearance",
    #     label_visibility="collapsed",
    #     help="Choose calculator appearance"
    # )


# --------------------------------------------------
# THEME COLORS
# --------------------------------------------------

dark = st.session_state.appearance == "Dark"
if dark:
    page_bg = "#111827"
    panel_bg = "#1f2937"
    text_color = "#f9fafb"
    muted_color = "#aab4c3"
    input_bg = "#111827"
    button_bg = "#374151"
    border_color = "#374151"

else:
    page_bg = "#f7f8fc"
    panel_bg = "#ffffff"
    text_color = "#172033"
    muted_color = "#7b8494"
    input_bg = "#ffffff"
    button_bg = "#ffffff"
    border_color = "#e2e6ef"


# --------------------------------------------------
# APPLY THEME CSS
# --------------------------------------------------

st.markdown(
    f"""
    <style>

    /* Main application background */

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {{
        background: {page_bg} !important;
        color: {text_color} !important;
    }}

    /* Main content */
    

    [data-testid="stMainBlockContainer"] {{
        background: {page_bg} !important;
    }}

    /* Header */

    [data-testid="stHeader"] {{
        background: {page_bg} !important;
    }}

    /* Calculator panel */
    /* Calculator Title */
.stApp .calc-title {{
    font-size: 60px !important;
    font-weight: 800 !important;
    line-height: 1.3 !important;
    text-align: left !important;
    color: {text_color} !important;
    margin-bottom: 5px !important;
}}

    # [data-testid="stVerticalBlockBorderWrapper"] {{
    #     background: {panel_bg} !important;
    #     border: 1px solid {border_color} !important;
    #     border-radius: 18px !important;
    # }}

    /* All normal text */

    .stApp p,
    .stApp label,
    .stApp span,
    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp .stMarkdown {{
        color: {text_color};
    }}

    /* Secondary text */

    [data-testid="stCaptionContainer"] {{
        color: {muted_color} !important;
    }}

    /* Calculator input */

    [data-testid="stTextInput"] input {{
        background: {input_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
        border-radius: 14px !important;
        caret-color: #3b82f6 !important;
        text-align: right !important;
        font-size: 1.6rem !important;
        font-weight: 600 !important;
    }}

    [data-testid="stTextInput"] input:focus {{
        border: 1px solid #3b82f6 !important;
        box-shadow: 0 0 0 1px #3b82f6 !important;
    }}

    /* Calculator buttons */

    .stButton > button {{
        background: {button_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
        border-radius: 13px !important;
        min-height: 3.4rem;
        font-weight: 650;
    }}

    .stButton > button:hover {{
        border-color: #3b82f6 !important;
        color: #3b82f6 !important;
    }}

    /* Equals button */

    .stButton > button[kind="primary"] {{
        background: #2563eb !important;
        color: white !important;
        border-color: #2563eb !important;
    }}

    /* Scientific functions and history */

    [data-testid="stExpander"] {{
        background: {panel_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px !important;
    }}

    [data-testid="stExpander"] summary {{
        color: {text_color} !important;
    }}

    /* Appearance selector */

    [data-testid="stSelectbox"] div[data-baseweb="select"] {{
        background: {panel_bg} !important;
        color: {text_color} !important;
        border-color: {border_color} !important;
    }}

    [data-testid="stSelectbox"] div[data-baseweb="select"] * {{
        color: {text_color} !important;
    }}

    /* Result */

    .result-value {{
        color: {text_color} !important;
        text-align: right;
        font-size: 2rem;
        font-weight: 750;
    }}

    .result-caption {{
        color: {muted_color} !important;
        text-align: right;
    }}

    /* Mobile */

    @media (max-width: 600px) {{
        .block-container {{
            padding: .65rem .55rem 1.25rem;
        }}

        .stButton > button {{
            min-height: 3rem;
            font-size: 1rem;
        }}

        [data-testid="stTextInput"] input {{
            font-size: 1.35rem !important;
        }}
    }}

    </style>
    """,
    unsafe_allow_html=True
)

# if dark:

#     page_bg = "#111827"
#     panel_bg = "#1f2937"
#     text_color = "#f9fafb"
#     muted_color = "#aab4c3"
#     input_bg = "#111827"
#     border_color = "#374151"
#     button_bg = "#374151"

# else:

#     page_bg = "#f7f8fc"
#     panel_bg = "#ffffff"
#     text_color = "#172033"
#     muted_color = "#7b8494"
#     input_bg = "#ffffff"
#     border_color = "#e2e6ef"
#     button_bg = "#ffffff"


# # --------------------------------------------------
# # CUSTOM CSS
# # --------------------------------------------------

# st.markdown(
#     f"""
#     <style>

#     /* Main application */

#     .stApp {{
#         background-color: {page_bg} !important;
#         color: {text_color} !important;
#     }}

#     .block-container {{
#         max-width: 620px;
#         padding: 1.25rem 1rem 2rem;
#     }}

#     /* Calculator heading */

#     .calc-title {{
#         text-align: center;
#         font-size: 1.45rem;
#         font-weight: 750;
#         color: {text_color};
#         margin: .1rem 0;
#     }}

#     .calc-subtitle {{
#         text-align: center;
#         color: {muted_color};
#         font-size: .86rem;
#         margin-bottom: 1rem;
#     }}

#     /* Calculator display */

#     [data-testid="stTextInput"] input {{
#         text-align: right !important;
#         font-size: 1.7rem !important;
#         font-weight: 600 !important;
#         min-height: 4rem;
#         border-radius: 14px !important;
#         font-variant-numeric: tabular-nums;
#         background-color: {input_bg} !important;
#         color: {text_color} !important;
#         border-color: {border_color} !important;
#         caret-color: #3b82f6 !important;
#     }}

#     [data-testid="stTextInput"] input:focus {{
#         border-color: #3b82f6 !important;
#         box-shadow: 0 0 0 1px #3b82f6 !important;
#     }}

#     /* Buttons */

#     div.stButton > button {{
#         min-height: 3.45rem;
#         border-radius: 13px;
#         font-size: 1.08rem;
#         font-weight: 650;
#         border: 1px solid {border_color};
#         background-color: {button_bg};
#         color: {text_color};
#     }}

#     div.stButton > button:hover {{
#         border-color: #3b82f6;
#         color: #3b82f6;
#     }}

#     /* Primary equals button */

#     div.stButton > button[kind="primary"] {{
#         background-color: #2563eb !important;
#         color: #ffffff !important;
#         border-color: #2563eb !important;
#     }}

#     div.stButton > button[kind="primary"]:hover {{
#         background-color: #1d4ed8 !important;
#     }}

#     /* Calculator panel */

#     [data-testid="stVerticalBlockBorderWrapper"] {{
#         background-color: {panel_bg};
#         border-color: {border_color};
#         border-radius: 18px;
#     }}

#     /* Result */

#     .result-caption {{
#         color: {muted_color};
#         font-size: .82rem;
#         text-align: right;
#         margin-top: .6rem;
#     }}

#     .result-value {{
#         font-size: 2rem;
#         font-weight: 750;
#         text-align: right;
#         color: {text_color};
#         overflow-wrap: anywhere;
#     }}

#     /* Selectbox */

#     [data-testid="stSelectbox"] div[data-baseweb="select"] {{
#         background-color: {panel_bg};
#         color: {text_color};
#     }}

#     /* Spacing */

#     div[data-testid="stHorizontalBlock"] {{
#         gap: .55rem;
#     }}

#     /* Mobile responsive design */

#     @media (max-width: 600px) {{

#         .block-container {{
#             padding: .65rem .55rem 1.25rem;
#         }}

#         div.stButton > button {{
#             min-height: 3rem;
#             font-size: 1rem;
#             padding: .25rem .1rem;
#         }}

#         [data-testid="stTextInput"] input {{
#             min-height: 3.5rem;
#             font-size: 1.35rem !important;
#         }}

#         .calc-title {{
#             font-size: 1.25rem;
#         }}

#     }}

#     </style>
#     """,
#     unsafe_allow_html=True
# )

# --------------------------------------------------
# CALCULATOR DISPLAY WITH EQUALS BUTTON
# --------------------------------------------------

with st.container(border=True):

    st.caption("EXPRESSION")

    display_col, equals_col = st.columns(
        [4, 1],
        vertical_alignment="center"
    )

    with display_col:

        st.text_input(
            "Calculator expression",
            key="expression",
            on_change=sanitize_expression,
            label_visibility="collapsed",
            placeholder="0",
            help=(
                "Enter numbers, operators or supported "
                "scientific functions."
            )
        )

    with equals_col:

        st.button(
            "=",
            key="equals_button",
            type="primary",
            on_click=run_calculation,
            use_container_width=True
        )

    # Error and result display

    if st.session_state.last_error:

        st.error(st.session_state.last_error)

    elif st.session_state.last_result is not None:

        st.caption("RESULT")

        st.markdown(
            f'<div class="result-value">'
            f'{format_result(st.session_state.last_result)}'
            f'</div>',
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            '<div class="result-caption">'
            'Enter an expression to begin'
            '</div>',
            unsafe_allow_html=True
        )


# --------------------------------------------------
# BASIC CALCULATOR KEYPAD
# --------------------------------------------------

key_rows = [

    [
        ("AC", "AC"),
        ("⌫", "BACK"),
        ("(", "("),
        (")", ")")
    ],

    [
        ("7", "7"),
        ("8", "8"),
        ("9", "9"),
        ("÷", "/")
    ],

    [
        ("4", "4"),
        ("5", "5"),
        ("6", "6"),
        ("×", "*")
    ],

    [
        ("1", "1"),
        ("2", "2"),
        ("3", "3"),
        ("−", "-")
    ],

    [
        ("0", "0"),
        (".", "."),
        ("%", "%"),
        ("+", "+")
    ],

]

for row_index, row in enumerate(key_rows):

    cols = st.columns(4)

    for col, (label, token) in zip(cols, row):

        with col:

            if token == "AC":

                st.button(
                    label,
                    key=f"key_{row_index}_{label}",
                    on_click=clear_all,
                    use_container_width=True
                )

            elif token == "BACK":

                st.button(
                    label,
                    key=f"key_{row_index}_{label}",
                    on_click=backspace,
                    use_container_width=True
                )

            else:

                st.button(
                    label,
                    key=f"key_{row_index}_{label}",
                    on_click=add_token,
                    args=(token,),
                    use_container_width=True
                )


# --------------------------------------------------
# SCIENTIFIC CALCULATOR
# --------------------------------------------------

with st.expander("Scientific Functions", expanded=False):

    sci_rows = [

        [
            ("sin", "sin("),
            ("cos", "cos("),
            ("tan", "tan(")
        ],

        [
            ("log", "log("),
            ("ln", "ln("),
            ("abs", "abs(")
        ],

        [
            ("x²", "SQUARE"),
            ("√", "SQRT"),
            ("π", "pi"),
            ("e", "e")
        ],

        [
            ("^", "**"),
            ("Ans", "ANS")
        ],

    ]

    for row_index, row in enumerate(sci_rows):

        cols = st.columns(len(row))

        for col, (label, token) in zip(cols, row):

            with col:

                if token == "ANS":

                    st.button(
                        label,
                        key=f"sci_{row_index}_{label}",
                        on_click=insert_answer,
                        use_container_width=True
                    )

                elif token == "SQUARE":

                    st.button(
                        label,
                        key=f"sci_{row_index}_{label}",
                        on_click=square_expression,
                        use_container_width=True
                    )

                elif token == "SQRT":

                    st.button(
                        label,
                        key=f"sci_{row_index}_{label}",
                        on_click=wrap_sqrt,
                        use_container_width=True
                    )

                else:

                    st.button(
                        label,
                        key=f"sci_{row_index}_{label}",
                        on_click=add_token,
                        args=(token,),
                        use_container_width=True
                    )


# --------------------------------------------------
# SUPPORTED OPERATIONS
# --------------------------------------------------

st.caption(
    "Supported: +, −, ×, ÷, %, **, parentheses, "
    "sqrt(), sin(), cos(), tan(), log(), ln(), "
    "abs(), pi, e."
)


# --------------------------------------------------
# CALCULATION HISTORY
# --------------------------------------------------

with st.expander(
    f"History ({len(st.session_state.history)})",
    expanded=False
):

    if st.session_state.history:

        for item in st.session_state.history:

            st.markdown(
                f"**{item['expression']} = {item['result']}**"
            )

            st.caption(item["time"])
            st.divider()

        # CSV download

        buffer = io.StringIO()

        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "time",
                "expression",
                "result"
            ]
        )

        writer.writeheader()
        writer.writerows(st.session_state.history)

        st.download_button(
            "Download History as CSV",
            data=buffer.getvalue(),
            file_name="calculator_history.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.button(
            "Clear History",
            on_click=clear_history,
            use_container_width=True
        )

    else:

        st.caption(
            "Your calculations will appear here."
        )


# --------------------------------------------------
# SIDEBAR HELP
# --------------------------------------------------

# with st.sidebar:

#     st.subheader("How to Use")

#     st.write(
#         "Use the keypad or type an expression "
#         "in the calculator display."
#     )

#     st.write("Press = to calculate.")

#     st.write("Examples:")

#     st.code(
#         "2 + 3 * 4\n"
#         "(2 + 3) * 4\n"
#         "sqrt(25)\n"
#         "sin(30)\n"
#         "100 / 4 + 6**2"
#     )

#     st.write(
#         "Standard mathematical precedence applies. "
#         "Parentheses can change the calculation order."
#     )
# """Responsive calculator app built with Streamlit."""
# from datetime import datetime
# import csv
# import io
# import re

# import streamlit as st
# from calculator import CalculatorError, evaluate_expression, format_result

# st.set_page_config(
#     page_title="Calculator",
#     page_icon="🧮",
#     layout="centered",
#     initial_sidebar_state="collapsed",
# )

# DEFAULTS = {
#     "expression": "",
#     "history": [],
#     "last_result": None,
#     "last_error": "",
#     "just_evaluated": False,
#     "appearance": "Light",
# }
# for key, value in DEFAULTS.items():
#     if key not in st.session_state:
#         st.session_state[key] = value

# ALLOWED_NAMES = {"sqrt", "sin", "cos", "tan", "log", "ln", "abs", "pi", "e"}


# def sanitize_expression():
#     """Allow only calculator numbers and operators."""
#     raw = st.session_state.expression

#     cleaned = re.sub(
#         r"[^0-9+\-*/().%\s]",
#         "",
#         raw
#     )

#     st.session_state.expression = cleaned
# # def sanitize_expression():
# #     """Keep only calculator characters and supported function/constants."""
# #     raw = st.session_state.expression
# #     cleaned = re.sub(r"[^0-9A-Za-z+\-*/().%\s]", "", raw)
# #     cleaned = re.sub(
# #         r"[A-Za-z]+",
# #         lambda match: match.group(0) if match.group(0) in ALLOWED_NAMES else "",
# #         cleaned,
# #     )
# #     st.session_state.expression = cleaned


# def add_token(token: str):
#     if st.session_state.just_evaluated and token not in ("+", "-", "*", "/", "%", "**"):
#         st.session_state.expression = ""
#     st.session_state.expression += token
#     st.session_state.just_evaluated = False
#     st.session_state.last_error = ""


# def clear_all():
#     st.session_state.expression = ""
#     st.session_state.last_result = None
#     st.session_state.last_error = ""
#     st.session_state.just_evaluated = False


# def backspace():
#     st.session_state.expression = st.session_state.expression[:-1]
#     st.session_state.last_error = ""
#     st.session_state.just_evaluated = False


# def wrap_sqrt():
#     current = st.session_state.expression.strip()
#     st.session_state.expression = f"sqrt({current})" if current else "sqrt("
#     st.session_state.just_evaluated = False
#     st.session_state.last_error = ""


# def square_expression():
#     current = st.session_state.expression.strip()
#     if current:
#         st.session_state.expression = f"({current})**2"
#     st.session_state.just_evaluated = False
#     st.session_state.last_error = ""


# def insert_answer():
#     if st.session_state.last_result is not None:
#         add_token(str(st.session_state.last_result))
#     else:
#         st.session_state.last_error = "There is no previous answer yet."


# def run_calculation():
#     expression = st.session_state.expression.strip()
#     try:
#         if not expression:
#             raise CalculatorError("Enter an expression first.")
#         result = evaluate_expression(expression)
#         result_text = format_result(result)
#         st.session_state.last_result = result
#         st.session_state.last_error = ""
#         st.session_state.history.insert(0, {
#             "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#             "expression": expression,
#             "result": result_text,
#         })
#         st.session_state.history = st.session_state.history[:100]
#         st.session_state.expression = str(result)
#         st.session_state.just_evaluated = True
#     except CalculatorError as exc:
#         st.session_state.last_error = str(exc)
#         st.session_state.last_result = None
#         st.session_state.just_evaluated = False
#     except Exception:
#         st.session_state.last_error = "Unable to calculate this expression."
#         st.session_state.last_result = None
#         st.session_state.just_evaluated = False


# def clear_history():
#     st.session_state.history = []


# # Appearance selector
# head_left, head_right = st.columns([3, 1])
# with head_left:
#     st.markdown('<div class="calc-title">🧮 Calculator</div>', unsafe_allow_html=True)
#     st.markdown(
#         '<div class="calc-subtitle">Standard • Multi-step expressions</div>',
#         unsafe_allow_html=True,
#     )
# with head_right:
#     st.selectbox(
#         "Appearance",
#         ["Light", "Dark"],
#         key="appearance",
#         label_visibility="collapsed",
#         help="Choose light or dark appearance",
#     )

# dark = st.session_state.appearance == "Dark"
# if dark:
#     page_bg = "#111827"
#     panel_bg = "#1f2937"
#     text_color = "#f9fafb"
#     muted_color = "#aab4c3"
#     input_bg = "#111827"
#     border_color = "#374151"
#     button_bg = "#374151"
# else:
#     page_bg = "#f7f8fc"
#     panel_bg = "#ffffff"
#     text_color = "#172033"
#     muted_color = "#7b8494"
#     input_bg = "#ffffff"
#     border_color = "#e2e6ef"
#     button_bg = "#ffffff"
# # if dark:
# #     page_bg = "#111827"
# #     panel_bg = "#1f2937"
# #     text_color = "#f9fafb"
# #     muted_color = "#aab4c3"
# #     input_bg = "#111827"
# #     border_color = "#374151"
# # else:
# #     # pass
# #     page_bg = "#f7f8fc"
# #     panel_bg = "#ffffff"
# #     text_color = "#172033"
# #     muted_color = "#7b8494"
# #     input_bg = "#ffffff"
# #     border_color = "#e2e6ef"

# st.markdown(
#     f"""
#     <style>
#       .stApp {{ background: {page_bg}; color: {text_color}; }}
#       .block-container {{ max-width: 620px; padding: 1.25rem 1rem 2rem; }}
#       .calc-title {{ text-align:center; font-size:1.45rem; font-weight:750;
#                      color:{text_color}; margin:.1rem 0; }}
#       .calc-subtitle {{ text-align:center; color:{muted_color}; font-size:.86rem;
#                         margin-bottom:1rem; }}
#       div[data-testid="stTextInput"] input {{
#         text-align:right; font-size:1.7rem; font-weight:600; min-height:4rem;
#         border-radius:14px; font-variant-numeric:tabular-nums;
#         background:{input_bg}; color:{text_color}; border_color:{border_color};
#         caret-color:#3b82f6;
#       }}
#       div.stButton > button {{
#         min-height:3.45rem; border-radius:13px; font-size:1.08rem;
#         font-weight:650; border:1px solid {border_color};
#       }}
#       div[data-testid="stHorizontalBlock"] {{ gap:.55rem; }}
#       .result-caption {{ color:{muted_color}; font-size:.82rem;
#                          text-align:right; margin-top:.6rem; }}
#       .result-value {{ font-size:2rem; font-weight:750; text-align:right;
#                        color:{text_color}; overflow-wrap:anywhere; }}
#       div[data-testid="stVerticalBlockBorderWrapper"] {{
#         background:{panel_bg}; border-color:{border_color};
#         border-radius:18px;
#       }}
#       @media (max-width: 600px) {{
#         .block-container {{ padding:.65rem .55rem 1.25rem; }}
#         div.stButton > button {{ min-height:3rem; font-size:1rem;
#                                  padding:.25rem .1rem; }}
#         div[data-testid="stTextInput"] input {{ min-height:3.5rem;
#                                                font-size:1.45rem; }}
#         .calc-title {{ font-size:1.25rem; }}
#       }}
#     </style>
#     """,
#     unsafe_allow_html=True,
# )

# with st.container(border=True):
#     st.caption("EXPRESSION")
#     st.text_input(
#         "Calculator expression",
#         key="expression",
#         on_change=sanitize_expression,
#         label_visibility="collapsed",
#         placeholder="0",
#         help=(
#             "Enter numbers, operators, parentheses, or supported functions. "
#             "Unsupported characters are removed."
#         ),
#     )
#     if st.session_state.last_error:
#         st.error(st.session_state.last_error)
#     elif st.session_state.last_result is not None:
#         st.caption("RESULT")
#         st.markdown(
#             f'<div class="result-value">{format_result(st.session_state.last_result)}</div>',
#             unsafe_allow_html=True,
#         )
#     else:
#         st.markdown(
#             '<div class="result-caption">Enter an expression to begin</div>',
#             unsafe_allow_html=True,
#         )

# # The equals key is in the conventional bottom-right keypad position.
# key_rows = [
#     [("AC", "AC"), ("⌫", "BACK"), ("(", "("), (")", ")")],
#     [("7", "7"), ("8", "8"), ("9", "9"), ("÷", "/")],
#     [("4", "4"), ("5", "5"), ("6", "6"), ("×", "*")],
#     [("1", "1"), ("2", "2"), ("3", "3"), ("−", "-")],
#     [("0", "0"), (".", "."), ("%", "%"), ("+", "+")],
# ]
# for row_index, row in enumerate(key_rows):
#     cols = st.columns(4)
#     for col, (label, token) in zip(cols, row):
#         with col:
#             if token == "AC":
#                 st.button(label, key=f"key_{row_index}_{label}",
#                           on_click=clear_all, use_container_width=True)
#             elif token == "BACK":
#                 st.button(label, key=f"key_{row_index}_{label}",
#                           on_click=backspace, use_container_width=True)
#             else:
#                 st.button(label, key=f"key_{row_index}_{label}",
#                           on_click=add_token, args=(token,),
#                           use_container_width=True)

# # Scientific keys
# with st.expander("Scientific functions"):
#     sci_rows = [
#         [("sin", "sin("), ("cos", "cos("), ("tan", "tan(")],
#         [("log", "log("), ("ln", "ln("), ("abs", "abs(")],
#         [("x²", "SQUARE"), ("√", "SQRT"), ("π", "pi"), ("e", "e")],
#         [("^", "**"), ("Ans", "ANS")],
#     ]
#     for row_index, row in enumerate(sci_rows):
#         cols = st.columns(len(row))
#         for col, (label, token) in zip(cols, row):
#             with col:
#                 if token == "ANS":
#                     st.button(label, key=f"sci_{row_index}_{label}",
#                               on_click=insert_answer, use_container_width=True)
#                 elif token == "SQUARE":
#                     st.button(label, key=f"sci_{row_index}_{label}",
#                               on_click=square_expression, use_container_width=True)
#                 elif token == "SQRT":
#                     st.button(label, key=f"sci_{row_index}_{label}",
#                               on_click=wrap_sqrt, use_container_width=True)
#                 else:
#                     st.button(label, key=f"sci_{row_index}_{label}",
#                               on_click=add_token, args=(token,),
#                               use_container_width=True)

# # Equals occupies the bottom-right position, like a desktop calculator.
# equals_cols = st.columns(4)
# with equals_cols[3]:
#     st.button("=", type="primary", on_click=run_calculation,
#               use_container_width=True)

# st.caption(
#     "Supported: +, −, ×, ÷, %, **, parentheses, sqrt(), sin(), cos(), "
#     "tan(), log(), ln(), abs(), pi, e."
# )

# with st.expander(f"History ({len(st.session_state.history)})", expanded=False):
#     if st.session_state.history:
#         for item in st.session_state.history:
#             st.markdown(f"**{item['expression']} = {item['result']}**")
#             st.caption(item["time"])
#             st.divider()
#         buffer = io.StringIO()
#         writer = csv.DictWriter(buffer, fieldnames=["time", "expression", "result"])
#         writer.writeheader()
#         writer.writerows(st.session_state.history)
#         st.download_button(
#             "Download history as CSV",
#             data=buffer.getvalue(),
#             file_name="calculator_history.csv",
#             mime="text/csv",
#             use_container_width=True,
#         )
#         st.button("Clear history", on_click=clear_history, use_container_width=True)
#     else:
#         st.caption("Your calculations will appear here.")

# with st.sidebar:
#     st.subheader("How to use")
#     st.write("Use the keypad or type an expression in the display. Press **=** to calculate.")
#     st.write("Examples:")
#     st.code("2 + 3 * 4\n(2 + 3) * 4\n100 / 4 + 6**2")
#     st.write(
#         "Standard precedence applies: multiplication and division happen before "
#         "addition and subtraction, unless parentheses change the order."
#     )
