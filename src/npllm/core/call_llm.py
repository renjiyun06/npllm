from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from litellm import acompletion, completion, completion_cost
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
    system_prompt_template: str = f.read()

with open(prompts / "system_prompt_template_no_inspect.md", "r") as f:
    system_prompt_template_no_inspect: str = f.read()

with open(prompts / "user_prompt_template.md", "r") as f:
    user_prompt_template: str = f.read()

with open(prompts / "user_prompt_template_no_inspect.md", "r") as f:
    user_prompt_template_no_inspect: str = f.read()

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
    current_program_snippet_id: str
    program_snippets: str
    llm_kwargs: Dict[str, Any]
    inspected_mode: bool

@dataclass
class LLMCallResult:
    call_id: str
    result: Optional[Any]
    reasoning: Optional[str]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    completion_cost: float

def _populate_prompt_template(template, replacements):
    prompt = template
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)
    return prompt

def _get_system_and_user_prompt(llm_call_info: LLMCallInfo) -> tuple[str, str]:
    if llm_call_info.inspected_mode:
        system_prompt = _populate_prompt_template(
            system_prompt_template,
            {
                "{{role}}": llm_call_info.role,
                "{{program_snippets}}": llm_call_info.program_snippets,
                "{{current_program_snippet_id}}": llm_call_info.current_program_snippet_id,
                "{{code_context}}": llm_call_info.code_context
            }
        )
        user_prompt = _populate_prompt_template(
            user_prompt_template,
            {
                "{{current_program_snippet_id}}": llm_call_info.current_program_snippet_id,
                "{{method_name}}": llm_call_info.method_name,
                "{{call_line_number}}": str(llm_call_info.call_line_number),
                "{{args}}": repr(llm_call_info.args),
                "{{kwargs}}": repr(llm_call_info.kwargs),
                "{{expected_return_type}}": repr(llm_call_info.expected_return_type)
            }
        )
    else:
        system_prompt = _populate_prompt_template(
            system_prompt_template_no_inspect,
            {
                "{{role}}": llm_call_info.role,
                "{{code_context}}": llm_call_info.code_context
            }
        )
        user_prompt = _populate_prompt_template(
            user_prompt_template_no_inspect,
            {
                "{{method_name}}": llm_call_info.method_name,
                "{{call_line_number}}": str(llm_call_info.call_line_number),
                "{{args}}": repr(llm_call_info.args),
                "{{kwargs}}": repr(llm_call_info.kwargs),
                "{{expected_return_type}}": repr(llm_call_info.expected_return_type)
            }
        )

    return system_prompt, user_prompt

def _assemble_messages(llm_call_info: LLMCallInfo) -> List[Dict[str, str]]:
    logger.info(f"The model used for LLM call {llm_call_info.call_id} is {llm_call_info.model} with args {llm_call_info.llm_kwargs}")
    system_prompt, user_prompt = _get_system_and_user_prompt(llm_call_info)
    logger.debug(f"""System Prompt for {llm_call_info.call_id}: \n\n{system_prompt}\n""")
    logger.debug(f"""User Prompt for {llm_call_info.call_id}: \n\n{user_prompt}\n""")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    return messages

def _parse_llm_response(response, llm_call_info: LLMCallInfo) -> LLMCallResult:
    content = response.choices[0].message.content.strip()
    logger.debug(f"""Raw response from LLM for {llm_call_info.call_id}: \n\n{content}\n""")

    content = response.choices[0].message.content.strip()
    logger.debug(f"""Raw response from LLM for {llm_call_info.call_id}: \n\n{content}\n""")

    json_str = None
    reasoning = None
    if "<RESULT>" in content and "</RESULT>" in content:
        json_str = content.split("<RESULT>")[1].split("</RESULT>")[0].strip()
    if "<REASONING>" in content and "</REASONING>" in content:
        reasoning = content.split("<REASONING>")[1].split("</REASONING>")[0].strip()

    if json_str.startswith("```json") and json_str.endswith("```"):
        json_str = json_str[len("```json"):-len("```")].strip()

    try:
        json_value = json.loads(json_str)
    except Exception as e_1:
        logger.warning(f"Failed to parse JSON from LLM response for {llm_call_info.call_id}, error: {e_1}, try to repair the JSON")
        try:
            json_value = json_repair.loads(json_str)
            logger.debug(f"Successfully repaired JSON from LLM response for {llm_call_info.call_id}, repaired JSON: \n\n{json.dumps(json_value, indent=2)}\n")
        except Exception as e_2:
            logger.error(f"Failed to repair JSON from LLM response for {llm_call_info.call_id}, error: {e_2}")
            # here we just raise the original exception
            # TODO we can try to call llm again to repair the JSON
            raise e_2

    logger.debug(f"Reasoning from LLM for {llm_call_info.call_id}: \n\n{reasoning}\n")
    result = llm_call_info.expected_return_type.convert(json_value, "__root", strict=False)
    logger.info(f"Successfully called LLM for {llm_call_info.call_id}")

    llm_call_result = LLMCallResult(
        call_id=llm_call_info.call_id,
        result=result,
        reasoning=reasoning,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        total_tokens=response.usage.total_tokens,
        completion_cost=completion_cost(response)
    )
    return llm_call_result

async def call_llm_async(llm_call_info: LLMCallInfo) -> LLMCallResult:
    response = await acompletion(
        model=llm_call_info.model,
        messages=_assemble_messages(llm_call_info),
        **llm_call_info.llm_kwargs
    )

    return _parse_llm_response(response, llm_call_info)

def call_llm_sync(llm_call_info: LLMCallInfo) -> LLMCallResult:
    response = completion(
        model=llm_call_info.model,
        messages=_assemble_messages(llm_call_info),
        **llm_call_info.llm_kwargs
    )

    return _parse_llm_response(response, llm_call_info)
    

