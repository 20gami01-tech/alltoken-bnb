import streamlit as st
import qrcode
import requests
from io import BytesIO

# ---------------- PAGE CONFIG ---------------- #
st.set_page_config(page_title="BNB Chain QR Generator", page_icon="🟡", layout="centered")

# ---------------- LOGIN CONFIG ---------------- #
USERNAME = "admin"
PASSWORD = "admin@500"

# ---------------- SESSION INIT ---------------- #
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "token_info" not in st.session_state:
    st.session_state.token_info = None
if "last_contract" not in st.session_state:
    st.session_state.last_contract = ""

# ================================================
# HELPERS
# ================================================
# Get your FREE key at: https://developers.moralis.com  (free tier: 40k units/day)
MORALIS_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjNiOTI1OTM4LWE2YTAtNGRiMy05NDliLTYzOGZjNjFjMDExYyIsIm9yZ0lkIjoiNTEyNjcxIiwidXNlcklkIjoiNTI3NTI4IiwidHlwZUlkIjoiMjg1MmNlOWYtNmEzMy00MmQxLThkMzItN2YxOTBkZmU1YjE1IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NzcwOTAxNzIsImV4cCI6NDkzMjg1MDE3Mn0.HfuJJOvZ24psDOBfL7e05LFehbgsjpUAtdCNS_yBf40"
ERC20_SELECTOR  = "a9059cbb"   # transfer(address,uint256) — same on every EVM chain

def normalize(addr: str) -> str:
    addr = addr.strip()
    if addr.lower().startswith("0x"):
        addr = addr[2:]
    return addr.lower()

def fetch_token_info(contract_no0x: str) -> dict:
    """
    Calls Moralis ERC20 metadata endpoint for BNB Smart Chain (chain=bsc).
    Returns dict with: name, symbol, decimals, address, etc.
    Raises ValueError if token not found or API error.
    """
    url = f"https://deep-index.moralis.io/api/v2.2/erc20/metadata?chain=bsc&addresses=0x{contract_no0x}"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY,
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if not data or not isinstance(data, list) or len(data) == 0:
        raise ValueError("Token not found or invalid contract address")

    return data[0]  # Moralis returns a list; we only asked for one address

def build_link(contract_with_0x: str, to_addr_no0x: str, amount: float, decimals: int) -> str:
    to_padded    = to_addr_no0x.lower().rjust(64, "0")
    amount_units = int(amount * (10 ** decimals))
    amount_hex   = hex(amount_units)[2:].rjust(64, "0")
    data_hex     = ERC20_SELECTOR + to_padded + amount_hex
    return (
        "https://link.trustwallet.com/send"
        f"?asset=c20000714"
        f"&address={contract_with_0x}"
        f"&data={data_hex}"
    )

def make_qr(link: str) -> bytes:
    buf = BytesIO()
    qrcode.make(link).save(buf)
    buf.seek(0)
    return buf.read()

# ================================================
# LOGIN
# ================================================
if not st.session_state.logged_in:
    st.title("🔐 Login Required")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == USERNAME and p == PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.stop()

# ================================================
# MAIN APP
# ================================================
st.title("🟡 BNB Chain Token QR Generator")
st.caption("Paste the token's BNB Smart Chain contract address — auto-detects symbol & decimals")
st.markdown("---")

# ── Step 1: Token contract address ──────────────
st.subheader("Step 1 — Token Contract Address (BNB Chain)")
st.caption("e.g. USDT on BSC → 0x55d398326f99059fF775485246999027B3197955")

col1, col2 = st.columns([3, 1])
with col1:
    raw_contract = st.text_input(
        "Token contract address (0x…)",
        label_visibility="collapsed",
        placeholder="",
    )
with col2:
    lookup = st.button("🔍 Detect Token", use_container_width=True)

if lookup:
    if not raw_contract:
        st.error("Enter a contract address.")
    else:
        clean = normalize(raw_contract)
        if len(clean) != 40:
            st.error(f"Address must be 40 hex chars after stripping 0x (got {len(clean)}).")
        else:
            with st.spinner("Looking up token on Moralis…"):
                try:
                    info = fetch_token_info(clean)
                    st.session_state.token_info    = info
                    st.session_state.last_contract = clean
                except ValueError as e:
                    st.error(f"Token not found: {e}")
                    st.session_state.token_info = None
                except requests.RequestException as e:
                    st.error(f"Network error: {e}")
                    st.session_state.token_info = None

# ── Show detected token ──────────────────────────
if st.session_state.token_info:
    info     = st.session_state.token_info
    symbol   = info.get("symbol", "???")
    name     = info.get("name", "Unknown")
    # Moralis returns decimals as a string e.g. "18"
    decimals = int(info.get("decimals") or 18)
    contract_with_0x = f"0x{st.session_state.last_contract}"

    st.success(f"✅ Detected: **{name}** ({symbol})  ·  Decimals: {decimals}  ·  Contract: `{contract_with_0x}`")

    # ── Step 2: Receiver wallet address ─────────────
    st.markdown("---")
    st.subheader("Step 2 — Receiver Wallet Address")
    raw_to = st.text_input(
        "Receiver's wallet address (0x…)",
        placeholder="0xABC123…",
    )

    # ── Step 3: Amount ───────────────────────────────
    st.markdown("---")
    st.subheader(f"Step 3 — Amount ({symbol})")
    amount = st.number_input(f"Amount in {symbol}", min_value=0.0, step=0.01, format="%.6f")

    # ── Generate ─────────────────────────────────────
    st.markdown("---")
    if st.button("⚡ Generate QR", use_container_width=True):
        if not raw_to:
            st.error("Enter the receiver wallet address.")
        else:
            to_clean = normalize(raw_to)
            if len(to_clean) != 40:
                st.error(f"Receiver address must be 40 hex chars (got {len(to_clean)}).")
            elif amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                link = build_link(contract_with_0x, to_clean, amount, decimals)
                qr   = make_qr(link)

                st.image(qr, caption=f"Scan with Trust Wallet — {amount} {symbol} (BEP-20 on BNB Chain)")

                with st.expander("🔗 Deep Link"):
                    st.code(link)

                with st.expander("🛠 Calldata Breakdown"):
                    to_padded    = to_clean.lower().rjust(64, "0")
                    amount_units = int(amount * (10 ** decimals))
                    amount_hex   = hex(amount_units)[2:].rjust(64, "0")
                    st.text(f"Function selector : {ERC20_SELECTOR}  (transfer(address,uint256))")
                    st.text(f"Token contract    : {contract_with_0x}")
                    st.text(f"To (padded 32B)   : {to_padded}")
                    st.text(f"Decimals          : {decimals}")
                    st.text(f"Amount (units)    : {amount_units}  ({amount} x 10^{decimals})")
                    st.text(f"Amount (hex pad)  : {amount_hex}")

st.markdown("---")
st.caption("Token data powered by Moralis Web3 API")
