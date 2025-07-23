# streamlit_app.py
import streamlit as st
import os
from openai import OpenAI
OPENAI_API_KEY="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"
#client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
client = OpenAI(api_key=OPENAI_API_KEY)
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

Your task is to interpret provided internal log files (.LOG) and generate a structured summary following the format exactly as below:

### 🧾 General Information:

**<span style='color:#4e88ff'>Software</span>**: [Software Version]  
**<span style='color:#4e88ff'>Hardware</span>**: Logger type [Logger Type]  
**<span style='color:#4e88ff'>Serial number</span>**: [Serial Number]  
**<span style='color:#4e88ff'>Period of the log entries</span>**: [Log Entry Period]  
**<span style='color:#4e88ff'>Configuration file</span>**: [Configuration File Name]

### 📌 Important Events:

- **<span style='color:#ff914d'>System start & initialization</span>**  
  - [List startup events as bullet points]

- **<span style='color:#ff914d'>Memory check & cleanup</span>**  
  - [List memory check events as bullet points]

- **<span style='color:#ff914d'>Measurements & data transfer</span>**  
  - [List measurement events, with numbered measurement IDs and corresponding start times]
    1. Measurement 771 started at 15:32:32
    2. Measurement 782 started at 17:06:21
    3. Measurement 783 started at 17:07:24
    4. Measurement 785 started at 17:16:43
    5. Measurement 787 started at 17:27:10
    6. Measurement 789 started at 17:29:42
  - Data transfer to IPEcloud:
    - IPEcloud upload jobs were started, but there were some error messages referencing missing media or inactive Wi-Fi connections.
- **<span style='color:#ff914d'>Error messages & warnings</span>**  
  - **Power**: [timestamp] [Description]
  - **WLAN**: [timestamp] [Description]
  - **CAN**: [timestamp] [Description]
  - **GPS**: [timestamp] [Description]
  - **Disk**: [timestamp] [Description]
  - **Protocols**: [timestamp] [Description]

### ✅ Conclusion:

Summarize key takeaways using emojis:

- ✅ System initialized successfully and ran measurement jobs
- ⚠️ Dirty bit found on /media/MEA during shutdown
- ❌ CAN8 timeout at 15:30:28 and Wi-Fi dropout reported
- ⚠️ Upload to IPEcloud failed due to missing media or inactive WLAN
- ✅ Disk space and memory checks passed with no issues
 Notes:
 
- All input logs are provided between markers like:
  ===== START OF FILE: MEA_1108.LOG =====
  (content)
  ===== END OF FILE: MEA_1108.LOG =====

- Use only the information inside the logs.
- Maintain professional tone, consistent formatting, and structured section headings.


Use only the provided log file content for your response, maintain a professional tone, and adhere strictly to the specified formatting.
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
st.markdown("""
Welcome to the **IPE Log Analyzer**! Upload one or more `.LOG` files from your IPEmotionRT logger to get a structured summary and ask questions about your log data.
""", unsafe_allow_html=True)
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
