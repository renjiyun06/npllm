from dataclasses import dataclass
from typing import List, Dict, Any
from litellm import acompletion
import logging
from dotenv import load_dotenv
import json
import json_repair
from importlib import resources

from npllm.core.type import Type

logger = logging.getLogger(__name__)

load_dotenv()

prompts = resources.files('npllm.core.prompts')
with open(prompts / "system_prompt_template.md", "r") as f:
    system_prompt_template = f.read()

with open(prompts / "user_prompt_template.md", "r") as f:
    user_prompt_template = f.read()

@dataclass
class LLMCallInfo:
    call_id: str
    role: str
    code_context: str
    call_line_number: int
    method_name: str
    args: List[Any]
    kwargs: Dict[Any, Any]
    expected_return_type: Type
    model: str
    llm_kwargs: Dict[str, Any]

async def call_llm(llm_call_info: LLMCallInfo) -> Any:
    logger.info(f"The model used for LLM call {llm_call_info.call_id} is {llm_call_info.model} with args {llm_call_info.llm_kwargs}")
    system_prompt = _populate_prompt_template(system_prompt_template, {
        "{{role}}": llm_call_info.role,
        "{{code_context}}": llm_call_info.code_context
    })
    user_prompt = _populate_prompt_template(user_prompt_template, {
        "{{call_line_number}}": str(llm_call_info.call_line_number),
        "{{method_name}}": llm_call_info.method_name,
        "{{args}}": repr(llm_call_info.args),
        "{{kwargs}}": repr(llm_call_info.kwargs),
        "{{expected_return_type}}": repr(llm_call_info.expected_return_type)
    })

    logger.debug(f"""System Prompt for {llm_call_info.call_id}: \n\n{system_prompt}\n\n""")
    logger.debug(f"""User Prompt for {llm_call_info.call_id}: \n\n{user_prompt}\n\n""")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = await acompletion(
        model=llm_call_info.model,
        messages=messages,
        **llm_call_info.llm_kwargs
    )
    content = response.choices[0].message.content.strip()
    logger.debug(f"""Raw response from LLM for {llm_call_info.call_id}: \n\n{content}\n\n""")

    # llm's response following the below format:
    # <RESULT>
    # ...
    # </RESULT>
    # <CONTEXT_UNDERSTANDING>
    # ...
    # </CONTEXT_UNDERSTANDING>
    # <COMPUTATION_LOGIC>
    # ...
    # </COMPUTATION_LOGIC>

    json_str = None
    reasoning = None
    if "<RESULT>" in content and "</RESULT>" in content:
        json_str = content.split("<RESULT>")[1].split("</RESULT>")[0].strip()
    if "<CONTEXT_UNDERSTANDING>" in content and "</CONTEXT_UNDERSTANDING>" in content:
        context_understanding = content.split("<CONTEXT_UNDERSTANDING>")[1].split("</CONTEXT_UNDERSTANDING>")[0].strip()
    if "<COMPUTATION_LOGIC>" in content and "</COMPUTATION_LOGIC>" in content:
        computation_logic = content.split("<COMPUTATION_LOGIC>")[1].split("</COMPUTATION_LOGIC>")[0].strip()

    if json_str.startswith("```json") and json_str.endswith("```"):
        json_str = json_str[len("```json"):-len("```")].strip()

    try:
        json_value = json.loads(json_str)
    except Exception as e_1:
        logger.warning(f"Failed to parse JSON from LLM response for {llm_call_info.call_id}, error: {e_1}, try to repair the JSON")
        try:
            json_value = json_repair.loads(json_str)
            logger.debug(f"Successfully repaired JSON from LLM response for {llm_call_info.call_id}, repaired JSON: \n\n{json.dumps(json_value, indent=2)}\n\n")
        except Exception as e_2:
            logger.error(f"Failed to repair JSON from LLM response for {llm_call_info.call_id}, error: {e_2}")
            # here we just raise the original exception
            # TODO we can try to call llm again to repair the JSON
            raise e_2

    logger.debug(f"""Context Understanding from LLM for {llm_call_info.call_id}: \n\n{context_understanding}\n\n""")
    logger.debug(f"""Computation Logic from LLM for {llm_call_info.call_id}: \n\n{computation_logic}\n\n""")

    result = llm_call_info.expected_return_type.convert(json_value, "__root", strict=False)
    logger.info(f"Successfully called LLM for {llm_call_info.call_id}")
    return result

def _populate_prompt_template(template, replacements):
    prompt = template
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)
    return prompt