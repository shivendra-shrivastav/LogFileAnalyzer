import streamlit as st
import os
import zipfile
import concurrent.futures
from openai import OpenAI
import tiktoken

# ------------------- CONFIGURABLE: Use "gpt-3.5-turbo" for lowest cost, "gpt-4o" for best quality ---------------
MODEL_NAME = "gpt-3.5-turbo"  # Or "gpt-4o" for better/faster summary, more tokens

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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



# ------------------- PARALLEL EXTRACTION ----------------------

def extract_one_zip(uploaded_zip):
    """Extract .LOG files from one zip file."""
    log_files = []
    with zipfile.ZipFile(uploaded_zip) as z:
        for file_info in z.infolist():
            if file_info.filename.upper().endswith(".LOG") and not file_info.is_dir():
                with z.open(file_info) as f:
                    text = f.read().decode("utf-8", errors="ignore")
                    display_name = f"{uploaded_zip.name}:{os.path.basename(file_info.filename)}"
                    log_files.append((display_name, text))
    return log_files

def extract_logs_from_zips_parallel(uploaded_zips):
    """Extract logs from all zips in parallel."""
    log_files = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(extract_one_zip, uploaded_zips)
        for res in results:
            log_files.extend(res)
    return log_files

def combine_log_file_contents(log_files):
    content = ""
    for filename, file_text in log_files:
        content += f"\n\n===== START OF FILE: {filename} =====\n"
        content += file_text
        content += f"\n===== END OF FILE: {filename} =====\n"
    return content

# ------------------- TOKEN-BASED CHUNKING ----------------------

def chunk_log_content_by_tokens(content, max_tokens=5000, model_name=MODEL_NAME):
    encoding = tiktoken.encoding_for_model(model_name)
    lines = content.splitlines()
    chunk = []
    token_count = 0

    for line in lines:
        tokens_in_line = len(encoding.encode(line + "\n"))
        if token_count + tokens_in_line > max_tokens and chunk:
            yield "\n".join(chunk)
            chunk = []
            token_count = 0
        chunk.append(line)
        token_count += tokens_in_line

    if chunk:
        yield "\n".join(chunk)

# ------------------- PARALLEL GPT SUMMARIZATION ----------------------

def summarize_chunk(chunk, chunk_idx=None, model_name=MODEL_NAME):
    chunk_system_prompt = system_prompt
    if chunk_idx is not None:
        chunk_system_prompt += f"\n\n(This is chunk {chunk_idx+1})"
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": chunk_system_prompt},
            {"role": "user", "content": chunk}
        ]
    )
    return response.choices[0].message.content

def summarize_summaries(summaries, model_name=MODEL_NAME):
    combined_prompt = (
        f"{system_prompt}\n\n"
        "Here are summaries of different chunks of the log. Please combine them into a single structured summary as per the format."
    )
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": combined_prompt},
            {"role": "user", "content": "\n\n".join(summaries)}
        ]
    )
    return response.choices[0].message.content

def summarize_chunks_parallel(log_chunks, model_name=MODEL_NAME):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        chunk_args = [(chunk, idx, model_name) for idx, chunk in enumerate(log_chunks)]
        results = list(executor.map(lambda args: summarize_chunk(*args), chunk_args))
    return results

# ------------------- SESSION/RESET HANDLING ----------------------

st.set_page_config(page_title="📊 IPE Log Analyzer", layout="wide")
st.title("🛠️ IPE Log Analyzer (Fast Mode)")
st.markdown(f"""
Now supports **multiple `.zip` uploads**, parallel extraction, and parallel chunk summarization!  
**Current model:** `{MODEL_NAME}`  
*Tip: Use "gpt-3.5-turbo" for fastest & cheapest summaries, "gpt-4o" for best balance of speed, context, and quality.*
""", unsafe_allow_html=True)

uploaded_zips = st.file_uploader(
    "📂 Upload one or more `.zip` files of logs",
    type="zip",
    accept_multiple_files=True
)

if "last_filenames" not in st.session_state:
    st.session_state.last_filenames = []

uploaded_zip_names = [f.name for f in uploaded_zips] if uploaded_zips else []

if not uploaded_zip_names and st.session_state.last_filenames:
    st.session_state.clear()
    st.session_state.last_filenames = []

if uploaded_zip_names and uploaded_zip_names != st.session_state.last_filenames:
    st.session_state.clear()
    st.session_state.last_filenames = uploaded_zip_names

# ------------------- MAIN APP LOGIC ----------------------

if uploaded_zips:
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.summarized = False

    if not st.session_state.summarized:
        with st.spinner("Extracting logs from zip files in parallel..."):
            log_files = extract_logs_from_zips_parallel(uploaded_zips)
            if not log_files:
                st.error("No `.LOG` files found in the uploaded zip(s)!")
            else:
                log_content = combine_log_file_contents(log_files)

        if log_files:
            MAX_TOKENS_PER_CHUNK = 5000
            with st.spinner("Chunking log files by tokens..."):
                log_chunks = list(chunk_log_content_by_tokens(log_content, max_tokens=MAX_TOKENS_PER_CHUNK, model_name=MODEL_NAME))
            num_chunks = len(log_chunks)

            # ----------- PARALLEL SUMMARIZATION -----------
            st.info(f"Summarizing {num_chunks} chunk(s) in parallel...")

            with st.spinner("Summarizing all chunks in parallel... (UI progress only updates when all are done)"):
                def summarize_for_thread(args):
                    chunk, idx, model_name = args
                    return summarize_chunk(chunk, idx, model_name)

                chunk_args = [(chunk, idx, MODEL_NAME) for idx, chunk in enumerate(log_chunks)]
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    chunk_summaries = list(executor.map(summarize_for_thread, chunk_args))

            st.success("All chunks summarized!")


            # ----------- FINAL SUMMARY -----------
            if len(chunk_summaries) > 1:
                with st.spinner("Combining all chunk summaries..."):
                    final_summary = summarize_summaries(chunk_summaries, model_name=MODEL_NAME)
            else:
                final_summary = chunk_summaries[0]

            st.session_state.messages.append({"role": "system", "content": system_prompt})
            st.session_state.messages.append({"role": "user", "content": "Log file(s) summary"})
            st.session_state.messages.append({"role": "assistant", "content": final_summary})
            st.session_state.summarized = True

        if log_files:
            st.success("✅ Log summary generated! Ask your questions below:")

# ------------------- CHAT SECTION ----------------------

if st.session_state.get("messages"):
    for msg in st.session_state.messages[2:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("Ask a question about the logs..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Thinking..."):
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=st.session_state.messages
            )
            reply = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply, unsafe_allow_html=True)
else:
    st.info("⬆️ Upload one or more `.zip` files above to begin.")
