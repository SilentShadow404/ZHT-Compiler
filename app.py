import sys
import re
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from zht_compiler.compiler_engine import CompilerEngine
from zht_compiler.semantics import SemanticAnalyzer

# ─── Page Config (must be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title="ZHT Compiler Studio",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #08101e; }
[data-testid="stSidebar"] { background: #0d1a2d !important; border-right: 1px solid #1e3a5f; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Header ── */
.zht-header {
    background: linear-gradient(135deg, #0d1f40 0%, #0a1628 100%);
    border: 1px solid #1e3a5f; border-radius: 12px;
    padding: 18px 26px; margin-bottom: 18px;
    display: flex; align-items: center; gap: 14px;
}
.zht-header-title { font-size: 1.8rem; font-weight: 700; color: #e2e8f0; margin: 0; }
.zht-header-sub   { font-size: 0.82rem; color: #64b5f6; margin-top: 2px; }
.zht-badge {
    margin-left: auto; background: #132f4c; border: 1px solid #1e4976;
    color: #64b5f6; font-size: 0.7rem; font-weight: 600;
    padding: 4px 10px; border-radius: 20px; letter-spacing: 0.5px;
    white-space: nowrap;
}

/* ── Section labels ── */
.zht-label {
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.2px; color: #64b5f6; margin-bottom: 6px;
    display: flex; align-items: center; gap: 5px;
}

/* ── Console ── */
.zht-console-bar {
    background: #0a1628; border: 1px solid #1a3350;
    border-radius: 8px 8px 0 0; padding: 7px 14px;
    display: flex; align-items: center; gap: 6px;
}
.zht-dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; }
.zht-dot-r { background: #ff5f57; }
.zht-dot-y { background: #febc2e; }
.zht-dot-g { background: #28c840; }
.zht-console-lbl { font-size: 0.7rem; color: #3d6080; font-family: 'JetBrains Mono', monospace; margin-left: 4px; }
.zht-console {
    background: #050d18; border: 1px solid #1a3350; border-top: none;
    border-radius: 0 0 8px 8px; padding: 14px 16px; min-height: 190px;
    font-family: 'JetBrains Mono', monospace; font-size: 0.84rem;
    color: #a8d8a0; white-space: pre-wrap; line-height: 1.65;
}
.zht-console-empty { color: #2d4a6e; font-style: italic; }

/* ── Banners ── */
.zht-success {
    background: #0a1f16; border: 1px solid #0f4a2a;
    border-left: 4px solid #00c9a7; border-radius: 8px;
    padding: 10px 16px; color: #a0f0d8; font-size: 0.82rem; margin-top: 10px;
}
.zht-error-box {
    background: #1a0d0d; border: 1px solid #5c1a1a;
    border-left: 4px solid #ff4757; border-radius: 8px;
    padding: 12px 16px; margin-top: 10px;
}
.zht-error-title { color: #ff6b6b; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }
.zht-error-item { color: #ffaaaa; font-size: 0.82rem; font-family: 'JetBrains Mono', monospace; padding: 3px 0; }
.zht-error-item::before { content: "✗ "; color: #ff4757; }

/* ── Input section ── */
.zht-input-box {
    background: #0d1a2d; border: 1px solid #1e3a5f;
    border-left: 4px solid #ffb347; border-radius: 8px;
    padding: 12px 16px; margin-top: 10px;
}
.zht-input-title { color: #ffb347; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }

/* ── Stats ── */
.zht-stats { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.zht-stat {
    background: #0d1a2d; border: 1px solid #1e3a5f; border-radius: 8px;
    padding: 7px 12px; text-align: center; flex: 1; min-width: 70px;
}
.zht-stat-val { font-size: 1.2rem; font-weight: 700; color: #64b5f6; font-family: 'JetBrains Mono', monospace; }
.zht-stat-lbl { font-size: 0.62rem; color: #4a7cb5; text-transform: uppercase; letter-spacing: 0.7px; margin-top: 2px; }

/* ── Token table ── */
.tok-table { width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono', monospace; font-size: 0.79rem; }
.tok-table th { background: #0d1a2d; color: #64b5f6; font-size: 0.64rem; text-transform: uppercase; letter-spacing: 0.8px; padding: 8px 10px; border-bottom: 1px solid #1e3a5f; text-align: left; }
.tok-table td { padding: 4px 10px; border-bottom: 1px solid #0f2035; color: #c8daf0; }
.tok-table tr:hover td { background: #0f2035; }
.tok-kw  { color: #c792ea !important; font-weight: 600; }
.tok-ty  { color: #82aaff !important; font-weight: 600; }
.tok-lit { color: #c3e88d !important; }
.tok-op  { color: #f78c6c !important; }
.tok-id  { color: #89ddff !important; }
.tok-pun { color: #676e95 !important; }
.tok-eof { color: #3d5369 !important; font-style: italic; }

/* ── IR ── */
.zht-ir {
    background: #050d18; border: 1px solid #1a3350; border-radius: 8px;
    padding: 14px 16px; font-family: 'JetBrains Mono', monospace;
    font-size: 0.81rem; line-height: 1.7; color: #9ec5fe;
    overflow: auto; white-space: pre; max-height: 460px;
}
.ir-fn  { color: #c792ea; font-weight: 700; }
.ir-lbl { color: #ffcb6b; }
.ir-jmp { color: #f78c6c; }
.ir-al  { color: #82aaff; }
.ir-io  { color: #c3e88d; }

/* ── AST / Sym ── */
.zht-ast {
    background: #050d18; border: 1px solid #1a3350; border-radius: 8px;
    padding: 14px 16px; font-family: 'JetBrains Mono', monospace;
    font-size: 0.79rem; color: #c8daf0; line-height: 1.6;
    white-space: pre; overflow: auto; max-height: 460px;
}
.sym-table { width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono', monospace; font-size: 0.79rem; }
.sym-table th { background: #0d1a2d; color: #64b5f6; font-size: 0.64rem; text-transform: uppercase; letter-spacing: 0.8px; padding: 8px 10px; border-bottom: 1px solid #1e3a5f; text-align: left; }
.sym-table td { padding: 5px 10px; border-bottom: 1px solid #0f2035; color: #c8daf0; }
.sym-table tr:hover td { background: #0f2035; }
.sym-fn  { color: #c792ea !important; }
.sym-arr { color: #82aaff !important; }
.sym-var { color: #89ddff !important; }
.sym-typ { color: #c3e88d !important; }

/* ── Divider ── */
.zht-hr { border: none; border-top: 1px solid #1a3350; margin: 14px 0; }

/* ── Widget overrides ── */
.stTextArea textarea {
    background: #050d18 !important; border: 1px solid #1e3a5f !important;
    color: #e2e8f0 !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.84rem !important; line-height: 1.6 !important;
    border-radius: 8px !important;
}
.stTextInput input {
    background: #050d18 !important; border: 1px solid #1e3a5f !important;
    color: #e2e8f0 !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important; border-radius: 8px !important;
}
.stSelectbox > div > div {
    background: #050d18 !important; border: 1px solid #1e3a5f !important;
    color: #e2e8f0 !important; border-radius: 8px !important;
}
.stButton button {
    background: linear-gradient(135deg, #0055b3, #0070e0) !important;
    color: white !important; border: none !important; border-radius: 8px !important;
    font-weight: 700 !important; font-size: 0.86rem !important;
    box-shadow: 0 4px 12px rgba(0,112,224,.35) !important; transition: all .2s;
}
.stButton button:hover {
    background: linear-gradient(135deg, #0066cc, #0088ff) !important;
    transform: translateY(-1px);
}
.stTextArea label, .stTextInput label, .stSelectbox label {
    color: #4a7cb5 !important; font-size: 0.71rem !important;
    font-weight: 600 !important; text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}
[data-testid="stTabs"] button { font-size: 0.78rem !important; font-weight: 600 !important; color: #4a7cb5 !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #64b5f6 !important; }

/* ── Sidebar ── */
.sb-section { background: #0a1628; border: 1px solid #1a3350; border-radius: 8px; padding: 11px 13px; margin-bottom: 10px; }
.sb-title { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #64b5f6; margin-bottom: 7px; }
.sb-kw { display: inline-block; background: #132f4c; color: #82aaff; font-family: 'JetBrains Mono', monospace; font-size: 0.71rem; padding: 2px 7px; border-radius: 4px; margin: 2px; border: 1px solid #1e4976; }
</style>
""", unsafe_allow_html=True)

# ─── Samples ────────────────────────────────────────────────────────────────
SAMPLES = {
    "── Select a Sample ──": "",

    "1 · Bubble Sort  (Arrays + Nested Loops)": """\
whole main() {
    whole arr[6];
    arr[0] = 64;
    arr[1] = 34;
    arr[2] = 25;
    arr[3] = 12;
    arr[4] = 22;
    arr[5] = 11;
    whole n = 6;
    whole temp = 0;
    whole i = 0;
    whole j = 0;
    range(i = 0; i < n; i = i + 1) {
        range(j = 0; j < n - i - 1; j = j + 1) {
            when (arr[j] > arr[j + 1]) {
                temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
    show("Sorted array (ascending):");
    range(i = 0; i < n; i = i + 1) {
        show(arr[i]);
    }
}
""",

    "2 · Fibonacci  (Recursion + Range Loop)": """\
whole fibonacci(whole n) {
    when (n <= 1) {
        give n;
    }
    give fibonacci(n - 1) + fibonacci(n - 2);
}

whole main() {
    show("--- Fibonacci Sequence (first 10) ---");
    whole i = 0;
    range(i = 0; i < 10; i = i + 1) {
        show(fibonacci(i));
    }
    show("--- Done ---");
}
""",

    "3 · FizzBuzz  (While Loop + Flag Types)": """\
whole main() {
    show("FizzBuzz from 1 to 20:");
    whole i = 1;
    loop (i <= 20) {
        flag fizz = i % 3 == 0;
        flag buzz = i % 5 == 0;
        when (fizz && buzz) {
            show("FizzBuzz");
        } otherwise {
            when (fizz) {
                show("Fizz");
            } otherwise {
                when (buzz) {
                    show("Buzz");
                } otherwise {
                    show(i);
                }
            }
        }
        i = i + 1;
    }
    show("Done.");
}
""",

    "4 · Grade Calculator  (scan + when/otherwise)": """\
whole main() {
    show("=== Grade Calculator ===");
    show("Enter 5 exam scores below.");
    whole s1 = 0;
    whole s2 = 0;
    whole s3 = 0;
    whole s4 = 0;
    whole s5 = 0;
    scan(s1);
    scan(s2);
    scan(s3);
    scan(s4);
    scan(s5);
    whole avg = (s1 + s2 + s3 + s4 + s5) / 5;
    show("Average:");
    show(avg);
    when (avg >= 90) {
        show("Grade: A  -- Excellent!");
    } otherwise {
        when (avg >= 80) {
            show("Grade: B  -- Good");
        } otherwise {
            when (avg >= 70) {
                show("Grade: C  -- Average");
            } otherwise {
                when (avg >= 60) {
                    show("Grade: D  -- Below Average");
                } otherwise {
                    show("Grade: F  -- Fail");
                }
            }
        }
    }
}
""",

    "5 · Semantic Error Demo  (Undeclared + Type Mismatch)": """\
whole add(whole a, whole b) {
    give a + b;
}

whole main() {
    whole result = add(10, 20);
    show("Sum is:");
    show(result);
    show(undefined_var);
    text name = "ZHT";
    whole wrong = name;
}
""",
}

# ─── Global engine ───────────────────────────────────────────────────────────
_engine = CompilerEngine()

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _count_scans(src: str) -> int:
    """Count scan() call sites in the source (regex-based, fast)."""
    return len(re.findall(r'\bscan\s*\(', src))


def _tok_class(name: str) -> str:
    if name in ("WHOLE", "REAL", "LETTER", "TEXT", "FLAG", "EMPTY"):
        return "tok-ty"
    if name in ("WHEN", "OTHERWISE", "CHOOSE", "CASE", "DEFAULT",
                "LOOP", "RANGE", "BREAK", "SKIP", "GIVE", "SCAN", "SHOW"):
        return "tok-kw"
    if "LITERAL" in name:
        return "tok-lit"
    if name == "IDENTIFIER":
        return "tok-id"
    if name == "EOF":
        return "tok-eof"
    if name in ("PLUS", "MINUS", "STAR", "SLASH", "PERCENT",
                "ASSIGN", "EQ", "NEQ", "LT", "LTE", "GT", "GTE",
                "AND", "OR", "NOT"):
        return "tok-op"
    return "tok-pun"


def render_tokens(tokens):
    if not tokens:
        st.markdown('<p style="color:#2d4a6e;font-style:italic">No tokens.</p>',
                    unsafe_allow_html=True)
        return
    rows = ""
    for i, t in enumerate(tokens, 1):
        tn  = t.type.name if hasattr(t.type, "name") else str(t.type)
        css = _tok_class(tn)
        lex = str(t.lexeme).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lit = t.literal if t.literal is not None else ""
        rows += (
            f"<tr><td style='color:#3d5369'>{i}</td>"
            f"<td class='{css}'>{tn}</td>"
            f"<td class='{css}'>{lex}</td>"
            f"<td style='color:#546a7b'>{t.line}</td>"
            f"<td style='color:#546a7b'>{t.column}</td>"
            f"<td style='color:#a8c8a0;font-size:.74rem'>{lit}</td></tr>"
        )
    st.markdown(
        "<div style='overflow:auto;max-height:450px'>"
        "<table class='tok-table'><thead><tr>"
        "<th>#</th><th>Type</th><th>Lexeme</th>"
        "<th>Line</th><th>Col</th><th>Literal</th>"
        "</tr></thead><tbody>" + rows + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_ast(ast):
    if ast is None:
        st.markdown('<p style="color:#2d4a6e;font-style:italic">No AST.</p>',
                    unsafe_allow_html=True)
        return
    try:
        text = ast.pretty()
    except Exception:
        text = repr(ast)
    esc = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    st.markdown(f"<div class='zht-ast'>{esc}</div>", unsafe_allow_html=True)


def render_symbol_table(ast):
    if ast is None:
        st.markdown('<p style="color:#2d4a6e;font-style:italic">No AST.</p>',
                    unsafe_allow_html=True)
        return
    sem = SemanticAnalyzer()
    try:
        sem.analyze(ast)
    except Exception as exc:
        st.markdown(f'<p style="color:#ff6b6b">Symbol table error: {exc}</p>',
                    unsafe_allow_html=True)
        return
    syms = sem.global_scope.symbols
    if not syms:
        st.markdown('<p style="color:#2d4a6e;font-style:italic">Empty symbol table.</p>',
                    unsafe_allow_html=True)
        return
    rows = ""
    for name, sym in syms.items():
        if sym.is_func:
            cat, css = "function", "sym-fn"
            params = ", ".join(str(p) for p in sym.param_types) if sym.param_types else "—"
            typ_d  = f"func({params}) → {sym.ret_type}"
            size   = "—"
        elif sym.size:
            cat, css = "array", "sym-arr"
            typ_d, size = sym.typ, str(sym.size)
        else:
            cat, css = "variable", "sym-var"
            typ_d, size = sym.typ, "—"
        rows += (
            f"<tr><td class='{css}'>{name}</td>"
            f"<td class='sym-typ'>{typ_d}</td>"
            f"<td style='color:#546a7b;text-transform:capitalize'>{cat}</td>"
            f"<td style='color:#546a7b'>{size}</td></tr>"
        )
    st.markdown(
        "<div style='overflow:auto;max-height:450px'>"
        "<table class='sym-table'><thead><tr>"
        "<th>Name</th><th>Type / Signature</th><th>Category</th><th>Array Size</th>"
        "</tr></thead><tbody>" + rows + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_ir(ir):
    if ir is None:
        st.markdown('<p style="color:#2d4a6e;font-style:italic">IR not generated.</p>',
                    unsafe_allow_html=True)
        return
    instrs = getattr(ir, "instructions", [])
    if not instrs:
        st.markdown('<p style="color:#2d4a6e;font-style:italic">Empty IR.</p>',
                    unsafe_allow_html=True)
        return
    lines_html = ""
    for i, instr in enumerate(instrs, 1):
        parts = instr.strip().split()
        op  = parts[0] if parts else ""
        esc = instr.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        num = f"<span style='color:#2d4a6e;user-select:none;margin-right:14px'>{i:3d}</span>"
        if op in ("function", "endfunc"):
            body = f"<span class='ir-fn'>{esc}</span>"
        elif op == "label":
            body = f"<span class='ir-lbl'>{esc}:</span>"
        elif op in ("goto", "if_false"):
            body = f"<span class='ir-jmp'>{esc}</span>"
        elif op in ("alloc", "alloc_array", "param_decl"):
            body = f"<span class='ir-al'>{esc}</span>"
        elif op in ("print", "scan", "scani"):
            body = f"<span class='ir-io'>{esc}</span>"
        else:
            body = f"<span style='color:#9ec5fe'>{esc}</span>"
        lines_html += f"<div>{num}{body}</div>"
    st.markdown(f"<div class='zht-ir'>{lines_html}</div>", unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────────────────────
def render_sidebar():
    st.sidebar.markdown(
        "<h2 style='color:#64b5f6;font-size:1.05rem;font-weight:700;margin-bottom:2px'>"
        "⚙️ ZHT Language Reference</h2>"
        "<p style='color:#2d4a6e;font-size:0.73rem;margin-bottom:12px'>"
        "Custom C-like compiled language</p>",
        unsafe_allow_html=True,
    )

    def sec(title, html):
        st.sidebar.markdown(
            f"<div class='sb-section'><div class='sb-title'>{title}</div>{html}</div>",
            unsafe_allow_html=True,
        )

    def kws(*words):
        return " ".join(f"<span class='sb-kw'>{w}</span>" for w in words)

    sec("Data Types", f"""
        <table style='width:100%;font-size:.73rem;color:#94a3b8;border-collapse:collapse'>
        <tr><td>{kws('whole')}</td><td>Integer</td></tr>
        <tr><td>{kws('real')}</td><td>Float</td></tr>
        <tr><td>{kws('letter')}</td><td>Char</td></tr>
        <tr><td>{kws('text')}</td><td>String</td></tr>
        <tr><td>{kws('flag')}</td><td>Boolean: yes/no</td></tr>
        <tr><td>{kws('empty')}</td><td>Void</td></tr>
        </table>""")

    sec("Declarations", """
        <code style='font-size:.73rem;color:#c3e88d;font-family:JetBrains Mono,monospace'>
        whole x = 10;<br>real pi = 3.14;<br>
        flag done = no;<br>text msg = "hi";<br>
        whole arr[5];
        </code>""")

    sec("Control Flow", f"""
        <p style='color:#546a7b;font-size:.72rem;margin:0 0 4px'>Conditional:</p>
        <code style='font-size:.72rem;color:#c3e88d;font-family:JetBrains Mono,monospace'>
        {kws('when')} (cond) {{ }} {kws('otherwise')} {{ }}
        </code>""")

    sec("Loops", f"""
        <code style='font-size:.72rem;color:#c3e88d;font-family:JetBrains Mono,monospace'>
        loop (i &lt; 10) {{ ... }}<br><br>
        range(i=0; i&lt;n; i=i+1) {{ ... }}
        </code>
        <p style='color:#546a7b;font-size:.72rem;margin:6px 0 0'>{kws('break')} {kws('skip')}</p>""")

    sec("Functions", f"""
        <code style='font-size:.72rem;color:#c3e88d;font-family:JetBrains Mono,monospace'>
        whole add(whole a, whole b) {{<br>
        &nbsp; give a + b;<br>
        }}
        </code>""")

    sec("I/O", f"""
        <code style='font-size:.72rem;color:#c3e88d;font-family:JetBrains Mono,monospace'>
        scan(variable);<br>show(expression);
        </code>
        <p style='color:#546a7b;font-size:.71rem;margin:5px 0 0'>
        Each {kws('scan')} reads the next runtime input in order.</p>""")

    sec("Operators", """
        <table style='width:100%;font-size:.72rem;color:#94a3b8;border-collapse:collapse'>
        <tr><td style='color:#64b5f6'>Arithmetic</td><td>+ - * / %</td></tr>
        <tr><td style='color:#64b5f6'>Compare</td><td>== != &lt; &gt; &lt;= &gt;=</td></tr>
        <tr><td style='color:#64b5f6'>Logical</td><td>&amp;&amp; || !</td></tr>
        </table>""")

    sec("Rules", """
        <ul style='color:#546a7b;font-size:.72rem;padding-left:15px;margin:0;line-height:1.8'>
        <li>Every statement ends with <code style='color:#c3e88d'>;</code></li>
        <li>Blocks use <code style='color:#c3e88d'>{ }</code></li>
        <li><code style='color:#c3e88d'>main()</code> is the entry point</li>
        <li>Arrays are 0-indexed</li>
        <li>Comments: <code style='color:#c3e88d'>// ...</code> or <code style='color:#c3e88d'>/* */</code></li>
        </ul>""")

    st.sidebar.markdown(
        "<div style='margin-top:14px;padding:9px;background:#0a1628;border-radius:8px;"
        "border:1px solid #1a3350;text-align:center'>"
        "<span style='color:#2d4a6e;font-size:.68rem'>ZHT Compiler Studio v2.0</span><br>"
        "<span style='color:#1a3350;font-size:.63rem'>Lexer · Parser · Semantics · IR · Runtime</span>"
        "</div>",
        unsafe_allow_html=True,
    )



# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    render_sidebar()

    # ── Sample-change callback (fires before widgets render on rerun) ──────────
    def _load_sample():
        sel = st.session_state.get("sample_sel", "")
        if sel and sel != "── Select a Sample ──":
            st.session_state["editor_area"] = SAMPLES[sel]
            st.session_state["phase"]      = "idle"
            st.session_state["last_comp"]  = None
            st.session_state["output"]     = None
            st.session_state["status"]     = None
            st.session_state["errors"]     = []

    # ── Init session state ────────────────────────────────────────────────────
    defaults = {
        "editor_area": SAMPLES["1 · Bubble Sort  (Arrays + Nested Loops)"],
        "phase":       "idle",       # idle | compiled | awaiting_input | ran
        "last_comp":   None,
        "scan_count":  0,
        "output":      None,
        "status":      None,
        "errors":      [],
        "error_phase": "",
        "stats":       {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        "<div class='zht-header'>"
        "<div style='font-size:2.2rem'>⚙️</div>"
        "<div>"
        "<div class='zht-header-title'>ZHT Compiler Studio</div>"
        "<div class='zht-header-sub'>"
        "Lexical Analysis · Parsing · Semantic Analysis · IR Generation · Runtime Interpreter"
        "</div></div>"
        "<div class='zht-badge'>ZHT Language v2.0</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Two-column layout ─────────────────────────────────────────────────────
    left, right = st.columns([11, 10], gap="large")

    # ══════════════════════════════════════════════════════════════════════════
    # LEFT — Editor
    # ══════════════════════════════════════════════════════════════════════════
    with left:
        # Sample loader — selecting from dropdown loads code immediately
        st.markdown("<div class='zht-label'>📁 Load Sample Program</div>",
                    unsafe_allow_html=True)
        sample_keys = list(SAMPLES.keys())
        st.selectbox("Sample Program", sample_keys, key="sample_sel",
                     on_change=_load_sample, label_visibility="collapsed")
        st.markdown(
            "<p style='color:#2d4a6e;font-size:.71rem;margin:-4px 0 8px'>Select a sample to load it into the editor instantly.</p>",
            unsafe_allow_html=True,
        )

        st.markdown("<hr class='zht-hr'>", unsafe_allow_html=True)

        # Full-width editor
        st.markdown("<div class='zht-label'>✏️ Source Code Editor</div>",
                    unsafe_allow_html=True)
        src = st.text_area(
            "ZHT Source Code",
            key="editor_area",
            height=420,
            label_visibility="collapsed",
        )

        # Line-numbered view (always up to date — renders from current src)
        with st.expander("🔢  View with Line Numbers", expanded=False):
            st.code(src or "", language="c", line_numbers=True)

        # Compile button
        compile_clicked = st.button("▶  Compile & Analyze", use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # RIGHT — Output
    # ══════════════════════════════════════════════════════════════════════════
    with right:
        # Console output
        st.markdown(
            "<div class='zht-console-bar'>"
            "<span class='zht-dot zht-dot-r'></span>"
            "<span class='zht-dot zht-dot-y'></span>"
            "<span class='zht-dot zht-dot-g'></span>"
            "<span class='zht-console-lbl'>program output</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        out = st.session_state.get("output")
        if out is None:
            con = "<span class='zht-console-empty'>// Compile your program to see output here.</span>"
        elif out == "":
            con = "<span class='zht-console-empty'>// Program ran with no output.</span>"
        else:
            esc = str(out).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            con = esc
        st.markdown(f"<div class='zht-console'>{con}</div>", unsafe_allow_html=True)

        # Status / errors
        status = st.session_state.get("status")
        errors = st.session_state.get("errors", [])
        ephase = st.session_state.get("error_phase", "")

        if status == "success":
            s = st.session_state.get("stats", {})
            st.markdown(
                f"<div class='zht-success'>✔ Compiled &amp; ran successfully &nbsp;·&nbsp; "
                f"{s.get('tokens',0)} tokens &nbsp;·&nbsp; "
                f"{s.get('ir_lines',0)} IR instructions &nbsp;·&nbsp; "
                f"{s.get('time_ms',0):.1f} ms</div>",
                unsafe_allow_html=True,
            )

        elif status == "compiled_ok":
            st.markdown(
                "<div class='zht-success' style='border-left-color:#64b5f6'>"
                "✔ Compiled successfully — see inputs below, then click <b>▶ Run</b></div>",
                unsafe_allow_html=True,
            )

        elif status == "error" and errors:
            icons = {"Lexer": "🔴", "Parser": "🟠", "Semantic": "🟡", "Runtime": "🔵"}
            icon = icons.get(ephase, "🔴")
            items = "".join(f"<div class='zht-error-item'>{e}</div>" for e in errors)
            st.markdown(
                f"<div class='zht-error-box'>"
                f"<div class='zht-error-title'>{icon} {ephase} Error — {len(errors)} issue(s)</div>"
                f"{items}</div>",
                unsafe_allow_html=True,
            )

        # Stats
        if st.session_state.get("stats"):
            s = st.session_state["stats"]
            st.markdown(
                f"<div class='zht-stats'>"
                f"<div class='zht-stat'><div class='zht-stat-val'>{s.get('tokens',0)}</div><div class='zht-stat-lbl'>Tokens</div></div>"
                f"<div class='zht-stat'><div class='zht-stat-val'>{s.get('lines',0)}</div><div class='zht-stat-lbl'>Lines</div></div>"
                f"<div class='zht-stat'><div class='zht-stat-val'>{s.get('funcs',0)}</div><div class='zht-stat-lbl'>Functions</div></div>"
                f"<div class='zht-stat'><div class='zht-stat-val'>{s.get('syms',0)}</div><div class='zht-stat-lbl'>Symbols</div></div>"
                f"<div class='zht-stat'><div class='zht-stat-val'>{s.get('ir_lines',0)}</div><div class='zht-stat-lbl'>IR Lines</div></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # ── Interactive scan() inputs ─────────────────────────────────────────
        phase = st.session_state.get("phase", "idle")
        scan_count = st.session_state.get("scan_count", 0)

        if phase == "awaiting_input" and scan_count > 0:
            st.markdown(
                f"<div class='zht-input-box'>"
                f"<div class='zht-input-title'>⌨️ Runtime Inputs — {scan_count} scan() call(s) detected</div>"
                f"<p style='color:#94a3b8;font-size:.73rem;margin:-2px 0 8px'>Enter one value per input field. "
                f"Each scan() call reads the next value in order.</p>"
                f"</div>",
                unsafe_allow_html=True,
            )
            for i in range(scan_count):
                st.text_input(
                    f"scan() call #{i + 1}",
                    key=f"scan_inp_{i}",
                    placeholder=f"Value for scan call #{i + 1}",
                )

            if st.button("▶  Run Program", use_container_width=True):
                inputs = [
                    st.session_state.get(f"scan_inp_{i}", "")
                    for i in range(scan_count)
                ]
                _do_run(inputs)
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # Compile action
    # ══════════════════════════════════════════════════════════════════════════
    if compile_clicked:
        _do_compile(src)
        st.rerun()

    # ── Analysis tabs ─────────────────────────────────────────────────────────
    st.markdown("<hr class='zht-hr'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='zht-label' style='margin-bottom:8px'>🔬 Compiler Phase Analysis</div>",
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔤  Tokens  (Lexical)",
        "🌳  AST  (Syntax)",
        "📋  Symbol Table  (Semantic)",
        "⚡  Intermediate Code  (TAC)",
    ])
    comp = st.session_state.get("last_comp")

    with tab1:
        if comp and comp.tokens:
            st.markdown(
                f"<p style='color:#4a7cb5;font-size:.74rem;margin-bottom:6px'>"
                f"{len(comp.tokens)} token(s) produced by the lexer.</p>",
                unsafe_allow_html=True,
            )
            render_tokens(comp.tokens)
        else:
            st.markdown('<p style="color:#2d4a6e;font-style:italic;padding:16px 0">Compile a program to see tokens.</p>',
                        unsafe_allow_html=True)

    with tab2:
        if comp and comp.ast:
            st.markdown('<p style="color:#4a7cb5;font-size:.74rem;margin-bottom:6px">Abstract Syntax Tree from the recursive-descent parser.</p>',
                        unsafe_allow_html=True)
            render_ast(comp.ast)
        elif comp and comp.ast is None and comp.sem_errors:
            items = "".join(f"<div class='zht-error-item'>{e}</div>" for e in comp.sem_errors)
            st.markdown(f"<div class='zht-error-box'><div class='zht-error-title'>Parse / Lex failed — no AST</div>{items}</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#2d4a6e;font-style:italic;padding:16px 0">Compile a program to see the AST.</p>',
                        unsafe_allow_html=True)

    with tab3:
        if comp and comp.ast:
            st.markdown('<p style="color:#4a7cb5;font-size:.74rem;margin-bottom:6px">Global symbols after semantic analysis.</p>',
                        unsafe_allow_html=True)
            render_symbol_table(comp.ast)
        else:
            st.markdown('<p style="color:#2d4a6e;font-style:italic;padding:16px 0">Compile a program to see the symbol table.</p>',
                        unsafe_allow_html=True)

    with tab4:
        if comp and comp.ir:
            n_ir = len(getattr(comp.ir, "instructions", []))
            st.markdown(
                f"<p style='color:#4a7cb5;font-size:.74rem;margin-bottom:6px'>"
                f"Three-Address Code (TAC) — {n_ir} instruction(s).</p>",
                unsafe_allow_html=True,
            )
            render_ir(comp.ir)
        elif comp and comp.sem_errors:
            st.markdown('<div class="zht-error-box"><div class="zht-error-title">IR not generated — semantic errors present</div></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#2d4a6e;font-style:italic;padding:16px 0">Compile a program to see intermediate code.</p>',
                        unsafe_allow_html=True)


# ─── Compilation logic ────────────────────────────────────────────────────────
def _do_compile(src: str):
    from zht_compiler.ast import FuncDecl as _FD

    t0   = time.perf_counter()
    comp = _engine.compile(src)
    t1   = time.perf_counter()

    st.session_state["last_comp"] = comp

    # Stats
    sem2 = SemanticAnalyzer()
    n_syms = 0
    if comp.ast:
        try:
            sem2.analyze(comp.ast)
            n_syms = len(sem2.global_scope.symbols)
        except Exception:
            pass

    n_funcs  = sum(1 for d in (comp.ast.declarations if comp.ast else []) if isinstance(d, _FD))
    ir_lines = len(getattr(comp.ir, "instructions", [])) if comp.ir else 0

    st.session_state["stats"] = {
        "tokens":   len(comp.tokens),
        "lines":    len(src.splitlines()),
        "funcs":    n_funcs,
        "syms":     n_syms,
        "ir_lines": ir_lines,
        "time_ms":  (t1 - t0) * 1000,
    }

    if comp.sem_errors:
        # Decide phase label
        if comp.ast is None:
            phase_lbl = "Lexer / Parser"
        else:
            phase_lbl = "Semantic"
        st.session_state.update({
            "status":      "error",
            "error_phase": phase_lbl,
            "errors":      comp.sem_errors,
            "output":      None,
            "phase":       "idle",
            "scan_count":  0,
        })
        return

    # No errors — check if scan() calls are needed
    scan_count = _count_scans(src)
    if scan_count == 0:
        # Auto-run immediately
        _do_run([])
    else:
        st.session_state.update({
            "status":     "compiled_ok",
            "errors":     [],
            "phase":      "awaiting_input",
            "scan_count": scan_count,
            "output":     None,
        })


def _do_run(inputs):
    comp = st.session_state.get("last_comp")
    if comp is None:
        return

    result = _engine.run(comp, inputs)

    if result.startswith("Runtime error:") or result.startswith("Cannot run:"):
        st.session_state.update({
            "status":      "error",
            "error_phase": "Runtime",
            "errors":      [result],
            "output":      None,
            "phase":       "idle",
        })
    else:
        st.session_state.update({
            "status": "success",
            "errors": [],
            "output": result,
            "phase":  "ran",
        })


if __name__ == "__main__":
    main()
