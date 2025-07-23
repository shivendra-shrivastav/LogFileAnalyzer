# streamlit_app.py
import streamlit as st
import os
from openai import OpenAI
#OPENAI_API_KEY="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"
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ----------------------------- SYSTEM PROMPT -----------------------------
# system_prompt = """
# You are LogInsightGPT, a specialized assistant trained to interpret diagnostic and runtime logs from IPETRONIK's IPEmotionRT system (version 2024 R3.2 and 2025 R2.65794) running on hardware like the IPE833 or IPE853 loggers.

# Your primary responsibilities include:
# - Summarizing log session activity (e.g., system startup, measurement jobs, shutdowns)
# - Extracting key diagnostics such as:
#   - Errors
#   - Warnings
#   - Failed operations
#   - Protocol issues (CAN, Ethernet, WLAN, GPS)
#   - Disk or file system problems
# - Providing potential root cause insights for faults
# - Flagging abnormalities that deviate from expected operations

# Logs are structured in plain text with timestamps and various modules.
# Return output in short bullet points like:
# - ✅ Measurement 1108 started successfully at 15:30:27
# - ❌ CAN8 capture timed out – possible wiring/config issue
# - ⚠️ WLAN interface failed to initialize – DHCP socket error at 09:00:12
# - 🔥 Power bad detected at 09:00:14, caused job abort
# """

system_prompt = """
You are LogInsightGPT, an assistant specialized in analyzing and summarizing diagnostic and runtime logs from IPETRONIK's IPEmotionRT system (e.g., version 2024 R3.2 or 2025 R2.65794), running on logger types like IPE833 or IPE853.

Your task is to:
- Interpret internal log files (.LOG)
- Generate a structured and readable summary
- Use bold labels and colored field names (Streamlit-friendly HTML formatting)
- Format sections to match a clean report layout with headings and line breaks

---

Please format your output exactly like this:

---

### 🧾 General Information:

**<span style='color:#4e88ff'>Software</span>**: IPEmotionRT 2025 R2.65794  
**<span style='color:#4e88ff'>Hardware</span>**: Logger type IPE853  
**<span style='color:#4e88ff'>Serial number</span>**: 85300023  
**<span style='color:#4e88ff'>Period of the log entries</span>**: 07.07.2025 08:59:33 to 07.07.2025 15:32:16  
**<span style='color:#4e88ff'>Configuration file</span>**: IPE853_IP100_300625_23.rwf

---

### 📌 Important Events:

**<span style='color:#ff914d'>System start & initialization</span>**  
Summarize all boot, startup, and mount activity. Indicate if the logger started successfully, when, and how often.

**<span style='color:#ff914d'>Memory check & cleanup</span>**  
Report on disk checks (CheckDisk), file system integrity, and temp directory cleanup.

**<span style='color:#ff914d'>Measurements & data transfer</span>**  
List start/stop times of measurement runs, available storage, and conversion jobs. Mention IPEcloud uploads and if they failed.

**<span style='color:#ff914d'>Error messages & warnings</span>**  
Clearly list issues using bullet points grouped by category:
- **Power**: e.g., "Power bad" detected, unexpected shutdowns
- **WLAN**: Interface down, DHCP failures, no IP assignment
- **CAN**: Timeouts, CanServer errors
- **GPS**: Format or signal errors
- **Disk**: Dirty bit found, file system failures
- **Protocols**: Invalid or unexpected capture configs

---

### ✅ Conclusion:

Summarize 3–5 key takeaways using emojis and technical phrasing:

- ✅ System initialized successfully and ran measurement jobs
- ⚠️ Dirty bit found on /media/MEA during shutdown
- ❌ CAN8 timeout at 15:30:28 and Wi-Fi dropout reported
- ⚠️ Upload to IPEcloud failed due to missing media or inactive WLAN
- ✅ Disk space and memory checks passed with no issues

---

📝 Notes:
- All input logs are provided between markers like:
  ===== START OF FILE: LOG_1108_IPEmotionRT.LOG =====
  (content)
  ===== END OF FILE: LOG_1108_IPEmotionRT.LOG =====

- Use only the information inside the logs.
- Maintain professional tone, consistent formatting, and structured section headings.
"""

# ----------------------------- FUNCTIONS -----------------------------
def combine_uploaded_logs(uploaded_files):
    content = ""
    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        content += f"\n\n===== START OF FILE: {filename} =====\n"
        file_text = uploaded_file.read().decode("utf-8", errors="ignore")
        content += file_text
        content += f"\n===== END OF FILE: {filename} =====\n"
    return content

# ----------------------------- STREAMLIT UI -----------------------------
st.set_page_config(page_title="📊 IPE Log Analyzer", layout="wide")
st.title("🛠️ IPE Log Analyzer")
st.markdown(..., unsafe_allow_html=True)
uploaded_files = st.file_uploader("📂 Upload one or more `.LOG` files", type="LOG", accept_multiple_files=True)

if uploaded_files:
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.summarized = False

    if not st.session_state.summarized:
        with st.spinner("Analyzing logs and preparing summary..."):
            log_content = combine_uploaded_logs(uploaded_files)

            st.session_state.messages.append({"role": "system", "content": system_prompt})
            st.session_state.messages.append({"role": "user", "content": log_content})

            # Call GPT to generate the summary
            response = client.chat.completions.create(
                model="gpt-4",
                messages=st.session_state.messages
            )
            reply = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.session_state.summarized = True

        st.success("✅ Log summary generated! Ask your questions below:")

# ----------------------------- CHAT SECTION -----------------------------
if st.session_state.get("messages"):
    for msg in st.session_state.messages[2:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"],unsafe_allow_html=True)

    if prompt := st.chat_input("Ask a question about the logs..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Thinking..."):
            response = client.chat.completions.create(
                model="gpt-4",
                messages=st.session_state.messages
            )
            reply = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply, unsafe_allow_html=True)

else:
    st.info("⬆️ Upload your `.LOG` files above to begin.")
