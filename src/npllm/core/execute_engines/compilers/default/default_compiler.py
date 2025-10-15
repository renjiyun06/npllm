from importlib import resources
from typing import List, Any, Dict
import xml.etree.ElementTree as ET
from pathlib import Path
import re

import litellm
from litellm import acompletion, ModelResponse

from npllm.core.call_site import CallSite
from npllm.core.code_context_provider import CodeContextProvider
from npllm.core.llm_executor.compiler import Compiler, CompilationResult, SystemPromptTemplate, UserPromptTemplate
from npllm.utils.module_util import module_hash

import logging

logger = logging.getLogger(__name__)

litellm.callbacks = ["langsmith"]

def format(template, args: List[Any], kwargs: Dict[str, Any]) -> str:
    placeholders = re.findall(r"{{[^}]+}}", template)
    for original_placeholder in placeholders:
        placeholder = original_placeholder
        placeholder = placeholder.replace("{{", "").replace("}}", "")
        
        root_obj = None
        dot_chain = []
        if placeholder.startswith("arg"):
            placeholder = placeholder[len("arg"):]
            position_index = int(placeholder.split(".")[0])
            root_obj = args[position_index]
            dot_chain = placeholder.split(".")[1:]
        else:
            root_obj = kwargs[placeholder.split(".")[0]]
            dot_chain = placeholder.split(".")[1:]

        value = root_obj
        for field in dot_chain:
            value = getattr(value, field)

        formatted_value: List[str] = []
        if isinstance(value, list):
            for item in value:
                formatted_value.append(str(item))
        else:
            formatted_value.append(str(value))

        template = template.replace(original_placeholder, "\n".join(formatted_value))

    return template.strip()

class DefaultSystemPromptTemplate(SystemPromptTemplate):
    def __init__(self, node: ET.Element):
        self._node = node
    
    def format(self, default_output_json_schema: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
        role_and_context = self._node.find(DefaultCompilationResult.tag_role_and_context).text.strip()
        task_description = self._node.find(DefaultCompilationResult.tag_task_description).text.strip()
        guidelines = self._node.find(DefaultCompilationResult.tag_guidelines).text.strip()
        output = self._node.find(DefaultCompilationResult.tag_output)

        output_json_schema = None
        output_json_schema_node = output.find(DefaultCompilationResult.tag_output_json_schema)
        if output_json_schema_node is not None:
            output_json_schema = format(output_json_schema_node.text.strip(), args, kwargs)

        output_json_schema = output_json_schema or default_output_json_schema
        format_guidance = output.find(DefaultCompilationResult.tag_format_guidance).text.strip()
        return f"""
<role_and_context>
{role_and_context}
</role_and_context>
<task_description>
{task_description}
</task_description>
<guidelines>
{guidelines}
</guidelines>
<output>
<output_json_schema>
{output_json_schema}
</output_json_schema>
<format_guidance>
{format_guidance}
</format_guidance>
</output>
""".strip()
        

class DefaultUserPromptTemplate(UserPromptTemplate):
    def __init__(self, node: ET.Element):
        self._node = node

    def format(self, args: List[Any], kwargs: Dict[str, Any]) -> str:
        return format(self._node.text, args, kwargs)

class CompilationNotes:
    def __init__(self, node: ET.Element):
        self._node = node

class DefaultCompilationResult:
    tag_compilation_result = "compilation_result"
    tag_system_prompt = "system_prompt"
    tag_role_and_context = "role_and_context"
    tag_task_description = "task_description"
    tag_guidelines = "guidelines"
    tag_output = "output"
    tag_output_json_schema = "output_json_schema"
    tag_format_guidance = "format_guidance"
    tag_user_prompt_template = "user_prompt_template"
    tag_compilation_notes = "compilation_notes"

    @classmethod
    def from_llm_response(cls, response: ModelResponse, call_site: CallSite) -> 'DefaultCompilationResult':
        response_content = response.choices[0].message.content.strip()
        logger.debug(f"Raw response content from compile-time LLM: {response_content}")
        if response_content.startswith("```xml"):
            response_content = response_content[len("```xml"):-len("```")].strip()

        root = ET.fromstring(response_content)
        dependent_modules = call_site.dependent_modules
        dependent_modules_hash = {}
        for module_filename, dependent_module in dependent_modules.items():
            dependent_modules_hash[module_filename] = module_hash(dependent_module)
        return cls._parse(root, response_content, dependent_modules_hash)

    @classmethod
    def from_cache_file(cls, cache_file: Path) -> 'DefaultCompilationResult':
        with open(cache_file, "r", encoding='utf-8') as f:
            cache_content = f.read()
            splitter_index = cache_content.find("---\n")
            hash_content = cache_content[:splitter_index].strip()
            dependent_modules_hash = {}
            for line in hash_content.split("\n"):
                module_filename, module_hash = line.split(":")
                dependent_modules_hash[module_filename] = module_hash

            cache_content = cache_content[splitter_index + len("---\n"):]
            root = ET.fromstring(cache_content)
            return cls._parse(root, cache_content, dependent_modules_hash)

    @classmethod
    def _parse(cls, root: ET.Element, response_content: str, dependent_modules_hash: Dict[str, str]) -> 'DefaultCompilationResult':
        ET.indent(root, space="  ", level=0)
        system_prompt_node = root.find(cls.tag_system_prompt)
        system_prompt_template = DefaultSystemPromptTemplate(system_prompt_node)

        user_prompt_template_node = root.find(cls.tag_user_prompt_template)
        user_prompt_template = DefaultUserPromptTemplate(user_prompt_template_node)

        compilation_notes_node = root.find(cls.tag_compilation_notes)
        compilation_notes = CompilationNotes(compilation_notes_node)

        return cls(root, system_prompt_template, user_prompt_template, compilation_notes, response_content, dependent_modules_hash)

    def __init__(
        self,
        root: ET.Element,
        system_prompt_template: DefaultSystemPromptTemplate, 
        user_prompt_template: DefaultUserPromptTemplate, 
        compilation_notes: CompilationNotes,
        response_content: str,
        dependent_modules_hash: Dict[str, str]
    ):
        self.root = root
        self.system_prompt_template = system_prompt_template
        self.user_prompt_template = user_prompt_template
        self.compilation_notes = compilation_notes
        self.response_content = response_content
        self.dependent_modules_hash = dependent_modules_hash

class CompilationTask:
    def __init__(self, call_site: CallSite, code_context_provider: CodeContextProvider):
        self._call_site = call_site
        self._code_context_provider = code_context_provider

    def __str__(self) -> str:
        code_context = self._code_context_provider.get_code_context(self._call_site)
        positional_parameters = []
        keyword_parameters = []
        for arg_name, arg_type in self._call_site.positional_parameters + self._call_site.keyword_parameters:
            if isinstance(arg_name, int):
                positional_parameters.append(f"""<param position="{arg_name}" type="{arg_type}" />""")
            else:
                keyword_parameters.append(f"""<param name="{arg_name}" type="{arg_type}" />""")
        
        return f"""
<compile_task>
  <code_context>
{code_context.source}
  </code_context>

  <call_site>
    <location>
      <line_number>{code_context.call_site_line}</line_number>
      <method_name>{self._call_site.method_name}</method_name>
    </location>

    <parameter_spec>
      <positional>
{'\n'.join(positional_parameters)}
      </positional>
      <keyword>
{'\n'.join(keyword_parameters)}
      </keyword>
    </parameter_spec>
    
    <return_specification>
      <type>{self._call_site.return_type}</type>
      <json_schema>
{self._call_site.return_type.json_schema()}
      </json_schema>
    </return_specification>
  </call_site>
</compile_task>
""".strip()

class DefaultCompiler(Compiler):
    cache_dir = Path("~/.npllm/compilers/default/caches").expanduser()

    def __init__(self, model: str):
        self._model = model
        self._system_prompt_path = (
            resources.files('npllm.core.llm_executor.compilers.default') / 
            "system_prompt.md"
        )
        self._system_prompt = self._load_prompt()
        self._compilation_result_cache: Dict[CallSite, DefaultCompilationResult] = {}

    def _cache_filename(self, call_site: CallSite) -> str:
        return f"{call_site.module_filename.replace('/', '__SLASH__')}#{call_site.line_number}#{call_site.method_name}.xml"

    def _get_cache(self, call_site: CallSite) -> DefaultCompilationResult:
        if call_site in self._compilation_result_cache:
            return self._compilation_result_cache[call_site]
        
        cache_filename = self._cache_filename(call_site)
        cache_file = DefaultCompiler.cache_dir / cache_filename
        if cache_file.exists():
            compilation_result = DefaultCompilationResult.from_cache_file(cache_file)
            self._compilation_result_cache[call_site] = compilation_result
            return compilation_result
        
        return None

    def _save_cache(self, call_site: CallSite, compilation_result: DefaultCompilationResult):
        logger.info(f"Save compilation result to cache for {call_site}")
        self._compilation_result_cache[call_site] = compilation_result
        DefaultCompiler.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_filename = self._cache_filename(call_site)
        path = DefaultCompiler.cache_dir / cache_filename
        
        cache_file_content = ""
        dependent_modules = call_site.dependent_modules
        for module_filename, dependent_module in dependent_modules.items():
            cache_file_content += f"{module_filename}:{module_hash(dependent_module)}\n"
        
        cache_file_content += "---\n"
        cache_file_content += compilation_result.response_content
        with open(path, "w", encoding='utf-8') as f:
            f.write(cache_file_content)

    def _load_prompt(self):
        return self._system_prompt_path.read_text(encoding='utf-8')

    async def compile(self, call_site: CallSite, code_context_provider: CodeContextProvider) -> CompilationResult:
        compilation_result = self._get_cache(call_site)
        if compilation_result:
            dependent_modules = call_site.dependent_modules
            for module_filename, dependent_module in dependent_modules.items():
                cached_module_hash = compilation_result.dependent_modules_hash[module_filename]
                if cached_module_hash is None or cached_module_hash != module_hash(dependent_module):
                    logger.info(f"Dependent modules of {call_site} have been modified, need to recompile")
                    return await self._do_compile(call_site, code_context_provider)
            
            logger.info(f"No dependent modules have been modified, return cached compilation result for {call_site}")
            return compilation_result
        
        return await self._do_compile(call_site, code_context_provider)

    async def _do_compile(self, call_site: CallSite, code_context_provider: CodeContextProvider) -> CompilationResult:
        logger.info(f"Compile {call_site} with model {self._model}")
        task = CompilationTask(call_site, code_context_provider)
        logger.debug(f"Compilation task: {task}")
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": f"{task}"}
        ]

        try:
            response = await acompletion(
                model=self._model,
                messages=messages,
                metadata={
                    "run_name": "default-compiler-compile",
                    "project_name": "npllm"
                }
            )
            compilation_result = DefaultCompilationResult.from_llm_response(response, call_site)
            logger.info(f"Successfully compiled {call_site}")
            self._save_cache(call_site, compilation_result)
            return CompilationResult(
                system_prompt_template=compilation_result.system_prompt_template,
                user_prompt_template=compilation_result.user_prompt_template
            )
        except Exception as e:
            # TODO here we need a retry mechanism
            raise e