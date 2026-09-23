import streamlit as st
import copy
import math

# ==========================================
# 1. UI ENGINE (SVG GENERATOR)
# ==========================================
def get_wizard_svg(color, is_facing_right, has_shield, is_cursed):
    robe_color = "#FF4B4B" if color == "red" else "#4B4BFF"
    hat_band = "#8B0000" if color == "red" else "#00008B"
    wand_glow = "orange" if color == "red" else "cyan"
    
    shield_svg = '<circle cx="50" cy="65" r="45" fill="rgba(173, 216, 230, 0.4)" stroke="#00FFFF" stroke-width="3" stroke-dasharray="5,5"/>' if has_shield else ''
    curse_svg = '<text x="50" y="18" font-size="20" text-anchor="middle" fill="purple">☠️</text>' if is_cursed else ''
    
    eye_x1, eye_x2 = ("60", "45") if is_facing_right else ("40", "55")
    
    if is_facing_right:
        arms = f'''<line x1="45" y1="75" x2="25" y2="85" stroke="black" stroke-width="3"/>
<line x1="55" y1="75" x2="85" y2="60" stroke="black" stroke-width="3"/>
<line x1="85" y1="60" x2="95" y2="40" stroke="#8B4513" stroke-width="5"/>
<circle cx="95" cy="40" r="5" fill="{wand_glow}"/>'''
    else:
        arms = f'''<line x1="55" y1="75" x2="75" y2="85" stroke="black" stroke-width="3"/>
<line x1="45" y1="75" x2="15" y2="60" stroke="black" stroke-width="3"/>
<line x1="15" y1="60" x2="5" y2="40" stroke="#8B4513" stroke-width="5"/>
<circle cx="5" cy="40" r="5" fill="{wand_glow}"/>'''

    return f'''<div style="display: flex; justify-content: center; margin-bottom: 20px;">
<svg viewBox="0 0 100 130" width="180" height="220">
{shield_svg}
<polygon points="30,40 50,5 70,40" fill="{robe_color}"/>
<rect x="25" y="40" width="50" height="6" fill="{hat_band}"/>
<circle cx="50" cy="55" r="12" fill="white" stroke="black" stroke-width="2"/>
<circle cx="{eye_x1}" cy="52" r="2.5" fill="black"/>
<circle cx="{eye_x2}" cy="52" r="2.5" fill="black"/>
<polygon points="40,67 60,67 75,115 25,115" fill="{robe_color}" stroke="black" stroke-width="2"/>
{arms}
{curse_svg}
</svg>
</div>'''

# ==========================================
# 2. DEFINISI STATE & TRANSITION MODEL
# ==========================================
def init_state():
    if 'state' not in st.session_state:
        st.session_state.state = {
            'player_hp': 100,
            'npc_hp': 100,
            'player_potions': 3,
            'npc_potions': 3,
            'player_shield': False,
            'npc_shield': False,
            'player_cursed': False,
            'npc_cursed': False
        }
        st.session_state.logs = ["Pertarungan dimulai! AI menunggumu."]
        st.session_state.debug_info = {}

def get_available_actions(state, is_npc):
    actions = ['Fireball', 'Mana Shield', 'Curse']
    potions = state['npc_potions'] if is_npc else state['player_potions']
    if potions > 0:
        actions.append('Potion')
    return actions

def simulate_action(current_state, action, is_npc):
    state = copy.deepcopy(current_state)
    attacker_cursed = state['npc_cursed'] if is_npc else state['player_cursed']
    defender_shield = state['player_shield'] if is_npc else state['npc_shield']
    
    if is_npc: state['npc_shield'] = False
    else: state['player_shield'] = False

    if action == 'Fireball':
        damage = 25
        if attacker_cursed: damage -= 15 
        if defender_shield: damage = int(damage * 0.4) 
        
        if is_npc: state['player_hp'] -= damage
        else: state['npc_hp'] -= damage

    elif action == 'Mana Shield':
        if is_npc: state['npc_shield'] = True
        else: state['player_shield'] = True

    elif action == 'Potion':
        heal = 35
        if is_npc:
            state['npc_hp'] = min(100, state['npc_hp'] + heal)
            state['npc_potions'] -= 1
        else:
            state['player_hp'] = min(100, state['player_hp'] + heal)
            state['player_potions'] -= 1

    elif action == 'Curse':
        if is_npc: state['player_cursed'] = True
        else: state['npc_cursed'] = True

    return state

# ==========================================
# 3. ADVERSARIAL SEARCH (MINIMAX + ALPHA-BETA)
# ==========================================
def evaluation_function(state):
    w1, w2, w3 = 2.0, 1.5, 10.0 
    return (w1 * state['npc_hp']) - (w2 * state['player_hp']) + (w3 * state['npc_potions'])

def is_terminal(state):
    return state['player_hp'] <= 0 or state['npc_hp'] <= 0

def get_utility(state):
    if state['player_hp'] <= 0: return 1000 
    elif state['npc_hp'] <= 0: return -1000
    return 0

def minimax(state, depth, alpha, beta, is_npc_turn, tracker):
    tracker['node_count'] += 1
    
    if is_terminal(state): return get_utility(state)
    if depth == 0: return evaluation_function(state)

    if is_npc_turn:
        max_eval = -math.inf
        for action in get_available_actions(state, True):
            new_state = simulate_action(state, action, True)
            eval_score = minimax(new_state, depth - 1, alpha, beta, False, tracker)
            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)
            if beta <= alpha: break 
        return max_eval
    else:
        min_eval = math.inf
        for action in get_available_actions(state, False):
            new_state = simulate_action(state, action, False)
            eval_score = minimax(new_state, depth - 1, alpha, beta, True, tracker)
            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha: break
        return min_eval

def get_best_npc_action(state, depth=4):
    best_action = None
    best_score = -math.inf
    tracker = {'node_count': 0}
    action_scores = {}
    
    for action in get_available_actions(state, True):
        new_state = simulate_action(state, action, True)
        score = minimax(new_state, depth - 1, -math.inf, math.inf, False, tracker)
        action_scores[action] = score
        if score > best_score:
            best_score = score
            best_action = action
            
    return best_action, action_scores, tracker['node_count']

# ==========================================
# 4. GAME LOOP STRUKTUR
# ==========================================
st.set_page_config(page_title="Wizard Duel AI", layout="wide")
st.title("⚔️ Wizard Duel: Minimax AI")

init_state()
state = st.session_state.state

# --- AREA VISUAL ---
col1, col_vs, col2 = st.columns([4, 1, 4])

with col1:
    st.subheader("🧙‍♂️ You (Red Wizard)")
    st.markdown(get_wizard_svg("red", True, state['player_shield'], state['player_cursed']), unsafe_allow_html=True)
    st.progress(max(0, min(state['player_hp'], 100)) / 100)
    st.write(f"**HP:** {state['player_hp']}/100 | 🧪 **Potions:** {state['player_potions']}")

with col_vs:
    st.markdown("<h1 style='text-align: center; margin-top: 100px;'>VS</h1>", unsafe_allow_html=True)

with col2:
    st.subheader("🤖 AI (Blue Wizard)")
    st.markdown(get_wizard_svg("blue", False, state['npc_shield'], state['npc_cursed']), unsafe_allow_html=True)
    st.progress(max(0, min(state['npc_hp'], 100)) / 100)
    st.write(f"**HP:** {state['npc_hp']}/100 | 🧪 **Potions:** {state['npc_potions']}")

st.divider()

# --- CEK TERMINAL (GAME OVER) ---
if is_terminal(state):
    if state['player_hp'] <= 0: st.error("💀 Anda Kalah! AI mendominasi pertempuran.")
    else: st.success("🎉 Anda Menang! AI berhasil ditaklukkan.")
    if st.button("🔄 Main Lagi"):
        del st.session_state.state
        st.rerun()
    st.stop()

# --- INPUT & LOGIC ---
col_input, col_log, col_debug = st.columns([1.5, 1.5, 1])

with col_input:
    st.write("### Pilih Aksi:")
    actions = get_available_actions(state, False)
    
    player_action = None
    if st.button("🔥 Fireball", use_container_width=True, disabled='Fireball' not in actions): player_action = 'Fireball'
    if st.button("🛡️ Mana Shield", use_container_width=True, disabled='Mana Shield' not in actions): player_action = 'Mana Shield'
    if st.button("☠️ Curse", use_container_width=True, disabled='Curse' not in actions): player_action = 'Curse'
    if st.button("🧪 Drink Potion", use_container_width=True, disabled='Potion' not in actions): player_action = 'Potion'

    if player_action:
        st.session_state.state = simulate_action(st.session_state.state, player_action, is_npc=False)
        st.session_state.logs.append(f"🟢 **Player** menggunakan **{player_action}**!")
        
        if not is_terminal(st.session_state.state):
            best_action, scores, nodes = get_best_npc_action(st.session_state.state, depth=4)
            st.session_state.state = simulate_action(st.session_state.state, best_action, is_npc=True)
            st.session_state.logs.append(f"🔴 **AI** membalas dengan **{best_action}**!")
            
            st.session_state.debug_info = {'scores': scores, 'nodes': nodes, 'chosen': best_action}
        st.rerun()

with col_log:
    st.write("### 📜 Battle Log")
    for log in reversed(st.session_state.logs[-5:]):
        st.write(log)

with col_debug:
    st.write("### 🐛 Debug Metrics")
    if st.session_state.debug_info:
        info = st.session_state.debug_info
        st.info(f"**State Dieksplorasi:**\n{info['nodes']} Nodes")
        st.write("**Skor Prediksi Root:**")
        for act, score in info['scores'].items():
            if act == info['chosen']:
                st.markdown(f"- **{act}: {score:.1f}** 👈 *(Dipilih)*")
            else:
                st.markdown(f"- {act}: {score:.1f}")