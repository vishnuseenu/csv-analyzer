import base64
import logging

import streamlit as st
from openai import OpenAI
from openai.types.beta.assistant_stream_event import (
    ThreadRunStepCreated,
    ThreadRunStepDelta,
    ThreadRunStepCompleted,
    ThreadMessageCreated,
    ThreadMessageDelta,
) 
from openai.types.beta.threads.text_delta_block import TextDeltaBlock
from openai.types.beta.threads.runs.tool_calls_step_details import ToolCallsStepDetails
from openai.types.beta.threads.runs.code_interpreter_tool_call import (
    CodeInterpreterOutputImage,
    CodeInterpreterOutputLogs,
)

from create_assistant import create_assistant

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
st.set_page_config(page_title="CSV Ana", layout="wide")

# Get secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=OPENAI_API_KEY)
ASSISTANT_ID = create_assistant()

# Retrieve the assistant
assistant = client.beta.assistants.retrieve(ASSISTANT_ID)

# Apply custom CSS
st.html(
    """
        <style>
            #MainMenu {visibility: hidden}
            #header {visibility: hidden}
            #footer {visibility: hidden}
            .block-container {
                padding-top: 3rem;
                padding-bottom: 2rem;
                padding-left: 3rem;
                padding-right: 3rem;
                }
        </style>
        """
)

# Initialise session state
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False


# Moderation check
def moderation_endpoint(text) -> bool:
    """
    Checks if the text triggers the moderation endpoint

    Args:
    - text (str): The text to check

    Returns:
    - bool: True if the text is flagged
    """
    response = client.moderations.create(input=text)
    return response.results[0].flagged


# UI
st.subheader("Advanced Data Analysis & Visualisation Engine")
file_upload_box = st.empty()
upload_btn = st.empty()

# File Upload
if not st.session_state.file_uploaded:
    st.session_state.files = file_upload_box.file_uploader(
        "Please upload your dataset(s)", accept_multiple_files=True, type=["csv"]
    )

    if upload_btn.button("Upload") and st.session_state.files:
        st.session_state.file_id = []

        for file in st.session_state.files:
            oai_file = client.files.create(file=file, purpose="assistants")
            st.session_state.file_id.append(oai_file.id)
            logger.info(f"Uploaded new file: {oai_file.id}")

        st.toast("File(s) uploaded successfully", icon="🚀")
        st.session_state.file_uploaded = True
        file_upload_box.empty()
        upload_btn.empty()
        st.rerun()

if st.session_state.file_uploaded:
    # Create a new thread if not exists
    if "thread_id" not in st.session_state:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        logger.info(f"Created new thread: {st.session_state.thread_id}")

    # Update the thread to attach the file
    client.beta.threads.update(
        thread_id=st.session_state.thread_id,
        tool_resources={"code_interpreter": {"file_ids": st.session_state.file_id}},
    )

    # Initialize local history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            for item in message["items"]:
                item_type = item["type"]
                if item_type == "text":
                    st.markdown(item["content"])
                elif item_type == "image":
                    for image in item["content"]:
                        st.html(image)
                elif item_type == "code_input":
                    with st.status("Code", state="complete"):
                        st.code(item["content"])
                elif item_type == "code_output":
                    with st.status("Results", state="complete"):
                        st.code(item["content"])

    # Chat input
    if prompt := st.chat_input("Ask me a question about your dataset"):
        if moderation_endpoint(prompt):
            st.toast("Your message was flagged. Please try again.", icon="⚠")
            st.stop()

        st.session_state.messages.append(
            {"role": "user", "items": [{"type": "text", "content": prompt}]}
        )

        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id, role="user", content=prompt
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            stream = client.beta.threads.runs.create(
                thread_id=st.session_state.thread_id,
                assistant_id=ASSISTANT_ID,
                tool_choice={"type": "code_interpreter"},
                stream=True,
            )

            assistant_output = []

            for event in stream:
                if isinstance(event, ThreadRunStepCreated):
                    if event.data.step_details.type == "tool_calls":
                        assistant_output.append({"type": "code_input", "content": ""})
                        code_input_expander = st.status(
                            "Writing code ⏳ ...", expanded=True
                        )
                        code_input_block = code_input_expander.empty()

                elif isinstance(event, ThreadRunStepDelta):
                    if (
                        event.data.delta.step_details.tool_calls[0].code_interpreter
                        is not None
                    ):
                        code_interpreter = event.data.delta.step_details.tool_calls[
                            0
                        ].code_interpreter
                        code_input_delta = code_interpreter.input
                        if code_input_delta:
                            assistant_output[-1]["content"] += code_input_delta
                            code_input_block.empty()
                            code_input_block.code(assistant_output[-1]["content"])

                elif isinstance(event, ThreadRunStepCompleted):
                    if isinstance(event.data.step_details, ToolCallsStepDetails):
                        code_interpreter = event.data.step_details.tool_calls[
                            0
                        ].code_interpreter
                        if code_interpreter.outputs:
                            logger.info("Code interpreter output received")
                            code_input_expander.update(
                                label="Code", state="complete", expanded=False
                            )
                            # Image output
                            if any(
                                isinstance(output, CodeInterpreterOutputImage)
                                for output in code_interpreter.outputs
                            ):
                                image_html_list = []
                                for output in code_interpreter.outputs:
                                    if isinstance(output, CodeInterpreterOutputImage):
                                        image_file_id = output.image.file_id
                                        image_data = client.files.content(image_file_id)

                                        # Save file
                                        image_data_bytes = image_data.read()
                                        with open(
                                            f"images/{image_file_id}.png", "wb"
                                        ) as file:
                                            file.write(image_data_bytes)

                                        # Open file and encode as data
                                        with open(
                                            f"images/{image_file_id}.png", "rb"
                                        ) as file:
                                            contents = file.read()
                                            data_url = base64.b64encode(
                                                contents
                                            ).decode("utf-8")

                                        # Display image
                                        image_html = f'<p align="center"><img src="data:image/png;base64,{data_url}" width=600></p>'
                                        st.html(image_html)

                                        image_html_list.append(image_html)

                                assistant_output.append(
                                    {"type": "image", "content": image_html_list}
                                )
                            # Console log output
                            elif any(
                                isinstance(output, CodeInterpreterOutputLogs)
                                for output in code_interpreter.outputs
                            ):
                                assistant_output.append(
                                    {"type": "code_output", "content": ""}
                                )
                                code_output = next(
                                    (
                                        output.logs
                                        for output in code_interpreter.outputs
                                        if isinstance(output, CodeInterpreterOutputLogs)
                                    ),
                                    "",
                                )
                                with st.status("Results", state="complete"):
                                    st.code(code_output)
                                    assistant_output[-1]["content"] = code_output

                elif isinstance(event, ThreadMessageCreated):
                    assistant_output.append({"type": "text", "content": ""})
                    assistant_text_box = st.empty()

                elif isinstance(event, ThreadMessageDelta):
                    if isinstance(event.data.delta.content[0], TextDeltaBlock):
                        assistant_text_box.empty()
                        assistant_output[-1]["content"] += event.data.delta.content[
                            0
                        ].text.value
                        assistant_text_box.markdown(assistant_output[-1]["content"])

            st.session_state.messages.append(
                {"role": "assistant", "items": assistant_output}
            )